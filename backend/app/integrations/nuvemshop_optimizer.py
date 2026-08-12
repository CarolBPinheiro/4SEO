"""
Otimizador SEO para Nuvemshop - SiteCan PRO
Usa IA para gerar sugestões de otimização SEO para produtos, categorias, páginas e blog
"""
import os
import json
import re
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from openai import AsyncOpenAI

from .nuvemshop import (
    NuvemshopClient, 
    NuvemshopProduct,
    NuvemshopCategory,
    NuvemshopPage,
    NuvemshopBlogPost,
    OptimizationProposal,
    OptimizationStatus
)

logger = logging.getLogger(__name__)

# Configuração OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
from app.ai_config import AI_MODEL, completion_params, parse_ai_json

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

Sempre responda em português brasileiro.
Formate sua resposta SEMPRE como JSON válido, no formato exato solicitado em cada tarefa."""


class NuvemshopOptimizer:
    """Otimizador SEO para lojas Nuvemshop"""
    
    def __init__(self, nuvemshop_client: NuvemshopClient):
        self.nuvemshop = nuvemshop_client
        self.ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    
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
    
    def _build_enriched_prompt_blocks(self, target_keyword: str = None, serp_context: str = "", gsc_context: str = "") -> str:
        """Build extra prompt blocks for keyword, SERP, and GSC context"""
        blocks = []
        if target_keyword:
            blocks.append(f"\nKEYWORD ALVO: {target_keyword}\nTodas as otimizações DEVEM ser centradas nesta keyword.")
        if serp_context:
            blocks.append(f"\n{serp_context}\n\nIMPORTANTE: Analise os concorrentes acima. Suas sugestões devem SUPERAR os títulos e descrições deles.")
        if gsc_context:
            blocks.append(f"\n{gsc_context}\n\nUse esses dados para direcionar as otimizações.")
        if blocks:
            blocks.append("\nLEMBRETE: Preserve medidas, links externos, telefones, tabelas de tamanho e especificações técnicas do conteúdo original.")
        return "\n".join(blocks)
    
    def _extract_priority_fields(self, result_field: dict) -> dict:
        """Extract priority/impact/effort from AI response field"""
        return {
            "priority": result_field.get("priority"),
            "impact": result_field.get("impact"),
            "effort": result_field.get("effort"),
        }
    
    async def analyze_product(self, product_id: int) -> Dict[str, Any]:
        """Diagnóstico SEO contextual do produto (IA + fallback heurístico)."""
        from app.product_diagnosis import diagnose_product

        product = await self.nuvemshop.get_product(product_id)

        images_without_alt = 0
        for img in product.images or []:
            alt = img.get("alt", "")
            if isinstance(alt, dict):
                alt = alt.get("pt", "")
            if not alt:
                images_without_alt += 1

        enrichment: Dict[str, Any] = {}
        try:
            from app.data_enrichment import enrich_product_context
            enrichment = await enrich_product_context({
                "name": product.name,
                "title": product.name,
                "brand": product.brand or "",
                "tags": product.tags or "",
                "categories": product.categories or [],
            })
        except Exception as e:
            logger.warning(f"[nuvemshop] enrichment skipped: {e}")

        diagnosis = await diagnose_product(
            {
                "title": product.name,
                "name": product.name,
                "description": product.description,
                "seo_title": product.seo_title,
                "seo_description": product.seo_description,
                "tags": product.tags,
                "brand": product.brand,
                "categories": product.categories,
                "images_without_alt": images_without_alt,
            },
            ai_client=self.ai_client,
            enrichment=enrichment,
            platform="Nuvemshop",
        )

        return {
            "product": product.model_dump(),
            "score": diagnosis["score"],
            "score_justification": diagnosis["score_justification"],
            "summary": diagnosis["summary"],
            "issues": diagnosis["issues"],
            "opportunities": diagnosis.get("opportunities") or [],
            "recommended_actions": diagnosis.get("recommended_actions") or [],
            "recommendations": diagnosis.get("recommendations") or [],
            "images_without_alt": images_without_alt,
            "source": diagnosis.get("source"),
            "type": "product",
        }
    
    async def optimize_product(
        self,
        product_id: int,
        options: Dict[str, bool] = None,
        target_keyword: str = None,
        user: dict = None,
        page_url: str = None,
    ) -> List[OptimizationProposal]:
        """Gera propostas de otimização para um produto usando IA"""
        if not self.ai_client:
            logger.warning("OpenAI API key não configurada — otimização de IA indisponível; retornando lista vazia")
            return []
        
        product = await self.nuvemshop.get_product(product_id)

        if options is None:
            from app.product_diagnosis import actions_to_optimize_options, heuristic_diagnosis
            images_without_alt = 0
            for img in product.images or []:
                alt = img.get("alt", "")
                if isinstance(alt, dict):
                    alt = alt.get("pt", "")
                if not alt:
                    images_without_alt += 1
            heuristic = heuristic_diagnosis({
                "title": product.name,
                "description": product.description,
                "seo_title": product.seo_title,
                "seo_description": product.seo_description,
                "tags": product.tags,
                "images_without_alt": images_without_alt,
            })
            options = actions_to_optimize_options(heuristic.get("recommended_actions") or [])
        else:
            # Normaliza aliases do frontend (optimize_name -> optimize_title)
            if "optimize_name" in options and "optimize_title" not in options:
                options = {**options, "optimize_title": bool(options.get("optimize_name"))}
        
        proposals = []
        
        # Fetch contexto competitivo e de performance
        effective_keyword = target_keyword or product.name
        serp_context = await self._fetch_serp_context(effective_keyword) if effective_keyword else ""
        gsc_context = ""
        gsc_metrics = None
        if user and page_url:
            gsc_context, gsc_metrics = await self._fetch_gsc_context(user, page_url)

        # Data Enrichment obrigatório ANTES da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": product.name,
            "title": product.name,
            "brand": product.brand or "",
            "tags": product.tags or "",
            "categories": product.categories or [],
        }, user_id=user.get("user_id") if user else None)
        segmento = enriched.get("segmento", "")
        atributos = enriched.get("atributos_extraidos", [])
        keywords_mercado = enriched.get("keywords_mercado", [])

        extra_blocks = self._build_enriched_prompt_blocks(target_keyword, serp_context, gsc_context)
        if segmento:
            extra_blocks += f"\nSEGMENTO DE MERCADO: {segmento}"
        if atributos:
            extra_blocks += f"\nATRIBUTOS DO PRODUTO: {', '.join(atributos)}"
        if keywords_mercado:
            extra_blocks += f"\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(keywords_mercado[:10])}"
        
        pre_metrics_snapshot = None
        if gsc_metrics and gsc_metrics.get("found"):
            pre_metrics_snapshot = {
                "clicks": gsc_metrics.get("clicks", 0),
                "impressions": gsc_metrics.get("impressions", 0),
                "ctr": gsc_metrics.get("ctr", 0),
                "position": gsc_metrics.get("position", 0),
            }
        
        # Prompt para otimização
        prompt = f"""Analise este produto e sugira otimizações de SEO:

