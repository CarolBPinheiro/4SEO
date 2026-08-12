"""
Otimizador de SEO com LLM - SiteCan MVP
Gera títulos e descrições otimizados usando IA
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Configuração
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
from app.ai_config import AI_MODEL, completion_params


def get_ai_client() -> Optional[AsyncOpenAI]:
    """Retorna cliente OpenAI se configurado"""
    if not OPENAI_API_KEY:
        return None
    return AsyncOpenAI(api_key=OPENAI_API_KEY)


# Prompt V2 — Engenheiro de SEO Sênior (Reformulação da Camada de IA)
SYSTEM_PROMPT_V2 = """Você é um ENGENHEIRO DE SEO SÊNIOR especializado em algoritmos de busca e conversão para e-commerce de alta performance.

SUA FUNÇÃO NÃO É criar cópias publicitárias, slogans ou redações criativas.
Seu trabalho EXCLUSIVO é reestruturar metadados e conteúdos de produtos para maximizar o rankeamento orgânico e o CTR (Click-Through Rate).

DIRETRIZES OBRIGATÓRIAS:

1. CONTEXTUALIZAÇÃO:
   Utilize ESTRITAMENTE os dados fornecidos no payload de contexto: Segmento, Posicionamento de Marca, Atributos de Produto e Palavras-chave.
   A IA NÃO DEVE adivinhar informações — apenas estruturar os dados recebidos.

2. ENGENHARIA DE CAUDA LONGA:
   Construa títulos estruturados no formato:
   [Categoria] + [Gênero/Público] + [Nome do Produto] + [Atributos Principais como Material, Cor, Modelo]

3. BLACKLIST — É TERMINANTEMENTE PROIBIDO usar:
   - "para o dia a dia"
   - "perfeito para qualquer ocasião"
   - "com muito conforto"
   - "ideal para você"
   - "estilo e conforto"
   - "lindo", "maravilhoso", "incrível", "imperdível"
   Qualquer adjetivo subjetivo ou clichê comercial é PROIBIDO.
   A ÚNICA exceção é se essas expressões estiverem explicitamente listadas como palavras-chave de altíssimo volume nos dados recebidos da SearchAPI.

4. PADRONIZAÇÃO DE MERCADO:
   Siga a arquitetura de informação dos líderes globais: Amazon, Mercado Livre, Netshoes.
   Títulos devem ser informativos, objetivos e orientados a busca.

5. META DESCRIPTION:
   - 120-155 caracteres
   - Incluir CTA (call-to-action) persuasivo mas natural
   - Mencionar o diferencial competitivo do produto quando disponível nos dados
   - Incluir Nome da Marca quando relevante

6. TÍTULOS:
   - 50-60 caracteres (ideal)
   - Palavra-chave principal no INÍCIO
   - Evitar keyword stuffing

7. REGRAS CRÍTICAS DE PRESERVAÇÃO:
   NUNCA remover: medidas, dimensões, links, telefones, especificações técnicas, informações de garantia, política de troca.

