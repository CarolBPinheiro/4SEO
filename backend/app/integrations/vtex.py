"""
Integração VTEX - SiteCan PRO
Conecta lojas VTEX via App Key/App Token, lê produtos/categorias e atualiza SEO.

Catalog API: https://developers.vtex.com/docs/api-reference/catalog-api
Autenticação: https://developers.vtex.com/docs/guides/api-authentication-using-api-keys
Rate limits: https://developers.vtex.com/docs/guides/best-practices-for-avoiding-rate-limit-errors

IMPORTANTE (read-modify-write): o PUT de produto/categoria na VTEX substitui o
objeto inteiro. Toda atualização parcial DEVE fazer GET -> merge -> PUT do objeto
completo, preservando os campos não alterados (ver update_product_fields).
"""
import asyncio
import hashlib
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from pydantic import BaseModel
import logging

# Reutiliza o modelo de proposta existente (com transparencia) — não criar outro.
from app.integrations.nuvemshop import (
    OptimizationProposal,
    OptimizationStatus,
    RollbackRecord,
)

logger = logging.getLogger(__name__)

VTEX_DEFAULT_ENVIRONMENT = "vtexcommercestable"

# Campos de produto aceitos pelo PUT /api/catalog/pvt/product/{id}
# (shape idêntico ao retornado pelo GET — read-modify-write)
VTEX_PRODUCT_SEO_FIELDS = ("Name", "Title", "Description", "DescriptionShort", "MetaTagDescription", "KeyWords", "LinkId")
VTEX_CATEGORY_SEO_FIELDS = ("Name", "Title", "Description", "Keywords")

# Mapeamento optimization_type (padrão do produto 4SEO) -> campo da API VTEX
VTEX_PRODUCT_FIELD_MAP = {
    "name": "Name",
    "title": "Title",
    "seo_title": "Title",
    "description": "Description",
    "seo_description": "MetaTagDescription",
    "tags": "KeyWords",
    "keywords": "KeyWords",
    "handle": "LinkId",
    "link_id": "LinkId",
}
VTEX_CATEGORY_FIELD_MAP = {
    "category_name": "Name",
    "category_title": "Title",
    "category_seo_title": "Title",
    "category_description": "Description",
    "category_seo_description": "Description",
    "category_keywords": "Keywords",
    "category_tags": "Keywords",
}


class VtexAuthError(Exception):
    """Credenciais VTEX inválidas ou sem permissão (401/403)"""
    pass


class VtexNotFoundError(Exception):
    """Produto/categoria não encontrado na VTEX (404)"""
    pass


class VtexProduct(BaseModel):
    id: int
    name: str
    title: Optional[str] = None                 # Title = título SEO (<title>)
    link_id: Optional[str] = None               # LinkId = slug da URL
    description: Optional[str] = None
    description_short: Optional[str] = None
    seo_description: Optional[str] = None       # MetaTagDescription
    keywords: Optional[str] = None              # KeyWords (separadas por vírgula)
    brand: Optional[str] = None
    category_id: Optional[int] = None
    ref_id: Optional[str] = None
    is_active: bool = True
    is_visible: bool = True
    url: Optional[str] = None
    images: List[Dict[str, Any]] = []


class VtexCategory(BaseModel):
    id: int
    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    father_category_id: Optional[int] = None
    is_active: bool = True
    url: Optional[str] = None
    products_count: int = 0


