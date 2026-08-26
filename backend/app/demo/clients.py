"""Clients de plataforma que servem o catálogo fixture (sem HTTP externo)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.demo import store as demo_store
from app.demo.catalog import STORE_EMAIL, STORE_NAME
from app.demo.config import DEMO_STORES
from app.integrations.lojaintegrada import LojaIntegradaClient
from app.integrations.nuvemshop import NuvemshopClient
from app.integrations.shopify import ShopifyClient
from app.integrations.vtex import VtexClient


def _pt(value: Any) -> Any:
    if isinstance(value, dict) and "pt" in value:
        return value.get("pt")
    return value


def _unwrap_pt(data: Optional[Dict]) -> Dict[str, Any]:
    if not data:
        return {}
    out: Dict[str, Any] = {}
    for key, value in data.items():
        out[key] = _pt(value)
    return out


class DemoShopifyClient(ShopifyClient):
    """ShopifyClient cujo `_request` lê/grava o catálogo demo."""

    def __init__(self, shop_url: str, access_token: str = "demo_shopify_token"):
        super().__init__(shop_url=shop_url, access_token=access_token)

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None,
    ) -> Dict[str, Any]:
        method = method.upper()
        path = endpoint.split("?")[0]
        params = params or {}
        state = demo_store.get_state()

        if path == "/shop.json":
            cfg = DEMO_STORES["shopify"]
            return {
                "shop": {
                    "name": STORE_NAME,
                    "email": STORE_EMAIL,
                    "domain": cfg["store_url"],
                    "currency": "BRL",
                    "plan_name": "demo",
                }
            }

        if path == "/products.json":
            products = list(state["products"])
            collection_id = params.get("collection_id")
            if collection_id:
                cat = demo_store.find_category(int(collection_id))
                if cat:
                    products = [
                        p for p in products if int(p.get("category_id") or 0) == int(collection_id)
                    ]
            limit = int(params.get("limit") or 50)
            since_id = int(params.get("since_id") or 0)
            if since_id:
                products = [p for p in products if int(p["id"]) > since_id]
            return {"products": [_shopify_product(p) for p in products[:limit]]}

        m = re.fullmatch(r"/products/(\d+)\.json", path)
        if m:
            product = demo_store.find_product(int(m.group(1)))
            if not product:
                raise Exception("Shopify API Error (404): product not found")
            if method == "PUT" and data:
                product.update((data.get("product") or {}))
                demo_store.persist()
            return {"product": _shopify_product(product)}

        m = re.fullmatch(r"/products/(\d+)/metafields\.json", path)
        if m:
            pid = int(m.group(1))
            if method == "POST" and data:
                mf = (data.get("metafield") or {})
                demo_store.upsert_metafield(
                    "product",
                    pid,
                    mf.get("namespace") or "global",
                    mf.get("key") or "",
                    mf.get("value") or "",
                    mf.get("type") or "single_line_text_field",
                )
            return {"metafields": demo_store.metafields_for("product", pid)}

        m = re.fullmatch(r"/products/(\d+)/images/(\d+)\.json", path)
        if m and method == "PUT":
            product = demo_store.find_product(int(m.group(1)))
            image_id = int(m.group(2))
            alt = ((data or {}).get("image") or {}).get("alt")
            if product:
                for img in product.get("images") or []:
                    if int(img["id"]) == image_id:
                        img["alt"] = alt
                demo_store.persist()
            return {"image": {"id": image_id, "alt": alt}}

        if path == "/products/count.json":
            collection_id = params.get("collection_id")
            products = state["products"]
            if collection_id:
                products = [
                    p for p in products if int(p.get("category_id") or 0) == int(collection_id)
                ]
            return {"count": len(products)}

        if path in ("/custom_collections.json",):
            return {
                "custom_collections": [
                    _shopify_collection(c) for c in state["categories"]
                ]
            }
        if path in ("/smart_collections.json",):
            return {"smart_collections": []}

        m = re.fullmatch(r"/(custom|smart)_collections/(\d+)\.json", path)
        if m:
            cat = demo_store.find_category(int(m.group(2)))
            if not cat:
                raise Exception("Shopify API Error (404): collection not found")
            if method == "PUT" and data:
                payload = data.get("custom_collection") or data.get("smart_collection") or data.get("collection") or {}
                cat.update(payload)
                if "title" in payload:
                    cat["name"] = payload["title"]
                if "body_html" in payload:
                    cat["description"] = payload["body_html"]
                demo_store.persist()
            key = "custom_collections" if m.group(1) == "custom" else "smart_collections"
            return {key[:-1] if False else ("custom_collection" if m.group(1) == "custom" else "smart_collection"): _shopify_collection(cat)}

        m = re.fullmatch(r"/(custom|smart)_collections/(\d+)/metafields\.json", path)
        if m:
            cid = int(m.group(2))
            if method == "POST" and data:
                mf = data.get("metafield") or {}
                demo_store.upsert_metafield(
                    "collection",
                    cid,
                    mf.get("namespace") or "global",
                    mf.get("key") or "",
                    mf.get("value") or "",
                    mf.get("type") or "single_line_text_field",
                )
            return {"metafields": demo_store.metafields_for("collection", cid)}

        if path == "/pages.json":
            limit = int(params.get("limit") or 50)
            since_id = int(params.get("since_id") or 0)
            pages = list(state["pages"])
            if since_id:
                pages = [p for p in pages if int(p["id"]) > since_id]
            return {"pages": [_shopify_page(p) for p in pages[:limit]]}

        m = re.fullmatch(r"/pages/(\d+)\.json", path)
        if m:
            page = demo_store.find_page(int(m.group(1)))
            if not page:
                raise Exception("Shopify API Error (404): page not found")
            if method == "PUT" and data:
                page.update(data.get("page") or {})
                demo_store.persist()
            return {"page": _shopify_page(page)}

        m = re.fullmatch(r"/pages/(\d+)/metafields\.json", path)
        if m:
            pid = int(m.group(1))
            if method == "POST" and data:
                mf = data.get("metafield") or {}
                demo_store.upsert_metafield(
                    "page",
                    pid,
                    mf.get("namespace") or "global",
                    mf.get("key") or "",
                    mf.get("value") or "",
                    mf.get("type") or "single_line_text_field",
                )
            return {"metafields": demo_store.metafields_for("page", pid)}

        if path == "/blogs.json":
            return {"blogs": list(state["blogs"])}

        m = re.fullmatch(r"/blogs/(\d+)/articles\.json", path)
        if m:
            blog_id = int(m.group(1))
            articles = [a for a in state["articles"] if int(a["blog_id"]) == blog_id]
            return {"articles": [_shopify_article(a) for a in articles]}

        m = re.fullmatch(r"/blogs/(\d+)/articles/(\d+)\.json", path)
        if m:
            article = demo_store.find_article(int(m.group(2)))
            if not article:
                raise Exception("Shopify API Error (404): article not found")
            if method == "PUT" and data:
                article.update(data.get("article") or {})
                demo_store.persist()
            return {"article": _shopify_article(article)}

        m = re.fullmatch(r"/articles/(\d+)/metafields\.json", path)
        if m:
            aid = int(m.group(1))
            if method == "POST" and data:
                mf = data.get("metafield") or {}
                demo_store.upsert_metafield(
                    "article",
                    aid,
                    mf.get("namespace") or "global",
                    mf.get("key") or "",
                    mf.get("value") or "",
                    mf.get("type") or "single_line_text_field",
                )
            return {"metafields": demo_store.metafields_for("article", aid)}

        return {}


def _shopify_product(product: Dict[str, Any]) -> Dict[str, Any]:
    images = []
    for img in product.get("images") or []:
        images.append({**img, "alt": img.get("alt") or ""})
    return {
        "id": product["id"],
        "title": product.get("title"),
        "handle": product.get("handle"),
        "body_html": product.get("body_html"),
        "vendor": product.get("vendor"),
        "product_type": product.get("product_type"),
        "tags": product.get("tags"),
        "images": images,
    }


def _shopify_collection(category: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": category["id"],
        "title": category.get("name"),
        "handle": category.get("handle"),
        "body_html": category.get("description") or "",
        "image": None,
    }


def _shopify_page(page: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": page["id"],
        "title": page.get("title"),
        "handle": page.get("handle"),
        "body_html": page.get("body_html"),
        "published": True,
    }


def _shopify_article(article: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": article["id"],
        "blog_id": article.get("blog_id"),
        "title": article.get("title"),
        "handle": article.get("handle"),
        "body_html": article.get("body_html"),
        "author": article.get("author"),
        "published": True,
    }


class DemoNuvemshopClient(NuvemshopClient):
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Any:
        method = method.upper()
        path = endpoint.split("?")[0]
        params = params or {}
        payload = _unwrap_pt(data)
        state = demo_store.get_state()
        cfg = DEMO_STORES["nuvemshop"]

        if path == "/store":
            return {
                "id": int(cfg["store_id"]),
                "name": {"pt": STORE_NAME},
                "url_with_protocol": cfg["store_url"],
                "original_domain": "demo-4seo.lojavirtualnuvem.com.br",
                "email": STORE_EMAIL,
                "plan_name": "demo",
                "country": "BR",
                "languages": {"pt": True},
                "blog": f"{cfg['store_url']}/blog",
            }

        if path == "/products":
            products = list(state["products"])
            category_id = params.get("category_id")
            if category_id:
                products = [
                    p for p in products if int(p.get("category_id") or 0) == int(category_id)
                ]
            per_page = int(params.get("per_page") or 50)
            page = int(params.get("page") or 1)
            start = (page - 1) * per_page
            chunk = products[start : start + per_page]
            if not chunk and page > 1:
                raise Exception("Erro API Nuvemshop (404): Last page")
            return [_nuvem_product(p) for p in chunk]

        m = re.fullmatch(r"/products/(\d+)", path)
        if m:
            product = demo_store.find_product(int(m.group(1)))
            if not product:
                raise Exception("Erro API Nuvemshop (404): produto")
            if method == "PUT":
                _apply_nuvem_product(product, payload)
                demo_store.persist()
            return _nuvem_product(product)

        m = re.fullmatch(r"/products/(\d+)/images/(\d+)", path)
        if m and method == "PUT":
            product = demo_store.find_product(int(m.group(1)))
            image_id = int(m.group(2))
            alt = payload.get("alt")
            if product:
                for img in product.get("images") or []:
                    if int(img["id"]) == image_id:
                        img["alt"] = alt
                demo_store.persist()
            return {"id": image_id, "alt": {"pt": alt}}

        if path == "/categories":
            per_page = int(params.get("per_page") or 50)
            page = int(params.get("page") or 1)
            cats = list(state["categories"])
            start = (page - 1) * per_page
            return [_nuvem_category(c, state) for c in cats[start : start + per_page]]

        m = re.fullmatch(r"/categories/(\d+)", path)
        if m:
            cat = demo_store.find_category(int(m.group(1)))
            if not cat:
                raise Exception("Erro API Nuvemshop (404): categoria")
            if method == "PUT":
                for key in ("name", "description", "seo_title", "seo_description", "handle"):
                    if key in payload:
                        cat[key] = payload[key]
                demo_store.persist()
            return _nuvem_category(cat, state)

        if path == "/pages":
            return [_nuvem_page(p) for p in state["pages"]]

        m = re.fullmatch(r"/pages/(\d+)", path)
        if m:
            page = demo_store.find_page(int(m.group(1)))
            if not page:
                raise Exception("Erro API Nuvemshop (404): página")
            if method == "PUT":
                if "title" in payload:
                    page["title"] = payload["title"]
                if "content" in payload:
                    page["body_html"] = payload["content"]
                if "seo_title" in payload:
                    page["seo_title"] = payload["seo_title"]
                if "seo_description" in payload:
                    page["seo_description"] = payload["seo_description"]
                demo_store.persist()
            return _nuvem_page(page)

        if path in ("/blogs", "/blog"):
            return list(state["blogs"])

        m = re.fullmatch(r"/blogs/(\d+)/posts", path)
        if m:
            blog_id = int(m.group(1))
            return [
                _nuvem_article(a)
                for a in state["articles"]
                if int(a["blog_id"]) == blog_id
            ]

        m = re.fullmatch(r"/blogs/(\d+)/posts/(\d+)", path)
        if m:
            article = demo_store.find_article(int(m.group(2)))
            if not article:
                raise Exception("Erro API Nuvemshop (404): post")
            if method == "PUT":
                if "title" in payload:
                    article["title"] = payload["title"]
                if "content" in payload:
                    article["body_html"] = payload["content"]
                if "seo_title" in payload:
                    article["seo_title"] = payload["seo_title"]
                if "seo_description" in payload:
                    article["seo_description"] = payload["seo_description"]
                demo_store.persist()
            return _nuvem_article(article)

        return []


def _nuvem_product(product: Dict[str, Any]) -> Dict[str, Any]:
    images = []
    for img in product.get("images") or []:
        images.append(
            {
                "id": img["id"],
                "src": img.get("src"),
                "alt": {"pt": img.get("alt") or ""},
            }
        )
    return {
        "id": product["id"],
        "name": {"pt": product.get("title")},
        "handle": {"pt": product.get("handle")},
        "description": {"pt": product.get("body_html")},
        "seo_title": {"pt": product.get("seo_title") or ""},
        "seo_description": {"pt": product.get("seo_description") or ""},
        "images": images,
        "variants": [],
        "categories": [{"id": product.get("category_id")}],
        "tags": product.get("tags"),
        "brand": product.get("brand"),
    }


def _apply_nuvem_product(product: Dict[str, Any], payload: Dict[str, Any]) -> None:
    mapping = {
        "name": "title",
        "description": "body_html",
        "seo_title": "seo_title",
        "seo_description": "seo_description",
        "handle": "handle",
        "tags": "tags",
        "brand": "brand",
    }
    for src, dest in mapping.items():
        if src in payload:
            product[dest] = payload[src]


def _nuvem_category(category: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    count = sum(
        1
        for p in state["products"]
        if int(p.get("category_id") or 0) == int(category["id"])
    )
    return {
        "id": category["id"],
        "name": {"pt": category.get("name")},
        "handle": {"pt": category.get("handle")},
        "description": {"pt": category.get("description") or ""},
        "seo_title": {"pt": category.get("seo_title") or ""},
        "seo_description": {"pt": category.get("seo_description") or ""},
        "parent": None,
        "subcategories": [],
        "products_count": count,
    }


def _nuvem_page(page: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": page["id"],
        "title": {"pt": page.get("title")},
        "handle": {"pt": page.get("handle")},
        "content": {"pt": page.get("body_html")},
        "seo_title": {"pt": page.get("seo_title") or ""},
        "seo_description": {"pt": page.get("seo_description") or ""},
        "published": True,
    }


def _nuvem_article(article: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": article["id"],
        "title": {"pt": article.get("title")},
        "handle": {"pt": article.get("handle")},
        "content": {"pt": article.get("body_html")},
        "seo_title": {"pt": article.get("seo_title") or ""},
        "seo_description": {"pt": article.get("seo_description") or ""},
        "author": {"name": article.get("author")},
    }


class DemoVtexClient(VtexClient):
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Any:
        method = method.upper()
        path = endpoint.split("?")[0]
        params = params or {}
        state = demo_store.get_state()

        if path == "/api/catalog_system/pvt/products/GetProductAndSkuIds":
            ids = {str(p["id"]): [p["id"] * 10] for p in state["products"]}
            return {"data": ids}

        if path == "/api/catalog_system/pub/products/search":
            products = list(state["products"])
            fq = str(params.get("fq") or "")
            if fq.startswith("C:"):
                cid = int(fq.split(":", 1)[1])
                products = [p for p in products if int(p.get("category_id") or 0) == cid]
            start = int(params.get("_from") or 0)
            end = int(params.get("_to") or start + 49) + 1
            return [_vtex_search(p, self.store_url) for p in products[start:end]]

        if path.startswith("/api/catalog_system/pub/category/tree/"):
            return [_vtex_tree_node(c) for c in state["categories"]]

        m = re.fullmatch(r"/api/catalog/pvt/product/(\d+)", path)
        if m:
            product = demo_store.find_product(int(m.group(1)))
            if not product:
                from app.integrations.vtex import VtexNotFoundError

                raise VtexNotFoundError(path)
            if method == "PUT" and isinstance(data, dict):
                _apply_vtex_product(product, data)
                demo_store.persist()
            return _vtex_product_raw(product)

        m = re.fullmatch(r"/api/catalog/pvt/category/(\d+)", path)
        if m:
            cat = demo_store.find_category(int(m.group(1)))
            if not cat:
                from app.integrations.vtex import VtexNotFoundError

                raise VtexNotFoundError(path)
            if method == "PUT" and isinstance(data, dict):
                if "Name" in data:
                    cat["name"] = data["Name"]
                if "Title" in data:
                    cat["seo_title"] = data["Title"]
                if "Description" in data:
                    cat["description"] = data["Description"]
                if "Keywords" in data:
                    cat["keywords"] = data["Keywords"]
                demo_store.persist()
            return _vtex_category_raw(cat)

        return {}


def _vtex_search(product: Dict[str, Any], store_url: str) -> Dict[str, Any]:
    images = [
        {
            "imageId": str(img["id"]),
            "imageUrl": img.get("src"),
            "imageText": img.get("alt"),
        }
        for img in product.get("images") or []
    ]
    return {
        "productId": str(product["id"]),
        "productName": product.get("title"),
        "productTitle": product.get("seo_title") or product.get("title"),
        "linkText": product.get("handle"),
        "description": product.get("body_html"),
        "metaTagDescription": product.get("seo_description"),
        "brand": product.get("brand"),
        "items": [{"images": images}],
    }


def _vtex_product_raw(product: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "Id": product["id"],
        "Name": product.get("title"),
        "Title": product.get("seo_title") or "",
        "Description": product.get("body_html") or "",
        "DescriptionShort": "",
        "MetaTagDescription": product.get("seo_description") or "",
        "KeyWords": product.get("keywords") or "",
        "LinkId": product.get("handle"),
        "CategoryId": product.get("category_id"),
        "BrandId": 1,
        "IsActive": True,
        "IsVisible": True,
        "RefId": str(product["id"]),
    }


def _apply_vtex_product(product: Dict[str, Any], data: Dict[str, Any]) -> None:
    if "Name" in data:
        product["title"] = data["Name"]
    if "Title" in data:
        product["seo_title"] = data["Title"]
    if "Description" in data:
        product["body_html"] = data["Description"]
    if "MetaTagDescription" in data:
        product["seo_description"] = data["MetaTagDescription"]
    if "KeyWords" in data:
        product["keywords"] = data["KeyWords"]
    if "LinkId" in data:
        product["handle"] = data["LinkId"]


def _vtex_tree_node(category: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": category["id"],
        "name": category.get("name"),
        "Title": category.get("seo_title") or category.get("name"),
        "url": f"/categoria/{category.get('handle')}",
        "children": [],
    }


def _vtex_category_raw(category: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "Id": category["id"],
        "Name": category.get("name"),
        "Title": category.get("seo_title") or "",
        "Description": category.get("description") or "",
        "Keywords": category.get("keywords") or "",
        "FatherCategoryId": None,
        "IsActive": True,
        "LinkId": category.get("handle"),
        "HasChildren": False,
    }


class DemoLojaIntegradaClient(LojaIntegradaClient):
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Any:
        method = method.upper()
        path = endpoint.split("?")[0]
        if not path.endswith("/") and not path.startswith("/seo/"):
            # LI usa trailing slash em listagens
            pass
        params = params or {}
        state = demo_store.get_state()
        self.store_url = DEMO_STORES["lojaintegrada"]["store_url"]

        if path in ("/categoria/", "/categoria"):
            cats = list(state["categories"])
            categoria_id = params.get("categoria")
            if categoria_id:
                cats = [c for c in cats if int(c["id"]) == int(categoria_id)]
            return _li_list([_li_category_list(c) for c in cats], params)

        m = re.fullmatch(r"/categoria/(\d+)/?", path)
        if m:
            cat = demo_store.find_category(int(m.group(1)))
            if not cat:
                from app.integrations.lojaintegrada import LojaIntegradaNotFoundError

                raise LojaIntegradaNotFoundError(path)
            if method == "PUT" and data:
                if "nome" in data:
                    cat["name"] = data["nome"]
                if "descricao" in data:
                    cat["description"] = data["descricao"]
                demo_store.persist()
            return _li_category_detail(cat)

        if path in ("/produto/", "/produto"):
            products = list(state["products"])
            categoria = params.get("categoria")
            if categoria:
                products = [
                    p for p in products if int(p.get("category_id") or 0) == int(categoria)
                ]
            return _li_list([_li_product_list(p) for p in products], params)

        m = re.fullmatch(r"/produto/(\d+)/?", path)
        if m:
            product = demo_store.find_product(int(m.group(1)))
            if not product:
                from app.integrations.lojaintegrada import LojaIntegradaNotFoundError

                raise LojaIntegradaNotFoundError(path)
            if method == "PUT" and data:
                if "nome" in data:
                    product["title"] = data["nome"]
                if "descricao_completa" in data:
                    product["body_html"] = data["descricao_completa"]
                if "apelido" in data:
                    product["handle"] = data["apelido"]
                demo_store.persist()
            return _li_product_detail(product)

        if path in ("/seo/", "/seo") and method == "POST":
            created = demo_store.upsert_seo(None, data or {})
            return {**created, "resource_uri": f"/api/v1/seo/{created['id']}"}

        m = re.fullmatch(r"/seo/(\d+)/?", path)
        if m:
            seo_id = int(m.group(1))
            if method == "PUT" and data:
                return demo_store.upsert_seo(seo_id, data)
            seo = demo_store.get_seo(seo_id) or {"id": seo_id, "title": "", "description": "", "keyword": ""}
            return seo

        return {}


def _li_list(objects: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
    limit = int(params.get("limit") or 50)
    offset = int(params.get("offset") or 0)
    chunk = objects[offset : offset + limit]
    nxt = None
    if offset + limit < len(objects):
        nxt = f"?limit={limit}&offset={offset + limit}"
    return {
        "meta": {
            "limit": limit,
            "offset": offset,
            "total_count": len(objects),
            "next": nxt,
            "previous": None,
        },
        "objects": chunk,
    }


def _li_product_list(product: Dict[str, Any]) -> Dict[str, Any]:
    cfg = DEMO_STORES["lojaintegrada"]
    return {
        "id": product["id"],
        "nome": product.get("title"),
        "apelido": product.get("handle"),
        "url": f"{cfg['store_url']}/produto/{product.get('handle')}",
        "ativo": True,
        "imagem_principal": (product.get("images") or [{}])[0],
        "seo": f"/api/v1/seo/{product.get('seo_id')}",
    }


def _li_product_detail(product: Dict[str, Any]) -> Dict[str, Any]:
    row = _li_product_list(product)
    row["descricao_completa"] = product.get("body_html") or ""
    return row


def _li_category_list(category: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": category["id"],
        "nome": category.get("name"),
        "descricao": category.get("description") or "",
        "seo": f"/api/v1/seo/{category.get('seo_id')}",
        "categoria_pai": None,
    }


def _li_category_detail(category: Dict[str, Any]) -> Dict[str, Any]:
    return _li_category_list(category)


def create_demo_shopify_client(shop_url: Optional[str] = None) -> DemoShopifyClient:
    url = shop_url or DEMO_STORES["shopify"]["store_url"]
    return DemoShopifyClient(shop_url=url, access_token=DEMO_STORES["shopify"]["token"])


def create_demo_nuvemshop_client(store_id: Optional[str] = None) -> DemoNuvemshopClient:
    sid = store_id or DEMO_STORES["nuvemshop"]["store_id"]
    return DemoNuvemshopClient(sid, DEMO_STORES["nuvemshop"]["token"])


def create_demo_vtex_client(account_name: Optional[str] = None) -> DemoVtexClient:
    cfg = DEMO_STORES["vtex"]
    return DemoVtexClient(
        account_name=account_name or cfg["account_name"],
        app_key=cfg["app_key"],
        app_token=cfg["token"],
    )


def create_demo_lojaintegrada_client(chave_api: Optional[str] = None) -> DemoLojaIntegradaClient:
    token = chave_api or DEMO_STORES["lojaintegrada"]["token"]
    return DemoLojaIntegradaClient(token, "demo_app_key")