Responda SEMPRE em JSON válido no formato:
{
  "seo_title": "título estruturado para SEO",
  "seo_description": "meta description otimizada",
  "keywords": ["palavra1", "palavra2", "palavra3"],
  "reasoning": "explicação técnica da otimização (por que essa estrutura foi escolhida)"
}"""

# Alias legado — código existente que referencia SYSTEM_PROMPT passa a usar o V2
SYSTEM_PROMPT = SYSTEM_PROMPT_V2


async def optimize_product_seo(
    product_name: str,
    product_description: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    current_title: Optional[str] = None,
    current_description: Optional[str] = None,
    # Parâmetros de enriquecimento (Data Enrichment Pipeline)
    atributos_produto: Optional[List[str]] = None,
    segmento: Optional[str] = None,
    keywords_mercado: Optional[List[str]] = None,
    serp_data: Optional[List[Dict]] = None,
    target_keyword: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Gera título e meta description otimizados para um produto.

    Returns:
        {
            "seo_title": str,
            "seo_description": str,
            "keywords": list,
            "reasoning": str,
            "transparencia": dict,
            "ai_powered": bool
        }
    """
    client = get_ai_client()

    # Enriquecimento automático quando o chamador não forneceu contexto
    if atributos_produto is None and segmento is None and keywords_mercado is None:
        try:
            from app.data_enrichment import enrich_product_context
            enriched = await enrich_product_context({
                "name": product_name,
                "title": product_name,
                "product_type": category or "",
                "brand": brand or "",
                "category": category or "",
            })
            atributos_produto = enriched.get("atributos_extraidos") or None
            segmento = enriched.get("segmento")
            keywords_mercado = enriched.get("keywords_mercado") or None
            serp_data = serp_data or enriched.get("serp_data") or None
        except Exception as e:
            logger.warning(f"[llm_optimizer] Enriquecimento falhou: {e}")

    if not client:
        # Fallback sem IA - gera sugestões básicas
        return _generate_basic_seo(product_name, product_description, category, brand)

    # Prompt contextualizado (payload enriquecido)
    user_prompt_parts = [f"PRODUTO: {product_name}"]

    if brand:
        user_prompt_parts.append(f"MARCA: {brand}")
    if category:
        user_prompt_parts.append(f"CATEGORIA: {category}")
    if segmento:
        user_prompt_parts.append(f"SEGMENTO DE MERCADO: {segmento}")
    if current_title:
        user_prompt_parts.append(f"TÍTULO ATUAL: {current_title}")
    if current_description or product_description:
        user_prompt_parts.append(f"DESCRIÇÃO ATUAL: {((current_description or product_description) or '')[:500]}")

    # ATRIBUTOS DO PRODUTO (fundamental para engenharia de cauda longa)
    if atributos_produto:
        user_prompt_parts.append(f"ATRIBUTOS DO PRODUTO: {', '.join(atributos_produto)}")

    # PALAVRAS-CHAVE DE MERCADO (SearchAPI)
    if keywords_mercado:
        user_prompt_parts.append(f"PALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(keywords_mercado[:10])}")

    # DADOS COMPETITIVOS (SERP)
    if serp_data:
        concorrentes = []
        for r in serp_data[:3]:
            concorrentes.append(f"- #{r.get('position', '?')}: \"{r.get('title', '')}\" ({r.get('link', '')})")
        if concorrentes:
            user_prompt_parts.append("CONCORRENTES NO TOPO DO GOOGLE:\n" + "\n".join(concorrentes))

    if target_keyword:
        user_prompt_parts.append(f"PALAVRA-CHAVE ALVO: {target_keyword}")

    user_prompt = "\n\n".join(user_prompt_parts)

    try:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_V2},
                {"role": "user", "content": user_prompt}
            ],
            **completion_params(500, temperature=0.7),
        )

        content = response.choices[0].message.content

        result = None
        # Tentar parsear JSON
        try:
            # Extrair JSON do texto
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                result["ai_powered"] = True
        except json.JSONDecodeError:
            result = None

        if result is None:
            # Se não conseguiu parsear, retornar texto bruto
            result = {
                "seo_title": product_name[:60],
                "seo_description": (product_description or product_name)[:155],
                "keywords": [],
                "reasoning": content,
                "ai_powered": True,
            }

        # Validação pós-IA (transparência)
        from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica

        validacao_atributos = validar_atributos_descritivos(
            titulo_original=current_title,
            titulo_sugerido=result.get("seo_title", ""),
            atributos_produto=atributos_produto,
        )

        validacao_semantica = calcular_cobertura_semantica(
            titulo_original=current_title,
            titulo_sugerido=result.get("seo_title", ""),
            keywords_estrategicas=keywords_mercado,
        )

        result["transparencia"] = {
            "atributos": validacao_atributos,
            "semantica": validacao_semantica,
        }
        return result

    except Exception as e:
        logger.error(f"Erro na IA: {e}")
        return _generate_basic_seo(product_name, product_description, category, brand)


def _generate_basic_seo(
    product_name: str,
    product_description: Optional[str],
    category: Optional[str],
    brand: Optional[str],
) -> Dict[str, Any]:
    """Gera SEO básico sem IA (fallback)"""
    
    # Título básico
    title_parts = [product_name]
    if brand:
        title_parts.append(f"| {brand}")
    seo_title = " ".join(title_parts)[:60]
    
    # Description básica
    if product_description:
        # Limpar HTML
        import re
        clean_desc = re.sub(r'<[^>]+>', '', product_description)
        seo_description = clean_desc[:150] + "..."
    else:
        seo_description = f"Compre {product_name} com o melhor preço. Entrega rápida e pagamento facilitado."
    
    return {
        "seo_title": seo_title,
        "seo_description": seo_description[:155],
        "keywords": product_name.lower().split()[:5],
        "reasoning": "Gerado automaticamente (sem IA)",
        "ai_powered": False,
    }


