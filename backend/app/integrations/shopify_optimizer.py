"""
Serviço de Otimização SEO para Shopify com LLM
Inclui análise de imagens e geração de textos otimizados
Suporta: Produtos, Coleções, Páginas e Blog Posts
"""
import os
import json
import httpx
import base64
import re
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from openai import AsyncOpenAI

from app.integrations.shopify import (
    ShopifyClient, 
    ShopifyProduct,
    ShopifyCollection,
    ShopifyPage,
    ShopifyArticle,
    OptimizationProposal,
    OptimizationStatus,
    create_shopify_client,
)

logger = logging.getLogger(__name__)

# Configuração
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
from app.ai_config import AI_MODEL, completion_params, parse_ai_json
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o")  # Modelo com visão para análise de imagens


def get_ai_client() -> Optional[AsyncOpenAI]:
    """Retorna cliente OpenAI se configurado"""
    if not OPENAI_API_KEY:
        return None
    return AsyncOpenAI(api_key=OPENAI_API_KEY)


# SYSTEM_PROMPT_V2 — Engenheiro de SEO Sênior (Reformulação da Camada de IA)
SYSTEM_PROMPT_ECOMMERCE = """Você é um ENGENHEIRO DE SEO SÊNIOR especializado em algoritmos de busca e conversão para e-commerce de alta performance.

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
   NUNCA remover: medidas, dimensões, tabelas de tamanho, links externos, telefones, endereços, especificações técnicas, informações de garantia, política de troca.
   Ao otimizar descrições, ADICIONE e MELHORE — não substitua informações essenciais.

PRIORIZAÇÃO:
Para cada otimização, avalie e informe:
- priority: "high" (impacto direto em ranking/CTR), "medium" (melhoria relevante), "low" (ajuste fino)
- impact: "ranking" (melhora posição), "ctr" (melhora taxa de cliques), "conversao" (melhora vendas), "visibilidade" (Featured Snippets, rich results)
- effort: "low" (mudança simples de texto), "medium" (reescrita parcial), "high" (conteúdo novo)

Responda SEMPRE em JSON válido, no formato exato solicitado em cada tarefa."""

IMAGE_ANALYSIS_PROMPT = """Analise esta imagem de produto e gere um texto alternativo (alt text) otimizado para SEO.

O alt text deve:
1. Descrever claramente o que aparece na imagem
2. Incluir detalhes relevantes (cor, material, tamanho se visível)
3. Ser conciso (máximo 125 caracteres)
4. Incluir a palavra-chave do produto se relevante
5. Ser acessível para leitores de tela

Contexto do produto:
- Nome: {product_name}
- Categoria: {category}
- Marca: {brand}

Responda em JSON:
{{
  "alt_text": "texto alternativo otimizado",
  "description": "descrição do que a IA viu na imagem",
  "confidence": "alta/média/baixa"
}}"""

FAQ_GENERATION_PROMPT = """Gere um FAQ (Perguntas Frequentes) otimizado para SEO para este produto de e-commerce.

PRODUTO: {product_name}
CATEGORIA: {category}
MARCA: {brand}
DESCRIÇÃO: {description}

Gere 5-7 perguntas e respostas relevantes que:
1. Respondam dúvidas comuns dos consumidores
2. Incluam palavras-chave naturalmente
3. Sejam úteis para aparecer em Featured Snippets do Google
4. Abordem especificações, uso, cuidados e diferenciais

Responda em JSON:
{{
  "faqs": [
    {{"question": "pergunta", "answer": "resposta completa e informativa"}}
  ],
  "schema_type": "FAQPage"
}}"""

RICH_DESCRIPTION_PROMPT = """Crie uma descrição de produto otimizada para SEO com estrutura semântica completa.

PRODUTO: {product_name}
CATEGORIA: {category}
MARCA: {brand}
DESCRIÇÃO ATUAL: {current_description}

A descrição deve conter:
1. Parágrafo introdutório com palavra-chave principal
2. Lista de benefícios/características (bullet points)
3. Seção de especificações técnicas (se aplicável)
4. Seção "Por que escolher" com diferenciais
5. Heading tags (H2, H3) para estrutura semântica
6. Palavras-chave LSI (semânticas) naturalmente distribuídas

Responda em JSON:
{{
  "html": "descrição completa em HTML com headings e formatação",
  "word_count": número_de_palavras,
  "keywords_used": ["lista", "de", "keywords"],
  "headings": ["H2 e H3 utilizados"],
  "reasoning": "explicação da estrutura"
}}"""

TAGS_KEYWORDS_PROMPT = """Gere tags e palavras-chave otimizadas para este produto.

PRODUTO: {product_name}
CATEGORIA: {category}
MARCA: {brand}
DESCRIÇÃO: {description}

Gere:
1. Tags do produto (5-10 tags relevantes)
2. Palavras-chave principais (3-5)
3. Palavras-chave de cauda longa (3-5)
4. Palavras-chave LSI/semânticas (5-8)

Responda em JSON:
{{
  "tags": ["tag1", "tag2"],
  "main_keywords": ["keyword principal 1", "keyword principal 2"],
  "long_tail_keywords": ["frase longa 1", "frase longa 2"],
  "lsi_keywords": ["semântica 1", "semântica 2"],
  "reasoning": "explicação da escolha"
}}"""

COLLECTION_OPTIMIZATION_PROMPT = """Otimize o SEO desta coleção/categoria de e-commerce BASEADO NO CONTEXTO REAL DOS PRODUTOS.

COLEÇÃO: {collection_name}
DESCRIÇÃO ATUAL: {current_description}

=== PRODUTOS DESTA COLEÇÃO (contexto real) ===
{products_context}

IMPORTANTE: 
- Analise os produtos acima para entender o REAL contexto da coleção
- As otimizações DEVEM refletir os produtos reais (ex: se são produtos de snowboard, fale sobre snowboard)
- NÃO invente categorias ou produtos que não existem na coleção
- Use as palavras-chave e termos encontrados nos produtos reais

Gere otimizações em JSON:
{{
  "title": {{"value": "título otimizado baseado no contexto real (50-60 chars)", "reasoning": "motivo"}},
  "description": {{"value": "descrição HTML com H2/H3 e bullet points sobre os produtos REAIS, 200-400 palavras", "reasoning": "motivo"}},
  "seo_title": {{"value": "SEO title baseado nos produtos reais (50-60 chars)", "reasoning": "motivo"}},
  "seo_description": {{"value": "meta description sobre os produtos reais (120-155 chars)", "reasoning": "motivo"}}
}}"""

