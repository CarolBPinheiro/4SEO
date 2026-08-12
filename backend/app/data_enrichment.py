"""
Data Enrichment Pipeline
Enriquece o payload enviado à IA com dados de mercado,
SERP, keywords e atributos do produto.
"""
import re
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


async def enrich_product_context(
    product_data: Dict[str, Any],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enriquece o contexto de um produto ANTES de enviar para IA.

    Adiciona:
    - Keywords estratégicas via SearchAPI (top SERP keywords)
    - Dados competitivos da SERP (top 5 resultados)
    - Atributos extraídos do produto
    - Segmento inferido
    """
    enriched = dict(product_data)  # não modifica o original

    # 1. Extrair atributos descritivos do produto
    enriched["atributos_extraidos"] = _extract_product_attributes(product_data)

    # 2. Inferir segmento da loja
    enriched["segmento"] = _infer_segment(product_data)

    # 3. Buscar keywords estratégicas via SearchAPI (se configurada)
    enriched["keywords_mercado"] = []
    enriched["serp_data"] = []
    try:
        from app.integrations.searchapi_client import fetch_serp, SEARCHAPI_KEY
        if SEARCHAPI_KEY:
            keyword_alvo = product_data.get("name") or product_data.get("title", "")
            if keyword_alvo:
                serp = await fetch_serp(keyword_alvo, num_results=5)
                enriched["serp_data"] = serp.get("results", [])
                # Extrair keywords dos títulos dos concorrentes no SERP
                enriched["keywords_mercado"] = _extract_serp_keywords(serp)
    except Exception as e:
        logger.warning(f"[enrichment] SERP fetch falhou: {e}")

    # 4. Preservar o payload original para fallback
    return enriched


def _extract_product_attributes(product: Dict[str, Any]) -> List[str]:
    """Extrai atributos descritivos do produto."""
    attrs = []

    # De tags
    tags = product.get("tags", "")
    if isinstance(tags, str) and tags.strip():
        attrs.extend([t.strip() for t in tags.split(",") if t.strip()])

    # De variantes
    variants = product.get("variants") or []
    for v in variants[:3]:
        if isinstance(v, dict):
            for key in ("option1", "option2", "option3"):
                val = v.get(key, "")
                if isinstance(val, str) and val.strip():
                    attrs.append(val.strip())

    # De campos comuns
    for field in ("product_type", "brand", "vendor", "material", "color", "size"):
        val = product.get(field, "")
        if isinstance(val, str) and val.strip():
            attrs.append(val.strip())

    # De categorias
    categories = product.get("categories") or []
    for cat in categories:
        name = cat.get("name") if isinstance(cat, dict) else str(cat)
        # Nuvemshop usa nomes multilíngues: {"name": {"pt": "..."}}
        if isinstance(name, dict):
            name = name.get("pt") or next(iter(name.values()), "")
        if isinstance(name, str) and name.strip():
            attrs.append(name.strip())

    # Remover duplicatas mantendo ordem
    seen = set()
    unique = []
    for a in attrs:
        al = a.lower()
        if al not in seen:
            seen.add(al)
            unique.append(a)

    return unique[:15]


def _infer_segment(product: Dict[str, Any]) -> str:
    """Infere o segmento de mercado com base nos dados do produto."""
    type_str = (
        product.get("product_type") or
        product.get("category") or
        product.get("name") or
        ""
    ).lower()

    segment_map = {
        "moda": ["roupa", "camiseta", "vestido", "calça", "blusa", "sapato", "tênis", "sandália", "bolsa", "acessório"],
        "casa": ["casa", "decoração", "móvel", "cozinha", "banheiro", "quarto", "sala", "jardim"],
        "eletrônicos": ["celular", "notebook", "tablet", "fone", "carregador", "eletrônico", "smartphone"],
        "esportes": ["esporte", "academia", "fitness", "bicicleta", "yoga", "corrida", "musculação"],
        "beleza": ["beleza", "maquiagem", "perfume", "creme", "shampoo", "cosmético", "skincare"],
        "alimenticio": ["alimento", "bebida", "comida", "doce", "café", "chá", "suplemento"],
        "pet": ["pet", "cachorro", "gato", "ração", "brinquedo"],
        "infantil": ["infantil", "bebê", "criança", "brinquedo", "fralda"],
        "moveis": ["móvel", "sofá", "cadeira", "mesa", "estante", "guarda-roupa"],
        "joias": ["joia", "anel", "colar", "brinco", "pulseira", "ouro", "prata"],
    }

    for segmento, termos in segment_map.items():
        for termo in termos:
            if termo in type_str:
                return segmento

    return "ecommerce"


def _extract_serp_keywords(serp_data: Dict[str, Any]) -> List[str]:
    """Extrai keywords relevantes dos títulos dos concorrentes no SERP."""
    results = serp_data.get("results", [])
    keywords = set()
    for r in results[:5]:
        title = r.get("title", "")
        # Extrai palavras com 4+ caracteres (filtra stopwords)
        words = re.findall(r'[a-zA-ZÀ-ÿ]{4,}', title.lower())
        keywords.update(words)
    # Remove termos muito genéricos
    stopwords = {"para", "como", "seu", "sua", "com", "que", "mais", "aqui", "onde", "das", "dos", "uma"}
    return list(keywords - stopwords)[:10]
