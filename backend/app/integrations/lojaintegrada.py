"""
Integração Loja Integrada - SiteCan PRO
Conecta lojas Loja Integrada via chave_api (loja) + chave_aplicacao (integrador),
lê produtos/categorias e atualiza SEO.

API oficial (v1, TastyPie): https://api.awsli.com.br/v1/
Doc: https://api-docs.lojaintegrada.com.br/ (blueprint Apiary da v1 confirmado)

Autenticação (formato exato confirmado na doc oficial):
    Authorization: chave_api {CHAVE_API} aplicacao {CHAVE_APLICACAO}

Particularidades confirmadas:
- SEO é um RECURSO SEPARADO (/v1/seo/{id}) com campos {title, keyword, description};
  produto e categoria apontam para ele via campo "seo" (resource URI). Produto sem
  SEO pode vir com "seo": "/api/v1/seo/None".
- GET /v1/produto/{id} SÓ retorna descricao_completa com ?descricao_completa=1.
- PUT /v1/produto/{id} exige o objeto COMPLETO ("é necessário enviar todos os
  campos do produto") — read-modify-write obrigatório. PUT de categoria e de SEO
  aceitam body parcial (exemplos oficiais).
- Paginação TastyPie: {"meta": {limit, offset, total_count, next, previous}, "objects": [...]}.
- Rate limits: 3000 req/min por aplicação (Err 533), 100 req/min por loja (Err 633),
  1200 req/min por IP (Err 133) — HTTP 429 ao exceder.
- Planos grátis da Loja Integrada NÃO têm acesso à API.
"""
import os
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

LOJAINTEGRADA_API_URL = "https://api.awsli.com.br/v1"
# Chave do INTEGRADOR (4SEO) — secret de ambiente, nunca vem do lojista.
LOJAINTEGRADA_APP_KEY = os.getenv("LOJAINTEGRADA_APP_KEY", "")

# Campos do produto que o fluxo de SEO pode alterar via PUT completo do produto
LI_PRODUTO_EDITABLE_FIELDS = ("nome", "descricao_completa", "apelido")
# Campos read-only/computados removidos do body no read-modify-write do produto
LI_PRODUTO_READONLY_FIELDS = (
    "resource_uri", "data_criacao", "data_modificacao", "url",
    "imagem_principal", "imagens", "filhos", "grades", "variacoes", "seo",
)

# Mapeamento optimization_type (padrão do produto 4SEO) -> destino na API LI
# destino "seo.<campo>" = recurso /v1/seo; destino "produto.<campo>" = PUT completo do produto
LI_PRODUCT_FIELD_MAP = {
    "name": "produto.nome",
    "description": "produto.descricao_completa",
    "handle": "produto.apelido",
    "seo_title": "seo.title",
    "seo_description": "seo.description",
    "tags": "seo.keyword",
    "keywords": "seo.keyword",
}
LI_CATEGORY_FIELD_MAP = {
    "category_name": "categoria.nome",
    "category_description": "categoria.descricao",
    "category_seo_title": "seo.title",
    "category_seo_description": "seo.description",
    "category_keywords": "seo.keyword",
    "category_tags": "seo.keyword",
}


class LojaIntegradaAuthError(Exception):
    """Credenciais Loja Integrada inválidas (401/403) — inclui lojas em plano grátis"""
    pass


class LojaIntegradaNotFoundError(Exception):
    """Produto/categoria não encontrado na Loja Integrada (404)"""
    pass


def _parse_resource_id(resource_uri: Optional[str]) -> Optional[int]:
    """Extrai o ID numérico de um resource_uri TastyPie (ex: '/api/v1/seo/123')."""
    if not resource_uri or not isinstance(resource_uri, str):
        return None
    tail = resource_uri.rstrip("/").split("/")[-1]
    try:
        return int(tail)
    except (TypeError, ValueError):
        return None  # cobre "/api/v1/seo/None"


class LojaIntegradaProduct(BaseModel):
    id: int
    name: str                                  # nome
    handle: Optional[str] = None               # apelido (slug)
    description: Optional[str] = None          # descricao_completa
    seo_title: Optional[str] = None            # /v1/seo -> title
    seo_description: Optional[str] = None      # /v1/seo -> description
    seo_keywords: Optional[str] = None         # /v1/seo -> keyword
    seo_id: Optional[int] = None
    url: Optional[str] = None
    images: List[Dict[str, Any]] = []
    brand: Optional[str] = None
    ativo: bool = True