PAGE_OPTIMIZATION_PROMPT = """Otimize o SEO desta página institucional:

PÁGINA: {page_title}
TIPO: {page_type}
CONTEÚDO ATUAL: {current_content}

Páginas institucionais incluem: Sobre Nós, Contato, Política de Privacidade, FAQ, etc.

Gere otimizações em JSON:
{{
  "title": {{"value": "título otimizado", "reasoning": "motivo"}},
  "content": {{"value": "conteúdo HTML otimizado com estrutura semântica", "reasoning": "motivo"}},
  "seo_title": {{"value": "SEO title (50-60 chars)", "reasoning": "motivo"}},
  "seo_description": {{"value": "meta description (120-155 chars)", "reasoning": "motivo"}}
}}"""

ARTICLE_OPTIMIZATION_PROMPT = """Otimize o SEO deste artigo de blog:

TÍTULO: {article_title}
AUTOR: {author}
TAGS: {tags}
CONTEÚDO ATUAL: {current_content}

Artigos de blog são importantes para SEO de conteúdo e tráfego orgânico.

Gere otimizações em JSON:
{{
  "title": {{"value": "título otimizado para CTR e SEO", "reasoning": "motivo"}},
  "content": {{"value": "conteúdo HTML otimizado com H2/H3, listas e formatação", "reasoning": "motivo"}},
  "seo_title": {{"value": "SEO title (50-60 chars)", "reasoning": "motivo"}},
  "seo_description": {{"value": "meta description (120-155 chars)", "reasoning": "motivo"}},
  "tags": {{"value": "tag1, tag2, tag3", "reasoning": "motivo"}}
}}"""


