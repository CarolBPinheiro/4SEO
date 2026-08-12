"""
Integração Shopify - SiteCan MVP
Permite conectar lojas Shopify, ler produtos e atualizar SEO
Com suporte a rollback completo e validação de usuário
"""
import os
import re
import hmac
import hashlib
import secrets
import httpx
import json
import base64
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
from pydantic import BaseModel
from datetime import datetime, timezone
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Configurações
SHOPIFY_API_VERSION = "2024-01"

# Credenciais do app 4SEO no Shopify Partners / Dev Dashboard (OAuth)
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "").strip()
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "").strip()

# write_* inclui read_*. Produtos/coleções + páginas/blog.
# Docs: https://shopify.dev/docs/api/usage/access-scopes
SHOPIFY_OAUTH_SCOPES = os.getenv(
    "SHOPIFY_OAUTH_SCOPES",
    "write_products,write_content",
).strip()

_SHOP_DOMAIN_RE = re.compile(
    r"^(?:https?://)?([a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com)/?$"
)
_SHOP_HANDLE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]{0,60}$")

# States OAuth em memória (espelha Nuvemshop; persistência em oauth_states no banco)
_shopify_oauth_states: Dict[str, Dict[str, Any]] = {}


def _require_shopify_oauth_config() -> None:
    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        raise ValueError(
            "Configure SHOPIFY_API_KEY e SHOPIFY_API_SECRET no backend/.env "
            "(Shopify Partners → app 4SEO → Client ID / Client secret)."
        )


def normalize_shop_domain(shop: str) -> str:
    """
    Normaliza entrada do lojista para o domínio *.myshopify.com.
    Aceita: 'minha-loja', 'minha-loja.myshopify.com', 'https://minha-loja.myshopify.com'.
    """
    raw = (shop or "").strip().lower()
    if not raw:
        raise ValueError("Informe o domínio da loja Shopify.")

    raw = raw.replace("https://", "").replace("http://", "").strip("/")

    full_match = _SHOP_DOMAIN_RE.match(raw)
    if full_match:
        return full_match.group(1)

    handle = raw.replace(".myshopify.com", "").strip("/")
    if "." in handle or "/" in handle or not _SHOP_HANDLE_RE.match(handle):
        raise ValueError(
            "Domínio inválido. Use o nome da loja (ex.: minha-loja) ou minha-loja.myshopify.com."
        )
    return f"{handle}.myshopify.com"