PRODUTO:
- Nome: {product.name}
- Descrição atual: {product.description or 'Não tem'}
- Meta título: {product.seo_title or 'Não tem'}
- Meta descrição: {product.seo_description or 'Não tem'}
- Tags: {product.tags or 'Não tem'}
- Marca: {product.brand or 'Não informada'}
- Categorias: {', '.join([c.get('name', {}).get('pt', '') for c in product.categories]) if product.categories else 'Nenhuma'}{extra_blocks}

Gere um JSON com as seguintes otimizações (apenas os campos solicitados).
Para CADA campo inclua priority, impact e effort:
{{
    "title": {{"value": "título otimizado", "reasoning": "explicação", "priority": "high|medium|low", "impact": "ranking|ctr|conversao|visibilidade", "effort": "low|medium|high"}},
    "description": {{"value": "descrição otimizada em HTML", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_title": {{"value": "meta título otimizado", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_description": {{"value": "meta descrição otimizada", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "tags": {{"value": "tag1, tag2, tag3", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}}
}}

Campos solicitados: {', '.join([k.replace('optimize_', '').replace('generate_', '') for k, v in options.items() if v])}"""

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
            
            # Extrair JSON da resposta
            result = parse_ai_json(content, "produto Nuvemshop")
            if result:

                # Criar propostas
                field_mapping = {
                    "title": ("name", "optimize_title"),
                    "description": ("description", "optimize_description"),
                    "seo_title": ("seo_title", "optimize_seo_title"),
                    "seo_description": ("seo_description", "optimize_seo_description"),
                    "tags": ("tags", "generate_tags")
                }
                
                from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica

                for field, (attr, option) in field_mapping.items():
                    if field in result and options.get(option, False):
                        original = getattr(product, attr, None)
                        pf = self._extract_priority_fields(result[field])

                        proposal = OptimizationProposal(
                            id=self.nuvemshop._generate_proposal_id(),
                            product_id=product_id,
                            optimization_type=field,
                            field_name=attr,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field]["reasoning"],
                            status=OptimizationStatus.PENDING,
                            created_at=datetime.utcnow().isoformat(),
                            content_type="product",
                            priority=pf["priority"],
                            impact=pf["impact"],
                            effort=pf["effort"],
                            target_keyword=target_keyword,
                            pre_metrics=pre_metrics_snapshot,
                            transparencia={
                                "atributos": validar_atributos_descritivos(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    atributos_produto=atributos,
                                ),
                                "semantica": calcular_cobertura_semantica(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    keywords_estrategicas=keywords_mercado,
                                ),
                            },
                        )
                        self.nuvemshop._proposals[proposal.id] = proposal
                        proposals.append(proposal)
        
        except Exception as e:
            logger.error(f"Erro ao gerar otimizações: {e}")
        
        # Otimizar alt text das imagens
        if options.get("optimize_image_alts", True) and product.images:
            for img in product.images:
                img_id = img.get("id")
                current_alt = img.get("alt", "")
                if isinstance(current_alt, dict):
                    current_alt = current_alt.get("pt", "")
                
                if not current_alt:
                    try:
                        alt_prompt = f"""Gere um texto alternativo descritivo para a imagem do produto "{product.name}".
                        
O texto deve ser:
- Descritivo e natural
- Entre 50-125 caracteres
- Incluir o nome do produto

Responda apenas com o texto alternativo, sem aspas."""

                        alt_response = await self.ai_client.chat.completions.create(
                            model=AI_MODEL,
                            messages=[
                                {"role": "system", "content": "Você é um especialista em SEO e acessibilidade web."},
                                {"role": "user", "content": alt_prompt}
                            ],
                            **completion_params(100, temperature=0.7),
                        )
                        
                        alt_text = alt_response.choices[0].message.content.strip().strip('"')
                        
                        proposal = OptimizationProposal(
                            id=self.nuvemshop._generate_proposal_id(),
                            product_id=product_id,
                            optimization_type="image_alt",
                            field_name=f"image_alt_{img_id}",
                            original_value=current_alt,
                            proposed_value=alt_text,
                            reasoning="Texto alternativo para melhorar acessibilidade e SEO da imagem",
                            status=OptimizationStatus.PENDING,
                            created_at=datetime.utcnow().isoformat(),
                            content_type="product",
                        )
                        self.nuvemshop._proposals[proposal.id] = proposal
                        proposals.append(proposal)
                    
                    except Exception as e:
                        logger.error(f"Erro ao gerar alt text: {e}")
        
        return proposals
    
    async def analyze_category(self, category_id: int) -> Dict[str, Any]:
        """Analisa uma categoria e retorna métricas de SEO"""
        category = await self.nuvemshop.get_category(category_id)
        products = await self.nuvemshop.get_category_products(category_id, limit=10)
        
        issues = []
        score = 100
        
        # Verificar nome
        if not category.name:
            issues.append({"type": "missing_name", "message": "Categoria sem nome", "severity": "critical"})
            score -= 30
        
        # Verificar descrição
        if not category.description:
            issues.append({"type": "missing_description", "message": "Categoria sem descrição", "severity": "warning"})
            score -= 15
        elif len(category.description) < 50:
            issues.append({"type": "short_description", "message": "Descrição muito curta", "severity": "info"})
            score -= 5
        
        # Verificar SEO
        if not category.seo_title:
            issues.append({"type": "missing_seo_title", "message": "Meta título não definido", "severity": "warning"})
            score -= 10
        
        if not category.seo_description:
            issues.append({"type": "missing_seo_description", "message": "Meta descrição não definida", "severity": "warning"})
            score -= 10
        
        recommendations = []
        if not category.description:
            recommendations.append("Adicione uma descrição para a categoria")
        if not category.seo_title:
            recommendations.append("Adicione um meta título otimizado")
        if not category.seo_description:
            recommendations.append("Adicione uma meta descrição persuasiva")
        
        return {
            "category": category.model_dump(),
            "products_count": len(products),
            "products_sample": [p.model_dump() for p in products[:5]],
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "type": "category"
        }
    
    async def optimize_category(self, category_id: int, target_keyword: str = None, user: dict = None, page_url: str = None) -> List[OptimizationProposal]:
        """Gera propostas de otimização para uma categoria usando IA"""
        if not self.ai_client:
            logger.warning("OpenAI API key não configurada — otimização de IA indisponível; retornando lista vazia")
            return []
        
        category = await self.nuvemshop.get_category(category_id)
        products = await self.nuvemshop.get_category_products(category_id, limit=10)
        
        # Contexto dos produtos da categoria
        products_context = "\n".join([
            f"- {p.name}" for p in products[:10]
        ]) if products else "Nenhum produto"
        
        # Contexto competitivo
        effective_keyword = target_keyword or category.name
        serp_context = await self._fetch_serp_context(effective_keyword) if effective_keyword else ""
        gsc_context = ""
        gsc_metrics = None
        if user and page_url:
            gsc_context, gsc_metrics = await self._fetch_gsc_context(user, page_url)

        # Data Enrichment antes da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": category.name,
            "title": category.name,
        }, user_id=user.get("user_id") if user else None)
        atributos = enriched.get("atributos_extraidos", [])
        keywords_mercado = enriched.get("keywords_mercado", [])

        extra_blocks = self._build_enriched_prompt_blocks(target_keyword, serp_context, gsc_context)
        if enriched.get("segmento"):
            extra_blocks += f"\nSEGMENTO DE MERCADO: {enriched['segmento']}"
        if atributos:
            extra_blocks += f"\nATRIBUTOS: {', '.join(atributos)}"
        if keywords_mercado:
            extra_blocks += f"\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(keywords_mercado[:10])}"
        
        pre_metrics_snapshot = None
        if gsc_metrics and gsc_metrics.get("found"):
            pre_metrics_snapshot = {k: gsc_metrics.get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}
        
        prompt = f"""Analise esta categoria de e-commerce e sugira otimizações de SEO.

CATEGORIA:
- Nome: {category.name}
- Descrição atual: {category.description or 'Não tem'}
- Meta título: {category.seo_title or 'Não tem'}
- Meta descrição: {category.seo_description or 'Não tem'}

PRODUTOS DESTA CATEGORIA:
{products_context}{extra_blocks}

Gere um JSON com otimizações considerando os produtos reais da categoria.
Para CADA campo inclua priority, impact e effort:
{{
    "title": {{"value": "nome otimizado", "reasoning": "explicação", "priority": "high|medium|low", "impact": "ranking|ctr|conversao|visibilidade", "effort": "low|medium|high"}},
    "description": {{"value": "descrição otimizada em HTML", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_title": {{"value": "meta título otimizado (50-70 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_description": {{"value": "meta descrição otimizada (120-160 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}}
}}"""

        proposals = []
        
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
            
            result = parse_ai_json(content, "categoria Nuvemshop")
            if result:

                for field in ["title", "description", "seo_title", "seo_description"]:
                    if field in result:
                        field_name = "name" if field == "title" else field
                        original = getattr(category, field_name, None)
                        pf = self._extract_priority_fields(result[field])
                        
                        from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica
                        proposal = OptimizationProposal(
                            id=self.nuvemshop._generate_proposal_id(),
                            product_id=category_id,
                            optimization_type=f"category_{field}",
                            field_name=field_name,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field]["reasoning"],
                            status=OptimizationStatus.PENDING,
                            created_at=datetime.utcnow().isoformat(),
                            content_type="category",
                            priority=pf.get("priority"),
                            impact=pf.get("impact"),
                            effort=pf.get("effort"),
                            target_keyword=target_keyword,
                            pre_metrics=pre_metrics_snapshot,
                            transparencia={
                                "atributos": validar_atributos_descritivos(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    atributos_produto=atributos,
                                ),
                                "semantica": calcular_cobertura_semantica(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    keywords_estrategicas=keywords_mercado,
                                ),
                            },
                        )
                        self.nuvemshop._proposals[proposal.id] = proposal
                        proposals.append(proposal)
                        
        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de categoria: {e}")
        
        return proposals
    
    async def analyze_page(self, page_id: int) -> Dict[str, Any]:
        """Analisa uma página e retorna métricas de SEO"""
        page = await self.nuvemshop.get_page(page_id)
        
        issues = []
        score = 100
        
        # Verificar título
        if not page.title:
            issues.append({"type": "missing_title", "message": "Página sem título", "severity": "critical"})
            score -= 30
        
        # Verificar conteúdo
        if not page.content:
            issues.append({"type": "missing_content", "message": "Página sem conteúdo", "severity": "critical"})
            score -= 25
        elif len(page.content) < 200:
            issues.append({"type": "short_content", "message": "Conteúdo muito curto", "severity": "warning"})
            score -= 10
        
        # Verificar SEO
        if not page.seo_title:
            issues.append({"type": "missing_seo_title", "message": "Meta título não definido", "severity": "warning"})
            score -= 10
        
        if not page.seo_description:
            issues.append({"type": "missing_seo_description", "message": "Meta descrição não definida", "severity": "warning"})
            score -= 10
        
        recommendations = []
        if not page.seo_title:
            recommendations.append("Adicione um meta título otimizado")
        if not page.seo_description:
            recommendations.append("Adicione uma meta descrição persuasiva")
        if page.content and len(page.content) < 500:
            recommendations.append("Considere expandir o conteúdo da página")
        
        return {
            "page": page.model_dump(),
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "type": "page"
        }
    
    async def optimize_page(self, page_id: int, target_keyword: str = None, user: dict = None, page_url: str = None) -> List[OptimizationProposal]:
        """Gera propostas de otimização para uma página usando IA"""
        if not self.ai_client:
            logger.warning("OpenAI API key não configurada — otimização de IA indisponível; retornando lista vazia")
            return []
        
        page = await self.nuvemshop.get_page(page_id)
        
        # Contexto competitivo
        effective_keyword = target_keyword or page.title
        serp_context = await self._fetch_serp_context(effective_keyword) if effective_keyword else ""
        gsc_context = ""
        gsc_metrics = None
        if user and page_url:
            gsc_context, gsc_metrics = await self._fetch_gsc_context(user, page_url)

        # Data Enrichment antes da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": page.title,
            "title": page.title,
        }, user_id=user.get("user_id") if user else None)
        atributos = enriched.get("atributos_extraidos", [])
        keywords_mercado = enriched.get("keywords_mercado", [])

        extra_blocks = self._build_enriched_prompt_blocks(target_keyword, serp_context, gsc_context)
        if enriched.get("segmento"):
            extra_blocks += f"\nSEGMENTO DE MERCADO: {enriched['segmento']}"
        if atributos:
            extra_blocks += f"\nATRIBUTOS: {', '.join(atributos)}"
        if keywords_mercado:
            extra_blocks += f"\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(keywords_mercado[:10])}"
        
        pre_metrics_snapshot = None
        if gsc_metrics and gsc_metrics.get("found"):
            pre_metrics_snapshot = {k: gsc_metrics.get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}
        
        prompt = f"""Analise esta página e sugira otimizações de SEO.

PÁGINA:
- Título: {page.title}
- Conteúdo atual: {page.content[:500] if page.content else 'Não tem'}...
- Meta título: {page.seo_title or 'Não tem'}
- Meta descrição: {page.seo_description or 'Não tem'}{extra_blocks}

Gere um JSON com otimizações. Para CADA campo inclua priority, impact e effort:
{{
    "title": {{"value": "título otimizado", "reasoning": "explicação", "priority": "high|medium|low", "impact": "ranking|ctr|conversao|visibilidade", "effort": "low|medium|high"}},
    "content": {{"value": "conteúdo otimizado em HTML", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_title": {{"value": "meta título otimizado (50-70 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_description": {{"value": "meta descrição otimizada (120-160 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}}
}}"""

        proposals = []
        
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
            
            result = parse_ai_json(content, "página Nuvemshop")
            if result:

                for field in ["title", "content", "seo_title", "seo_description"]:
                    if field in result:
                        original = getattr(page, field, None)
                        pf = self._extract_priority_fields(result[field])
                        
                        from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica
                        proposal = OptimizationProposal(
                            id=self.nuvemshop._generate_proposal_id(),
                            product_id=page_id,
                            optimization_type=f"page_{field}",
                            field_name=field,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field]["reasoning"],
                            status=OptimizationStatus.PENDING,
                            created_at=datetime.utcnow().isoformat(),
                            content_type="page",
                            priority=pf.get("priority"),
                            impact=pf.get("impact"),
                            effort=pf.get("effort"),
                            target_keyword=target_keyword,
                            pre_metrics=pre_metrics_snapshot,
                            transparencia={
                                "atributos": validar_atributos_descritivos(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    atributos_produto=atributos,
                                ),
                                "semantica": calcular_cobertura_semantica(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    keywords_estrategicas=keywords_mercado,
                                ),
                            },
                        )
                        self.nuvemshop._proposals[proposal.id] = proposal
                        proposals.append(proposal)
                        
        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de página: {e}")
        
        return proposals
    
    async def analyze_blog_post(self, blog_id: int, post_id: int) -> Dict[str, Any]:
        """Analisa um post do blog e retorna métricas de SEO"""
        post = await self.nuvemshop.get_blog_post(blog_id, post_id)
        
        issues = []
        score = 100
        
        # Verificar título
        if not post.title:
            issues.append({"type": "missing_title", "message": "Post sem título", "severity": "critical"})
            score -= 30
        
        # Verificar conteúdo
        if not post.body:
            issues.append({"type": "missing_body", "message": "Post sem conteúdo", "severity": "critical"})
            score -= 25
        elif len(post.body) < 300:
            issues.append({"type": "short_body", "message": "Conteúdo muito curto", "severity": "warning"})
            score -= 10
        
        # Verificar SEO
        if not post.seo_title:
            issues.append({"type": "missing_seo_title", "message": "Meta título não definido", "severity": "warning"})
            score -= 10
        
        if not post.seo_description:
            issues.append({"type": "missing_seo_description", "message": "Meta descrição não definida", "severity": "warning"})
            score -= 10
        
        # Verificar tags
        if not post.tags:
            issues.append({"type": "missing_tags", "message": "Post sem tags", "severity": "info"})
            score -= 5
        
        recommendations = []
        if not post.seo_title:
            recommendations.append("Adicione um meta título otimizado")
        if not post.seo_description:
            recommendations.append("Adicione uma meta descrição persuasiva")
        if not post.tags:
            recommendations.append("Adicione tags relevantes ao post")
        
        return {
            "post": post.model_dump(),
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "type": "blog"
        }
    
    async def optimize_blog_post(self, blog_id: int, post_id: int, target_keyword: str = None, user: dict = None, page_url: str = None) -> List[OptimizationProposal]:
        """Gera propostas de otimização para um post do blog usando IA"""
        if not self.ai_client:
            logger.warning("OpenAI API key não configurada — otimização de IA indisponível; retornando lista vazia")
            return []
        
        post = await self.nuvemshop.get_blog_post(blog_id, post_id)
        
        # Contexto competitivo
        effective_keyword = target_keyword or post.title
        serp_context = await self._fetch_serp_context(effective_keyword) if effective_keyword else ""
        gsc_context = ""
        gsc_metrics = None
        if user and page_url:
            gsc_context, gsc_metrics = await self._fetch_gsc_context(user, page_url)

        # Data Enrichment antes da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": post.title,
            "title": post.title,
            "tags": post.tags or "",
        }, user_id=user.get("user_id") if user else None)
        atributos = enriched.get("atributos_extraidos", [])
        keywords_mercado = enriched.get("keywords_mercado", [])

        extra_blocks = self._build_enriched_prompt_blocks(target_keyword, serp_context, gsc_context)
        if enriched.get("segmento"):
            extra_blocks += f"\nSEGMENTO DE MERCADO: {enriched['segmento']}"
        if atributos:
            extra_blocks += f"\nATRIBUTOS: {', '.join(atributos)}"
        if keywords_mercado:
            extra_blocks += f"\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(keywords_mercado[:10])}"
        
        pre_metrics_snapshot = None
        if gsc_metrics and gsc_metrics.get("found"):
            pre_metrics_snapshot = {k: gsc_metrics.get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}
        
        prompt = f"""Analise este post de blog e sugira otimizações de SEO.

POST:
- Título: {post.title}
- Conteúdo: {post.body[:500] if post.body else 'Não tem'}...
- Meta título: {post.seo_title or 'Não tem'}
- Meta descrição: {post.seo_description or 'Não tem'}
- Tags: {post.tags or 'Não tem'}{extra_blocks}

Gere um JSON com otimizações. Para CADA campo inclua priority, impact e effort:
{{
    "title": {{"value": "título otimizado", "reasoning": "explicação", "priority": "high|medium|low", "impact": "ranking|ctr|conversao|visibilidade", "effort": "low|medium|high"}},
    "body": {{"value": "conteúdo otimizado em HTML", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_title": {{"value": "meta título otimizado (50-70 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_description": {{"value": "meta descrição otimizada (120-160 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "tags": {{"value": "tag1, tag2, tag3", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}}
}}"""

        proposals = []
        
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
            
            result = parse_ai_json(content, "post de blog Nuvemshop")
            if result:

                for field in ["title", "body", "seo_title", "seo_description", "tags"]:
                    if field in result:
                        original = getattr(post, field, None)
                        pf = self._extract_priority_fields(result[field])
                        
                        from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica
                        proposal = OptimizationProposal(
                            id=self.nuvemshop._generate_proposal_id(),
                            product_id=post_id,
                            optimization_type=f"blog_{field}",
                            field_name=field,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field]["reasoning"],
                            status=OptimizationStatus.PENDING,
                            created_at=datetime.utcnow().isoformat(),
                            content_type="blog",
                            blog_id=blog_id,
                            priority=pf.get("priority"),
                            impact=pf.get("impact"),
                            effort=pf.get("effort"),
                            target_keyword=target_keyword,
                            pre_metrics=pre_metrics_snapshot,
                            transparencia={
                                "atributos": validar_atributos_descritivos(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    atributos_produto=atributos,
                                ),
                                "semantica": calcular_cobertura_semantica(
                                    titulo_original=original,
                                    titulo_sugerido=result[field]["value"],
                                    keywords_estrategicas=keywords_mercado,
                                ),
                            },
                        )
                        self.nuvemshop._proposals[proposal.id] = proposal
                        proposals.append(proposal)
                        
        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de blog: {e}")
        
        return proposals
