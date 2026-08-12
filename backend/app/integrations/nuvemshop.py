"""
Integração Nuvemshop/Tiendanube - SiteCan PRO
Permite conectar lojas Nuvemshop via OAuth, ler produtos/categorias/páginas e atualizar SEO
"""
import os
import httpx
import hashlib
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
import logging
logger = logging.getLogger(__name__)


class NuvemshopAuthError(Exception):
    """Token de acesso inválido ou expirado"""
    pass


# Configurações OAuth - Nuvemshop Brasil
NUVEMSHOP_APP_ID = os.getenv("NUVEMSHOP_APP_ID", "").strip()
NUVEMSHOP_CLIENT_SECRET = os.getenv("NUVEMSHOP_CLIENT_SECRET", "").strip()
# IMPORTANTE: Usar versão 2025-03 da API para acessar endpoints novos como /pages e /blogs
NUVEMSHOP_API_URL = "https://api.nuvemshop.com.br/2025-03"


def _require_nuvemshop_oauth_config() -> None:
    if not NUVEMSHOP_APP_ID or not NUVEMSHOP_CLIENT_SECRET:
        raise RuntimeError(
            "Configure NUVEMSHOP_APP_ID e NUVEMSHOP_CLIENT_SECRET no backend/.env."
        )
NUVEMSHOP_AUTH_URL = "https://www.nuvemshop.com.br/apps"
NUVEMSHOP_TOKEN_URL = "https://www.tiendanube.com/apps/authorize/token"  # Token endpoint é na tiendanube mesmo

# Armazenamento em memória para tokens OAuth (em produção usar banco de dados)
_oauth_states: Dict[str, Dict[str, Any]] = {}
_store_tokens: Dict[str, Dict[str, Any]] = {}


class OptimizationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class NuvemshopProduct(BaseModel):
    id: int
    name: str
    handle: str
    description: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    url: Optional[str] = None
    images: List[Dict[str, Any]] = []
    variants: List[Dict[str, Any]] = []
    categories: List[Dict[str, Any]] = []
    tags: Optional[str] = None
    brand: Optional[str] = None


class NuvemshopCategory(BaseModel):
    id: int
    name: str
    handle: str
    description: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    url: Optional[str] = None
    parent_id: Optional[int] = None
    subcategories: List[int] = []
    products_count: int = 0


class NuvemshopPage(BaseModel):
    id: int
    title: str
    handle: str
    content: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    url: Optional[str] = None
    published: bool = True


class NuvemshopBlogPost(BaseModel):
    id: int
    blog_id: Optional[int] = None
    title: str
    handle: str
    body: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[str] = None
    published: bool = True
    published_at: Optional[str] = None


class NuvemshopStore(BaseModel):
    id: int
    name: str
    url: str
    email: Optional[str] = None
    plan: Optional[str] = None
    country: Optional[str] = None
    languages: Dict[str, Any] = {}
    blog: Optional[str] = None  # URL do blog da loja


class OptimizationProposal(BaseModel):
    id: str
    product_id: int
    optimization_type: str
    field_name: str
    original_value: Optional[str] = None
    proposed_value: str
    reasoning: str
    status: OptimizationStatus = OptimizationStatus.PENDING
    created_at: str
    approved_at: Optional[str] = None
    applied_at: Optional[str] = None
    content_type: str = "product"
    # Prioritização e contexto competitivo
    priority: Optional[str] = None        # 'high', 'medium', 'low'
    impact: Optional[str] = None          # 'ranking', 'ctr', 'conversao', 'visibilidade'
    effort: Optional[str] = None          # 'low', 'medium', 'high'
    target_keyword: Optional[str] = None  # Keyword alvo da otimização
    # Feedback loop  - métricas pré-apply
    pre_metrics: Optional[Dict[str, Any]] = None  # {clicks, impressions, ctr, position}
    blog_id: Optional[int] = None  # Necessário para blog posts
    # Transparência da IA (validação pós-geração: atributos + cobertura semântica)
    transparencia: Optional[Dict[str, Any]] = None


class RollbackRecord(BaseModel):
    id: str
    shop_url: str
    product_id: int
    field_name: str
    original_value: Optional[str] = None
    new_value: str
    applied_at: str
    rolled_back: bool = False
    rolled_back_at: Optional[str] = None
    content_type: str = "product"
    blog_id: Optional[int] = None
    # Necessário quando field_name sozinho é ambíguo entre entidades (ex.: VTEX/Loja
    # Integrada usam o mesmo field_name "seo_title" para produto e categoria, mas
    # cada uma resolve para um campo de API diferente — sem isso, rollback_single
    # perde essa informação e o rollback de categoria falha com "campo desconhecido").
    optimization_type: Optional[str] = None


# Scopes necessários para o SiteCan PRO
# Docs: https://tiendanube.github.io/api-documentation/authentication
NUVEMSHOP_SCOPES = [
    "read_products",
    "write_products", 
    "read_content",      # Páginas e blog
    "write_content",     # Editar páginas e blog
    "read_categories",
    "write_categories",
]