class ShopifyOAuth:
    """OAuth 2.0 authorization code grant (offline access token) para o app 4SEO."""

    @staticmethod
    def generate_auth_url(shop: str, redirect_uri: str) -> Dict[str, str]:
        _require_shopify_oauth_config()
        shop_domain = normalize_shop_domain(shop)
        state = secrets.token_urlsafe(32)

        _shopify_oauth_states[state] = {
            "shop": shop_domain,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        params = {
            "client_id": SHOPIFY_API_KEY,
            "scope": SHOPIFY_OAUTH_SCOPES,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        auth_url = f"https://{shop_domain}/admin/oauth/authorize?{urlencode(params)}"
        return {
            "auth_url": auth_url,
            "state": state,
            "shop": shop_domain,
        }

    @staticmethod
    def verify_hmac(query_params: Dict[str, str]) -> bool:
        """
        Valida o parâmetro hmac do callback OAuth da Shopify.
        Docs: https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/authorization-code-grant
        """
        _require_shopify_oauth_config()
        hmac_value = query_params.get("hmac")
        if not hmac_value:
            return False

        message_parts = []
        for key in sorted(query_params.keys()):
            if key == "hmac":
                continue
            message_parts.append(f"{key}={query_params[key]}")
        message = "&".join(message_parts)

        digest = hmac.new(
            SHOPIFY_API_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, hmac_value)

    @staticmethod
    async def exchange_code(shop: str, code: str, state: str) -> Dict[str, Any]:
        _require_shopify_oauth_config()
        shop_domain = normalize_shop_domain(shop)

        state_data = _shopify_oauth_states.pop(state, None) if state else None
        if state_data and state_data.get("shop") and state_data["shop"] != shop_domain:
            raise ValueError("O domínio da loja no callback não confere com o state OAuth.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://{shop_domain}/admin/oauth/access_token",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "client_id": SHOPIFY_API_KEY,
                    "client_secret": SHOPIFY_API_SECRET,
                    "code": code,
                },
            )

        if response.status_code != 200:
            logger.error(
                "[Shopify OAuth] Falha ao trocar code: status=%s body=%s",
                response.status_code,
                (response.text or "")[:300],
            )
            raise ValueError("Erro ao obter token OAuth da Shopify")

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ValueError("Resposta OAuth da Shopify sem access_token")

        return {
            "success": True,
            "shop": shop_domain,
            "access_token": access_token,
            "scope": data.get("scope", ""),
            "token_type": "offline",
        }


class OptimizationStatus(str, Enum):
    PENDING = "pending"           # Aguardando aprovação do usuário
    APPROVED = "approved"         # Aprovado, pronto para aplicar
    APPLIED = "applied"           # Aplicado na loja
    REJECTED = "rejected"         # Rejeitado pelo usuário
    ROLLED_BACK = "rolled_back"   # Revertido ao estado original


class ShopifyProduct(BaseModel):
    id: int
    title: str
    handle: str
    body_html: Optional[str] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: Optional[str] = None  # Tags do produto separadas por vírgula
    # SEO fields
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    url: Optional[str] = None
    # Image data
    images: Optional[List[Dict[str, Any]]] = None
    image_alt_texts: Optional[Dict[int, str]] = None


class ShopifyCollection(BaseModel):
    """Coleção/Categoria do Shopify"""
    id: int
    title: str
    handle: str
    body_html: Optional[str] = None
    # SEO fields
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    url: Optional[str] = None
    # Image
    image: Optional[Dict[str, Any]] = None
    products_count: Optional[int] = None
    collection_type: str = "custom"  # 'custom' ou 'smart'


class ShopifyPage(BaseModel):
    """Página institucional do Shopify"""
    id: int
    title: str
    handle: str
    body_html: Optional[str] = None
    # SEO fields
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    url: Optional[str] = None
    published: bool = True
    template_suffix: Optional[str] = None


class ShopifyBlog(BaseModel):
    """Blog do Shopify"""
    id: int
    title: str
    handle: str


class ShopifyArticle(BaseModel):
    """Artigo de blog do Shopify"""
    id: int
    blog_id: int
    title: str
    handle: str
    body_html: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[str] = None
    # SEO fields
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    url: Optional[str] = None
    # Image
    image: Optional[Dict[str, Any]] = None
    published: bool = True
    published_at: Optional[str] = None


class ShopifyImage(BaseModel):
    id: int
    product_id: int
    src: str
    alt: Optional[str] = None
    position: int = 1


class OptimizationProposal(BaseModel):
    """Proposta de otimização que requer aprovação do usuário"""
    id: str
    product_id: int
    optimization_type: str  # 'title', 'description', 'seo_title', 'seo_description', 'image_alt'
    field_name: str
    original_value: Optional[str] = None
    proposed_value: str
    reasoning: str
    status: OptimizationStatus = OptimizationStatus.PENDING
    created_at: str = None
    applied_at: Optional[str] = None
    image_id: Optional[int] = None  # Para otimizações de alt text
    content_type: str = "product"  # 'product', 'collection', 'page', 'article'
    # Prioritização e contexto competitivo
    priority: Optional[str] = None        # 'high', 'medium', 'low'
    impact: Optional[str] = None          # 'ranking', 'ctr', 'conversao', 'visibilidade'
    effort: Optional[str] = None          # 'low', 'medium', 'high'
    target_keyword: Optional[str] = None  # Keyword alvo da otimização
    # Feedback loop  - métricas pré-apply (snapshot no momento da criação)
    pre_metrics: Optional[Dict[str, Any]] = None  # {clicks, impressions, ctr, position}
    # Transparência da IA (validação pós-geração: atributos + cobertura semântica)
    transparencia: Optional[Dict[str, Any]] = None


class RollbackRecord(BaseModel):
    """Registro para permitir rollback completo"""
    id: str
    shop_url: str
    product_id: int
    field_name: str
    original_value: Optional[str]
    new_value: str
    applied_at: str
    rolled_back: bool = False
    rolled_back_at: Optional[str] = None
    image_id: Optional[int] = None
    content_type: str = "product"  # 'product', 'collection', 'page', 'article'
    blog_id: Optional[int] = None  # usado quando content_type == 'article'


class ShopifyClient:
    """
    Cliente para API do Shopify com suporte a:
    - Validação de usuário antes de aplicar mudanças
    - Rollback completo
    - Análise de imagens com LLM
    """
    
    def __init__(
        self, 
        shop_url: str, 
        api_key: str = None,
        api_secret: str = None,
        access_token: str = None
    ):
        """
        Args:
            shop_url: URL da loja (ex: minha-loja.myshopify.com)
            api_key: Chave de API (para autenticação básica)
            api_secret: Chave secreta da API
            access_token: Token de acesso (Admin API access token)
        """
        self.shop_url = shop_url.replace("https://", "").replace("http://", "").rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.base_url = f"https://{self.shop_url}/admin/api/{SHOPIFY_API_VERSION}"
        
        # Headers dependendo do tipo de autenticação
        if access_token:
            self.headers = {
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            }
            self.auth = None
        else:
            # Autenticação básica com API Key + Secret
            self.headers = {
                "Content-Type": "application/json",
            }
            self.auth = (api_key, api_secret) if api_key and api_secret else None
        
        # Armazenamento local de propostas e rollbacks (em produção, usar banco de dados)
        self._proposals: Dict[str, OptimizationProposal] = {}
        self._rollback_records: Dict[str, RollbackRecord] = {}
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Dict = None,
        params: Dict = None
    ) -> Dict[str, Any]:
        """Executa requisição à API do Shopify"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.base_url}{endpoint}"
            
            kwargs = {
                "method": method,
                "url": url,
                "headers": self.headers,
            }
            
            if self.auth:
                kwargs["auth"] = self.auth
            if data:
                kwargs["json"] = data
            if params:
                kwargs["params"] = params
            
            r = await client.request(**kwargs)
            
            if r.status_code >= 400:
                error_detail = r.text
                try:
                    error_json = r.json()
                    if "errors" in error_json:
                        error_detail = json.dumps(error_json["errors"])
                except:
                    pass
                raise Exception(f"Shopify API Error ({r.status_code}): {error_detail}")
            
            if r.text:
                return r.json()
            return {}
    
    async def test_connection(self) -> Dict[str, Any]:
        """Testa a conexão com a loja e retorna informações da loja"""
        try:
            result = await self._request("GET", "/shop.json")
            shop = result.get("shop", {})
            return {
                "success": True,
                "shop_name": shop.get("name"),
                "shop_email": shop.get("email"),
                "shop_domain": shop.get("domain"),
                "shop_currency": shop.get("currency"),
                "shop_plan": shop.get("plan_name"),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    async def get_products(self, limit: int = 50) -> List[ShopifyProduct]:
        """Lista produtos da loja com todas as informações para SEO"""
        result = await self._request("GET", "/products.json", params={"limit": limit})
        
        products = []
        for p in result.get("products", []):
            # Extrair alt texts das imagens
            image_alts = {}
            images_data = []
            for img in p.get("images", []):
                image_alts[img["id"]] = img.get("alt")
                images_data.append({
                    "id": img["id"],
                    "src": img["src"],
                    "alt": img.get("alt"),
                    "position": img.get("position", 1),
                })
            
            products.append(ShopifyProduct(
                id=p["id"],
                title=p["title"],
                handle=p["handle"],
                body_html=p.get("body_html"),
                vendor=p.get("vendor"),
                product_type=p.get("product_type"),
                tags=p.get("tags"),
                url=f"https://{self.shop_url}/products/{p['handle']}",
                images=images_data,
                image_alt_texts=image_alts,
            ))
        
        return products

    async def get_all_products(self, max_items: int = 500) -> List[ShopifyProduct]:
        """Lista TODOS os produtos com paginação via since_id"""
        all_products: List[ShopifyProduct] = []
        since_id = 0
        per_page = 250  # Shopify REST max

        while len(all_products) < max_items:
            params = {"limit": per_page}
            if since_id:
                params["since_id"] = since_id
            result = await self._request("GET", "/products.json", params=params)
            batch = result.get("products", [])
            if not batch:
                break

            for p in batch:
                image_alts = {}
                images_data = []
                for img in p.get("images", []):
                    image_alts[img["id"]] = img.get("alt")
                    images_data.append({
                        "id": img["id"], "src": img["src"],
                        "alt": img.get("alt"), "position": img.get("position", 1),
                    })
                all_products.append(ShopifyProduct(
                    id=p["id"], title=p["title"], handle=p["handle"],
                    body_html=p.get("body_html"), vendor=p.get("vendor"),
                    product_type=p.get("product_type"), tags=p.get("tags"),
                    url=f"https://{self.shop_url}/products/{p['handle']}",
                    images=images_data, image_alt_texts=image_alts,
                ))

            since_id = batch[-1]["id"]
            if len(batch) < per_page:
                break

        return all_products[:max_items]

    async def get_all_pages(self, max_items: int = 250) -> List[ShopifyPage]:
        """Lista TODAS as páginas com paginação via since_id"""
        all_pages: List[ShopifyPage] = []
        since_id = 0
        per_page = 250

        while len(all_pages) < max_items:
            params = {"limit": per_page}
            if since_id:
                params["since_id"] = since_id
            result = await self._request("GET", "/pages.json", params=params)
            batch = result.get("pages", [])
            if not batch:
                break

            for p in batch:
                all_pages.append(ShopifyPage(
                    id=p["id"], title=p["title"], handle=p["handle"],
                    body_html=p.get("body_html"),
                    url=f"https://{self.shop_url}/pages/{p['handle']}",
                    published=p.get("published_at") is not None,
                    template_suffix=p.get("template_suffix"),
                ))

            since_id = batch[-1]["id"]
            if len(batch) < per_page:
                break

        return all_pages[:max_items]

    async def get_all_collections(self, max_items: int = 250) -> List[ShopifyCollection]:
        """Lista TODAS as coleções (custom + smart) com paginação"""
        collections: List[ShopifyCollection] = []

        for col_type, endpoint, key in [
            ("custom", "/custom_collections.json", "custom_collections"),
            ("smart", "/smart_collections.json", "smart_collections"),
        ]:
            since_id = 0
            per_page = 250
            while len(collections) < max_items:
                params = {"limit": per_page}
                if since_id:
                    params["since_id"] = since_id
                try:
                    result = await self._request("GET", endpoint, params=params)
                except Exception as e:
                    logger.error(f"Erro ao buscar {col_type} collections: {e}")
                    break
                batch = result.get(key, [])
                if not batch:
                    break

                for c in batch:
                    products_count = await self.get_collection_products_count(c["id"])
                    collections.append(ShopifyCollection(
                        id=c["id"], title=c["title"], handle=c["handle"],
                        body_html=c.get("body_html"),
                        url=f"https://{self.shop_url}/collections/{c['handle']}",
                        image=c.get("image"), collection_type=col_type,
                        products_count=products_count,
                    ))

                since_id = batch[-1]["id"]
                if len(batch) < per_page:
                    break

        return collections[:max_items]

    async def get_product(self, product_id: int) -> ShopifyProduct:
        """Obtém um produto específico com detalhes completos"""
        result = await self._request("GET", f"/products/{product_id}.json")
        p = result.get("product", {})
        
        # Extrair alt texts das imagens
        image_alts = {}
        images_data = []
        for img in p.get("images", []):
            image_alts[img["id"]] = img.get("alt")
            images_data.append({
                "id": img["id"],
                "src": img["src"],
                "alt": img.get("alt"),
                "position": img.get("position", 1),
            })
        
        return ShopifyProduct(
            id=p["id"],
            title=p["title"],
            handle=p["handle"],
            body_html=p.get("body_html"),
            vendor=p.get("vendor"),
            product_type=p.get("product_type"),
            tags=p.get("tags"),
            url=f"https://{self.shop_url}/products/{p['handle']}",
            images=images_data,
            image_alt_texts=image_alts,
        )
    
    async def get_product_metafields(self, product_id: int) -> Dict[str, str]:
        """Obtém metafields SEO de um produto"""
        result = await self._request("GET", f"/products/{product_id}/metafields.json")
        
        seo_fields = {}
        for mf in result.get("metafields", []):
            if mf.get("namespace") == "global":
                if mf.get("key") == "title_tag":
                    seo_fields["seo_title"] = mf.get("value")
                    seo_fields["seo_title_id"] = mf.get("id")
                elif mf.get("key") == "description_tag":
                    seo_fields["seo_description"] = mf.get("value")
                    seo_fields["seo_description_id"] = mf.get("id")
        
        return seo_fields
    
    async def get_collection_products(self, collection_id: int, limit: int = 10) -> List[ShopifyProduct]:
        """Obtém os produtos de uma coleção para análise de contexto"""
        try:
            result = await self._request("GET", "/products.json", params={
                "collection_id": collection_id,
                "limit": limit,
            })
            
            products = []
            for p in result.get("products", []):
                products.append(ShopifyProduct(
                    id=p["id"],
                    title=p["title"],
                    handle=p["handle"],
                    body_html=p.get("body_html"),
                    vendor=p.get("vendor"),
                    product_type=p.get("product_type"),
                    tags=p.get("tags"),
                    url=f"https://{self.shop_url}/products/{p['handle']}",
                ))
            return products
        except Exception as e:
            logger.error(f"Erro ao buscar produtos da coleção {collection_id}: {e}")
            return []
    
    async def get_collection_products_count(self, collection_id: int) -> int:
        """Obtém a contagem de produtos em uma coleção"""
        try:
            # Método 1: Usar endpoint de contagem
            result = await self._request("GET", "/products/count.json", params={"collection_id": collection_id})
            count = result.get("count", 0)
            if count > 0:
                return count
            
            # Método 2: Se retornou 0, tentar buscar produtos diretamente (mais confiável)
            result = await self._request("GET", "/products.json", params={
                "collection_id": collection_id,
                "limit": 250,
                "fields": "id"  # Só precisa do ID para contar
            })
            return len(result.get("products", []))
        except Exception as e:
            logger.error(f"Erro ao buscar contagem de produtos da coleção {collection_id}: {e}")
            return 0
    
    async def get_collections(self, limit: int = 50) -> List[ShopifyCollection]:
        """Lista todas as coleções (custom + smart) com contagem de produtos"""
        collections = []
        
        # Custom Collections (Manuais)
        try:
            result = await self._request("GET", "/custom_collections.json", params={"limit": limit})
            for c in result.get("custom_collections", []):
                # Buscar contagem de produtos
                products_count = await self.get_collection_products_count(c["id"])
                
                collections.append(ShopifyCollection(
                    id=c["id"],
                    title=c["title"],
                    handle=c["handle"],
                    body_html=c.get("body_html"),
                    url=f"https://{self.shop_url}/collections/{c['handle']}",
                    image=c.get("image"),
                    collection_type="custom",
                    products_count=products_count,
                ))
        except Exception as e:
            logger.error(f"Erro ao buscar custom collections: {e}")
        
        # Smart Collections (Automáticas - com regras)
        try:
            result = await self._request("GET", "/smart_collections.json", params={"limit": limit})
            for c in result.get("smart_collections", []):
                # Buscar contagem de produtos
                products_count = await self.get_collection_products_count(c["id"])
                
                collections.append(ShopifyCollection(
                    id=c["id"],
                    title=c["title"],
                    handle=c["handle"],
                    body_html=c.get("body_html"),
                    url=f"https://{self.shop_url}/collections/{c['handle']}",
                    image=c.get("image"),
                    collection_type="smart",
                    products_count=products_count,
                ))
        except Exception as e:
            logger.error(f"Erro ao buscar smart collections: {e}")
        
        return collections
    
    async def get_collection(self, collection_id: int, collection_type: str = "custom") -> ShopifyCollection:
        """Obtém uma coleção específica"""
        # Tentar primeiro com o tipo informado, se falhar tentar o outro tipo
        endpoint = "/custom_collections" if collection_type == "custom" else "/smart_collections"
        key = "custom_collection" if collection_type == "custom" else "smart_collection"
        
        try:
            result = await self._request("GET", f"{endpoint}/{collection_id}.json")
            c = result.get(key, {})
        except Exception as e:
            # Se falhou, tentar o outro tipo
            alt_endpoint = "/smart_collections" if collection_type == "custom" else "/custom_collections"
            alt_key = "smart_collection" if collection_type == "custom" else "custom_collection"
            collection_type = "smart" if collection_type == "custom" else "custom"
            
            result = await self._request("GET", f"{alt_endpoint}/{collection_id}.json")
            c = result.get(alt_key, {})
        
        # Buscar contagem de produtos
        products_count = await self.get_collection_products_count(collection_id)
        
        return ShopifyCollection(
            id=c["id"],
            title=c["title"],
            handle=c["handle"],
            body_html=c.get("body_html"),
            url=f"https://{self.shop_url}/collections/{c['handle']}",
            image=c.get("image"),
            collection_type=collection_type,
            products_count=products_count,
        )
    
    async def get_collection_metafields(self, collection_id: int) -> Dict[str, str]:
        """Obtém metafields SEO de uma coleção"""
        result = await self._request("GET", f"/collections/{collection_id}/metafields.json")
        
        seo_fields = {}
        for mf in result.get("metafields", []):
            if mf.get("namespace") == "global":
                if mf.get("key") == "title_tag":
                    seo_fields["seo_title"] = mf.get("value")
                    seo_fields["seo_title_id"] = mf.get("id")
                elif mf.get("key") == "description_tag":
                    seo_fields["seo_description"] = mf.get("value")
                    seo_fields["seo_description_id"] = mf.get("id")
        
        return seo_fields
    
    async def update_collection(self, collection_id: int, collection_type: str, data: Dict) -> Dict:
        """Atualiza uma coleção"""
        endpoint = "/custom_collections" if collection_type == "custom" else "/smart_collections"
        key = "custom_collection" if collection_type == "custom" else "smart_collection"
        return await self._request("PUT", f"{endpoint}/{collection_id}.json", data={key: data})
    
    async def get_pages(self, limit: int = 50) -> List[ShopifyPage]:
        """Lista páginas institucionais"""
        result = await self._request("GET", "/pages.json", params={"limit": limit})
        
        pages = []
        for p in result.get("pages", []):
            pages.append(ShopifyPage(
                id=p["id"],
                title=p["title"],
                handle=p["handle"],
                body_html=p.get("body_html"),
                url=f"https://{self.shop_url}/pages/{p['handle']}",
                published=p.get("published_at") is not None,
                template_suffix=p.get("template_suffix"),
            ))
        
        return pages
    
    async def get_page(self, page_id: int) -> ShopifyPage:
        """Obtém uma página específica"""
        result = await self._request("GET", f"/pages/{page_id}.json")
        p = result.get("page", {})
        
        return ShopifyPage(
            id=p["id"],
            title=p["title"],
            handle=p["handle"],
            body_html=p.get("body_html"),
            url=f"https://{self.shop_url}/pages/{p['handle']}",
            published=p.get("published_at") is not None,
            template_suffix=p.get("template_suffix"),
        )
    
    async def get_page_metafields(self, page_id: int) -> Dict[str, str]:
        """Obtém metafields SEO de uma página"""
        result = await self._request("GET", f"/pages/{page_id}/metafields.json")
        
        seo_fields = {}
        for mf in result.get("metafields", []):
            if mf.get("namespace") == "global":
                if mf.get("key") == "title_tag":
                    seo_fields["seo_title"] = mf.get("value")
                    seo_fields["seo_title_id"] = mf.get("id")
                elif mf.get("key") == "description_tag":
                    seo_fields["seo_description"] = mf.get("value")
                    seo_fields["seo_description_id"] = mf.get("id")
        
        return seo_fields
    
    async def update_page(self, page_id: int, data: Dict) -> Dict:
        """Atualiza uma página"""
        return await self._request("PUT", f"/pages/{page_id}.json", data={"page": data})
    
    async def get_blogs(self) -> List[ShopifyBlog]:
        """Lista blogs da loja"""
        result = await self._request("GET", "/blogs.json")
        
        blogs = []
        for b in result.get("blogs", []):
            blogs.append(ShopifyBlog(
                id=b["id"],
                title=b["title"],
                handle=b["handle"],
            ))
        
        return blogs
    
    async def get_articles(self, blog_id: int = None, limit: int = 50) -> List[ShopifyArticle]:
        """Lista artigos de um blog ou todos os blogs"""
        articles = []
        blog_handles = {}  # Cache de blog handles
        
        if blog_id:
            # Buscar handle do blog
            blogs = await self.get_blogs()
            for b in blogs:
                blog_handles[b.id] = b.handle
            
            result = await self._request("GET", f"/blogs/{blog_id}/articles.json", params={"limit": limit})
            for a in result.get("articles", []):
                articles.append(self._parse_article(a, blog_handles.get(blog_id, str(blog_id))))
        else:
            # Buscar de todos os blogs
            blogs = await self.get_blogs()
            for blog in blogs:
                blog_handles[blog.id] = blog.handle
                result = await self._request("GET", f"/blogs/{blog.id}/articles.json", params={"limit": limit})
                for a in result.get("articles", []):
                    articles.append(self._parse_article(a, blog.handle))
        
        return articles
    
    def _parse_article(self, a: Dict, blog_handle: str = None) -> ShopifyArticle:
        """Parse de artigo do Shopify"""
        # Usar o handle do blog para a URL correta
        blog_path = blog_handle or str(a.get('blog_id'))
        
        return ShopifyArticle(
            id=a["id"],
            blog_id=a["blog_id"],
            title=a["title"],
            handle=a["handle"],
            body_html=a.get("body_html"),
            author=a.get("author"),
            tags=a.get("tags"),
            url=f"https://{self.shop_url}/blogs/{blog_path}/{a['handle']}",
            image=a.get("image"),
            published=a.get("published_at") is not None,
            published_at=a.get("published_at"),
        )
    
    async def get_article(self, blog_id: int, article_id: int) -> ShopifyArticle:
        """Obtém um artigo específico"""
        result = await self._request("GET", f"/blogs/{blog_id}/articles/{article_id}.json")
        return self._parse_article(result.get("article", {}))
    
    async def get_article_metafields(self, article_id: int) -> Dict[str, str]:
        """Obtém metafields SEO de um artigo"""
        result = await self._request("GET", f"/articles/{article_id}/metafields.json")
        
        seo_fields = {}
        for mf in result.get("metafields", []):
            if mf.get("namespace") == "global":
                if mf.get("key") == "title_tag":
                    seo_fields["seo_title"] = mf.get("value")
                    seo_fields["seo_title_id"] = mf.get("id")
                elif mf.get("key") == "description_tag":
                    seo_fields["seo_description"] = mf.get("value")
                    seo_fields["seo_description_id"] = mf.get("id")
        
        return seo_fields
    
    async def update_article(self, blog_id: int, article_id: int, data: Dict) -> Dict:
        """Atualiza um artigo"""
        return await self._request("PUT", f"/blogs/{blog_id}/articles/{article_id}.json", data={"article": data})
    
    def _generate_proposal_id(self) -> str:
        """Gera ID único para proposta"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    async def create_optimization_proposal(
        self,
        product_id: int,
        optimization_type: str,
        field_name: str,
        original_value: Optional[str],
        proposed_value: str,
        reasoning: str,
        image_id: Optional[int] = None,
        priority: Optional[str] = None,
        impact: Optional[str] = None,
        effort: Optional[str] = None,
        target_keyword: Optional[str] = None,
        pre_metrics: Optional[Dict[str, Any]] = None,
    ) -> OptimizationProposal:
        """
        Cria uma proposta de otimização que requer aprovação do usuário.
        NÃO aplica a mudança automaticamente.
        """
        proposal = OptimizationProposal(
            id=self._generate_proposal_id(),
            product_id=product_id,
            optimization_type=optimization_type,
            field_name=field_name,
            original_value=original_value,
            proposed_value=proposed_value,
            reasoning=reasoning,
            status=OptimizationStatus.PENDING,
            created_at=datetime.utcnow().isoformat(),
            image_id=image_id,
            priority=priority,
            impact=impact,
            effort=effort,
            target_keyword=target_keyword,
            pre_metrics=pre_metrics,
        )
        
        self._proposals[proposal.id] = proposal
        return proposal
    
    def get_pending_proposals(self, product_id: int = None) -> List[OptimizationProposal]:
        """Lista propostas pendentes de aprovação"""
        proposals = list(self._proposals.values())
        if product_id:
            proposals = [p for p in proposals if p.product_id == product_id]
        return [p for p in proposals if p.status == OptimizationStatus.PENDING]
    
    def get_all_proposals(self) -> List[OptimizationProposal]:
        """Lista todas as propostas"""
        return list(self._proposals.values())
    
    async def approve_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """
        Aprova uma proposta de otimização.
        A mudança ainda NÃO é aplicada - apenas marca como aprovada.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposta não encontrada: {proposal_id}")
        
        if proposal.status != OptimizationStatus.PENDING:
            raise ValueError(f"Proposta não está pendente: {proposal.status}")
        
        proposal.status = OptimizationStatus.APPROVED
        return {"success": True, "proposal_id": proposal_id, "status": "approved"}
    
    async def reject_proposal(self, proposal_id: str, reason: str = None) -> Dict[str, Any]:
        """Rejeita uma proposta de otimização"""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposta não encontrada: {proposal_id}")
        
        proposal.status = OptimizationStatus.REJECTED
        return {"success": True, "proposal_id": proposal_id, "status": "rejected"}
    
    async def apply_approved_proposals(self, product_id: int = None) -> Dict[str, Any]:
        """
        Aplica TODAS as propostas aprovadas para um item (ou todos).
        Suporta produtos, coleções, páginas e artigos.
        Cria registros de rollback para cada mudança.
        """
        approved = [
            p for p in self._proposals.values() 
            if p.status == OptimizationStatus.APPROVED
            and (product_id is None or p.product_id == product_id)
        ]
        
        if not approved:
            return {"success": True, "applied": 0, "message": "Nenhuma proposta aprovada para aplicar"}
        
        applied = 0
        errors = []
        rollback_records: List[Dict[str, Any]] = []
        
        # Agrupar por tipo de conteúdo e ID
        by_content: Dict[str, Dict[int, List[OptimizationProposal]]] = {
            "product": {},
            "collection": {},
            "page": {},
            "article": {},
        }
        
        for p in approved:
            content_type = p.content_type or "product"
            if p.product_id not in by_content[content_type]:
                by_content[content_type][p.product_id] = []
            by_content[content_type][p.product_id].append(p)
        
        # Aplicar propostas de produtos
        for prod_id, proposals in by_content["product"].items():
            try:
                result = await self._apply_product_proposals(prod_id, proposals)
                applied += result["applied"]
                rollback_records.extend(result.get("rollback_records", []))
            except Exception as e:
                errors.append(f"Produto {prod_id}: {str(e)}")
        
        # Aplicar propostas de coleções
        for coll_id, proposals in by_content["collection"].items():
            try:
                result = await self._apply_collection_proposals(coll_id, proposals)
                applied += result["applied"]
                rollback_records.extend(result.get("rollback_records", []))
            except Exception as e:
                errors.append(f"Coleção {coll_id}: {str(e)}")
        
        # Aplicar propostas de páginas
        for page_id, proposals in by_content["page"].items():
            try:
                result = await self._apply_page_proposals(page_id, proposals)
                applied += result["applied"]
                rollback_records.extend(result.get("rollback_records", []))
            except Exception as e:
                errors.append(f"Página {page_id}: {str(e)}")
        
        # Aplicar propostas de artigos
        for article_id, proposals in by_content["article"].items():
            try:
                result = await self._apply_article_proposals(article_id, proposals)
                applied += result["applied"]
                rollback_records.extend(result.get("rollback_records", []))
            except Exception as e:
                errors.append(f"Artigo {article_id}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "applied": applied,
            "rollback_records": rollback_records,
            "errors": errors if errors else None,
        }
    
    async def apply_proposals_direct(self, proposals_data: List[Dict]) -> Dict[str, Any]:
        """
        Aplica propostas diretamente a partir de dados do frontend.
        Funciona após cold starts (não depende de estado em memória).
        """
        proposals: List[OptimizationProposal] = []
        for p_data in proposals_data:
            try:
                proposal = OptimizationProposal(
                    id=p_data.get("id", self._generate_proposal_id()),
                    product_id=int(p_data["product_id"]),
                    optimization_type=p_data.get("optimization_type", p_data.get("field_name", "")),
                    field_name=p_data.get("field_name", p_data.get("optimization_type", "")),
                    original_value=p_data.get("original_value"),
                    proposed_value=p_data["proposed_value"],
                    reasoning=p_data.get("reasoning", ""),
                    status=OptimizationStatus.APPROVED,
                    created_at=p_data.get("created_at", datetime.utcnow().isoformat()),
                    content_type=p_data.get("content_type", "product"),
                    image_id=p_data.get("image_id"),
                )
                proposals.append(proposal)
            except Exception as e:
                logger.warning(f"Failed to parse Shopify proposal: {e}")
        
        if not proposals:
            return {"applied": 0, "rollback_records": [], "error": "No valid proposals to apply"}
        
        by_content: Dict[str, Dict[int, List[OptimizationProposal]]] = {
            "product": {}, "collection": {}, "page": {}, "article": {},
        }
        for p in proposals:
            ct = p.content_type or "product"
            if ct not in by_content:
                by_content[ct] = {}
            by_content[ct].setdefault(p.product_id, []).append(p)
        
        applied = 0
        errors: List[str] = []
        rollback_records: List[Dict[str, Any]] = []
        
        for prod_id, group in by_content["product"].items():
            try:
                r = await self._apply_product_proposals(prod_id, group)
                applied += r.get("applied", 0)
                rollback_records.extend(r.get("rollback_records", []))
            except Exception as e:
                errors.append(f"product:{prod_id}: {e}")
        for coll_id, group in by_content["collection"].items():
            try:
                r = await self._apply_collection_proposals(coll_id, group)
                applied += r.get("applied", 0)
                rollback_records.extend(r.get("rollback_records", []))
            except Exception as e:
                errors.append(f"collection:{coll_id}: {e}")
        for page_id, group in by_content["page"].items():
            try:
                r = await self._apply_page_proposals(page_id, group)
                applied += r.get("applied", 0)
                rollback_records.extend(r.get("rollback_records", []))
            except Exception as e:
                errors.append(f"page:{page_id}: {e}")
        for article_id, group in by_content["article"].items():
            try:
                r = await self._apply_article_proposals(article_id, group)
                applied += r.get("applied", 0)
                rollback_records.extend(r.get("rollback_records", []))
            except Exception as e:
                errors.append(f"article:{article_id}: {e}")
        
        result: Dict[str, Any] = {
            "success": len(errors) == 0,
            "applied": applied,
            "rollback_records": rollback_records,
        }
        if errors:
            result["errors"] = errors
        return result
    
    async def _apply_product_proposals(
        self, 
        product_id: int, 
        proposals: List[OptimizationProposal]
    ) -> Dict[str, Any]:
        """Aplica propostas de um produto específico"""
        applied = 0
        
        # Separar por tipo
        product_updates = {}
        metafield_updates = []
        image_updates = []
        faq_updates = []
        
        for p in proposals:
            if p.optimization_type == "title":
                product_updates["title"] = p.proposed_value
            elif p.optimization_type == "description":
                product_updates["body_html"] = p.proposed_value
            elif p.optimization_type == "rich_description":
                # Rich description substitui body_html
                product_updates["body_html"] = p.proposed_value
            elif p.optimization_type == "seo_title":
                metafield_updates.append(("title_tag", p.proposed_value))
            elif p.optimization_type == "seo_description":
                metafield_updates.append(("description_tag", p.proposed_value))
            elif p.optimization_type == "image_alt" and p.image_id:
                image_updates.append((p.image_id, p.proposed_value))
            elif p.optimization_type == "tags":
                # Tags - extrair do JSON
                try:
                    import json
                    tags_data = json.loads(p.proposed_value)
                    product_updates["tags"] = tags_data.get("tags_string", "")
                except:
                    product_updates["tags"] = p.proposed_value
            elif p.optimization_type == "faq":
                # FAQ salvo como metafield customizado
                faq_updates.append(("faq_html", p.proposed_value))
        
        # Aplicar atualizações do produto
        if product_updates:
            await self._request(
                "PUT",
                f"/products/{product_id}.json",
                data={"product": product_updates}
            )
        
        # Aplicar metafields
        for key, value in metafield_updates:
            await self._request(
                "POST",
                f"/products/{product_id}/metafields.json",
                data={
                    "metafield": {
                        "namespace": "global",
                        "key": key,
                        "value": value,
                        "type": "single_line_text_field"
                    }
                }
            )
        
        # Aplicar alt texts de imagens
        for image_id, alt_text in image_updates:
            await self._request(
                "PUT",
                f"/products/{product_id}/images/{image_id}.json",
                data={"image": {"id": image_id, "alt": alt_text}}
            )
        
        # Aplicar FAQ como metafield customizado
        for key, value in faq_updates:
            await self._request(
                "POST",
                f"/products/{product_id}/metafields.json",
                data={
                    "metafield": {
                        "namespace": "custom",
                        "key": key,
                        "value": value,
                        "type": "multi_line_text_field"
                    }
                }
            )
        
        # Criar registros de rollback e marcar como aplicado
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            # Criar rollback
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.shop_url,
                product_id=product_id,
                field_name=p.field_name,
                original_value=p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                image_id=p.image_id,
                content_type=p.content_type,  # Preservar tipo de conteúdo
            )
            self._rollback_records[rollback.id] = rollback
            rec = rollback.model_dump()
            rec["optimization_type"] = p.optimization_type
            rollback_records.append(rec)
            
            # Marcar proposta como aplicada
            p.status = OptimizationStatus.APPLIED
            p.applied_at = datetime.utcnow().isoformat()
            applied += 1
        
        return {"applied": applied, "rollback_records": rollback_records}
    
    async def _apply_collection_proposals(
        self, 
        collection_id: int, 
        proposals: List[OptimizationProposal]
    ) -> Dict[str, Any]:
        """Aplica propostas de uma coleção específica"""
        applied = 0
        
        # Determinar tipo de coleção (custom ou smart)
        collection_type = "custom"
        try:
            await self._request("GET", f"/custom_collections/{collection_id}.json")
        except:
            collection_type = "smart"
        
        # Separar por tipo
        collection_updates = {}
        metafield_updates = []
        
        for p in proposals:
            if p.optimization_type == "collection_title":
                collection_updates["title"] = p.proposed_value
            elif p.optimization_type == "collection_description":
                collection_updates["body_html"] = p.proposed_value
            elif p.optimization_type == "collection_seo_title":
                metafield_updates.append(("title_tag", p.proposed_value))
            elif p.optimization_type == "collection_seo_description":
                metafield_updates.append(("description_tag", p.proposed_value))
        
        # Aplicar atualizações da coleção
        if collection_updates:
            endpoint = f"/custom_collections/{collection_id}.json" if collection_type == "custom" else f"/smart_collections/{collection_id}.json"
            key = "custom_collection" if collection_type == "custom" else "smart_collection"
            await self._request("PUT", endpoint, data={key: collection_updates})
        
        # Aplicar metafields
        for key, value in metafield_updates:
            await self._request(
                "POST",
                f"/collections/{collection_id}/metafields.json",
                data={
                    "metafield": {
                        "namespace": "global",
                        "key": key,
                        "value": value,
                        "type": "single_line_text_field"
                    }
                }
            )
        
        # Criar registros de rollback e marcar como aplicado
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.shop_url,
                product_id=collection_id,
                field_name=p.field_name,
                original_value=p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                content_type="collection",
            )
            self._rollback_records[rollback.id] = rollback
            rec = rollback.model_dump()
            rec["optimization_type"] = p.optimization_type
            rollback_records.append(rec)
            
            p.status = OptimizationStatus.APPLIED
            p.applied_at = datetime.utcnow().isoformat()
            applied += 1
        
        return {"applied": applied, "rollback_records": rollback_records}
    
    async def _apply_page_proposals(
        self, 
        page_id: int, 
        proposals: List[OptimizationProposal]
    ) -> Dict[str, Any]:
        """Aplica propostas de uma página específica"""
        applied = 0
        
        # Separar por tipo
        page_updates = {}
        metafield_updates = []
        
        for p in proposals:
            if p.optimization_type == "page_title":
                page_updates["title"] = p.proposed_value
            elif p.optimization_type == "page_content":
                page_updates["body_html"] = p.proposed_value
            elif p.optimization_type == "page_seo_title":
                metafield_updates.append(("title_tag", p.proposed_value))
            elif p.optimization_type == "page_seo_description":
                metafield_updates.append(("description_tag", p.proposed_value))
        
        # Aplicar atualizações da página
        if page_updates:
            await self._request("PUT", f"/pages/{page_id}.json", data={"page": page_updates})
        
        # Aplicar metafields
        for key, value in metafield_updates:
            await self._request(
                "POST",
                f"/pages/{page_id}/metafields.json",
                data={
                    "metafield": {
                        "namespace": "global",
                        "key": key,
                        "value": value,
                        "type": "single_line_text_field"
                    }
                }
            )
        
        # Criar registros de rollback e marcar como aplicado
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.shop_url,
                product_id=page_id,
                field_name=p.field_name,
                original_value=p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                content_type="page",
            )
            self._rollback_records[rollback.id] = rollback
            rec = rollback.model_dump()
            rec["optimization_type"] = p.optimization_type
            rollback_records.append(rec)
            
            p.status = OptimizationStatus.APPLIED
            p.applied_at = datetime.utcnow().isoformat()
            applied += 1
        
        return {"applied": applied, "rollback_records": rollback_records}
    
    async def _apply_article_proposals(
        self, 
        article_id: int, 
        proposals: List[OptimizationProposal]
    ) -> Dict[str, Any]:
        """Aplica propostas de um artigo específico"""
        applied = 0
        
        # Precisamos descobrir o blog_id do artigo
        # Buscar em todos os blogs
        blog_id = None
        blogs_result = await self._request("GET", "/blogs.json")
        for blog in blogs_result.get("blogs", []):
            try:
                await self._request("GET", f"/blogs/{blog['id']}/articles/{article_id}.json")
                blog_id = blog["id"]
                break
            except:
                continue
        
        if not blog_id:
            raise ValueError(f"Não foi possível encontrar o blog do artigo {article_id}")
        
        # Separar por tipo
        article_updates = {}
        metafield_updates = []
        
        for p in proposals:
            if p.optimization_type == "article_title":
                article_updates["title"] = p.proposed_value
            elif p.optimization_type == "article_content":
                article_updates["body_html"] = p.proposed_value
            elif p.optimization_type == "article_seo_title":
                metafield_updates.append(("title_tag", p.proposed_value))
            elif p.optimization_type == "article_seo_description":
                metafield_updates.append(("description_tag", p.proposed_value))
            elif p.optimization_type == "article_tags":
                article_updates["tags"] = p.proposed_value
        
        # Aplicar atualizações do artigo
        if article_updates:
            await self._request(
                "PUT", 
                f"/blogs/{blog_id}/articles/{article_id}.json", 
                data={"article": article_updates}
            )
        
        # Aplicar metafields
        for key, value in metafield_updates:
            await self._request(
                "POST",
                f"/articles/{article_id}/metafields.json",
                data={
                    "metafield": {
                        "namespace": "global",
                        "key": key,
                        "value": value,
                        "type": "single_line_text_field"
                    }
                }
            )
        
        # Criar registros de rollback e marcar como aplicado
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.shop_url,
                product_id=article_id,
                field_name=p.field_name,
                original_value=p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                content_type="article",
                blog_id=blog_id,
            )
            self._rollback_records[rollback.id] = rollback
            rec = rollback.model_dump()
            rec["optimization_type"] = p.optimization_type
            rollback_records.append(rec)
            
            p.status = OptimizationStatus.APPLIED
            p.applied_at = datetime.utcnow().isoformat()
            applied += 1
        
        return {"applied": applied, "rollback_records": rollback_records}
    
    async def _upsert_metafield(
        self,
        owner_resource: str,
        owner_id: int,
        namespace: str,
        key: str,
        value: str,
        mf_type: str = "single_line_text_field",
    ) -> None:
        """Cria ou atualiza um metafield. Se valor vazio e metafield existe, remove.

        owner_resource: 'products' | 'collections' | 'pages' | 'articles'
        """
        safe_value = value if value is not None else ""
        try:
            result = await self._request("GET", f"/{owner_resource}/{owner_id}/metafields.json")
        except Exception as e:
            logger.error(f"Falha ao listar metafields {owner_resource}/{owner_id}: {e}")
            result = {"metafields": []}

        existing_id = None
        for mf in result.get("metafields", []) or []:
            if mf.get("namespace") == namespace and mf.get("key") == key:
                existing_id = mf.get("id")
                break

        if existing_id:
            if safe_value == "":
                try:
                    await self._request("DELETE", f"/metafields/{existing_id}.json")
                    return
                except Exception as e:
                    logger.warning(f"Falha ao deletar metafield {existing_id}, tentando PUT vazio: {e}")
            await self._request(
                "PUT",
                f"/metafields/{existing_id}.json",
                data={"metafield": {"id": existing_id, "value": safe_value, "type": mf_type}},
            )
        else:
            await self._request(
                "POST",
                f"/{owner_resource}/{owner_id}/metafields.json",
                data={
                    "metafield": {
                        "namespace": namespace,
                        "key": key,
                        "value": safe_value,
                        "type": mf_type,
                    }
                },
            )

    async def rollback_direct(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reverte uma alteração a partir dos dados enviados pelo frontend.
        Não depende de estado em memória - funciona após cold starts.
        """
        content_type = record.get("content_type", "product")
        product_id = record.get("product_id")
        original_value = record.get("original_value")
        optimization_type = record.get("optimization_type") or ""
        image_id = record.get("image_id")
        blog_id = record.get("blog_id")
        
        if product_id is None:
            raise ValueError("product_id é obrigatório no registro de rollback")
        product_id = int(product_id)
        
        ot = optimization_type.strip()
        
        try:
            if content_type == "product":
                if ot == "title":
                    await self._request("PUT", f"/products/{product_id}.json", data={"product": {"title": original_value}})
                elif ot in ("description", "rich_description"):
                    await self._request("PUT", f"/products/{product_id}.json", data={"product": {"body_html": original_value}})
                elif ot == "tags":
                    tags_val = original_value
                    try:
                        import json as _json
                        parsed = _json.loads(original_value) if original_value else None
                        if isinstance(parsed, dict):
                            tags_val = parsed.get("tags_string", "")
                    except Exception:
                        pass
                    await self._request("PUT", f"/products/{product_id}.json", data={"product": {"tags": tags_val}})
                elif ot == "seo_title":
                    await self._upsert_metafield("products", product_id, "global", "title_tag", original_value or "")
                elif ot == "seo_description":
                    await self._upsert_metafield("products", product_id, "global", "description_tag", original_value or "")
                elif ot == "image_alt":
                    if not image_id:
                        raise ValueError("image_id é obrigatório para rollback de alt text")
                    await self._request("PUT", f"/products/{product_id}/images/{image_id}.json", data={"image": {"id": image_id, "alt": original_value or ""}})
                elif ot == "faq":
                    await self._upsert_metafield("products", product_id, "custom", "faq_html", original_value or "", mf_type="multi_line_text_field")
                else:
                    raise ValueError(f"Tipo de otimização desconhecido: {ot}")
            elif content_type == "collection":
                col_type = "custom"
                try:
                    await self._request("GET", f"/custom_collections/{product_id}.json")
                except Exception:
                    col_type = "smart"
                endpoint = f"/custom_collections/{product_id}.json" if col_type == "custom" else f"/smart_collections/{product_id}.json"
                key = "custom_collection" if col_type == "custom" else "smart_collection"
                if ot == "collection_title":
                    await self._request("PUT", endpoint, data={key: {"title": original_value}})
                elif ot == "collection_description":
                    await self._request("PUT", endpoint, data={key: {"body_html": original_value}})
                elif ot == "collection_seo_title":
                    await self._upsert_metafield("collections", product_id, "global", "title_tag", original_value or "")
                elif ot == "collection_seo_description":
                    await self._upsert_metafield("collections", product_id, "global", "description_tag", original_value or "")
                else:
                    raise ValueError(f"Tipo de otimização desconhecido: {ot}")
            elif content_type == "page":
                if ot == "page_title":
                    await self._request("PUT", f"/pages/{product_id}.json", data={"page": {"title": original_value}})
                elif ot == "page_content":
                    await self._request("PUT", f"/pages/{product_id}.json", data={"page": {"body_html": original_value}})
                elif ot == "page_seo_title":
                    await self._upsert_metafield("pages", product_id, "global", "title_tag", original_value or "")
                elif ot == "page_seo_description":
                    await self._upsert_metafield("pages", product_id, "global", "description_tag", original_value or "")
                else:
                    raise ValueError(f"Tipo de otimização desconhecido: {ot}")
            elif content_type == "article":
                if not blog_id:
                    # Tentar descobrir o blog_id
                    blogs_result = await self._request("GET", "/blogs.json")
                    for blog in blogs_result.get("blogs", []):
                        try:
                            await self._request("GET", f"/blogs/{blog['id']}/articles/{product_id}.json")
                            blog_id = blog["id"]
                            break
                        except Exception:
                            continue
                if not blog_id:
                    raise ValueError(f"blog_id não encontrado para artigo {product_id}")
                if ot == "article_title":
                    await self._request("PUT", f"/blogs/{blog_id}/articles/{product_id}.json", data={"article": {"title": original_value}})
                elif ot == "article_content":
                    await self._request("PUT", f"/blogs/{blog_id}/articles/{product_id}.json", data={"article": {"body_html": original_value}})
                elif ot == "article_tags":
                    await self._request("PUT", f"/blogs/{blog_id}/articles/{product_id}.json", data={"article": {"tags": original_value or ""}})
                elif ot == "article_seo_title":
                    await self._upsert_metafield("articles", product_id, "global", "title_tag", original_value or "")
                elif ot == "article_seo_description":
                    await self._upsert_metafield("articles", product_id, "global", "description_tag", original_value or "")
                else:
                    raise ValueError(f"Tipo de otimização desconhecido: {ot}")
            else:
                raise ValueError(f"content_type desconhecido: {content_type}")
        except Exception as e:
            logger.error(f"Erro no rollback_direct ({content_type}/{ot}): {e}")
            raise
        
        # Marca na memória se existir
        rid = record.get("id")
        if rid and rid in self._rollback_records:
            self._rollback_records[rid].rolled_back = True
            self._rollback_records[rid].rolled_back_at = datetime.utcnow().isoformat()
        
        return {"rolled_back": 1, "message": f"Alteração revertida: {ot or 'campo'}"}
    
    def get_rollback_records(self, product_id: int = None) -> List[RollbackRecord]:
        """Lista registros disponíveis para rollback"""
        records = list(self._rollback_records.values())
        if product_id:
            records = [r for r in records if r.product_id == product_id]
        return [r for r in records if not r.rolled_back]
    
    async def rollback_single(self, rollback_id: str) -> Dict[str, Any]:
        """Reverte uma única mudança"""
        record = self._rollback_records.get(rollback_id)
        if not record:
            raise ValueError(f"Registro de rollback não encontrado: {rollback_id}")
        
        if record.rolled_back:
            raise ValueError("Esta mudança já foi revertida")
        
        # Aplicar valor original
        if record.field_name == "title":
            await self._request(
                "PUT",
                f"/products/{record.product_id}.json",
                data={"product": {"title": record.original_value or ""}}
            )
        elif record.field_name == "body_html":
            await self._request(
                "PUT",
                f"/products/{record.product_id}.json",
                data={"product": {"body_html": record.original_value or ""}}
            )
        elif record.field_name in ("seo_title", "seo_description"):
            key = "title_tag" if record.field_name == "seo_title" else "description_tag"
            if record.original_value:
                await self._request(
                    "POST",
                    f"/products/{record.product_id}/metafields.json",
                    data={
                        "metafield": {
                            "namespace": "global",
                            "key": key,
                            "value": record.original_value,
                            "type": "single_line_text_field"
                        }
                    }
                )
        elif record.field_name == "image_alt" and record.image_id:
            await self._request(
                "PUT",
                f"/products/{record.product_id}/images/{record.image_id}.json",
                data={"image": {"id": record.image_id, "alt": record.original_value or ""}}
            )
        
        # Marcar como revertido
        record.rolled_back = True
        record.rolled_back_at = datetime.utcnow().isoformat()
        
        # Atualizar proposta relacionada
        for p in self._proposals.values():
            if (p.product_id == record.product_id and 
                p.field_name == record.field_name and
                p.status == OptimizationStatus.APPLIED):
                p.status = OptimizationStatus.ROLLED_BACK
        
        return {"success": True, "rollback_id": rollback_id}
    
    async def rollback_product(self, product_id: int) -> Dict[str, Any]:
        """Reverte TODAS as mudanças de um produto"""
        records = self.get_rollback_records(product_id)
        
        if not records:
            return {"success": True, "rolled_back": 0, "message": "Nenhuma mudança para reverter"}
        
        rolled_back = 0
        errors = []
        
        for record in records:
            try:
                await self.rollback_single(record.id)
                rolled_back += 1
            except Exception as e:
                errors.append(f"{record.field_name}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "rolled_back": rolled_back,
            "errors": errors if errors else None,
        }
    
    async def rollback_all(self) -> Dict[str, Any]:
        """Reverte TODAS as mudanças de TODOS os produtos"""
        records = self.get_rollback_records()
        
        if not records:
            return {"success": True, "rolled_back": 0, "message": "Nenhuma mudança para reverter"}
        
        rolled_back = 0
        errors = []
        
        for record in records:
            try:
                await self.rollback_single(record.id)
                rolled_back += 1
            except Exception as e:
                errors.append(f"Produto {record.product_id} - {record.field_name}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "rolled_back": rolled_back,
            "errors": errors if errors else None,
        }
    
    async def update_product_seo(
        self, 
        product_id: int, 
        title: Optional[str] = None,
        body_html: Optional[str] = None,
        seo_title: Optional[str] = None,
        seo_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Use create_optimization_proposal + apply_approved_proposals
        Mantido para compatibilidade.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            if title or body_html:
                payload = {"product": {}}
                if title:
                    payload["product"]["title"] = title
                if body_html:
                    payload["product"]["body_html"] = body_html
                
                kwargs = {
                    "url": f"{self.base_url}/products/{product_id}.json",
                    "headers": self.headers,
                    "json": payload
                }
                if self.auth:
                    kwargs["auth"] = self.auth
                
                r = await client.put(**kwargs)
                if r.status_code not in (200, 201):
                    raise Exception(f"Erro ao atualizar produto: {r.text}")
            
            if seo_title or seo_description:
                metafields = []
                if seo_title:
                    metafields.append({
                        "namespace": "global",
                        "key": "title_tag",
                        "value": seo_title,
                        "type": "single_line_text_field"
                    })
                if seo_description:
                    metafields.append({
                        "namespace": "global", 
                        "key": "description_tag",
                        "value": seo_description,
                        "type": "single_line_text_field"
                    })
                
                for mf in metafields:
                    kwargs = {
                        "url": f"{self.base_url}/products/{product_id}/metafields.json",
                        "headers": self.headers,
                        "json": {"metafield": mf}
                    }
                    if self.auth:
                        kwargs["auth"] = self.auth
                    
                    r = await client.post(**kwargs)
            
            return {"success": True, "product_id": product_id}
    
    # Métodos get_pages() e get_collections() já definidos acima


# Helper para criar cliente a partir de credenciais
def create_shopify_client(
    shop_url: str, 
    api_key: str = None,
    api_secret: str = None,
    access_token: str = None
) -> ShopifyClient:
    """
    Cria cliente Shopify com as credenciais fornecidas.
    
    Duas formas de autenticação:
    1. api_key + api_secret: Para apps privados (desenvolvimento)
    2. access_token: Para apps públicos (OAuth2)
    """
    return ShopifyClient(
        shop_url=shop_url,
        api_key=api_key,
        api_secret=api_secret,
        access_token=access_token,
    )