class LojaIntegradaCategory(BaseModel):
    id: int
    name: str                                  # nome
    description: Optional[str] = None          # descricao
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    seo_id: Optional[int] = None
    parent_id: Optional[int] = None            # categoria_pai (resource URI)
    products_count: int = 0


class LojaIntegradaClient:
    """
    Cliente para a API v1 da Loja Integrada (TastyPie).

    - Base URL única: https://api.awsli.com.br/v1
    - Auth: header `Authorization: chave_api {X} aplicacao {Y}`
    - 429 -> backoff (limite de 100 req/min por loja é o mais apertado)
    """

    def __init__(self, chave_api: str, chave_aplicacao: Optional[str] = None):
        self.chave_api = chave_api.strip()
        self.chave_aplicacao = (chave_aplicacao or LOJAINTEGRADA_APP_KEY).strip()
        self.base_url = LOJAINTEGRADA_API_URL
        self.headers = {
            "Authorization": f"chave_api {self.chave_api} aplicacao {self.chave_aplicacao}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Identificador da loja para registros (a LI não expõe um id de loja simples;
        # usamos um hash curto da chave_api)
        self.store_key = hashlib.md5(self.chave_api.encode()).hexdigest()[:12]
        self.store_url: str = ""  # preenchido no primeiro get_produto (campo url)

        self._proposals: Dict[str, OptimizationProposal] = {}
        self._rollback_records: Dict[str, RollbackRecord] = {}
        # Um lock por (tipo, id) evita que duas chamadas concorrentes de
        # ensure_*_seo para o MESMO produto/categoria (ex.: duplo clique em
        # "Aplicar", ou duas abas) criem dois registros de SEO distintos —
        # sem lock, ambas veem "sem SEO ainda" e criam um cada, e uma das
        # alterações de SEO aplicadas pelo usuário é silenciosamente perdida.
        self._seo_locks: Dict[str, asyncio.Lock] = {}

    def _get_seo_lock(self, key: str) -> asyncio.Lock:
        # dict.setdefault é atômico no event loop single-threaded do asyncio
        # (não há ponto de await entre a checagem e a criação do lock).
        return self._seo_locks.setdefault(key, asyncio.Lock())

    def _generate_proposal_id(self) -> str:
        return hashlib.md5(f"{datetime.utcnow().isoformat()}{secrets.token_hex(4)}".encode()).hexdigest()[:8]

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Any:
        """Requisição à API da LI com retry/backoff em 429 (100 req/min por loja)."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"[LojaIntegrada API] {method} {url} params={params}")

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

            logger.debug(f"[LojaIntegrada API] Response status: {response.status_code}")

            if response.status_code == 429 and attempt < max_retries:
                delay = min(5.0 * (2.0 ** attempt), 60.0)
                attempt += 1
                logger.warning(f"[LojaIntegrada API] 429 rate limit — aguardando {delay}s (tentativa {attempt}/{max_retries})")
                await asyncio.sleep(delay)
                continue

            if response.status_code in (401, 403):
                raise LojaIntegradaAuthError(
                    "Credenciais Loja Integrada inválidas. Verifique a Chave de API da loja "
                    "(lembrando que planos grátis da Loja Integrada não têm acesso à API)."
                )
            if response.status_code == 404:
                raise LojaIntegradaNotFoundError(f"Recurso não encontrado na Loja Integrada: {endpoint}")
            if response.status_code >= 400:
                logger.error(f"[LojaIntegrada API] ERROR Response body: {response.text[:500]}")
                raise Exception(f"Erro API Loja Integrada ({response.status_code}): {response.text[:300]}")

            # PUT de SEO/categoria responde 202; DELETE 204
            if response.status_code in (202, 204) and not response.text:
                return {}
            try:
                return response.json() if response.text else {}
            except ValueError:
                return {}

    async def _list_paginated(self, endpoint: str, max_items: int, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Percorre listagem TastyPie seguindo meta.next até max_items."""
        items: List[Dict[str, Any]] = []
        offset = 0
        limit = 50
        while len(items) < max_items:
            page_params = {**(params or {}), "limit": limit, "offset": offset}
            response = await self._request("GET", endpoint, params=page_params)
            objects = (response or {}).get("objects", [])
            meta = (response or {}).get("meta", {}) or {}
            if not objects:
                break
            items.extend(objects)
            if not meta.get("next"):
                break
            # Respeita o limit efetivo aplicado pela API (pode ser menor que o pedido)
            effective = meta.get("limit") or limit
            offset += effective
        return items[:max_items]

    # ==================== CONEXÃO ====================

    async def test_connection(self) -> Dict[str, Any]:
        """Testa credenciais com uma listagem barata"""
        try:
            response = await self._request("GET", "/categoria/", params={"limit": 1})
            total = ((response or {}).get("meta") or {}).get("total_count", 0)
            return {"success": True, "connected": True, "categorias": total}
        except Exception as e:
            return {"success": False, "connected": False, "error": str(e)}

    # ==================== SEO (recurso separado) ====================

    async def get_seo(self, seo_id: int) -> Dict[str, Any]:
        """GET /v1/seo/{id} -> {title, keyword, description, base_uri, ...}"""
        return await self._request("GET", f"/seo/{seo_id}/")

    async def update_seo(self, seo_id: int, changes: Dict[str, str]) -> Dict[str, Any]:
        """PUT /v1/seo/{id} com body parcial {title?, keyword?, description?} (202)"""
        safe = {k: v for k, v in changes.items() if k in ("title", "keyword", "description")}
        if not safe:
            return {}
        return await self._request("PUT", f"/seo/{seo_id}/", data=safe)

    async def _resolve_seo(self, seo_uri: Optional[str]) -> tuple:
        """Resolve o resource URI de SEO -> (seo_id, dados). Tolerante a '/seo/None'."""
        seo_id = _parse_resource_id(seo_uri)
        if not seo_id:
            return None, {}
        try:
            data = await self.get_seo(seo_id)
            return seo_id, (data or {})
        except Exception as e:
            logger.warning(f"[LojaIntegrada] SEO {seo_id} não carregado: {e}")
            return seo_id, {}

    # ==================== PRODUTOS ====================

    def _parse_product(self, p: Dict[str, Any], seo: Dict[str, Any] = None, seo_id: Optional[int] = None) -> LojaIntegradaProduct:
        seo = seo or {}
        images = []
        principal = p.get("imagem_principal")
        if isinstance(principal, dict):
            src = principal.get("media") or principal.get("grande") or principal.get("url")
            if src:
                images.append({"id": principal.get("id"), "src": src, "alt": None})
        return LojaIntegradaProduct(
            id=int(p.get("id")),
            name=p.get("nome") or "",
            handle=p.get("apelido") or None,
            description=p.get("descricao_completa") or None,
            seo_title=seo.get("title") or None,
            seo_description=seo.get("description") or None,
            seo_keywords=seo.get("keyword") or None,
            seo_id=seo_id or _parse_resource_id(p.get("seo")),
            url=p.get("url") or None,
            images=images,
            ativo=bool(p.get("ativo", True)),
        )

    async def get_all_products(self, max_items: int = 500) -> List[LojaIntegradaProduct]:
        """Lista produtos (listagem não inclui descricao_completa nem dados de SEO)."""
        raw = await self._list_paginated("/produto/", max_items=max_items)
        products = []
        for p in raw:
            try:
                product = self._parse_product(p)
                if product.url and not self.store_url:
                    # Deriva a URL base da loja a partir da URL de um produto
                    parts = product.url.split("/")
                    if len(parts) >= 3:
                        self.store_url = "/".join(parts[:3])
                products.append(product)
            except Exception as e:
                logger.warning(f"[LojaIntegrada] Erro ao parsear produto id={p.get('id')}: {e}")
        return products

    async def get_produto_raw(self, product_id: int) -> Dict[str, Any]:
        """GET do produto completo — SEMPRE com descricao_completa=1 (senão o campo não vem
        e um PUT completo posterior apagaria a descrição)."""
        return await self._request("GET", f"/produto/{product_id}/", params={"descricao_completa": 1})

    async def get_product(self, product_id: int) -> LojaIntegradaProduct:
        """Obtém um produto com descrição completa + dados de SEO (recurso /seo)"""
        p = await self.get_produto_raw(product_id)
        seo_id, seo = await self._resolve_seo(p.get("seo"))
        return self._parse_product(p, seo=seo, seo_id=seo_id)

    async def update_produto_fields(self, product_id: int, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza campos do PRODUTO (nome/descricao_completa/apelido) com
        read-modify-write: GET completo (descricao_completa=1) -> merge -> PUT completo.
        A doc oficial exige "todos os campos" no PUT de produto.
        """
        raw = await self.get_produto_raw(product_id)
        if not raw or raw.get("id") is None:
            raise ValueError(f"Produto {product_id} não encontrado na Loja Integrada")

        safe_changes = {k: v for k, v in changes.items() if k in LI_PRODUTO_EDITABLE_FIELDS}
        if not safe_changes:
            return {"original": {}, "updated": False}

        original = {k: raw.get(k) for k in safe_changes}
        merged = {**raw, **safe_changes}
        # Remove campos read-only/computados (relacionais editáveis como
        # categorias/marca/pai são mantidos — o PUT exige o objeto completo)
        for readonly in LI_PRODUTO_READONLY_FIELDS:
            merged.pop(readonly, None)
        merged.pop("id", None)
        await self._request("PUT", f"/produto/{product_id}/", data=merged)
        return {"original": original, "updated": True}

    async def _create_seo(self, base_uri: str) -> Optional[int]:
        """Cria registro de SEO via POST /v1/seo/ (best-effort — criação não é
        documentada em detalhe na doc oficial)."""
        try:
            created = await self._request("POST", "/seo/", data={
                "base_uri": base_uri,
                "title": "", "keyword": "", "description": "",
            })
            return _parse_resource_id((created or {}).get("resource_uri")) or (created or {}).get("id")
        except Exception as e:
            logger.warning(f"[LojaIntegrada] Não foi possível criar SEO para {base_uri}: {e}")
            return None

    async def ensure_product_seo(self, product_id: int) -> Optional[int]:
        """Garante que o produto tem registro de SEO; retorna o seo_id (ou None).
        Serializado por produto para evitar criar 2 registros de SEO em
        chamadas concorrentes (ver _seo_locks)."""
        async with self._get_seo_lock(f"product:{product_id}"):
            p = await self.get_produto_raw(product_id)
            seo_id = _parse_resource_id(p.get("seo"))
            if seo_id:
                return seo_id
            return await self._create_seo(f"/api/v1/produto/{product_id}")

    async def ensure_category_seo(self, category_id: int) -> Optional[int]:
        """Garante que a categoria tem registro de SEO; retorna o seo_id (ou None).
        Serializado por categoria para evitar criar 2 registros de SEO em
        chamadas concorrentes (ver _seo_locks)."""
        async with self._get_seo_lock(f"category:{category_id}"):
            c = await self._request("GET", f"/categoria/{category_id}/")
            seo_id = _parse_resource_id(c.get("seo"))
            if seo_id:
                return seo_id
            return await self._create_seo(f"/api/v1/categoria/{category_id}")

    # ==================== CATEGORIAS ====================

    def _parse_category(self, c: Dict[str, Any], seo: Dict[str, Any] = None, seo_id: Optional[int] = None) -> LojaIntegradaCategory:
        seo = seo or {}
        return LojaIntegradaCategory(
            id=int(c.get("id")),
            name=c.get("nome") or "",
            description=c.get("descricao") or None,
            seo_title=seo.get("title") or None,
            seo_description=seo.get("description") or None,
            seo_keywords=seo.get("keyword") or None,
            seo_id=seo_id or _parse_resource_id(c.get("seo")),
            parent_id=_parse_resource_id(c.get("categoria_pai")),
        )

    async def get_all_categories(self, max_items: int = 100) -> List[LojaIntegradaCategory]:
        """Lista categorias (a listagem NÃO traz o campo seo — só o detalhe traz)."""
        raw = await self._list_paginated("/categoria/", max_items=max_items)
        categories = []
        for c in raw:
            try:
                categories.append(self._parse_category(c))
            except Exception as e:
                logger.warning(f"[LojaIntegrada] Erro ao parsear categoria id={c.get('id')}: {e}")
        return categories

    async def get_category(self, category_id: int) -> LojaIntegradaCategory:
        """Obtém uma categoria com dados de SEO (o detalhe inclui o resource URI de seo)"""
        c = await self._request("GET", f"/categoria/{category_id}/")
        seo_id, seo = await self._resolve_seo(c.get("seo"))
        return self._parse_category(c, seo=seo, seo_id=seo_id)

    async def update_categoria_fields(self, category_id: int, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza campos da CATEGORIA (PUT parcial aceito — exemplo oficial da doc)"""
        safe_changes = {k: v for k, v in changes.items() if k in ("nome", "descricao")}
        if not safe_changes:
            return {"original": {}, "updated": False}
        raw = await self._request("GET", f"/categoria/{category_id}/")
        original = {k: raw.get(k) for k in safe_changes}
        await self._request("PUT", f"/categoria/{category_id}/", data=safe_changes)
        return {"original": original, "updated": True}

    async def get_category_products(self, category_id: int, limit: int = 10) -> List[LojaIntegradaProduct]:
        """Produtos de uma categoria (filtro TastyPie por categoria)"""
        try:
            raw = await self._list_paginated("/produto/", max_items=limit, params={"categoria": category_id})
            return [self._parse_product(p) for p in raw]
        except Exception as e:
            logger.warning(f"[LojaIntegrada] Erro ao buscar produtos da categoria {category_id}: {e}")
            return []

    # ==================== PROPOSTAS (mesmo protocolo Nuvemshop) ====================

    def get_proposals(self, status: Optional[str] = None, content_type: Optional[str] = None) -> List[OptimizationProposal]:
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status.value == status]
        if content_type:
            proposals = [p for p in proposals if p.content_type == content_type]
        return proposals

    def approve_proposals(self, proposal_ids: List[str]) -> int:
        approved = 0
        for pid in proposal_ids:
            if pid in self._proposals:
                self._proposals[pid].status = OptimizationStatus.APPROVED
                self._proposals[pid].approved_at = datetime.utcnow().isoformat()
                approved += 1
        return approved

    def reject_proposals(self, proposal_ids: List[str]) -> int:
        rejected = 0
        for pid in proposal_ids:
            if pid in self._proposals:
                self._proposals[pid].status = OptimizationStatus.REJECTED
                rejected += 1
        return rejected

    def _resolve_target(self, content_type: str, optimization_type: Optional[str], field_name: str) -> Optional[str]:
        """Resolve optimization_type -> destino ('seo.title', 'produto.nome', 'categoria.nome', ...)"""
        ot = (optimization_type or "").strip() or (field_name or "").strip()
        if content_type == "product":
            return LI_PRODUCT_FIELD_MAP.get(ot)
        if content_type == "category":
            return LI_CATEGORY_FIELD_MAP.get(ot)
        return None

    async def _apply_group(
        self,
        content_type: str,
        content_id: int,
        proposals: List[OptimizationProposal],
    ) -> Dict[str, Any]:
        """Aplica um grupo de propostas de um produto/categoria (agrupa por destino).

        Registra rollback/status APPLIED em CADA fase assim que ela tem sucesso
        (não só no final) — se a fase de SEO falhar DEPOIS de a fase de
        entidade já ter escrito de verdade na loja (PUT real), a mudança de
        entidade continua rollback-ável e marcada como aplicada; sem isso, uma
        falha na 2ª fase deixava a 1ª mudança aplicada na loja real sem
        nenhum rollback record nem status correto (bug real, não hipotético)."""
        seo_changes: Dict[str, str] = {}
        entity_changes: Dict[str, Any] = {}
        entity_proposals: List[OptimizationProposal] = []
        seo_proposals: List[OptimizationProposal] = []
        for p in proposals:
            target = self._resolve_target(content_type, p.optimization_type, p.field_name)
            if not target:
                logger.warning(f"[LojaIntegrada] Campo desconhecido para apply: {content_type}/{p.optimization_type}")
                continue
            scope, field = target.split(".", 1)
            if scope == "seo":
                seo_changes[field] = p.proposed_value
                seo_proposals.append(p)
            else:
                entity_changes[field] = p.proposed_value
                entity_proposals.append(p)

        if not seo_changes and not entity_changes:
            return {"applied": 0, "rollback_records": []}

        applied = 0
        rollback_records: List[Dict[str, Any]] = []

        def _record_applied(scope_proposals: List[OptimizationProposal], originals: Dict[str, Any]) -> None:
            nonlocal applied
            for p in scope_proposals:
                target = self._resolve_target(content_type, p.optimization_type, p.field_name)
                _, field = target.split(".", 1)
                rollback = RollbackRecord(
                    id=self._generate_proposal_id(),
                    shop_url=self.store_key,
                    product_id=content_id,
                    field_name=p.field_name,
                    original_value=originals.get(field) if originals.get(field) is not None else p.original_value,
                    new_value=p.proposed_value,
                    applied_at=datetime.utcnow().isoformat(),
                    content_type=content_type,
                    optimization_type=p.optimization_type,
                )
                self._rollback_records[rollback.id] = rollback
                rollback_records.append(rollback.model_dump())
                p.status = OptimizationStatus.APPLIED
                p.applied_at = datetime.utcnow().isoformat()
                applied += 1

        # 1) Campos da entidade (produto: PUT completo; categoria: PUT parcial).
        # Registra rollback/APPLIED assim que o PUT tem sucesso — antes de
        # tentar a etapa de SEO abaixo.
        if entity_changes:
            if content_type == "product":
                result = await self.update_produto_fields(content_id, entity_changes)
            else:
                result = await self.update_categoria_fields(content_id, entity_changes)
            _record_applied(entity_proposals, result.get("original") or {})

        # 2) Campos de SEO (recurso /v1/seo). Se isto falhar, o rollback/status
        # da primeira etapa acima já foi persistido e não é perdido.
        if seo_changes:
            if content_type == "product":
                seo_id = await self.ensure_product_seo(content_id)
            else:
                seo_id = await self.ensure_category_seo(content_id)
            if seo_id:
                current = await self.get_seo(seo_id)
                seo_originals = {k: (current or {}).get(k) for k in seo_changes}
                await self.update_seo(seo_id, seo_changes)
                _record_applied(seo_proposals, seo_originals)
            else:
                raise ValueError(
                    "Não foi possível localizar/criar o registro de SEO na Loja Integrada para este item."
                )

        return {"applied": applied, "rollback_records": rollback_records}

    async def apply_approved_proposals(self, item_id: Optional[int] = None) -> Dict[str, Any]:
        """Aplica propostas aprovadas (em memória)"""
        approved = [p for p in self._proposals.values() if p.status == OptimizationStatus.APPROVED]
        if item_id:
            approved = [p for p in approved if p.product_id == item_id]

        by_content: Dict[tuple, List[OptimizationProposal]] = {}
        for p in approved:
            by_content.setdefault((p.content_type, p.product_id), []).append(p)

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
                logger.warning(f"[LojaIntegrada] Failed to parse proposal: {e}")

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
                logger.error(f"[LojaIntegrada] Error applying {content_type} proposals for {content_id}: {e}")
                errors.append(f"{content_type}:{content_id}: {str(e)}")

        result: Dict[str, Any] = {"applied": applied, "rollback_records": rollback_records}
        if errors:
            result["errors"] = errors
        return result

    # ==================== ROLLBACK ====================

    def get_rollback_records(self, content_type: Optional[str] = None) -> List[RollbackRecord]:
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

        target = self._resolve_target(content_type, optimization_type, field_name)
        if not target:
            raise ValueError(f"Campo desconhecido para rollback: {content_type}/{optimization_type or field_name}")

        scope, field = target.split(".", 1)
        if scope == "seo":
            if content_type == "product":
                seo_id = await self.ensure_product_seo(int(product_id))
            else:
                seo_id = await self.ensure_category_seo(int(product_id))
            if not seo_id:
                raise ValueError("Registro de SEO não encontrado para rollback")
            await self.update_seo(seo_id, {field: original_value or ""})
        elif content_type == "product":
            await self.update_produto_fields(int(product_id), {field: original_value})
        else:
            await self.update_categoria_fields(int(product_id), {field: original_value})

        rid = record.get("id")
        if rid and rid in self._rollback_records:
            self._rollback_records[rid].rolled_back = True
            self._rollback_records[rid].rolled_back_at = datetime.utcnow().isoformat()

        return {"rolled_back": 1, "message": f"Alteração revertida: {field}"}

    async def rollback_single(self, rollback_id: str) -> Dict[str, Any]:
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
        rolled_back = 0
        for record in list(self._rollback_records.values()):
            if not record.rolled_back:
                try:
                    await self.rollback_single(record.id)
                    rolled_back += 1
                except Exception:
                    pass
        return {"rolled_back": rolled_back, "message": f"{rolled_back} alteração(ões) revertida(s)"}


_lojaintegrada_clients: Dict[str, LojaIntegradaClient] = {}


def create_lojaintegrada_client(chave_api: str, chave_aplicacao: Optional[str] = None) -> LojaIntegradaClient:
    """Cria (ou recupera do cache) cliente Loja Integrada para uma loja"""
    key = hashlib.md5(chave_api.strip().encode()).hexdigest()[:12]
    if key in _lojaintegrada_clients:
        return _lojaintegrada_clients[key]
    client = LojaIntegradaClient(chave_api, chave_aplicacao)
    _lojaintegrada_clients[key] = client
    return client


def get_lojaintegrada_client(store_key: str) -> Optional[LojaIntegradaClient]:
    """Recupera cliente existente pelo store_key (hash curto da chave_api)"""
    return _lojaintegrada_clients.get(store_key)