class ShopifySEOOptimizer:
    """
    Serviço de otimização SEO para Shopify usando LLM.
    
    Features:
    - Análise e otimização de títulos e descrições
    - Análise de imagens com IA para gerar alt texts
    - Sistema de propostas com validação de usuário
    - Rollback completo
    - Contexto competitivo via SERP (SearchAPI.io)
    - Dados de performance via GSC
    - Keyword alvo como eixo central
    """
    
    def __init__(self, shopify_client: ShopifyClient):
        self.shopify = shopify_client
        self.ai_client = get_ai_client()
    
    async def _fetch_serp_context(self, keyword: str) -> str:
        """Fetch SERP data and format as prompt context"""
        try:
            from app.integrations.searchapi_client import fetch_serp
            serp = await fetch_serp(keyword, geo="BR", num_results=5)
            results = serp.get("results", [])
            if not results:
                return ""
            lines = [f"=== CONCORRENTES NO GOOGLE para '{keyword}' ==="]
            for r in results:
                lines.append(f"#{r['position']}: {r['title']}")
                lines.append(f"   URL: {r['displayed_link']}")
                lines.append(f"   Snippet: {r['snippet']}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"SERP fetch skipped: {e}")
            return ""
    
    async def _fetch_gsc_context(self, user: dict, page_url: str) -> tuple:
        """Fetch GSC page-level metrics. Returns (formatted_str, raw_dict)"""
        try:
            from app.integrations.gsc import get_gsc_tokens, fetch_gsc_page_performance
            tokens = await get_gsc_tokens(user.get("user_id", ""))
            if not tokens or not tokens.get("access_token"):
                return "", None
            data = await fetch_gsc_page_performance(tokens["access_token"], tokens["site_url"], page_url)
            if not data.get("found"):
                return "", None
            lines = [
                "=== PERFORMANCE ATUAL (Google Search Console, últimos 30 dias) ===",
                f"Cliques: {data['clicks']}",
                f"Impressões: {data['impressions']}",
                f"CTR: {data['ctr']}%",
                f"Posição média: {data['position']}",
            ]
            top_q = data.get("top_queries", [])[:5]
            if top_q:
                lines.append("Queries que trazem tráfego:")
                for q in top_q:
                    lines.append(f"  - \"{q['query']}\" (pos {q['position']}, CTR {q['ctr']}%)")
            return "\n".join(lines), data
        except Exception as e:
            logger.warning(f"GSC fetch skipped: {e}")
            return "", None
    
    async def analyze_product(self, product_id: int) -> Dict[str, Any]:
        """Diagnóstico SEO contextual do produto (IA + fallback heurístico)."""
        from app.product_diagnosis import diagnose_product

        product = await self.shopify.get_product(product_id)
        metafields = await self.shopify.get_product_metafields(product_id)

        images_without_alt = []
        if product.images:
            for img in product.images:
                if not img.get("alt"):
                    images_without_alt.append(img)

        enrichment: Dict[str, Any] = {}
        try:
            from app.data_enrichment import enrich_product_context
            enrichment = await enrich_product_context({
                "name": product.title,
                "title": product.title,
                "tags": product.tags or "",
            })
        except Exception as e:
            logger.warning(f"[shopify] enrichment skipped: {e}")

        diagnosis = await diagnose_product(
            {
                "title": product.title,
                "name": product.title,
                "description": product.body_html,
                "body_html": product.body_html,
                "seo_title": metafields.get("seo_title") or "",
                "seo_description": metafields.get("seo_description") or "",
                "tags": product.tags,
                "images_without_alt": len(images_without_alt),
            },
            ai_client=self.ai_client,
            enrichment=enrichment,
            platform="Shopify",
        )

        has_faq = bool(metafields.get("faq_html") or ("faq" in (product.body_html or "").lower()))
        has_schema = "application/ld+json" in (product.body_html or "").lower()

        return {
            "product": product.model_dump(),
            "metafields": metafields,
            "issues": diagnosis["issues"],
            "score": diagnosis["score"],
            "score_justification": diagnosis["score_justification"],
            "summary": diagnosis["summary"],
            "opportunities": diagnosis.get("opportunities") or [],
            "recommended_actions": diagnosis.get("recommended_actions") or [],
            "recommendations": diagnosis.get("recommendations") or [],
            "images_without_alt": images_without_alt,
            "source": diagnosis.get("source"),
            "seo_features": {
                "has_semantic_structure": ("<h2" in (product.body_html or "").lower()) or ("<h3" in (product.body_html or "").lower()),
                "has_faq": has_faq,
                "has_schema": has_schema,
                "tags_count": len(product.tags.split(",")) if product.tags else 0,
            },
            "type": "product",
        }

    async def generate_optimizations(
        self, 
        product_id: int,
        optimize_title: bool = True,
        optimize_description: bool = True,
        optimize_seo_title: bool = True,
        optimize_seo_description: bool = True,
        optimize_image_alts: bool = True,
        generate_faq: bool = True,
        generate_rich_description: bool = False,
        generate_tags: bool = True,
        target_keyword: str = None,
        user: dict = None,
        page_url: str = None,
    ) -> List[OptimizationProposal]:
        """
        Gera propostas de otimização para um produto.
        As propostas NÃO são aplicadas automaticamente - requerem aprovação.
        
        Args:
            product_id: ID do produto no Shopify
            target_keyword: Keyword alvo para direcionar otimizações
            user: Dict do usuário autenticado (para buscar GSC)
            page_url: URL da página do produto (para buscar GSC)
        """
        product = await self.shopify.get_product(product_id)
        metafields = await self.shopify.get_product_metafields(product_id)
        
        proposals = []
        
        if not self.ai_client:
            # Fallback sem IA
            return await self._generate_basic_optimizations(
                product, metafields, 
                optimize_title, optimize_description,
                optimize_seo_title, optimize_seo_description,
                optimize_image_alts
            )
        
        # Data Enrichment obrigatório ANTES da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": product.title,
            "title": product.title,
            "product_type": product.product_type,
            "vendor": product.vendor,
            "tags": getattr(product, "tags", ""),
            "body_html": product.body_html,
            "variants": getattr(product, "variants", None) or [],
        }, user_id=user.get("user_id") if user else None)

        # Gerar otimizações com IA
        context = {
            "product_name": product.title,
            "current_description": product.body_html,
            "category": product.product_type,
            "brand": product.vendor,
            "current_seo_title": metafields.get("seo_title"),
            "current_seo_description": metafields.get("seo_description"),
            "target_keyword": target_keyword,
            "segmento": enriched.get("segmento", ""),
            "atributos": enriched.get("atributos_extraidos", []),
            "keywords_mercado": enriched.get("keywords_mercado", []),
            "serp_data": enriched.get("serp_data", []),
        }
        
        # Fetch contexto competitivo (SERP) e performance (GSC)
        serp_context = ""
        gsc_context = ""
        gsc_metrics = None
        
        effective_keyword = target_keyword or product.title
        if effective_keyword:
            serp_context = await self._fetch_serp_context(effective_keyword)
        
        if user and page_url:
            gsc_context, gsc_metrics = await self._fetch_gsc_context(user, page_url)
        
        context["serp_context"] = serp_context
        context["gsc_context"] = gsc_context
        context["gsc_metrics"] = gsc_metrics
        
        # Otimizar título e descrições em uma única chamada
        if any([optimize_title, optimize_description, optimize_seo_title, optimize_seo_description]):
            text_proposals = await self._generate_text_optimizations(
                product, metafields, context,
                optimize_title, optimize_description,
                optimize_seo_title, optimize_seo_description
            )
            proposals.extend(text_proposals)
        
        # Gerar descrição rica com estrutura semântica
        if generate_rich_description:
            rich_desc_proposal = await self._generate_rich_description(product, context)
            if rich_desc_proposal:
                proposals.append(rich_desc_proposal)
        
        # Gerar FAQ automático
        if generate_faq:
            faq_proposal = await self._generate_faq(product, context)
            if faq_proposal:
                proposals.append(faq_proposal)
        
        # Gerar tags e keywords
        if generate_tags:
            tags_proposal = await self._generate_tags_keywords(product, context)
            if tags_proposal:
                proposals.append(tags_proposal)
        
        # Otimizar alt texts das imagens
        if optimize_image_alts and product.images:
            for img in product.images:
                if not img.get("alt"):
                    try:
                        alt_proposal = await self._generate_image_alt(
                            product, img, context
                        )
                        if alt_proposal:
                            proposals.append(alt_proposal)
                    except Exception as e:
                        logger.error(f"Erro ao analisar imagem {img['id']}: {e}")
        
        return proposals
    
    async def _generate_text_optimizations(
        self,
        product: ShopifyProduct,
        metafields: Dict[str, str],
        context: Dict[str, Any],
        optimize_title: bool,
        optimize_description: bool,
        optimize_seo_title: bool,
        optimize_seo_description: bool,
    ) -> List[OptimizationProposal]:
        """Gera otimizações de texto usando LLM com contexto competitivo"""
        proposals = []
        
        keyword_line = ""
        if context.get("target_keyword"):
            keyword_line = f"\nKEYWORD ALVO: {context['target_keyword']}\nTodas as otimizações DEVEM ser centradas nesta keyword."
        
        serp_block = ""
        if context.get("serp_context"):
            serp_block = f"\n\n{context['serp_context']}\n\nIMPORTANTE: Analise os concorrentes acima. Suas sugestões devem SUPERAR os títulos e descrições deles."
        
        gsc_block = ""
        if context.get("gsc_context"):
            gsc_block = f"\n\n{context['gsc_context']}\n\nUse esses dados para direcionar as otimizações: se CTR é baixo, foque em títulos mais atrativos; se posição é ruim, foque em relevância semântica."

        # Blocos do payload enriquecido (Data Enrichment Pipeline)
        segmento_line = ""
        if context.get("segmento"):
            segmento_line = f"\nSEGMENTO DE MERCADO: {context['segmento']}"

        atributos_line = ""
        if context.get("atributos"):
            atributos_line = f"\nATRIBUTOS DO PRODUTO: {', '.join(context['atributos'])}"

        keywords_line = ""
        if context.get("keywords_mercado"):
            keywords_line = f"\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(context['keywords_mercado'][:10])}"

        prompt = f"""Otimize o SEO deste produto de e-commerce:

PRODUTO: {context['product_name']}
CATEGORIA: {context['category'] or 'Não informada'}
MARCA: {context['brand'] or 'Não informada'}{segmento_line}{atributos_line}{keywords_line}{keyword_line}

CONTEÚDO ATUAL:
- Título: {context['product_name']}
- Descrição: {(context['current_description'] or '')[:500]}
- SEO Title: {context['current_seo_title'] or 'Não definido'}
- Meta Description: {context['current_seo_description'] or 'Não definida'}{serp_block}{gsc_block}

LEMBRETE: Preserve medidas, links externos, telefones, tabelas de tamanho e especificações técnicas do conteúdo original.

Gere otimizações em JSON. Para CADA campo inclua priority, impact e effort:
{{
  "title": {{"value": "título otimizado (50-60 chars)", "reasoning": "motivo", "priority": "high|medium|low", "impact": "ranking|ctr|conversao|visibilidade", "effort": "low|medium|high"}},
  "description": {{"value": "descrição HTML otimizada", "reasoning": "motivo", "priority": "...", "impact": "...", "effort": "..."}},
  "seo_title": {{"value": "SEO title (50-60 chars)", "reasoning": "motivo", "priority": "...", "impact": "...", "effort": "..."}},
  "seo_description": {{"value": "meta description (120-155 chars)", "reasoning": "motivo", "priority": "...", "impact": "...", "effort": "..."}}
}}

Inclua apenas os campos que precisam de otimização."""

        try:
            response = await self.ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ECOMMERCE},
                    {"role": "user", "content": prompt}
                ],
                **completion_params(1500, temperature=0.7),
            )
            
            content = response.choices[0].message.content
            
            # Parsear JSON
            result = parse_ai_json(content, "produto Shopify")
            if result:

                # Validação pós-IA (transparência)
                from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica

                def _transparencia(original_value: Optional[str], novo_valor: str) -> Dict[str, Any]:
                    return {
                        "atributos": validar_atributos_descritivos(
                            titulo_original=original_value,
                            titulo_sugerido=novo_valor,
                            atributos_produto=context.get("atributos"),
                        ),
                        "semantica": calcular_cobertura_semantica(
                            titulo_original=original_value,
                            titulo_sugerido=novo_valor,
                            keywords_estrategicas=context.get("keywords_mercado"),
                        ),
                    }

                target_kw = context.get("target_keyword")
                gsc_metrics = context.get("gsc_metrics")
                pre_metrics_snapshot = None
                if gsc_metrics and gsc_metrics.get("found"):
                    pre_metrics_snapshot = {
                        "clicks": gsc_metrics.get("clicks", 0),
                        "impressions": gsc_metrics.get("impressions", 0),
                        "ctr": gsc_metrics.get("ctr", 0),
                        "position": gsc_metrics.get("position", 0),
                    }
                
                # Criar propostas
                if optimize_title and "title" in result:
                    proposal = await self.shopify.create_optimization_proposal(
                        product_id=product.id,
                        optimization_type="title",
                        field_name="title",
                        original_value=product.title,
                        proposed_value=result["title"]["value"],
                        reasoning=result["title"]["reasoning"],
                        priority=result["title"].get("priority"),
                        impact=result["title"].get("impact"),
                        effort=result["title"].get("effort"),
                        target_keyword=target_kw,
                        pre_metrics=pre_metrics_snapshot,
                    )
                    proposal.transparencia = _transparencia(product.title, result["title"]["value"])
                    proposals.append(proposal)

                if optimize_description and "description" in result:
                    proposal = await self.shopify.create_optimization_proposal(
                        product_id=product.id,
                        optimization_type="description",
                        field_name="body_html",
                        original_value=product.body_html,
                        proposed_value=result["description"]["value"],
                        reasoning=result["description"]["reasoning"],
                        priority=result["description"].get("priority"),
                        impact=result["description"].get("impact"),
                        effort=result["description"].get("effort"),
                        target_keyword=target_kw,
                        pre_metrics=pre_metrics_snapshot,
                    )
                    proposal.transparencia = _transparencia(product.body_html, result["description"]["value"])
                    proposals.append(proposal)

                if optimize_seo_title and "seo_title" in result:
                    proposal = await self.shopify.create_optimization_proposal(
                        product_id=product.id,
                        optimization_type="seo_title",
                        field_name="seo_title",
                        original_value=metafields.get("seo_title"),
                        proposed_value=result["seo_title"]["value"],
                        reasoning=result["seo_title"]["reasoning"],
                        priority=result["seo_title"].get("priority"),
                        impact=result["seo_title"].get("impact"),
                        effort=result["seo_title"].get("effort"),
                        target_keyword=target_kw,
                        pre_metrics=pre_metrics_snapshot,
                    )
                    proposal.transparencia = _transparencia(metafields.get("seo_title") or product.title, result["seo_title"]["value"])
                    proposals.append(proposal)

                if optimize_seo_description and "seo_description" in result:
                    proposal = await self.shopify.create_optimization_proposal(
                        product_id=product.id,
                        optimization_type="seo_description",
                        field_name="seo_description",
                        original_value=metafields.get("seo_description"),
                        proposed_value=result["seo_description"]["value"],
                        reasoning=result["seo_description"]["reasoning"],
                        priority=result["seo_description"].get("priority"),
                        impact=result["seo_description"].get("impact"),
                        effort=result["seo_description"].get("effort"),
                        target_keyword=target_kw,
                        pre_metrics=pre_metrics_snapshot,
                    )
                    proposal.transparencia = _transparencia(metafields.get("seo_description"), result["seo_description"]["value"])
                    proposals.append(proposal)

        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de texto: {e}")
        
        return proposals
    
    async def _generate_image_alt(
        self,
        product: ShopifyProduct,
        image: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[OptimizationProposal]:
        """Gera alt text para uma imagem usando visão da IA"""
        
        # Tentar análise com visão
        try:
            # Baixar imagem e converter para base64
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(image["src"])
                if response.status_code == 200:
                    image_data = base64.b64encode(response.content).decode("utf-8")
                    
                    # Determinar tipo de mídia
                    content_type = response.headers.get("content-type", "image/jpeg")
                    
                    prompt = IMAGE_ANALYSIS_PROMPT.format(
                        product_name=context["product_name"],
                        category=context["category"] or "Não informada",
                        brand=context["brand"] or "Não informada",
                    )
                    
                    # Chamada com visão
                    vision_response = await self.ai_client.chat.completions.create(
                        model=VISION_MODEL,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{content_type};base64,{image_data}",
                                            "detail": "low"  # Usar baixa resolução para economizar tokens
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=300,
                    )
                    
                    content = vision_response.choices[0].message.content
                    
                    # Parsear JSON
                    result = parse_ai_json(content, "alt-text de imagem Shopify")
                    if result:

                        proposal = await self.shopify.create_optimization_proposal(
                            product_id=product.id,
                            optimization_type="image_alt",
                            field_name="image_alt",
                            original_value=image.get("alt"),
                            proposed_value=result["alt_text"],
                            reasoning=f"Análise de IA: {result.get('description', 'Imagem analisada')}",
                            image_id=image["id"],
                        )
                        return proposal
                        
        except Exception as e:
            logger.error(f"Erro na análise de imagem com visão: {e}")
        
        # Fallback: gerar alt baseado no nome do produto
        return await self._generate_basic_image_alt(product, image, context)
    
    async def _generate_basic_image_alt(
        self,
        product: ShopifyProduct,
        image: Dict[str, Any],
        context: Dict[str, Any],
    ) -> OptimizationProposal:
        """Gera alt text básico sem análise de imagem"""
        
        # Construir alt text baseado no contexto
        parts = [context["product_name"]]
        if context["brand"]:
            parts.append(f"da {context['brand']}")
        if context["category"]:
            parts.append(f"- {context['category']}")
        
        alt_text = " ".join(parts)[:125]  # Limitar a 125 caracteres
        
        proposal = await self.shopify.create_optimization_proposal(
            product_id=product.id,
            optimization_type="image_alt",
            field_name="image_alt",
            original_value=image.get("alt"),
            proposed_value=alt_text,
            reasoning="Alt text gerado automaticamente baseado no nome do produto",
            image_id=image["id"],
        )
        return proposal
    
    async def _generate_basic_optimizations(
        self,
        product: ShopifyProduct,
        metafields: Dict[str, str],
        optimize_title: bool,
        optimize_description: bool,
        optimize_seo_title: bool,
        optimize_seo_description: bool,
        optimize_image_alts: bool,
    ) -> List[OptimizationProposal]:
        """Gera otimizações básicas sem IA (fallback)"""
        proposals = []
        
        # SEO Title básico
        if optimize_seo_title and not metafields.get("seo_title"):
            title_parts = [product.title]
            if product.vendor:
                title_parts.append(f"| {product.vendor}")
            seo_title = " ".join(title_parts)[:60]
            
            proposal = await self.shopify.create_optimization_proposal(
                product_id=product.id,
                optimization_type="seo_title",
                field_name="seo_title",
                original_value=None,
                proposed_value=seo_title,
                reasoning="Título SEO gerado automaticamente (sem IA)",
            )
            proposals.append(proposal)
        
        # SEO Description básica
        if optimize_seo_description and not metafields.get("seo_description"):
            seo_desc = f"Compre {product.title} com o melhor preço. Entrega rápida e pagamento facilitado."[:155]
            
            proposal = await self.shopify.create_optimization_proposal(
                product_id=product.id,
                optimization_type="seo_description",
                field_name="seo_description",
                original_value=None,
                proposed_value=seo_desc,
                reasoning="Meta description gerada automaticamente (sem IA)",
            )
            proposals.append(proposal)
        
        # Image alts básicos
        if optimize_image_alts and product.images:
            for img in product.images:
                if not img.get("alt"):
                    proposal = await self._generate_basic_image_alt(
                        product, img, 
                        {
                            "product_name": product.title,
                            "brand": product.vendor,
                            "category": product.product_type,
                        }
                    )
                    proposals.append(proposal)
        
        return proposals
    
    async def _generate_faq(
        self,
        product: ShopifyProduct,
        context: Dict[str, Any],
    ) -> Optional[OptimizationProposal]:
        """Gera FAQ automático para o produto com Schema.org markup"""
        try:
            prompt = FAQ_GENERATION_PROMPT.format(
                product_name=context["product_name"],
                category=context["category"] or "Não informada",
                brand=context["brand"] or "Não informada",
                description=(context["current_description"] or "")[:500],
            )
            
            response = await self.ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ECOMMERCE},
                    {"role": "user", "content": prompt}
                ],
                **completion_params(1500, temperature=0.7),
            )
            
            content = response.choices[0].message.content
            
            result = parse_ai_json(content, "FAQ Shopify")
            if result:

                # Construir HTML do FAQ com Schema.org
                faq_html = self._build_faq_html(result.get("faqs", []))
                
                proposal = await self.shopify.create_optimization_proposal(
                    product_id=product.id,
                    optimization_type="faq",
                    field_name="faq_html",
                    original_value=None,
                    proposed_value=faq_html,
                    reasoning=f"FAQ gerado com {len(result.get('faqs', []))} perguntas para Featured Snippets",
                )
                return proposal
                
        except Exception as e:
            logger.error(f"Erro ao gerar FAQ: {e}")
        return None
    
    def _build_faq_html(self, faqs: List[Dict[str, str]]) -> str:
        """Constrói HTML do FAQ com Schema.org FAQPage markup"""
        if not faqs:
            return ""
        
        # Schema.org JSON-LD
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": faq["answer"]
                    }
                }
                for faq in faqs
            ]
        }
        
        html = f'''<script type="application/ld+json">
{json.dumps(schema, ensure_ascii=False, indent=2)}
</script>
<div class="product-faq">
<h2>Perguntas Frequentes</h2>'''
        
        for faq in faqs:
            html += f'''
<div class="faq-item">
  <h3 class="faq-question">{faq["question"]}</h3>
  <p class="faq-answer">{faq["answer"]}</p>
</div>'''
        
        html += "\n</div>"
        return html
    
    async def _generate_rich_description(
        self,
        product: ShopifyProduct,
        context: Dict[str, Any],
    ) -> Optional[OptimizationProposal]:
        """Gera descrição rica com estrutura semântica completa"""
        try:
            prompt = RICH_DESCRIPTION_PROMPT.format(
                product_name=context["product_name"],
                category=context["category"] or "Não informada",
                brand=context["brand"] or "Não informada",
                current_description=(context["current_description"] or "Sem descrição")[:500],
            )
            
            response = await self.ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ECOMMERCE},
                    {"role": "user", "content": prompt}
                ],
                **completion_params(2000, temperature=0.7),
            )
            
            content = response.choices[0].message.content
            
            result = parse_ai_json(content, "descrição rica Shopify")
            if result:

                keywords_str = ", ".join(result.get("keywords_used", []))
                headings_str = ", ".join(result.get("headings", []))
                
                proposal = await self.shopify.create_optimization_proposal(
                    product_id=product.id,
                    optimization_type="rich_description",
                    field_name="body_html",
                    original_value=product.body_html,
                    proposed_value=result["html"],
                    reasoning=f"Descrição rica: {result.get('word_count', 0)} palavras, "
                              f"headings: {headings_str}, keywords: {keywords_str}",
                )
                return proposal
                
        except Exception as e:
            logger.error(f"Erro ao gerar descrição rica: {e}")
        return None
    
    async def _generate_tags_keywords(
        self,
        product: ShopifyProduct,
        context: Dict[str, Any],
    ) -> Optional[OptimizationProposal]:
        """Gera tags e palavras-chave otimizadas para o produto"""
        try:
            prompt = TAGS_KEYWORDS_PROMPT.format(
                product_name=context["product_name"],
                category=context["category"] or "Não informada",
                brand=context["brand"] or "Não informada",
                description=(context["current_description"] or "")[:500],
            )
            
            response = await self.ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ECOMMERCE},
                    {"role": "user", "content": prompt}
                ],
                **completion_params(800, temperature=0.7),
            )
            
            content = response.choices[0].message.content
            
            result = parse_ai_json(content, "tags/keywords Shopify")
            if result:

                # Combinar todas as tags em uma string para Shopify
                all_tags = result.get("tags", [])
                tags_string = ", ".join(all_tags)
                
                # Criar valor detalhado com todas as keywords
                detailed_value = {
                    "tags": all_tags,
                    "tags_string": tags_string,
                    "main_keywords": result.get("main_keywords", []),
                    "long_tail_keywords": result.get("long_tail_keywords", []),
                    "lsi_keywords": result.get("lsi_keywords", []),
                }
                
                proposal = await self.shopify.create_optimization_proposal(
                    product_id=product.id,
                    optimization_type="tags",
                    field_name="tags",
                    original_value=product.tags,
                    proposed_value=json.dumps(detailed_value, ensure_ascii=False),
                    reasoning=result.get("reasoning", "Tags e keywords gerados por IA"),
                )
                return proposal
                
        except Exception as e:
            logger.error(f"Erro ao gerar tags/keywords: {e}")
        return None
    
    async def optimize_all_products(
        self, 
        limit: int = 50,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """
        Analisa e gera otimizações para todos os produtos.
        
        Args:
            limit: Máximo de produtos a processar
            auto_approve: Se True, aprova automaticamente (NÃO RECOMENDADO)
        
        Returns:
            Resumo das otimizações geradas
        """
        products = await self.shopify.get_products(limit=limit)
        
        total_proposals = 0
        products_analyzed = 0
        errors = []
        
        for product in products:
            try:
                proposals = await self.generate_optimizations(product.id)
                total_proposals += len(proposals)
                products_analyzed += 1
                
                if auto_approve:
                    for p in proposals:
                        await self.shopify.approve_proposal(p.id)
                        
            except Exception as e:
                errors.append(f"Produto {product.id}: {str(e)}")
        
        return {
            "products_analyzed": products_analyzed,
            "total_proposals": total_proposals,
            "auto_approved": auto_approve,
            "errors": errors if errors else None,
            "message": f"Geradas {total_proposals} propostas de otimização para {products_analyzed} produtos",
        }
    
    async def analyze_collection(self, collection_id: int, collection_type: str = "custom") -> Dict[str, Any]:
        """Analisa uma coleção e identifica oportunidades de otimização SEO"""
        collection = await self.shopify.get_collection(collection_id, collection_type)
        metafields = await self.shopify.get_collection_metafields(collection_id)
        
        issues = []
        recommendations = []
        score = 100
        
        # Análise do título
        if not collection.title:
            issues.append({"type": "missing_title", "severity": "critical"})
            score -= 25
        elif len(collection.title) < 20:
            issues.append({"type": "short_title", "severity": "warning"})
            score -= 10
            recommendations.append("Expandir título da coleção para melhor SEO")
        
        # Análise da descrição
        if not collection.body_html:
            issues.append({"type": "missing_description", "severity": "critical"})
            score -= 20
            recommendations.append("Adicionar descrição rica à coleção")
        else:
            desc_len = len(collection.body_html)
            if desc_len < 200:
                issues.append({"type": "short_description", "severity": "warning"})
                score -= 10
                recommendations.append("Expandir descrição (mín. 200 palavras recomendado)")
            
            # Verificar estrutura semântica
            has_h2 = "<h2" in collection.body_html.lower()
            if not has_h2:
                issues.append({"type": "no_semantic_structure", "severity": "warning"})
                score -= 5
                recommendations.append("Adicionar headings H2/H3 para melhor estrutura")
        
        # Análise de SEO title
        seo_title = metafields.get("seo_title")
        if not seo_title:
            issues.append({"type": "missing_seo_title", "severity": "important"})
            score -= 15
            recommendations.append("Adicionar Meta Title personalizado")
        
        # Análise de SEO description
        seo_description = metafields.get("seo_description")
        if not seo_description:
            issues.append({"type": "missing_seo_description", "severity": "important"})
            score -= 15
            recommendations.append("Adicionar Meta Description")
        
        # Imagem da coleção
        if not collection.image:
            issues.append({"type": "missing_collection_image", "severity": "warning"})
            score -= 5
            recommendations.append("Adicionar imagem de destaque à coleção")
        
        return {
            "collection": collection.model_dump(),
            "metafields": metafields,
            "issues": issues,
            "score": max(0, score),
            "recommendations": recommendations,
            "type": "collection",
        }
    
    async def generate_collection_optimizations(
        self,
        collection_id: int,
        collection_type: str = "custom",
    ) -> List[OptimizationProposal]:
        """Gera propostas de otimização para uma coleção baseado no contexto real dos produtos"""
        collection = await self.shopify.get_collection(collection_id, collection_type)
        metafields = await self.shopify.get_collection_metafields(collection_id)
        
        # IMPORTANTE: Buscar produtos da coleção para contexto real
        products = await self.shopify.get_collection_products(collection_id, limit=10)
        
        # Criar contexto dos produtos para o LLM
        products_context = ""
        if products:
            products_context = "\n".join([
                f"- {p.title} ({p.product_type or 'sem categoria'}): {(p.body_html or 'sem descrição')[:150]}... | Tags: {p.tags or 'sem tags'}"
                for p in products
            ])
        else:
            products_context = "(Nenhum produto encontrado nesta coleção)"
        
        proposals = []

        if not self.ai_client:
            return proposals

        # Data Enrichment antes da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": collection.title,
            "title": collection.title,
            "body_html": collection.body_html,
        })

        prompt = COLLECTION_OPTIMIZATION_PROMPT.format(
            collection_name=collection.title,
            current_description=(collection.body_html or "")[:500],
            products_context=products_context,
        )
        if enriched.get("keywords_mercado"):
            prompt += f"\n\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(enriched['keywords_mercado'][:10])}"
        if enriched.get("segmento"):
            prompt += f"\nSEGMENTO DE MERCADO: {enriched['segmento']}"
        if enriched.get("atributos_extraidos"):
            prompt += f"\nATRIBUTOS: {', '.join(enriched['atributos_extraidos'])}"
        
        try:
            response = await self.ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ECOMMERCE},
                    {"role": "user", "content": prompt}
                ],
                **completion_params(1500, temperature=0.7),
            )
            
            content = response.choices[0].message.content
            
            result = parse_ai_json(content, "coleção Shopify")
            if result:

                # Criar propostas
                for field in ["title", "description", "seo_title", "seo_description"]:
                    if field in result:
                        field_name = "body_html" if field == "description" else field
                        original = getattr(collection, field_name, None) or metafields.get(field)
                        
                        from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica
                        proposal = OptimizationProposal(
                            id=self.shopify._generate_proposal_id(),
                            product_id=collection_id,  # Usando product_id para manter compatibilidade
                            optimization_type=f"collection_{field}",
                            field_name=field_name,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field]["reasoning"],
                            status=OptimizationStatus.PENDING,
                            created_at=__import__('datetime').datetime.utcnow().isoformat(),
                            content_type="collection",
                            transparencia={
                                "atributos": validar_atributos_descritivos(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    atributos_produto=enriched.get("atributos_extraidos"),
                                ),
                                "semantica": calcular_cobertura_semantica(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    keywords_estrategicas=enriched.get("keywords_mercado"),
                                ),
                            },
                        )
                        self.shopify._proposals[proposal.id] = proposal
                        proposals.append(proposal)
                        
        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de coleção: {e}")
        
        return proposals
    
    async def analyze_page(self, page_id: int) -> Dict[str, Any]:
        """Analisa uma página institucional"""
        page = await self.shopify.get_page(page_id)
        metafields = await self.shopify.get_page_metafields(page_id)
        
        issues = []
        recommendations = []
        score = 100
        
        # Análise do título
        if not page.title:
            issues.append({"type": "missing_title", "severity": "critical"})
            score -= 25
        
        # Análise do conteúdo
        if not page.body_html:
            issues.append({"type": "missing_content", "severity": "critical"})
            score -= 30
            recommendations.append("Adicionar conteúdo à página")
        else:
            content_len = len(page.body_html)
            if content_len < 300:
                issues.append({"type": "short_content", "severity": "warning"})
                score -= 10
                recommendations.append("Expandir conteúdo da página")
            
            # Verificar estrutura
            has_h2 = "<h2" in page.body_html.lower()
            has_h3 = "<h3" in page.body_html.lower()
            if not has_h2 and not has_h3:
                issues.append({"type": "no_semantic_structure", "severity": "warning"})
                score -= 5
                recommendations.append("Adicionar headings H2/H3")
        
        # SEO
        seo_title = metafields.get("seo_title")
        if not seo_title:
            issues.append({"type": "missing_seo_title", "severity": "important"})
            score -= 15
            recommendations.append("Adicionar Meta Title")
        
        seo_description = metafields.get("seo_description")
        if not seo_description:
            issues.append({"type": "missing_seo_description", "severity": "important"})
            score -= 15
            recommendations.append("Adicionar Meta Description")
        
        return {
            "page": page.model_dump(),
            "metafields": metafields,
            "issues": issues,
            "score": max(0, score),
            "recommendations": recommendations,
            "type": "page",
        }
    
    async def generate_page_optimizations(self, page_id: int) -> List[OptimizationProposal]:
        """Gera propostas de otimização para uma página"""
        page = await self.shopify.get_page(page_id)
        metafields = await self.shopify.get_page_metafields(page_id)
        
        proposals = []
        
        if not self.ai_client:
            return proposals
        
        # Detectar tipo de página
        page_type = "institucional"
        handle_lower = page.handle.lower()
        if "about" in handle_lower or "sobre" in handle_lower:
            page_type = "Sobre Nós"
        elif "contact" in handle_lower or "contato" in handle_lower:
            page_type = "Contato"
        elif "faq" in handle_lower:
            page_type = "FAQ"
        elif "privacy" in handle_lower or "privacidade" in handle_lower:
            page_type = "Política de Privacidade"
        elif "terms" in handle_lower or "termos" in handle_lower:
            page_type = "Termos de Uso"
        
        # Data Enrichment antes da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": page.title,
            "title": page.title,
            "body_html": page.body_html,
        })

        prompt = PAGE_OPTIMIZATION_PROMPT.format(
            page_title=page.title,
            page_type=page_type,
            current_content=(page.body_html or "")[:500],
        )
        if enriched.get("segmento"):
            prompt += f"\n\nSEGMENTO DE MERCADO: {enriched['segmento']}"
        if enriched.get("atributos_extraidos"):
            prompt += f"\nATRIBUTOS: {', '.join(enriched['atributos_extraidos'])}"
        if enriched.get("keywords_mercado"):
            prompt += f"\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(enriched['keywords_mercado'][:10])}"
        
        try:
            response = await self.ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ECOMMERCE},
                    {"role": "user", "content": prompt}
                ],
                **completion_params(2000, temperature=0.7),
            )
            
            content = response.choices[0].message.content
            
            result = parse_ai_json(content, "página Shopify")
            if result:

                for field in ["title", "content", "seo_title", "seo_description"]:
                    if field in result:
                        field_name = "body_html" if field == "content" else field
                        original = getattr(page, field_name, None) or metafields.get(field)
                        
                        from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica
                        proposal = OptimizationProposal(
                            id=self.shopify._generate_proposal_id(),
                            product_id=page_id,
                            optimization_type=f"page_{field}",
                            field_name=field_name,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field]["reasoning"],
                            status=OptimizationStatus.PENDING,
                            created_at=__import__('datetime').datetime.utcnow().isoformat(),
                            content_type="page",
                            transparencia={
                                "atributos": validar_atributos_descritivos(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    atributos_produto=enriched.get("atributos_extraidos"),
                                ),
                                "semantica": calcular_cobertura_semantica(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    keywords_estrategicas=enriched.get("keywords_mercado"),
                                ),
                            },
                        )
                        self.shopify._proposals[proposal.id] = proposal
                        proposals.append(proposal)
                        
        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de página: {e}")
        
        return proposals
    
    async def analyze_article(self, blog_id: int, article_id: int) -> Dict[str, Any]:
        """Analisa um artigo de blog"""
        article = await self.shopify.get_article(blog_id, article_id)
        metafields = await self.shopify.get_article_metafields(article_id)
        
        issues = []
        recommendations = []
        score = 100
        
        # Análise do título
        if not article.title:
            issues.append({"type": "missing_title", "severity": "critical"})
            score -= 25
        elif len(article.title) < 30:
            issues.append({"type": "short_title", "severity": "warning"})
            score -= 5
            recommendations.append("Expandir título do artigo")
        elif len(article.title) > 70:
            issues.append({"type": "long_title", "severity": "warning"})
            score -= 5
            recommendations.append("Reduzir título para melhor exibição")
        
        # Análise do conteúdo
        if not article.body_html:
            issues.append({"type": "missing_content", "severity": "critical"})
            score -= 30
            recommendations.append("Adicionar conteúdo ao artigo")
        else:
            # Contar palavras aproximadamente
            import re
            words = len(re.findall(r'\w+', article.body_html))
            if words < 300:
                issues.append({"type": "short_content", "severity": "warning", "word_count": words})
                score -= 15
                recommendations.append(f"Artigo com apenas ~{words} palavras. Recomendado: 800+ palavras")
            elif words < 800:
                issues.append({"type": "medium_content", "severity": "info", "word_count": words})
                recommendations.append(f"Considere expandir para 1000+ palavras para melhor ranking")
            
            # Estrutura
            has_h2 = "<h2" in article.body_html.lower()
            has_h3 = "<h3" in article.body_html.lower()
            if not has_h2:
                issues.append({"type": "no_h2_headings", "severity": "warning"})
                score -= 5
                recommendations.append("Adicionar subtítulos H2 para estruturar o conteúdo")
        
        # Tags
        if not article.tags:
            issues.append({"type": "missing_tags", "severity": "warning"})
            score -= 5
            recommendations.append("Adicionar tags ao artigo")
        
        # Imagem de destaque
        if not article.image:
            issues.append({"type": "missing_featured_image", "severity": "warning"})
            score -= 5
            recommendations.append("Adicionar imagem de destaque")
        
        # SEO
        seo_title = metafields.get("seo_title")
        if not seo_title:
            issues.append({"type": "missing_seo_title", "severity": "important"})
            score -= 10
            recommendations.append("Adicionar Meta Title")
        
        seo_description = metafields.get("seo_description")
        if not seo_description:
            issues.append({"type": "missing_seo_description", "severity": "important"})
            score -= 10
            recommendations.append("Adicionar Meta Description")
        
        return {
            "article": article.model_dump(),
            "metafields": metafields,
            "issues": issues,
            "score": max(0, score),
            "recommendations": recommendations,
            "type": "article",
        }
    
    async def generate_article_optimizations(self, blog_id: int, article_id: int) -> List[OptimizationProposal]:
        """Gera propostas de otimização para um artigo"""
        article = await self.shopify.get_article(blog_id, article_id)
        metafields = await self.shopify.get_article_metafields(article_id)
        
        proposals = []
        
        if not self.ai_client:
            return proposals
        
        # Data Enrichment antes da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": article.title,
            "title": article.title,
            "tags": article.tags or "",
            "body_html": article.body_html,
        })

        prompt = ARTICLE_OPTIMIZATION_PROMPT.format(
            article_title=article.title,
            author=article.author or "Não informado",
            tags=article.tags or "Nenhuma",
            current_content=(article.body_html or "")[:800],
        )
        if enriched.get("segmento"):
            prompt += f"\n\nSEGMENTO DE MERCADO: {enriched['segmento']}"
        if enriched.get("atributos_extraidos"):
            prompt += f"\nATRIBUTOS: {', '.join(enriched['atributos_extraidos'])}"
        if enriched.get("keywords_mercado"):
            prompt += f"\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(enriched['keywords_mercado'][:10])}"
        
        try:
            response = await self.ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ECOMMERCE},
                    {"role": "user", "content": prompt}
                ],
                **completion_params(2500, temperature=0.7),
            )
            
            content = response.choices[0].message.content
            
            result = parse_ai_json(content, "artigo Shopify")
            if result:

                for field in ["title", "content", "seo_title", "seo_description", "tags"]:
                    if field in result:
                        field_name = "body_html" if field == "content" else field
                        original = getattr(article, field_name, None) or metafields.get(field)
                        
                        from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica
                        proposal = OptimizationProposal(
                            id=self.shopify._generate_proposal_id(),
                            product_id=article_id,
                            optimization_type=f"article_{field}",
                            field_name=field_name,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field]["reasoning"],
                            status=OptimizationStatus.PENDING,
                            created_at=__import__('datetime').datetime.utcnow().isoformat(),
                            content_type="article",
                            transparencia={
                                "atributos": validar_atributos_descritivos(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    atributos_produto=enriched.get("atributos_extraidos"),
                                ),
                                "semantica": calcular_cobertura_semantica(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    keywords_estrategicas=enriched.get("keywords_mercado"),
                                ),
                            },
                        )
                        self.shopify._proposals[proposal.id] = proposal
                        proposals.append(proposal)
                        
        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de artigo: {e}")
        
        return proposals


def create_shopify_optimizer(
    shop_url: str,
    api_key: str = None,
    api_secret: str = None,
    access_token: str = None,
) -> ShopifySEOOptimizer:
    """
    Cria instância do otimizador SEO para Shopify.
    """
    client = create_shopify_client(
        shop_url=shop_url,
        api_key=api_key,
        api_secret=api_secret,
        access_token=access_token,
    )
    return ShopifySEOOptimizer(client)