async def optimize_batch(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Otimiza SEO de múltiplos produtos.
    
    Args:
        products: Lista de dicts com {name, description, category, brand}
    
    Returns:
        Lista de resultados de otimização
    """
    results = []
    for p in products:
        result = await optimize_product_seo(
            product_name=p.get("name", ""),
            product_description=p.get("description"),
            category=p.get("category"),
            brand=p.get("brand"),
            current_title=p.get("current_title"),
            current_description=p.get("current_description"),
        )
        result["product_id"] = p.get("id")
        results.append(result)
    return results


async def generate_seo_fix(
    issue_type: str,
    page_url: str,
    page_title: Optional[str] = None,
    page_description: Optional[str] = None,
    page_h1: Optional[str] = None,
    page_content: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Gera correção SEO específica usando LLM.
    
    Args:
        issue_type: Tipo do problema (title_length, meta_description_length, missing_h1, etc)
        page_url: URL da página
        page_title: Título atual
        page_description: Meta description atual
        page_h1: H1 atual
        page_content: Conteúdo da página (opcional, para contexto)
    
    Returns:
        {
            "original": str,
            "optimized": str,
            "explanation": str,
            "html_code": str,
            "ai_powered": bool
        }
    """
    client = get_ai_client()
    
    fix_prompts = {
        "title_length": f"""O título desta página está {'muito curto' if len(page_title or '') < 30 else 'muito longo'}.
Título atual: "{page_title}"
Crie um título SEO otimizado (50-60 caracteres) que:
- Inclua a palavra-chave principal no início
- Seja atrativo para cliques
- Descreva claramente o conteúdo""",

        "meta_description_length": f"""A meta description está {'muito curta' if len(page_description or '') < 70 else 'muito longa'}.
Meta atual: "{page_description}"
Crie uma meta description otimizada (120-155 caracteres) que:
- Inclua um CTA (call-to-action)
- Contenha palavras-chave relevantes
- Incentive o clique""",

        "missing_h1": f"""Esta página não tem H1.
Título: "{page_title}"
URL: {page_url}
Crie um H1 otimizado que:
- Descreva claramente o conteúdo da página
- Inclua a palavra-chave principal
- Seja único e relevante""",

        "missing_h2": f"""Esta página não tem H2 (subtítulos).
Título: "{page_title}"
Crie 3-4 sugestões de H2 que:
- Organizem o conteúdo em seções lógicas
- Incluam palavras-chave secundárias
- Melhorem a escaneabilidade""",

        # Códigos separados curto/longo (Dashboard V2) reaproveitam a lógica de tamanho
        "title_too_short": f"""O título desta página está muito curto.
Título atual: "{page_title}"
Crie um título SEO otimizado (50-60 caracteres) que:
- Inclua a palavra-chave principal no início
- Seja atrativo para cliques
- Descreva claramente o conteúdo""",

        "title_too_long": f"""O título desta página está muito longo.
Título atual: "{page_title}"
Crie um título SEO otimizado (50-60 caracteres) que:
- Inclua a palavra-chave principal no início
- Seja atrativo para cliques
- Descreva claramente o conteúdo""",

        "meta_description_short": f"""A meta description está muito curta.
Meta atual: "{page_description}"
Crie uma meta description otimizada (120-155 caracteres) que:
- Inclua um CTA (call-to-action)
- Contenha palavras-chave relevantes
- Incentive o clique""",

        "meta_description_long": f"""A meta description está muito longa.
Meta atual: "{page_description}"
Crie uma meta description otimizada (120-155 caracteres) que:
- Inclua um CTA (call-to-action)
- Contenha palavras-chave relevantes
- Incentive o clique""",

        "missing_schema": f"""Esta página não tem Schema.org (dados estruturados).
Tipo de página: {_detect_page_type(page_url)}
Título: "{page_title}"
Gere o código JSON-LD Schema.org apropriado.""",

        "missing_img_alt": f"""Esta página tem imagens sem texto alternativo.
Título: "{page_title}"
Gere 3 exemplos de textos alt otimizados para imagens.""",

        "missing_canonical": f"""Esta página não tem tag canonical.
URL: {page_url}
Gere a tag canonical correta.""",
    }
    
    prompt = fix_prompts.get(issue_type, f"Corrija o problema de SEO: {issue_type}")
    
    if not client:
        # Fallback sem IA
        return _generate_basic_fix(issue_type, page_url, page_title, page_description, page_h1)
    
    try:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": """Você é um especialista em SEO técnico.
Responda SEMPRE em JSON:
{
  "original": "valor atual ou 'ausente'",
  "optimized": "valor otimizado",
  "explanation": "explicação breve",
  "html_code": "código HTML pronto para usar"
}"""},
                {"role": "user", "content": prompt}
            ],
            **completion_params(600, temperature=0.7),
        )
        
        content = response.choices[0].message.content
        
        # Parsear JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            result["ai_powered"] = True
            result["issue_type"] = issue_type
            return result
            
    except Exception as e:
        logger.error(f"Erro ao gerar fix: {e}")
    
    return _generate_basic_fix(issue_type, page_url, page_title, page_description, page_h1)


def _detect_page_type(url: str) -> str:
    """Detecta tipo de página pela URL"""
    url_lower = url.lower()
    if "/product" in url_lower or "/produto" in url_lower:
        return "Product"
    elif "/collection" in url_lower or "/categoria" in url_lower:
        return "CollectionPage"
    elif "/blog" in url_lower or "/artigo" in url_lower:
        return "Article"
    elif url_lower.endswith("/") or url_lower.count("/") <= 3:
        return "WebPage"
    return "WebPage"


def _generate_basic_fix(
    issue_type: str,
    page_url: str,
    page_title: Optional[str],
    page_description: Optional[str],
    page_h1: Optional[str],
) -> Dict[str, Any]:
    """Gera correção básica sem IA"""
    
    fixes = {
        "title_length": {
            "original": page_title or "ausente",
            "optimized": (page_title or "")[:60] if page_title else "Título da Página | Sua Marca",
            "explanation": "Título ajustado para 60 caracteres",
            "html_code": f'<title>{(page_title or "")[:60]}</title>',
        },
        "meta_description_length": {
            "original": page_description or "ausente",
            "optimized": (page_description or "")[:155] if page_description else "Descrição otimizada da página com call-to-action.",
            "explanation": "Meta description ajustada para 155 caracteres",
            "html_code": f'<meta name="description" content="{(page_description or "")[:155]}">',
        },
        # Códigos separados curto/longo (Dashboard V2)
        "title_too_short": {
            "original": page_title or "ausente",
            "optimized": (page_title or "")[:60] if page_title else "Título da Página | Sua Marca",
            "explanation": "Título ajustado para 60 caracteres",
            "html_code": f'<title>{(page_title or "")[:60]}</title>',
        },
        "title_too_long": {
            "original": page_title or "ausente",
            "optimized": (page_title or "")[:60] if page_title else "Título da Página | Sua Marca",
            "explanation": "Título ajustado para 60 caracteres",
            "html_code": f'<title>{(page_title or "")[:60]}</title>',
        },
        "meta_description_short": {
            "original": page_description or "ausente",
            "optimized": (page_description or "")[:155] if page_description else "Descrição otimizada da página com call-to-action.",
            "explanation": "Meta description ajustada para 155 caracteres",
            "html_code": f'<meta name="description" content="{(page_description or "")[:155]}">',
        },
        "meta_description_long": {
            "original": page_description or "ausente",
            "optimized": (page_description or "")[:155] if page_description else "Descrição otimizada da página com call-to-action.",
            "explanation": "Meta description ajustada para 155 caracteres",
            "html_code": f'<meta name="description" content="{(page_description or "")[:155]}">',
        },
        "missing_h1": {
            "original": "ausente",
            "optimized": page_title or "Título Principal",
            "explanation": "H1 baseado no título da página",
            "html_code": f'<h1>{page_title or "Título Principal"}</h1>',
        },
        "missing_h2": {
            "original": "ausente",
            "optimized": "Seções sugeridas: Visão Geral, Características, Benefícios",
            "explanation": "H2s para organizar conteúdo",
            "html_code": '<h2>Visão Geral</h2>\n<h2>Características</h2>\n<h2>Benefícios</h2>',
        },
        "missing_schema": {
            "original": "ausente",
            "optimized": "Schema.org WebPage",
            "explanation": "Dados estruturados básicos",
            "html_code": f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "{page_title or 'Página'}",
  "url": "{page_url}"
}}
</script>''',
        },
        "missing_img_alt": {
            "original": "ausente",
            "optimized": "Adicione descrições relevantes às imagens",
            "explanation": "Alt text melhora acessibilidade e SEO",
            "html_code": '<img src="imagem.jpg" alt="Descrição da imagem">',
        },
        "missing_canonical": {
            "original": "ausente",
            "optimized": page_url,
            "explanation": "Canonical define URL preferida",
            "html_code": f'<link rel="canonical" href="{page_url}">',
        },
    }
    
    fix = fixes.get(issue_type, {
        "original": "desconhecido",
        "optimized": "Consulte documentação SEO",
        "explanation": f"Tipo de issue não reconhecido: {issue_type}",
        "html_code": "<!-- Correção manual necessária -->",
    })
    
    fix["ai_powered"] = False
    fix["issue_type"] = issue_type
    return fix


async def apply_all_fixes(
    page_url: str,
    issues: List[str],
    page_title: Optional[str] = None,
    page_description: Optional[str] = None,
    page_h1: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Gera todas as correções para uma página.
    
    Returns:
        {
            "page_url": str,
            "fixes": [lista de correções],
            "total_issues": int,
            "ai_powered": bool,
            "export_html": str (código completo para copiar)
        }
    """
    fixes = []
    for issue in issues:
        fix = await generate_seo_fix(
            issue_type=issue,
            page_url=page_url,
            page_title=page_title,
            page_description=page_description,
            page_h1=page_h1,
        )
        fixes.append(fix)
    
    # Gerar HTML consolidado
    html_parts = ["<!-- SEO Fixes gerados por SiteCan -->"]
    for fix in fixes:
        if fix.get("html_code"):
            html_parts.append(f"\n<!-- Fix: {fix.get('issue_type', 'unknown')} -->")
            html_parts.append(fix["html_code"])
    
    return {
        "page_url": page_url,
        "fixes": fixes,
        "total_issues": len(issues),
        "ai_powered": any(f.get("ai_powered") for f in fixes),
        "export_html": "\n".join(html_parts),
    }


async def analyze_seo_issues(
    title: Optional[str],
    description: Optional[str],
    h1: Optional[str],
    url: str,
) -> Dict[str, Any]:
    """
    Analisa problemas de SEO de uma página e sugere melhorias com IA.
    """
    client = get_ai_client()
    
    issues = []
    
    # Análise básica
    if not title:
        issues.append("[ERRO] Título ausente")
    elif len(title) < 30:
        issues.append("ATENCAO: Título muito curto")
    elif len(title) > 60:
        issues.append("ATENCAO: Título muito longo")
    
    if not description:
        issues.append("[ERRO] Meta description ausente")
    elif len(description) < 70:
        issues.append("ATENCAO: Meta description muito curta")
    elif len(description) > 160:
        issues.append("ATENCAO: Meta description muito longa")
    
    if not h1:
        issues.append("[ERRO] H1 ausente")
    
    result = {
        "issues": issues,
        "score": max(0, 100 - len(issues) * 15),
        "suggestions": [],
        "ai_powered": False,
    }
    
    # Se tiver IA, gerar sugestões detalhadas
    if client and issues:
        try:
            response = await client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "Você é um consultor de SEO. Dê sugestões práticas e diretas."},
                    {"role": "user", "content": f"""Analise esta página e sugira melhorias:

URL: {url}
Título: {title or 'Nenhum'}
Meta Description: {description or 'Nenhuma'}
H1: {h1 or 'Nenhum'}

Problemas encontrados: {', '.join(issues)}

Dê 3 sugestões práticas de melhoria."""}
                ],
                **completion_params(300, temperature=0.5),
            )
            result["suggestions"] = response.choices[0].message.content.split("\n")
            result["ai_powered"] = True
        except Exception as e:
            logger.error(f"Erro na análise IA: {e}")
    
    return result
