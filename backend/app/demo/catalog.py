"""Catálogo fixture compartilhado pelas quatro plataformas demo.

Produtos deliberadamente quebrados (title curto, meta vazia, imagem sem alt)
para a Análise e o scan exibirem oportunidades reais.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

STORE_NAME = "Loja Demo 4SEO"
STORE_EMAIL = "contato@demo.4seo.local"

CATEGORIES: List[Dict[str, Any]] = [
    {
        "id": 101,
        "name": "Tênis",
        "handle": "tenis",
        "description": "",
        "seo_title": "",
        "seo_description": "",
        "keywords": "",
    },
    {
        "id": 102,
        "name": "Camisetas",
        "handle": "camisetas",
        "description": "Camisetas de algodão",
        "seo_title": "Camisetas",
        "seo_description": "Camisetas",
        "keywords": "camiseta",
    },
    {
        "id": 103,
        "name": "Acessórios",
        "handle": "acessorios",
        "description": "Bolsas, cintos e mais para completar o look do dia a dia com estilo.",
        "seo_title": "Acessórios de moda feminina e masculina | Loja Demo 4SEO",
        "seo_description": (
            "Compre acessórios de moda com frete rápido. Bolsas, cintos e carteiras "
            "com os melhores preços da Loja Demo 4SEO."
        ),
        "keywords": "acessorios, bolsa, cinto",
    },
    {
        "id": 104,
        "name": "Outlet",
        "handle": "outlet",
        "description": "",
        "seo_title": "",
        "seo_description": "",
        "keywords": "",
    },
]

PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Tênis",
        "handle": "tenis-run",
        "body_html": "<p>Tênis confortável.</p>",
        "vendor": "DemoSport",
        "product_type": "Tênis",
        "tags": "",
        "seo_title": "",
        "seo_description": "",
        "keywords": "",
        "category_id": 101,
        "brand": "DemoSport",
        "images": [
            {"id": 11, "src": "https://placehold.co/600x600?text=Tenis", "alt": None, "position": 1},
        ],
    },
    {
        "id": 2,
        "title": "Camiseta Básica Algodão Masculina Azul Marinho Premium Comfort Fit",
        "handle": "camiseta-basica-azul",
        "body_html": "<h1>Camiseta</h1><h1>Algodão</h1><p>Camiseta 100% algodão.</p>",
        "vendor": "DemoWear",
        "product_type": "Camisetas",
        "tags": "algodao",
        "seo_title": "Camiseta",
        "seo_description": "Camiseta boa",
        "keywords": "camiseta",
        "category_id": 102,
        "brand": "DemoWear",
        "images": [
            {"id": 21, "src": "https://placehold.co/600x600?text=Camiseta", "alt": None, "position": 1},
        ],
    },
    {
        "id": 3,
        "title": "Bolsa tote lona",
        "handle": "bolsa-tote",
        "body_html": "<p>Bolsa tote de lona resistente para o dia a dia.</p>",
        "vendor": "DemoBag",
        "product_type": "Acessórios",
        "tags": "bolsa, tote",
        "seo_title": "",
        "seo_description": "",
        "keywords": "",
        "category_id": 103,
        "brand": "DemoBag",
        "images": [
            {"id": 31, "src": "https://placehold.co/600x600?text=Bolsa", "alt": "Bolsa tote lona bege", "position": 1},
        ],
    },
    {
        "id": 4,
        "title": "Tênis casual branco",
        "handle": "tenis-casual-branco",
        "body_html": "",
        "vendor": "DemoSport",
        "product_type": "Tênis",
        "tags": "",
        "seo_title": "",
        "seo_description": "",
        "keywords": "",
        "category_id": 101,
        "brand": "DemoSport",
        "images": [
            {"id": 41, "src": "https://placehold.co/600x600?text=Casual", "alt": None, "position": 1},
        ],
    },
    {
        "id": 5,
        "title": "Cinto couro",
        "handle": "cinto-couro",
        "body_html": "<p>Cinto.</p>",
        "vendor": "DemoBag",
        "product_type": "Acessórios",
        "tags": "cinto",
        "seo_title": "Cinto",
        "seo_description": "",
        "keywords": "cinto",
        "category_id": 103,
        "brand": "DemoBag",
        "images": [],
    },
    {
        "id": 6,
        "title": "Camiseta estampada feminina",
        "handle": "camiseta-estampada",
        "body_html": "<p>Estampa exclusiva da coleção verão.</p>",
        "vendor": "DemoWear",
        "product_type": "Camisetas",
        "tags": "feminino, verao",
        "seo_title": "Camiseta estampada feminina | DemoWear",
        "seo_description": (
            "Camiseta estampada feminina em algodão. Compre na Loja Demo 4SEO "
            "com frete rápido e troca fácil."
        ),
        "keywords": "camiseta feminina, estampada",
        "category_id": 102,
        "brand": "DemoWear",
        "images": [
            {"id": 61, "src": "https://placehold.co/600x600?text=Estampa", "alt": "Camiseta estampada feminina", "position": 1},
        ],
    },
    {
        "id": 7,
        "title": "Tênis running 42",
        "handle": "tenis-running-42",
        "body_html": "<p>Amortecimento para corrida.</p>",
        "vendor": "DemoSport",
        "product_type": "Tênis",
        "tags": "running",
        "seo_title": "",
        "seo_description": "Tênis bom",
        "keywords": "",
        "category_id": 101,
        "brand": "DemoSport",
        "images": [
            {"id": 71, "src": "https://placehold.co/600x600?text=Run", "alt": None, "position": 1},
        ],
    },
    {
        "id": 8,
        "title": "Carteira slim",
        "handle": "carteira-slim",
        "body_html": "<p>Carteira compacta de couro sintético.</p>",
        "vendor": "DemoBag",
        "product_type": "Acessórios",
        "tags": "",
        "seo_title": "Carteira",
        "seo_description": "",
        "keywords": "",
        "category_id": 103,
        "brand": "DemoBag",
        "images": [
            {"id": 81, "src": "https://placehold.co/600x600?text=Carteira", "alt": None, "position": 1},
        ],
    },
    {
        "id": 9,
        "title": "Camiseta oversized",
        "handle": "camiseta-oversized",
        "body_html": "<p>Corte oversized unissex.</p>",
        "vendor": "DemoWear",
        "product_type": "Camisetas",
        "tags": "oversized",
        "seo_title": "",
        "seo_description": "",
        "keywords": "oversized",
        "category_id": 102,
        "brand": "DemoWear",
        "images": [
            {"id": 91, "src": "https://placehold.co/600x600?text=Over", "alt": None, "position": 1},
        ],
    },
    {
        "id": 10,
        "title": "Meia esportiva kit 3",
        "handle": "meia-esportiva",
        "body_html": "<p>Kit com 3 pares.</p>",
        "vendor": "DemoSport",
        "product_type": "Acessórios",
        "tags": "meia",
        "seo_title": "",
        "seo_description": "",
        "keywords": "",
        "category_id": 104,
        "brand": "DemoSport",
        "images": [
            {"id": 101, "src": "https://placehold.co/600x600?text=Meia", "alt": None, "position": 1},
        ],
    },
    {
        "id": 11,
        "title": "Boné aba curva",
        "handle": "bone-aba-curva",
        "body_html": "<p>Boné ajustável.</p>",
        "vendor": "DemoWear",
        "product_type": "Acessórios",
        "tags": "bone",
        "seo_title": "Boné",
        "seo_description": "Boné legal",
        "keywords": "bone",
        "category_id": 104,
        "brand": "DemoWear",
        "images": [
            {"id": 111, "src": "https://placehold.co/600x600?text=Bone", "alt": None, "position": 1},
        ],
    },
    {
        "id": 12,
        "title": "Tênis slip on",
        "handle": "tenis-slip-on",
        "body_html": "<p>Entrada fácil, palmilha macia.</p>",
        "vendor": "DemoSport",
        "product_type": "Tênis",
        "tags": "slipon",
        "seo_title": "Tênis slip on unissex | DemoSport",
        "seo_description": (
            "Tênis slip on unissex com palmilha macia. Frete rápido na Loja Demo 4SEO."
        ),
        "keywords": "slip on, tenis casual",
        "category_id": 101,
        "brand": "DemoSport",
        "images": [
            {"id": 121, "src": "https://placehold.co/600x600?text=Slip", "alt": "Tênis slip on preto", "position": 1},
        ],
    },
]

PAGES: List[Dict[str, Any]] = [
    {
        "id": 201,
        "title": "Sobre",
        "handle": "sobre",
        "body_html": "<p>Somos a Loja Demo 4SEO.</p>",
        "seo_title": "",
        "seo_description": "",
    },
    {
        "id": 202,
        "title": "Trocas e devoluções política completa da loja demo 4seo para clientes",
        "handle": "trocas",
        "body_html": "<h1>Trocas</h1><h1>Devoluções</h1>",
        "seo_title": "Trocas",
        "seo_description": "Política",
    },
    {
        "id": 203,
        "title": "Contato",
        "handle": "contato",
        "body_html": "<p>Fale conosco pelo e-mail contato@demo.4seo.local.</p>",
        "seo_title": "Contato | Loja Demo 4SEO",
        "seo_description": "Fale com a Loja Demo 4SEO. Atendimento em horário comercial.",
    },
]

BLOGS: List[Dict[str, Any]] = [
    {"id": 301, "title": "Blog", "handle": "blog"},
]

ARTICLES: List[Dict[str, Any]] = [
    {
        "id": 401,
        "blog_id": 301,
        "title": "Como escolher tênis",
        "handle": "como-escolher-tenis",
        "body_html": "<p>Dicas rápidas.</p>",
        "seo_title": "",
        "seo_description": "",
        "author": "Equipe Demo",
    },
    {
        "id": 402,
        "blog_id": 301,
        "title": "Tendências de verão 2026 para moda casual urbana",
        "handle": "tendencias-verao",
        "body_html": "<p>Cores e cortes da estação.</p>",
        "seo_title": "Tendências",
        "seo_description": "Verão",
        "author": "Equipe Demo",
    },
]


def fresh_state() -> Dict[str, Any]:
    """Estado mutável do catálogo (produtos/categorias/páginas + metafields)."""
    products = deepcopy(PRODUCTS)
    metafields: Dict[str, List[Dict[str, Any]]] = {}
    next_mf = 9000
    for product in products:
        key = f"product:{product['id']}"
        mfs: List[Dict[str, Any]] = []
        if product.get("seo_title"):
            next_mf += 1
            mfs.append(
                {
                    "id": next_mf,
                    "namespace": "global",
                    "key": "title_tag",
                    "value": product["seo_title"],
                    "type": "single_line_text_field",
                }
            )
        if product.get("seo_description"):
            next_mf += 1
            mfs.append(
                {
                    "id": next_mf,
                    "namespace": "global",
                    "key": "description_tag",
                    "value": product["seo_description"],
                    "type": "single_line_text_field",
                }
            )
        metafields[key] = mfs
    for page in PAGES:
        key = f"page:{page['id']}"
        mfs = []
        if page.get("seo_title"):
            next_mf += 1
            mfs.append(
                {
                    "id": next_mf,
                    "namespace": "global",
                    "key": "title_tag",
                    "value": page["seo_title"],
                    "type": "single_line_text_field",
                }
            )
        if page.get("seo_description"):
            next_mf += 1
            mfs.append(
                {
                    "id": next_mf,
                    "namespace": "global",
                    "key": "description_tag",
                    "value": page["seo_description"],
                    "type": "single_line_text_field",
                }
            )
        metafields[key] = mfs
    seos: Dict[int, Dict[str, Any]] = {}
    next_seo = 500
    for product in products:
        next_seo += 1
        seos[str(next_seo)] = {
            "id": next_seo,
            "title": product.get("seo_title") or "",
            "description": product.get("seo_description") or "",
            "keyword": product.get("keywords") or "",
            "base_uri": f"/produto/{product['id']}/",
        }
        product["seo_id"] = next_seo
    for category in CATEGORIES:
        next_seo += 1
        seos[str(next_seo)] = {
            "id": next_seo,
            "title": category.get("seo_title") or "",
            "description": category.get("seo_description") or "",
            "keyword": category.get("keywords") or "",
            "base_uri": f"/categoria/{category['id']}/",
        }
        category["seo_id"] = next_seo
    return {
        "products": products,
        "categories": deepcopy(CATEGORIES),
        "pages": deepcopy(PAGES),
        "blogs": deepcopy(BLOGS),
        "articles": deepcopy(ARTICLES),
        "metafields": metafields,
        "seos": seos,
        "next_metafield_id": next_mf + 1,
        "next_seo_id": next_seo + 1,
    }