class NuvemshopOAuth:
    """Gerencia o fluxo OAuth da Nuvemshop"""
    
    @staticmethod
    def generate_auth_url(redirect_uri: str) -> Dict[str, str]:
        """
        Gera URL de autorização OAuth
        
        Returns:
            Dict com auth_url e state
        """
        _require_nuvemshop_oauth_config()
        state = secrets.token_urlsafe(32)
        
        # Salvar state para validação posterior
        _oauth_states[state] = {
            "redirect_uri": redirect_uri,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Montar URL com scopes
        # Formato: /apps/{app_id}/authorize?state={state}
        # Os scopes são configurados no Portal de Parceiros, não na URL
        auth_url = f"{NUVEMSHOP_AUTH_URL}/{NUVEMSHOP_APP_ID}/authorize?state={state}"
        
        return {
            "auth_url": auth_url,
            "state": state
        }
    
    @staticmethod
    async def exchange_code(code: str, state: str) -> Dict[str, Any]:
        """
        Troca authorization code por access token
        
        Args:
            code: Authorization code recebido no callback
            state: State para validação CSRF
            
        Returns:
            Dict com access_token, store_id, etc.
        """
        _require_nuvemshop_oauth_config()

        # Validar state (em desenvolvimento, apenas logar aviso se não encontrado)
        if state in _oauth_states:
            del _oauth_states[state]
        else:
            logger.warning(
                "[Nuvemshop OAuth] State não encontrado no cache "
                "(pode ter expirado ou o servidor reiniciou)"
            )

        async with httpx.AsyncClient() as client:
            payload = {
                "client_id": NUVEMSHOP_APP_ID,
                "client_secret": NUVEMSHOP_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
            }

            response = await client.post(
                NUVEMSHOP_TOKEN_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
            )

            if response.status_code != 200:
                raise ValueError("Erro ao obter token OAuth da Nuvemshop")
            
            data = response.json()
            
            # Salvar token
            store_id = str(data.get("user_id"))
            _store_tokens[store_id] = {
                "access_token": data.get("access_token"),
                "token_type": data.get("token_type"),
                "scope": data.get("scope"),
                "store_id": store_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            return {
                "success": True,
                "store_id": store_id,
                "access_token": data.get("access_token"),
                "scope": data.get("scope")
            }
    
    @staticmethod
    def get_stored_token(store_id: str) -> Optional[str]:
        """Recupera token armazenado para uma loja"""
        token_data = _store_tokens.get(store_id)
        if token_data:
            return token_data.get("access_token")
        return None
    
    @staticmethod
    def store_token(store_id: str, access_token: str):
        """Armazena token manualmente (para testes)"""
        _store_tokens[store_id] = {
            "access_token": access_token,
            "store_id": store_id,
            "created_at": datetime.utcnow().isoformat()
        }


class NuvemshopClient:
    """
    Cliente para API da Nuvemshop/Tiendanube.
    """
    
    def __init__(self, store_id: str, access_token: str):
        """
        Args:
            store_id: ID da loja na Nuvemshop
            access_token: Token de acesso OAuth2
        """
        self.store_id = store_id
        self.access_token = access_token
        self.base_url = f"{NUVEMSHOP_API_URL}/{store_id}"
        self.headers = {
            "Authentication": f"bearer {access_token}",
            "User-Agent": "SiteCan PRO (contato@sitecan.com)",
            "Content-Type": "application/json",
        }
        self.language = "pt"  # Idioma padrão
        self._cached_store: Optional[NuvemshopStore] = None  # Cache para evitar chamadas repetidas a /store
        
        # Armazenamento local de propostas e rollbacks
        self._proposals: Dict[str, OptimizationProposal] = {}
        self._rollback_records: Dict[str, RollbackRecord] = {}
    
    def _generate_proposal_id(self) -> str:
        """Gera ID único para proposta"""
        return hashlib.md5(f"{datetime.utcnow().isoformat()}{secrets.token_hex(4)}".encode()).hexdigest()[:8]
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Faz requisição à API da Nuvemshop"""
        url = f"{self.base_url}{endpoint}"
        
        logger.debug(f"[Nuvemshop API] {method} {url} params={params}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = await client.put(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Método não suportado: {method}")
            
            logger.debug(f"[Nuvemshop API] Response status: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"[Nuvemshop API] ERROR Response body: {response.text[:500]}")
                if response.status_code == 401:
                    raise NuvemshopAuthError("Token de acesso inválido ou expirado. Reconecte sua loja Nuvemshop.")
                raise Exception(f"Erro API Nuvemshop ({response.status_code}): {response.text}")
            
            if response.status_code == 204:
                return {}
            
            result = response.json()
            logger.debug(f"[Nuvemshop API] Response type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A (list)'}")
            return result
    
    def _extract_text(self, value: Any, lang: str = None) -> str:
        """Extrai texto de campo multilíngue ou string simples"""
        if value is None:
            return ""
        if isinstance(value, dict):
            lang = lang or self.language
            return value.get(lang, value.get("pt", value.get("es", "")))
        return str(value)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Testa a conexão com a loja"""
        try:
            store = await self.get_store()
            return {"success": True, "connected": True, "store": store}
        except Exception as e:
            return {"success": False, "connected": False, "error": str(e)}
    
    async def get_store(self) -> NuvemshopStore:
        """Obtém informações da loja (com cache em memória)"""
        if self._cached_store:
            return self._cached_store
        store = await self._request("GET", "/store")
        self._cached_store = NuvemshopStore(
            id=store.get("id"),
            name=self._extract_text(store.get("name")),
            url=store.get("url_with_protocol", store.get("original_domain", "")),
            email=store.get("email"),
            plan=store.get("plan_name"),
            country=store.get("country"),
            languages=store.get("languages", {}),
            blog=store.get("blog")
        )
        return self._cached_store
    
    async def get_products(self, limit: int = 50, page: int = 1) -> List[NuvemshopProduct]:
        """Lista produtos da loja"""
        response = await self._request("GET", "/products", params={
            "per_page": limit,
            "page": page
        })
        
        # API pode retornar lista diretamente ou objeto paginado
        if isinstance(response, dict):
            products = response.get("results", response.get("products", []))
            if not isinstance(products, list):
                logger.warning(f"[Nuvemshop] Resposta inesperada de /products: keys={response.keys()}")
                products = []
        else:
            products = response
        
        result = []
        store = await self.get_store()
        
        for p in products:
            try:
                product = NuvemshopProduct(
                    id=p.get("id"),
                    name=self._extract_text(p.get("name")),
                    handle=self._extract_text(p.get("handle", "")),
                    description=self._extract_text(p.get("description")),
                    seo_title=self._extract_text(p.get("seo_title")),
                    seo_description=self._extract_text(p.get("seo_description")),
                    url=f"{store.url}/productos/{self._extract_text(p.get('handle', ''))}",
                    images=p.get("images", []),
                    variants=p.get("variants", []),
                    categories=p.get("categories", []),
                    tags=p.get("tags"),
                    brand=p.get("brand")
                )
                result.append(product)
            except Exception as e:
                logger.warning(f"[Nuvemshop] Erro ao parsear produto id={p.get('id')}: {e}")
        
        return result

    async def get_all_products(self, max_items: int = 500) -> List[NuvemshopProduct]:
        """Lista TODOS os produtos com paginação automática"""
        all_products: List[NuvemshopProduct] = []
        page = 1
        per_page = 50  # Nuvemshop max per_page for products

        while len(all_products) < max_items:
            try:
                batch = await self.get_products(limit=per_page, page=page)
            except Exception as e:
                # Nuvemshop retorna 404 ao requisitar página além da última
                msg = str(e)
                if "404" in msg or "Last page" in msg:
                    logger.info(f"[Nuvemshop] Fim da paginação de produtos em page={page}")
                else:
                    logger.error(f"[Nuvemshop] Erro ao paginar produtos (page={page}): {e}")
                break
            if not batch:
                break
            all_products.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        return all_products[:max_items]

    async def get_all_categories(self, max_items: int = 250) -> List[NuvemshopCategory]:
        """Lista TODAS as categorias com paginação automática"""
        all_cats: List[NuvemshopCategory] = []
        page = 1
        per_page = 50

        while len(all_cats) < max_items:
            try:
                response = await self._request("GET", "/categories", params={
                    "per_page": per_page, "page": page
                })
                if isinstance(response, dict):
                    items = response.get("categories", response.get("results", []))
                else:
                    items = response or []
                if not items:
                    break

                store = await self.get_store()
                for c in items:
                    all_cats.append(NuvemshopCategory(
                        id=c.get("id"),
                        name=self._extract_text(c.get("name")),
                        handle=self._extract_text(c.get("handle")),
                        description=self._extract_text(c.get("description")),
                        seo_title=self._extract_text(c.get("seo_title")),
                        seo_description=self._extract_text(c.get("seo_description")),
                        url=f"{store.url}/categorias/{self._extract_text(c.get('handle'))}",
                        parent_id=c.get("parent"),
                        subcategories=c.get("subcategories", []),
                        products_count=c.get("products_count", 0),
                    ))

                if len(items) < per_page:
                    break
                page += 1
            except Exception as e:
                logger.error(f"[Nuvemshop] Erro ao paginar categorias (page={page}): {e}")
                break

        return all_cats[:max_items]

    async def get_all_pages(self, max_items: int = 100) -> List[NuvemshopPage]:
        """Lista TODAS as páginas com paginação automática"""
        all_pages: List[NuvemshopPage] = []
        page = 1
        per_page = 20  # Nuvemshop API limita a 20 por página

        while len(all_pages) < max_items:
            try:
                response = await self._request("GET", "/pages", params={
                    "per_page": per_page, "page": page
                })
                if isinstance(response, list):
                    items = response
                elif isinstance(response, dict):
                    items = response.get("pages", response.get("results", []))
                else:
                    break
                if not items:
                    break

                store = await self.get_store()
                for p in items:
                    all_pages.append(NuvemshopPage(
                        id=p.get("id"),
                        title=self._extract_text(p.get("name", p.get("title"))),
                        handle=self._extract_text(p.get("handle")),
                        content=self._extract_text(p.get("content")),
                        seo_title=self._extract_text(p.get("seo_title")),
                        seo_description=self._extract_text(p.get("seo_description")),
                        url=f"{store.url}/{self._extract_text(p.get('handle'))}",
                        published=p.get("published", True),
                    ))

                if len(items) < per_page:
                    break
                page += 1
            except Exception as e:
                logger.error(f"[Nuvemshop] Erro ao paginar páginas (page={page}): {e}")
                break

        return all_pages[:max_items]

    async def get_product(self, product_id: int) -> NuvemshopProduct:
        """Obtém um produto específico"""
        p = await self._request("GET", f"/products/{product_id}")
        store = await self.get_store()
        
        return NuvemshopProduct(
            id=p.get("id"),
            name=self._extract_text(p.get("name")),
            handle=self._extract_text(p.get("handle")),
            description=self._extract_text(p.get("description")),
            seo_title=self._extract_text(p.get("seo_title")),
            seo_description=self._extract_text(p.get("seo_description")),
            url=f"{store.url}/productos/{self._extract_text(p.get('handle'))}",
            images=p.get("images", []),
            variants=p.get("variants", []),
            categories=p.get("categories", []),
            tags=p.get("tags"),
            brand=p.get("brand")
        )
    
    async def update_product(self, product_id: int, data: Dict) -> Dict:
        """Atualiza um produto"""
        # Converter para formato multilíngue se necessário
        update_data = {}
        for key, value in data.items():
            if key in ["name", "description", "seo_title", "seo_description", "handle"]:
                update_data[key] = {self.language: value}
            else:
                update_data[key] = value
        
        return await self._request("PUT", f"/products/{product_id}", data=update_data)
    
    async def update_product_image(self, product_id: int, image_id: int, alt_text: str) -> Dict:
        """Atualiza alt text de uma imagem de produto"""
        return await self._request(
            "PUT", 
            f"/products/{product_id}/images/{image_id}",
            data={"alt": {self.language: alt_text}}
        )
    
    async def get_categories(self, limit: int = 50) -> List[NuvemshopCategory]:
        """Lista categorias da loja"""
        try:
            categories = await self._request("GET", "/categories", params={"per_page": limit})
            
            # Tratar caso a resposta seja um dict com estrutura aninhada
            if isinstance(categories, dict):
                categories = categories.get("categories", categories.get("results", []))
            
            result = []
            store = await self.get_store()
            
            for c in (categories or []):
                # Buscar contagem de produtos na categoria
                products_count = 0
                try:
                    # A API Nuvemshop retorna products_count no objeto da categoria
                    # ou podemos buscar via endpoint de produtos com filtro
                    products_count = c.get("products_count", 0)
                    
                    # Se não veio na resposta, tentar buscar contando
                    if products_count == 0:
                        cat_products = await self._request(
                            "GET", 
                            "/products", 
                            params={"category_id": c.get("id"), "per_page": 1, "fields": "id"}
                        )
                        # A API retorna header com total, mas podemos usar len se for lista completa
                        if isinstance(cat_products, list):
                            # Fazer uma segunda chamada para contar - usar per_page=200 para pegar mais
                            cat_products_full = await self._request(
                                "GET", 
                                "/products", 
                                params={"category_id": c.get("id"), "per_page": 200, "fields": "id"}
                            )
                            products_count = len(cat_products_full) if isinstance(cat_products_full, list) else 0
                except Exception as count_err:
                    logger.error(f"[Nuvemshop] Erro ao contar produtos da categoria {c.get('id')}: {count_err}")
                    products_count = 0
                
                category = NuvemshopCategory(
                    id=c.get("id"),
                    name=self._extract_text(c.get("name")),
                    handle=self._extract_text(c.get("handle")),
                    description=self._extract_text(c.get("description")),
                    seo_title=self._extract_text(c.get("seo_title")),
                    seo_description=self._extract_text(c.get("seo_description")),
                    url=f"{store.url}/categorias/{self._extract_text(c.get('handle'))}",
                    parent_id=c.get("parent"),
                    subcategories=c.get("subcategories", []),
                    products_count=products_count
                )
                result.append(category)
            
            return result
        except Exception as e:
            logger.error(f"[Nuvemshop] Erro ao carregar categorias: {e}")
            return []
    
    async def get_category(self, category_id: int) -> NuvemshopCategory:
        """Obtém uma categoria específica"""
        c = await self._request("GET", f"/categories/{category_id}")
        store = await self.get_store()
        
        return NuvemshopCategory(
            id=c.get("id"),
            name=self._extract_text(c.get("name")),
            handle=self._extract_text(c.get("handle")),
            description=self._extract_text(c.get("description")),
            seo_title=self._extract_text(c.get("seo_title")),
            seo_description=self._extract_text(c.get("seo_description")),
            url=f"{store.url}/categorias/{self._extract_text(c.get('handle'))}",
            parent_id=c.get("parent"),
            subcategories=c.get("subcategories", [])
        )
    
    async def update_category(self, category_id: int, data: Dict) -> Dict:
        """Atualiza uma categoria"""
        update_data = {}
        for key, value in data.items():
            if key in ["name", "description", "seo_title", "seo_description", "handle"]:
                update_data[key] = {self.language: value}
            else:
                update_data[key] = value
        
        return await self._request("PUT", f"/categories/{category_id}", data=update_data)
    
    async def get_category_products(self, category_id: int, limit: int = 10) -> List[NuvemshopProduct]:
        """Obtém produtos de uma categoria"""
        products = await self._request(
            "GET", 
            "/products", 
            params={"category_id": category_id, "per_page": limit}
        )
        
        result = []
        store = await self.get_store()
        
        for p in products:
            product = NuvemshopProduct(
                id=p.get("id"),
                name=self._extract_text(p.get("name")),
                handle=self._extract_text(p.get("handle")),
                description=self._extract_text(p.get("description")),
                url=f"{store.url}/productos/{self._extract_text(p.get('handle'))}",
                images=p.get("images", []),
            )
            result.append(product)
        
        return result
    
    async def get_pages(self, limit: int = 20) -> List[NuvemshopPage]:
        """Lista páginas da loja (máximo 20 por página)"""
        try:
            # API limita per_page a 20
            per_page = min(limit, 20)
            logger.debug(f"[Nuvemshop] Buscando páginas... endpoint: /pages, per_page={per_page}")
            response = await self._request("GET", "/pages", params={"per_page": per_page})
            logger.debug(f"[Nuvemshop] Resposta de páginas (tipo): {type(response)}")
            logger.debug(f"[Nuvemshop] Resposta de páginas (conteúdo): {response}")
            
            # A API pode retornar lista direta ou estrutura aninhada
            pages = []
            if isinstance(response, list):
                pages = response
            elif isinstance(response, dict):
                # Tentar várias estruturas possíveis
                pages = response.get("pages", response.get("results", []))
                if isinstance(pages, dict):
                    pages = pages.get("results", [])
            
            logger.debug(f"[Nuvemshop] Páginas extraídas: {len(pages)} itens")
            
            result = []
            store = await self.get_store()
            
            for p in pages:
                page = NuvemshopPage(
                    id=p.get("id"),
                    title=self._extract_text(p.get("name", p.get("title"))),  # API usa "name" não "title"
                    handle=self._extract_text(p.get("handle")),
                    content=self._extract_text(p.get("content")),
                    seo_title=self._extract_text(p.get("seo_title")),
                    seo_description=self._extract_text(p.get("seo_description")),
                    url=f"{store.url}/{self._extract_text(p.get('handle'))}",
                    published=p.get("published", True)
                )
                result.append(page)
            
            return result
        except Exception as e:
            logger.error(f"[Nuvemshop] Erro ao carregar páginas: {e}")
            # Retornar lista vazia se der erro (ex: loja sem páginas)
            return []
    
    async def get_page(self, page_id: int) -> NuvemshopPage:
        """Obtém uma página específica"""
        p = await self._request("GET", f"/pages/{page_id}")
        store = await self.get_store()
        
        return NuvemshopPage(
            id=p.get("id"),
            title=self._extract_text(p.get("title")),
            handle=self._extract_text(p.get("handle")),
            content=self._extract_text(p.get("content")),
            seo_title=self._extract_text(p.get("seo_title")),
            seo_description=self._extract_text(p.get("seo_description")),
            url=f"{store.url}/{self._extract_text(p.get('handle'))}",
            published=p.get("published", True)
        )
    
    async def update_page(self, page_id: int, data: Dict) -> Dict:
        """Atualiza uma página"""
        update_data = {}
        for key, value in data.items():
            if key in ["title", "content", "seo_title", "seo_description", "handle"]:
                update_data[key] = {self.language: value}
            else:
                update_data[key] = value
        
        return await self._request("PUT", f"/pages/{page_id}", data=update_data)
    
    async def _request_v1(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Requisição para API v1 (usada para blogs)"""
        url = f"https://api.nuvemshop.com.br/v1/{self.store_id}{endpoint}"
        headers = {
            "Authentication": f"bearer {self.access_token}",
            "User-Agent": "SiteCanPRO (suporte@sitecan.com.br)",
            "Content-Type": "application/json"
        }
        
        logger.debug(f"[Nuvemshop API v1] {method} {url} params={params}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            logger.debug(f"[Nuvemshop API v1] Response status: {response.status_code}")
            
            if response.status_code >= 400:
                error_body = response.text
                logger.error(f"[Nuvemshop API v1] ERROR Response body: {error_body}")
                raise Exception(f"Erro API Nuvemshop v1 ({response.status_code}): {error_body}")
            
            if response.status_code == 204:
                return {}
            
            result = response.json()
            logger.debug(f"[Nuvemshop API v1] Response: {type(result)}")
            return result
    
    async def _try_blog_posts(self, blog_id, limit: int = 50) -> list:
        """Tenta buscar posts de um blog_id específico, retorna lista de posts raw ou []"""
        # Tentar API versionada primeiro (2025-03)
        try:
            response = await self._request("GET", f"/blogs/{blog_id}/posts", params={"per_page": limit})
            logger.debug(f"[Nuvemshop] Posts do blog {blog_id} (versioned): status OK, type={type(response)}")
            return self._parse_blog_response(response)
        except Exception as e1:
            logger.error(f"[Nuvemshop] Versioned API falhou para blog {blog_id}: {e1}")
        
        # Fallback: API v1
        try:
            response = await self._request_v1("GET", f"/blogs/{blog_id}/posts", params={"per_page": limit})
            logger.debug(f"[Nuvemshop] Posts do blog {blog_id} (v1): status OK, type={type(response)}")
            return self._parse_blog_response(response)
        except Exception as e2:
            logger.error(f"[Nuvemshop] V1 API também falhou para blog {blog_id}: {e2}")
        
        return []
    
    def _parse_blog_response(self, response) -> list:
        """Parseia resposta de posts do blog"""
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            posts = response.get("posts", response.get("results", response.get("data", [])))
            if isinstance(posts, dict):
                posts = posts.get("results", [])
            return posts if isinstance(posts, list) else []
        return []
    
    async def get_blogs(self) -> List[Dict]:
        """Lista blogs da loja (tenta endpoint não documentado)"""
        try:
            logger.debug(f"[Nuvemshop] Buscando blogs...")
            
            # Tentar API versionada primeiro (2025-03)
            try:
                blogs = await self._request("GET", "/blogs")
                logger.debug(f"[Nuvemshop] Blogs encontrados (versioned API): {blogs}")
                if isinstance(blogs, list) and blogs:
                    return blogs
                elif isinstance(blogs, dict):
                    items = blogs.get("blogs", blogs.get("results", []))
                    if items:
                        return items
            except Exception as e1:
                logger.error(f"[Nuvemshop] API versionada falhou para /blogs: {e1}")
            
            # Fallback: API v1
            try:
                blogs = await self._request_v1("GET", "/blogs")
                logger.debug(f"[Nuvemshop] Blogs encontrados (v1 API): {blogs}")
                if isinstance(blogs, list) and blogs:
                    return blogs
                elif isinstance(blogs, dict):
                    items = blogs.get("blogs", blogs.get("results", []))
                    if items:
                        return items
            except Exception as e2:
                logger.error(f"[Nuvemshop] API v1 também falhou para /blogs: {e2}")
            
            return []
        except Exception as e:
            logger.error(f"[Nuvemshop] Erro ao buscar blogs: {e}")
            return []
    
    async def get_blog_posts(self, limit: int = 50) -> List[NuvemshopBlogPost]:
        """Lista posts do blog"""
        try:
            logger.debug(f"[Nuvemshop] Buscando posts do blog... store_id={self.store_id}")
            
            # 1. Tentar descobrir blog_ids via endpoint de listagem
            blogs = await self.get_blogs()
            
            # 2. Se não encontrou, tentar múltiplos blog_ids candidatos
            if not blogs:
                logger.debug(f"[Nuvemshop] Nenhum blog listado - tentando blog_ids candidatos...")
                # Candidatos: blog_id=1 (padrão), blog_id=store_id (convenção alternativa)
                candidate_ids = [1]
                try:
                    sid = int(self.store_id)
                    if sid != 1:
                        candidate_ids.append(sid)
                except (ValueError, TypeError):
                    pass
                
                for cid in candidate_ids:
                    posts_raw = await self._try_blog_posts(cid, limit)
                    if posts_raw:
                        logger.debug(f"[Nuvemshop] Blog encontrado com blog_id={cid}! ({len(posts_raw)} posts)")
                        blogs = [{"id": cid}]
                        break
                
                if not blogs:
                    logger.debug(f"[Nuvemshop] Nenhum blog encontrado com nenhum candidato")
                    return []
            
            all_posts = []
            store = await self.get_store()
            
            for blog in blogs:
                blog_id = blog.get("id") if isinstance(blog, dict) else blog
                logger.debug(f"[Nuvemshop] Buscando posts do blog {blog_id}...")
                
                try:
                    posts_raw = await self._try_blog_posts(blog_id, limit)
                    
                    for p in posts_raw:
                        # Extrair metadata se existir (novo formato da API)
                        metadata = p.get("metadata", {}) or {}
                        
                        title = self._extract_text(p.get("title") or metadata.get("title", ""))
                        handle = self._extract_text(p.get("handle") or metadata.get("handle", ""))
                        body = self._extract_text(p.get("body") or p.get("content") or metadata.get("summary", ""))
                        seo_title = self._extract_text(p.get("seo_title") or metadata.get("seo_title", ""))
                        seo_description = self._extract_text(p.get("seo_description") or metadata.get("seo_description", ""))
                        
                        post = NuvemshopBlogPost(
                            id=p.get("id"),
                            blog_id=blog_id,
                            title=title,
                            handle=handle,
                            body=body,
                            seo_title=seo_title,
                            seo_description=seo_description,
                            url=f"{store.url}/blog/{handle}" if handle else "",
                            author=p.get("author"),
                            tags=p.get("tags"),
                            published=p.get("published", True),
                            published_at=p.get("published_at")
                        )
                        all_posts.append(post)
                except Exception as blog_err:
                    logger.error(f"[Nuvemshop] Erro ao buscar posts do blog {blog_id}: {blog_err}")
                    continue
            
            logger.debug(f"[Nuvemshop] Total de posts encontrados: {len(all_posts)}")
            return all_posts
        except Exception as e:
            logger.error(f"[Nuvemshop] Erro ao buscar posts do blog: {e}")
            return []
    
    async def get_blog_post(self, blog_id: int, post_id: int) -> NuvemshopBlogPost:
        """Obtém um post específico"""
        p = None
        try:
            p = await self._request("GET", f"/blogs/{blog_id}/posts/{post_id}")
        except Exception:
            p = await self._request_v1("GET", f"/blogs/{blog_id}/posts/{post_id}")
        
        store = await self.get_store()
        metadata = p.get("metadata", {}) or {}
        
        title = self._extract_text(p.get("title") or metadata.get("title", ""))
        handle = self._extract_text(p.get("handle") or metadata.get("handle", ""))
        body = self._extract_text(p.get("body") or p.get("content") or metadata.get("summary", ""))
        seo_title = self._extract_text(p.get("seo_title") or metadata.get("seo_title", ""))
        seo_description = self._extract_text(p.get("seo_description") or metadata.get("seo_description", ""))
        
        return NuvemshopBlogPost(
            id=p.get("id"),
            blog_id=blog_id,
            title=title,
            handle=handle,
            body=body,
            seo_title=seo_title,
            seo_description=seo_description,
            url=f"{store.url}/blog/{handle}" if handle else "",
            author=p.get("author"),
            tags=p.get("tags"),
            published=p.get("published", True),
            published_at=p.get("published_at")
        )
    
    async def update_blog_post(self, blog_id: int, post_id: int, data: Dict) -> Dict:
        """Atualiza um post do blog"""
        # Formato para API v1
        update_data = {}
        
        # Campos localizados (precisam do código do idioma)
        localized_fields = ["title", "body", "seo_title", "seo_description", "handle"]
        for key in localized_fields:
            if key in data:
                update_data[key] = {self.language: data[key]}
        
        # Campos simples
        for key in ["tags", "published", "author"]:
            if key in data:
                update_data[key] = data[key]
        
        try:
            return await self._request("PUT", f"/blogs/{blog_id}/posts/{post_id}", data=update_data)
        except Exception:
            return await self._request_v1("PUT", f"/blogs/{blog_id}/posts/{post_id}", data=update_data)
    
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
    
    async def apply_approved_proposals(self, item_id: Optional[int] = None) -> Dict[str, Any]:
        """Aplica propostas aprovadas"""
        approved = [p for p in self._proposals.values() 
                   if p.status == OptimizationStatus.APPROVED]
        
        if item_id:
            approved = [p for p in approved if p.product_id == item_id]
        
        # Agrupar por tipo de conteúdo e item
        by_content = {}
        for p in approved:
            key = (p.content_type, p.product_id)
            if key not in by_content:
                by_content[key] = []
            by_content[key].append(p)
        
        applied = 0
        rollback_records: List[Dict[str, Any]] = []
        
        for (content_type, content_id), proposals in by_content.items():
            if content_type == "product":
                result = await self._apply_product_proposals(content_id, proposals)
            elif content_type == "category":
                result = await self._apply_category_proposals(content_id, proposals)
            elif content_type == "page":
                result = await self._apply_page_proposals(content_id, proposals)
            elif content_type == "blog":
                result = await self._apply_blog_proposals(content_id, proposals)
            else:
                continue
            
            applied += result.get("applied", 0)
            rollback_records.extend(result.get("rollback_records", []))
        
        return {"applied": applied, "rollback_records": rollback_records}
    
    async def _apply_product_proposals(
        self, 
        product_id: int, 
        proposals: List[OptimizationProposal]
    ) -> Dict[str, Any]:
        """Aplica propostas de um produto específico"""
        applied = 0
        product_updates = {}
        image_updates = []
        
        for p in proposals:
            if p.optimization_type == "title":
                product_updates["name"] = p.proposed_value
            elif p.optimization_type == "description":
                product_updates["description"] = p.proposed_value
            elif p.optimization_type == "seo_title":
                product_updates["seo_title"] = p.proposed_value
            elif p.optimization_type == "seo_description":
                product_updates["seo_description"] = p.proposed_value
            elif p.optimization_type == "tags":
                product_updates["tags"] = p.proposed_value
            elif p.optimization_type == "image_alt":
                # Extrair image_id do field_name
                parts = p.field_name.split("_")
                if len(parts) >= 2:
                    image_id = int(parts[-1])
                    image_updates.append((image_id, p.proposed_value))
        
        # Aplicar atualizações do produto
        if product_updates:
            await self.update_product(product_id, product_updates)
        
        # Aplicar atualizações de imagens
        for image_id, alt_text in image_updates:
            await self.update_product_image(product_id, image_id, alt_text)
        
        # Criar registros de rollback e marcar como aplicado
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.store_id,
                product_id=product_id,
                field_name=p.field_name,
                original_value=p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                content_type="product",
            )
            self._rollback_records[rollback.id] = rollback
            record_dict = rollback.model_dump()
            record_dict["optimization_type"] = p.optimization_type
            rollback_records.append(record_dict)
            
            p.status = OptimizationStatus.APPLIED
            p.applied_at = datetime.utcnow().isoformat()
            applied += 1
        
        return {"applied": applied, "rollback_records": rollback_records}
    
    async def _apply_category_proposals(
        self, 
        category_id: int, 
        proposals: List[OptimizationProposal]
    ) -> Dict[str, Any]:
        """Aplica propostas de uma categoria específica"""
        applied = 0
        category_updates = {}
        
        for p in proposals:
            if p.optimization_type == "category_title":
                category_updates["name"] = p.proposed_value
            elif p.optimization_type == "category_description":
                category_updates["description"] = p.proposed_value
            elif p.optimization_type == "category_seo_title":
                category_updates["seo_title"] = p.proposed_value
            elif p.optimization_type == "category_seo_description":
                category_updates["seo_description"] = p.proposed_value
        
        if category_updates:
            await self.update_category(category_id, category_updates)
        
        # Criar registros de rollback
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.store_id,
                product_id=category_id,
                field_name=p.field_name,
                original_value=p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                content_type="category",
            )
            self._rollback_records[rollback.id] = rollback
            record_dict = rollback.model_dump()
            record_dict["optimization_type"] = p.optimization_type
            rollback_records.append(record_dict)
            
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
        page_updates = {}
        
        for p in proposals:
            if p.optimization_type == "page_title":
                page_updates["title"] = p.proposed_value
            elif p.optimization_type == "page_content":
                page_updates["content"] = p.proposed_value
            elif p.optimization_type == "page_seo_title":
                page_updates["seo_title"] = p.proposed_value
            elif p.optimization_type == "page_seo_description":
                page_updates["seo_description"] = p.proposed_value
        
        if page_updates:
            await self.update_page(page_id, page_updates)
        
        # Criar registros de rollback
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.store_id,
                product_id=page_id,
                field_name=p.field_name,
                original_value=p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                content_type="page",
            )
            self._rollback_records[rollback.id] = rollback
            record_dict = rollback.model_dump()
            record_dict["optimization_type"] = p.optimization_type
            rollback_records.append(record_dict)
            
            p.status = OptimizationStatus.APPLIED
            p.applied_at = datetime.utcnow().isoformat()
            applied += 1
        
        return {"applied": applied, "rollback_records": rollback_records}
    
    async def _apply_blog_proposals(
        self, 
        post_id: int, 
        proposals: List[OptimizationProposal]
    ) -> Dict[str, Any]:
        """Aplica propostas de um post do blog"""
        applied = 0
        post_updates = {}
        
        for p in proposals:
            if p.optimization_type == "blog_title":
                post_updates["title"] = p.proposed_value
            elif p.optimization_type == "blog_body":
                post_updates["body"] = p.proposed_value
            elif p.optimization_type == "blog_seo_title":
                post_updates["seo_title"] = p.proposed_value
            elif p.optimization_type == "blog_seo_description":
                post_updates["seo_description"] = p.proposed_value
            elif p.optimization_type == "blog_tags":
                post_updates["tags"] = p.proposed_value
        
        if post_updates:
            blog_id = next((p.blog_id for p in proposals if p.blog_id), None)
            if not blog_id:
                logger.warning(f"Cannot apply blog proposals for post {post_id}: blog_id not found")
                return {"applied": 0}
            await self.update_blog_post(blog_id, post_id, post_updates)
        
        # Criar registros de rollback
        blog_id_val = next((p.blog_id for p in proposals if p.blog_id), None)
        rollback_records: List[Dict[str, Any]] = []
        for p in proposals:
            rollback = RollbackRecord(
                id=self._generate_proposal_id(),
                shop_url=self.store_id,
                product_id=post_id,
                field_name=p.field_name,
                original_value=p.original_value,
                new_value=p.proposed_value,
                applied_at=datetime.utcnow().isoformat(),
                content_type="blog",
                blog_id=blog_id_val,
            )
            self._rollback_records[rollback.id] = rollback
            record_dict = rollback.model_dump()
            record_dict["optimization_type"] = p.optimization_type
            rollback_records.append(record_dict)
            
            p.status = OptimizationStatus.APPLIED
            p.applied_at = datetime.utcnow().isoformat()
            applied += 1
        
        return {"applied": applied, "rollback_records": rollback_records}
    
    async def apply_proposals_direct(self, proposals_data: List[Dict]) -> Dict[str, Any]:
        """Aplica propostas diretamente a partir de dados do frontend (sem depender de estado em memória)"""
        proposals = []
        for p_data in proposals_data:
            try:
                proposal = OptimizationProposal(
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
                    blog_id=p_data.get("blog_id"),
                )
                proposals.append(proposal)
            except Exception as e:
                logger.warning(f"Failed to parse proposal: {e}")
        
        if not proposals:
            return {"applied": 0, "error": "No valid proposals to apply"}
        
        by_content: Dict[tuple, List[OptimizationProposal]] = {}
        for p in proposals:
            key = (p.content_type, p.product_id)
            if key not in by_content:
                by_content[key] = []
            by_content[key].append(p)
        
        applied = 0
        errors = []
        rollback_records: List[Dict[str, Any]] = []
        
        for (content_type, content_id), group in by_content.items():
            try:
                if content_type == "product":
                    result = await self._apply_product_proposals(content_id, group)
                elif content_type == "category":
                    result = await self._apply_category_proposals(content_id, group)
                elif content_type == "page":
                    result = await self._apply_page_proposals(content_id, group)
                elif content_type == "blog":
                    result = await self._apply_blog_proposals(content_id, group)
                else:
                    continue
                applied += result.get("applied", 0)
                rollback_records.extend(result.get("rollback_records", []))
            except Exception as e:
                logger.error(f"Error applying {content_type} proposals for {content_id}: {e}")
                errors.append(f"{content_type}:{content_id}: {str(e)}")
        
        result: Dict[str, Any] = {"applied": applied, "rollback_records": rollback_records}
        if errors:
            result["errors"] = errors
        return result
    
    def get_rollback_records(self, content_type: Optional[str] = None) -> List[RollbackRecord]:
        """Lista registros de rollback"""
        records = list(self._rollback_records.values())
        
        if content_type:
            records = [r for r in records if r.content_type == content_type]
        
        return [r for r in records if not r.rolled_back]
    
    def _resolve_api_field(self, content_type: str, optimization_type: Optional[str], field_name: str) -> Optional[str]:
        """Retorna o nome do campo na API a partir de optimization_type/field_name"""
        ot = (optimization_type or "").strip()
        # Produto
        product_map = {
            "title": "name",
            "description": "description",
            "seo_title": "seo_title",
            "seo_description": "seo_description",
            "tags": "tags",
        }
        category_map = {
            "category_title": "name",
            "category_description": "description",
            "category_seo_title": "seo_title",
            "category_seo_description": "seo_description",
        }
        page_map = {
            "page_title": "title",
            "page_content": "content",
            "page_seo_title": "seo_title",
            "page_seo_description": "seo_description",
        }
        blog_map = {
            "blog_title": "title",
            "blog_body": "body",
            "blog_seo_title": "seo_title",
            "blog_seo_description": "seo_description",
            "blog_tags": "tags",
        }
        if content_type == "product" and ot in product_map:
            return product_map[ot]
        if content_type == "category" and ot in category_map:
            return category_map[ot]
        if content_type == "page" and ot in page_map:
            return page_map[ot]
        if content_type == "blog" and ot in blog_map:
            return blog_map[ot]
        # Fallback: use field_name as-is (legacy)
        return field_name
    
    async def rollback_direct(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reverte uma alteração a partir dos dados enviados pelo frontend.
        Não depende de estado em memória - funciona após cold starts.
        """
        content_type = record.get("content_type", "product")
        product_id = record.get("product_id")
        original_value = record.get("original_value")
        optimization_type = record.get("optimization_type")
        field_name = record.get("field_name", "")
        blog_id = record.get("blog_id")
        
        if product_id is None:
            raise ValueError("product_id é obrigatório no registro de rollback")
        
        api_field = self._resolve_api_field(content_type, optimization_type, field_name)
        if not api_field:
            raise ValueError(f"Campo desconhecido para rollback: {content_type}/{optimization_type}")
        
        payload = {api_field: original_value}
        
        if content_type == "product":
            await self.update_product(int(product_id), payload)
        elif content_type == "category":
            await self.update_category(int(product_id), payload)
        elif content_type == "page":
            await self.update_page(int(product_id), payload)
        elif content_type == "blog":
            if not blog_id:
                raise ValueError("blog_id é obrigatório para rollback de post")
            await self.update_blog_post(int(blog_id), int(product_id), payload)
        else:
            raise ValueError(f"Tipo de conteúdo não suportado: {content_type}")
        
        # Se existir na memória, marca como revertido
        rid = record.get("id")
        if rid and rid in self._rollback_records:
            self._rollback_records[rid].rolled_back = True
            self._rollback_records[rid].rolled_back_at = datetime.utcnow().isoformat()
        
        return {"rolled_back": 1, "message": f"Alteração revertida: {api_field}"}
    
    async def rollback_single(self, rollback_id: str) -> Dict[str, Any]:
        """Reverte uma única alteração"""
        if rollback_id not in self._rollback_records:
            raise ValueError(f"Rollback {rollback_id} não encontrado")
        
        record = self._rollback_records[rollback_id]
        
        if record.rolled_back:
            raise ValueError("Esta alteração já foi revertida")
        
        # Reverter baseado no tipo de conteúdo
        if record.content_type == "product":
            await self.update_product(record.product_id, {record.field_name: record.original_value})
        elif record.content_type == "category":
            await self.update_category(record.product_id, {record.field_name: record.original_value})
        elif record.content_type == "page":
            await self.update_page(record.product_id, {record.field_name: record.original_value})
        elif record.content_type == "blog":
            if not record.blog_id:
                raise ValueError("blog_id não disponível no registro de rollback")
            await self.update_blog_post(record.blog_id, record.product_id, {record.field_name: record.original_value})
        
        record.rolled_back = True
        record.rolled_back_at = datetime.utcnow().isoformat()
        
        return {"rolled_back": 1, "message": f"Alteração revertida: {record.field_name}"}
    
    async def rollback_all(self) -> Dict[str, Any]:
        """Reverte todas as alterações"""
        rolled_back = 0
        
        for record in self._rollback_records.values():
            if not record.rolled_back:
                try:
                    await self.rollback_single(record.id)
                    rolled_back += 1
                except Exception:
                    pass
        
        return {"rolled_back": rolled_back, "message": f"{rolled_back} alteração(ões) revertida(s)"}


_nuvemshop_clients: Dict[str, NuvemshopClient] = {}


def create_nuvemshop_client(store_id: str, access_token: Optional[str] = None) -> NuvemshopClient:
    """
    Cria ou recupera cliente Nuvemshop para uma loja
    
    Args:
        store_id: ID da loja
        access_token: Token de acesso (se não fornecido, tenta recuperar do armazenamento)
    """
    if store_id in _nuvemshop_clients:
        return _nuvemshop_clients[store_id]
    
    if not access_token:
        access_token = NuvemshopOAuth.get_stored_token(store_id)
        if not access_token:
            raise ValueError(f"Token não encontrado para loja {store_id}. Faça o login OAuth primeiro.")
    
    client = NuvemshopClient(store_id, access_token)
    _nuvemshop_clients[store_id] = client
    
    return client


def get_nuvemshop_client(store_id: str) -> Optional[NuvemshopClient]:
    """Recupera cliente existente para uma loja"""
    return _nuvemshop_clients.get(store_id)