class VtexClient:
    """
    Cliente para a Catalog API da VTEX.

    - Base URL por conta: https://{accountName}.{environment}.com.br
    - Headers: X-VTEX-API-AppKey / X-VTEX-API-AppToken
    - 429 -> respeita Retry-After com backoff exponencial
    """

    def __init__(
        self,
        account_name: str,
        app_key: str,
        app_token: str,
        environment: str = VTEX_DEFAULT_ENVIRONMENT,
    ):
        self.account_name = account_name.strip().lower().rstrip("/")
        self.app_key = app_key.strip()
        self.app_token = app_token.strip()
        self.environment = environment or VTEX_DEFAULT_ENVIRONMENT
        self.base_url = f"https://{self.account_name}.{self.environment}.com.br"
        self.store_url = self.base_url  # URL pública base (domínio custom não é conhecido via Catalog API)
        self.headers = {
            "X-VTEX-API-AppKey": self.app_key,
            "X-VTEX-API-AppToken": self.app_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Armazenamento local de propostas e rollbacks (mesmo padrão Nuvemshop/Shopify)
        self._proposals: Dict[str, OptimizationProposal] = {}
        self._rollback_records: Dict[str, RollbackRecord] = {}

    def _generate_proposal_id(self) -> str:
        """Gera ID único para proposta"""
        return hashlib.md5(f"{datetime.utcnow().isoformat()}{secrets.token_hex(4)}".encode()).hexdigest()[:8]

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Any:
        """Faz requisição à API da VTEX com retry/backoff em 429 (Retry-After)."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"[VTEX API] {method} {url} params={params}")

        attempt = 0
        while True:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=self.headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=data, params=params)
                elif method == "PUT":
                    response = await client.put(url, headers=self.headers, json=data, params=params)
                elif method == "DELETE":
                    response = await client.delete(url, headers=self.headers, params=params)
                else:
                    raise ValueError(f"Método não suportado: {method}")

            logger.debug(f"[VTEX API] Response status: {response.status_code}")

            # Rate limit: 429 + Retry-After (boas práticas oficiais VTEX)
            if response.status_code == 429 and attempt < max_retries:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 2.0 ** attempt
                except (TypeError, ValueError):
                    delay = 2.0 ** attempt
                delay = min(delay, 30.0)
                attempt += 1
                logger.warning(f"[VTEX API] 429 rate limit — aguardando {delay}s (tentativa {attempt}/{max_retries})")
                await asyncio.sleep(delay)
                continue

            if response.status_code in (401, 403):
                raise VtexAuthError(
                    "Credenciais VTEX inválidas ou sem permissão de Catálogo. "
                    "Verifique App Key/App Token e as roles no License Manager."
                )
            if response.status_code == 404:
                raise VtexNotFoundError(f"Recurso não encontrado na VTEX: {endpoint}")
            if response.status_code >= 400:
                logger.error(f"[VTEX API] ERROR Response body: {response.text[:500]}")
                raise Exception(f"Erro API VTEX ({response.status_code}): {response.text[:300]}")

            if response.status_code == 204 or not response.text:
                return {}
            try:
                return response.json()
            except ValueError:
                return {}

    # ==================== CONEXÃO ====================

    async def test_connection(self) -> Dict[str, Any]:
        """Testa credenciais com uma chamada barata à Catalog API"""
        try:
            await self._request(
                "GET",
                "/api/catalog_system/pvt/products/GetProductAndSkuIds",
                params={"_from": 1, "_to": 1},
            )
            return {
                "success": True,
                "connected": True,
                "account": self.account_name,
                "store_url": self.store_url,
            }
        except Exception as e:
            return {"success": False, "connected": False, "error": str(e)}

    # ==================== PRODUTOS ====================

    def _parse_search_product(self, p: Dict[str, Any]) -> VtexProduct:
        """Parseia item da busca pública (catalog_system/pub/products/search)"""
        link_text = p.get("linkText") or ""
        images = []
        for item in (p.get("items") or [])[:1]:
            for img in item.get("images", []) or []:
                images.append({"id": img.get("imageId"), "src": img.get("imageUrl"), "alt": img.get("imageText")})
        return VtexProduct(
            id=int(p.get("productId")),
            name=p.get("productName") or "",
            title=p.get("productTitle") or None,
            link_id=link_text or None,
            description=p.get("description") or None,
            seo_description=p.get("metaTagDescription") or None,
            brand=p.get("brand") or None,
            url=f"{self.store_url}/{link_text}/p" if link_text else None,
            images=images,
        )

    async def get_products(self, limit: int = 50, offset: int = 0) -> List[VtexProduct]:
        """
        Lista produtos via busca pública (1 chamada por página de até 50).
        Obs.: a busca pública retorna apenas produtos ativos/visíveis.
        """
        _from = offset
        _to = offset + min(limit, 50) - 1
        response = await self._request(
            "GET",
            "/api/catalog_system/pub/products/search",
            params={"_from": _from, "_to": _to},
        )
        products = []
        for p in (response or []):
            try:
                products.append(self._parse_search_product(p))
            except Exception as e:
                logger.warning(f"[VTEX] Erro ao parsear produto {p.get('productId')}: {e}")
        return products

    async def get_all_products(self, max_items: int = 500) -> List[VtexProduct]:
        """Lista produtos com paginação automática (busca pública, blocos de 50)."""
        all_products: List[VtexProduct] = []
        offset = 0
        per_page = 50
        while len(all_products) < max_items:
            try:
                batch = await self.get_products(limit=per_page, offset=offset)
            except Exception as e:
                # VTEX retorna 206 (partial) normalmente; erro real encerra a paginação
                logger.error(f"[VTEX] Erro ao paginar produtos (offset={offset}): {e}")
                break
            if not batch:
                break
            all_products.extend(batch)
            if len(batch) < per_page:
                break
            offset += per_page
        return all_products[:max_items]

    async def get_product_raw(self, product_id: int) -> Dict[str, Any]:
        """GET do objeto completo do produto (shape aceito pelo PUT)"""
        return await self._request("GET", f"/api/catalog/pvt/product/{product_id}")

    async def get_product(self, product_id: int) -> VtexProduct:
        """Obtém um produto específico (Catalog pvt — inclui campos SEO completos)"""
        p = await self.get_product_raw(product_id)
        link_id = p.get("LinkId") or ""
        return VtexProduct(
            id=int(p.get("Id")),
            name=p.get("Name") or "",
            title=p.get("Title") or None,
            link_id=link_id or None,
            description=p.get("Description") or None,
            description_short=p.get("DescriptionShort") or None,
            seo_description=p.get("MetaTagDescription") or None,
            keywords=p.get("KeyWords") or None,
            category_id=p.get("CategoryId"),
            ref_id=p.get("RefId") or None,
            is_active=bool(p.get("IsActive", True)),
            is_visible=bool(p.get("IsVisible", True)),
            url=f"{self.store_url}/{link_id}/p" if link_id else None,
        )

    async def update_product_fields(self, product_id: int, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza campos do produto com read-modify-write:
        GET objeto completo -> merge dos campos alterados -> PUT objeto completo.
        Retorna {original: {campo: valor_anterior}, updated: bool}.
        """
        raw = await self.get_product_raw(product_id)
        if not raw or raw.get("Id") is None:
            raise ValueError(f"Produto {product_id} não encontrado na VTEX")

        # Apenas campos de SEO são permitidos neste fluxo (proteção contra corrupção)
        safe_changes = {k: v for k, v in changes.items() if k in VTEX_PRODUCT_SEO_FIELDS}
        if not safe_changes:
            return {"original": {}, "updated": False}

        original = {k: raw.get(k) for k in safe_changes}
        merged = {**raw, **safe_changes}
        # O Id vai no path do PUT; removido do body por segurança
        merged.pop("Id", None)
        await self._request("PUT", f"/api/catalog/pvt/product/{product_id}", data=merged)
        return {"original": original, "updated": True}

    # ==================== CATEGORIAS ====================

    async def get_category_tree(self, levels: int = 3) -> List[Dict[str, Any]]:
        """Árvore de categorias (endpoint público)"""
        return await self._request("GET", f"/api/catalog_system/pub/category/tree/{levels}") or []

    async def get_all_categories(self, max_items: int = 100) -> List[VtexCategory]:
        """Lista categorias achatando a árvore pública"""
        tree = await self.get_category_tree(levels=3)
        flat: List[VtexCategory] = []

        def _walk(nodes: List[Dict[str, Any]], parent_id: Optional[int] = None):
            for node in nodes or []:
                if len(flat) >= max_items:
                    return
                try:
                    flat.append(VtexCategory(
                        id=int(node.get("id")),
                        name=node.get("name") or "",
                        title=node.get("Title") or None,
                        father_category_id=parent_id,
                        url=node.get("url") or None,
                    ))
                except Exception as e:
                    logger.warning(f"[VTEX] Erro ao parsear categoria {node.get('id')}: {e}")
                _walk(node.get("children") or [], node.get("id"))

        _walk(tree)
        return flat[:max_items]

    async def get_category_raw(self, category_id: int) -> Dict[str, Any]:
        """GET do objeto completo da categoria (shape aceito pelo PUT)"""
        return await self._request("GET", f"/api/catalog/pvt/category/{category_id}")

    async def get_category(self, category_id: int) -> VtexCategory:
        """Obtém uma categoria específica (inclui campos SEO)"""
        c = await self.get_category_raw(category_id)
        return VtexCategory(
            id=int(c.get("Id")),
            name=c.get("Name") or "",
            title=c.get("Title") or None,
            description=c.get("Description") or None,
            keywords=c.get("Keywords") or None,
            father_category_id=c.get("FatherCategoryId"),
            is_active=bool(c.get("IsActive", True)),
        )

    async def update_category_fields(self, category_id: int, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza campos da categoria com read-modify-write (GET -> merge -> PUT)"""
        raw = await self.get_category_raw(category_id)
        if not raw or raw.get("Id") is None:
            raise ValueError(f"Categoria {category_id} não encontrada na VTEX")

        safe_changes = {k: v for k, v in changes.items() if k in VTEX_CATEGORY_SEO_FIELDS}
        if not safe_changes:
            return {"original": {}, "updated": False}

        original = {k: raw.get(k) for k in safe_changes}
        merged = {**raw, **safe_changes}
        # O GET de categoria retorna campos read-only que NÃO devem ir no PUT
        # (confirmado no OpenAPI oficial da Catalog API)
        for readonly in ("Id", "LinkId", "HasChildren", "TreePath", "TreePathIds", "TreePathLinkIds"):
            merged.pop(readonly, None)
        await self._request("PUT", f"/api/catalog/pvt/category/{category_id}", data=merged)
        return {"original": original, "updated": True}

    async def get_category_products(self, category_id: int, limit: int = 10) -> List[VtexProduct]:
        """Produtos de uma categoria (busca pública com filtro fq)"""
        try:
            response = await self._request(
                "GET",
                "/api/catalog_system/pub/products/search",
                params={"fq": f"C:{category_id}", "_from": 0, "_to": max(0, min(limit, 50) - 1)},
            )
            return [self._parse_search_product(p) for p in (response or [])]
        except Exception as e:
            logger.warning(f"[VTEX] Erro ao buscar produtos da categoria {category_id}: {e}")
            return []

    # ==================== PROPOSTAS (mesmo protocolo Nuvemshop) ====================

    def get_proposals(self, status: Optional[str] = None, content_type: Optional[str] = None) -> List[OptimizationProposal]:
        """Lista propostas com filtros opcionais"""
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status.value == status]
        if content_type:
            proposals = [p for p in proposals if p.content_type == content_type]
        return proposals

    def approve_proposals(self, proposal_ids: List[str]) -> int:
        """Aprova propostas selecionadas"""
        approved = 0
        for pid in proposal_ids:
            if pid in self._proposals:
                self._proposals[pid].status = OptimizationStatus.APPROVED
                self._proposals[pid].approved_at = datetime.utcnow().isoformat()
                approved += 1
        return approved

    def reject_proposals(self, proposal_ids: List[str]) -> int:
        """Rejeita propostas selecionadas"""
        rejected = 0
        for pid in proposal_ids:
            if pid in self._proposals:
                self._proposals[pid].status = OptimizationStatus.REJECTED
                rejected += 1
        return rejected

    def _resolve_api_field(self, content_type: str, optimization_type: Optional[str], field_name: str) -> Optional[str]:
        """Resolve optimization_type/field_name para o campo da API VTEX"""
        ot = (optimization_type or "").strip() or (field_name or "").strip()
        if content_type == "product":
            return VTEX_PRODUCT_FIELD_MAP.get(ot)
        if content_type == "category":
            return VTEX_CATEGORY_FIELD_MAP.get(ot)
        return None

    async def _apply_group(
        self,
        content_type: str,
        content_id: int,
        proposals: List[OptimizationProposal],
    ) -> Dict[str, Any]:
        """Aplica um grupo de propostas (produto OU categoria) num único read-modify-write"""
        changes: Dict[str, Any] = {}
        for p in proposals:
            api_field = self._resolve_api_field(content_type, p.optimization_type, p.field_name)
            if not api_field:
                logger.warning(f"[VTEX] Campo desconhecido para apply: {content_type}/{p.optimization_type}")
                continue
            changes[api_field] = p.proposed_value

        if not changes:
            return {"applied": 0, "rollback_records": []}

        if content_type == "product":
            result = await self.update_product_fields(content_id, changes)
        else:
            result = await self.update_category_fields(content_id, changes)

        originals = result.get("original", {})
        applied = 0
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            api_field = self._resolve_api_field(content_type, p.optimization_type, p.field_name)
            if not api_field or api_field not in changes:
                continue
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.account_name,
                product_id=content_id,
                field_name=p.field_name,
                original_value=originals.get(api_field) if originals.get(api_field) is not None else p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                content_type=content_type,
                optimization_type=p.optimization_type,
            )
            self._rollback_records[rollback.id] = rollback
            record_dict = rollback.model_dump()
            rollback_records.append(record_dict)

            p.status = OptimizationStatus.APPLIED
            p.applied_at = datetime.utcnow().isoformat()
            applied += 1

        return {"applied": applied, "rollback_records": rollback_records}

    async def apply_approved_proposals(self, item_id: Optional[int] = None) -> Dict[str, Any]:
        """Aplica propostas aprovadas (em memória)"""
        approved = [p for p in self._proposals.values() if p.status == OptimizationStatus.APPROVED]
        if item_id:
            approved = [p for p in approved if p.product_id == item_id]

        by_content: Dict[tuple, List[OptimizationProposal]] = {}
        for p in approved:
            key = (p.content_type, p.product_id)
            by_content.setdefault(key, []).append(p)

        applied = 0
        rollback_records: List[Dict[str, Any]] = []
        for (content_type, content_id), group in by_content.items():
            if content_type not in ("product", "category"):
                continue
            result = await self._apply_group(content_type, content_id, group)
            applied += result.get("applied", 0)
            rollback_records.extend(result.get("rollback_records", []))

        return {"applied": applied, "rollback_records": rollback_records}

    async def apply_proposals_direct(self, proposals_data: List[Dict]) -> Dict[str, Any]:
        """Aplica propostas enviadas pelo frontend (stateless — sobrevive a cold starts)"""
        proposals = []
        for p_data in proposals_data:
            try:
                proposals.append(OptimizationProposal(
                    id=p_data.get("id", self._generate_proposal_id()),
                    product_id=p_data["product_id"],
                    optimization_type=p_data.get("optimization_type", p_data.get("field_name", "")),
                    field_name=p_data.get("field_name", p_data.get("optimization_type", "")),
                    original_value=p_data.get("original_value"),
                    proposed_value=p_data["proposed_value"],
                    reasoning=p_data.get("reasoning", ""),
                    status=OptimizationStatus.APPROVED,
                    created_at=p_data.get("created_at", datetime.utcnow().isoformat()),
                    content_type=p_data.get("content_type", "product"),
                ))
            except Exception as e:
                logger.warning(f"[VTEX] Failed to parse proposal: {e}")

        if not proposals:
            return {"applied": 0, "error": "No valid proposals to apply"}

        by_content: Dict[tuple, List[OptimizationProposal]] = {}
        for p in proposals:
            by_content.setdefault((p.content_type, p.product_id), []).append(p)

        applied = 0
        errors = []
        rollback_records: List[Dict[str, Any]] = []
        for (content_type, content_id), group in by_content.items():
            if content_type not in ("product", "category"):
                continue
            try:
                result = await self._apply_group(content_type, content_id, group)
                applied += result.get("applied", 0)
                rollback_records.extend(result.get("rollback_records", []))
            except Exception as e:
                logger.error(f"[VTEX] Error applying {content_type} proposals for {content_id}: {e}")
                errors.append(f"{content_type}:{content_id}: {str(e)}")

        result: Dict[str, Any] = {"applied": applied, "rollback_records": rollback_records}
        if errors:
            result["errors"] = errors
        return result

    # ==================== ROLLBACK ====================

    def get_rollback_records(self, content_type: Optional[str] = None) -> List[RollbackRecord]:
        """Lista registros de rollback pendentes"""
        records = list(self._rollback_records.values())
        if content_type:
            records = [r for r in records if r.content_type == content_type]
        return [r for r in records if not r.rolled_back]

    async def rollback_direct(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Reverte uma alteração a partir dos dados do frontend (stateless)"""
        content_type = record.get("content_type", "product")
        product_id = record.get("product_id")
        original_value = record.get("original_value")
        optimization_type = record.get("optimization_type")
        field_name = record.get("field_name", "")

        if product_id is None:
            raise ValueError("product_id é obrigatório no registro de rollback")

        api_field = self._resolve_api_field(content_type, optimization_type, field_name)
        if not api_field:
            raise ValueError(f"Campo desconhecido para rollback: {content_type}/{optimization_type or field_name}")

        if content_type == "product":
            await self.update_product_fields(int(product_id), {api_field: original_value})
        elif content_type == "category":
            await self.update_category_fields(int(product_id), {api_field: original_value})
        else:
            raise ValueError(f"Tipo de conteúdo não suportado: {content_type}")

        rid = record.get("id")
        if rid and rid in self._rollback_records:
            self._rollback_records[rid].rolled_back = True
            self._rollback_records[rid].rolled_back_at = datetime.utcnow().isoformat()

        return {"rolled_back": 1, "message": f"Alteração revertida: {api_field}"}

    async def rollback_single(self, rollback_id: str) -> Dict[str, Any]:
        """Reverte uma única alteração (registro em memória)"""
        if rollback_id not in self._rollback_records:
            raise ValueError(f"Rollback {rollback_id} não encontrado")
        record = self._rollback_records[rollback_id]
        if record.rolled_back:
            raise ValueError("Esta alteração já foi revertida")

        return await self.rollback_direct({
            "id": record.id,
            "content_type": record.content_type,
            "product_id": record.product_id,
            "field_name": record.field_name,
            "optimization_type": record.optimization_type,
            "original_value": record.original_value,
        })

    async def rollback_all(self) -> Dict[str, Any]:
        """Reverte todas as alterações pendentes"""
        rolled_back = 0
        for record in list(self._rollback_records.values()):
            if not record.rolled_back:
                try:
                    await self.rollback_single(record.id)
                    rolled_back += 1
                except Exception:
                    pass
        return {"rolled_back": rolled_back, "message": f"{rolled_back} alteração(ões) revertida(s)"}


_vtex_clients: Dict[str, VtexClient] = {}


def create_vtex_client(
    account_name: str,
    app_key: str,
    app_token: str,
    environment: str = VTEX_DEFAULT_ENVIRONMENT,
) -> VtexClient:
    """Cria (ou recupera do cache) cliente VTEX para uma conta"""
    key = account_name.strip().lower()
    if key in _vtex_clients:
        return _vtex_clients[key]
    client = VtexClient(account_name, app_key, app_token, environment)
    _vtex_clients[key] = client
    return client


def get_vtex_client(account_name: str) -> Optional[VtexClient]:
    """Recupera cliente existente para uma conta"""
    return _vtex_clients.get(account_name.strip().lower())
