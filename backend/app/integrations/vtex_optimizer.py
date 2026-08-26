"""
Otimizador SEO para lojas VTEX - SiteCan PRO
Gera propostas de otimização (produtos e categorias) com IA, seguindo o mesmo
pipeline dos otimizadores Shopify/Nuvemshop: data enrichment -> SYSTEM_PROMPT_V2 ->
validação pós-IA (transparência).

Campos VTEX (Catalog API):
- Produto: Name, Title (title tag), Description, MetaTagDescription, KeyWords, LinkId
- Categoria: Name, Title (title tag), Description (= meta description da categoria), Keywords
"""
import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from openai import AsyncOpenAI

from app.integrations.vtex import VtexClient
from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus
# Mesmo system prompt V2 ("Engenheiro de SEO Sênior") usado pelos demais otimizadores
from app.integrations.nuvemshop_optimizer import SYSTEM_PROMPT_ECOMMERCE
from app.ai_config import AI_MODEL, completion_params, parse_ai_json

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class VtexSEOOptimizer:
    """Otimizador SEO para lojas VTEX"""

    def __init__(self, vtex_client: VtexClient):
        self.vtex = vtex_client
        self.ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    # ==================== HELPERS DE ENRIQUECIMENTO (padrão dos demais otimizadores) ====================

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

    def _transparencia(self, original: Optional[str], proposed: str, atributos: list, keywords: list) -> Dict[str, Any]:
        """Validação pós-IA: atributos descritivos + cobertura semântica"""
        from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica
        return {
            "atributos": validar_atributos_descritivos(
                titulo_original=original,
                titulo_sugerido=proposed,
                atributos_produto=atributos,
            ),
            "semantica": calcular_cobertura_semantica(
                titulo_original=original,
                titulo_sugerido=proposed,
                keywords_estrategicas=keywords,
            ),
        }

    # ==================== PRODUTOS ====================

    async def analyze_product(self, product_id: int) -> Dict[str, Any]:
        """Diagnóstico SEO contextual do produto (IA + fallback heurístico)."""
        from app.product_diagnosis import diagnose_product

        product = await self.vtex.get_product(product_id)

        enrichment: Dict[str, Any] = {}
        try:
            from app.data_enrichment import enrich_product_context
            enrichment = await enrich_product_context({
                "name": product.name,
                "title": product.title or product.name,
                "tags": product.keywords or "",
            })
        except Exception as e:
            logger.warning(f"[vtex] enrichment skipped: {e}")

        diagnosis = await diagnose_product(
            {
                "title": product.name,
                "name": product.name,
                "description": product.description,
                "seo_title": product.title,
                "seo_description": product.seo_description,
                "tags": product.keywords,
                "keywords": product.keywords,
            },
            ai_client=self.ai_client,
            enrichment=enrichment,
            platform="VTEX",
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
            "source": diagnosis.get("source"),
            "type": "product",
        }

    async def optimize_product(
        self,
        product_id: int,
        target_keyword: str = None,
        user: dict = None,
        page_url: str = None,
        recommended_actions: List[str] = None,
    ) -> List[OptimizationProposal]:
        """Gera propostas de otimização para um produto usando IA"""
        if not self.ai_client:
            from app.demo.llm import canned_vtex_product, should_use_canned_llm

            if should_use_canned_llm():
                return await canned_vtex_product(self, product_id)
            logger.warning("OpenAI API key não configurada — otimização de IA indisponível; retornando lista vazia")
            return []

        product = await self.vtex.get_product(product_id)
        page_url = page_url or product.url

        from app.product_diagnosis import actions_to_optimize_options, heuristic_diagnosis
        if recommended_actions is None:
            heuristic = heuristic_diagnosis({
                "title": product.name,
                "description": product.description,
                "seo_title": product.title,
                "seo_description": product.seo_description,
                "tags": product.keywords,
            })
            recommended_actions = heuristic.get("recommended_actions") or []
        opts = actions_to_optimize_options(recommended_actions)
        # VTEX usa "name" no JSON da IA para o título do produto
        allowed_fields = set()
        if opts.get("optimize_title"):
            allowed_fields.add("name")
        if opts.get("optimize_description"):
            allowed_fields.add("description")
        if opts.get("optimize_seo_title"):
            allowed_fields.add("seo_title")
        if opts.get("optimize_seo_description"):
            allowed_fields.add("seo_description")
        if opts.get("generate_tags"):
            allowed_fields.add("tags")
        if not allowed_fields:
            return []

        # Contexto competitivo
        effective_keyword = target_keyword or product.name
        serp_context = await self._fetch_serp_context(effective_keyword) if effective_keyword else ""
        gsc_context = ""
        gsc_metrics = None
        if user and page_url:
            gsc_context, gsc_metrics = await self._fetch_gsc_context(user, page_url)

        # Data Enrichment antes da chamada de IA
        from app.data_enrichment import enrich_product_context
        enriched = await enrich_product_context({
            "name": product.name,
            "title": product.title or product.name,
            "description": product.description or "",
            "tags": product.keywords or "",
        }, user_id=user.get("user_id") if user else None)
        atributos = enriched.get("atributos_extraidos", [])
        keywords_mercado = enriched.get("keywords_mercado", [])

        extra_blocks = self._build_enriched_prompt_blocks(target_keyword, serp_context, gsc_context)
        if enriched.get("segmento"):
            extra_blocks += f"\nSEGMENTO DE MERCADO: {enriched['segmento']}"
        if atributos:
            extra_blocks += f"\nATRIBUTOS DO PRODUTO: {', '.join(atributos)}"
        if keywords_mercado:
            extra_blocks += f"\nPALAVRAS-CHAVE ESTRATÉGICAS (alto volume de busca): {', '.join(keywords_mercado[:10])}"

        pre_metrics_snapshot = None
        if gsc_metrics and gsc_metrics.get("found"):
            pre_metrics_snapshot = {k: gsc_metrics.get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}

        prompt = f"""Analise este produto de e-commerce VTEX e sugira otimizações de SEO.

PRODUTO:
- Nome: {product.name}
- Title tag atual: {product.title or 'Não tem'}
- Descrição: {(product.description or 'Não tem')[:500]}
- Meta descrição: {product.seo_description or 'Não tem'}
- Palavras-chave: {product.keywords or 'Não tem'}{extra_blocks}

Gere um JSON com otimizações. Para CADA campo inclua priority, impact e effort:
{{
    "name": {{"value": "nome otimizado do produto", "reasoning": "explicação", "priority": "high|medium|low", "impact": "ranking|ctr|conversao|visibilidade", "effort": "low|medium|high"}},
    "description": {{"value": "descrição otimizada em HTML", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_title": {{"value": "title tag otimizado (50-60 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_description": {{"value": "meta descrição otimizada (120-150 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "tags": {{"value": "palavra1, palavra2, palavra3", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}}
}}"""

        proposals = []
        original_map = {
            "name": product.name,
            "description": product.description,
            "seo_title": product.title,
            "seo_description": product.seo_description,
            "tags": product.keywords,
        }

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
            result = parse_ai_json(content, "produto VTEX")
            if result:

                for field in ["name", "description", "seo_title", "seo_description", "tags"]:
                    if field not in allowed_fields:
                        continue
                    if field in result and isinstance(result[field], dict) and result[field].get("value"):
                        original = original_map.get(field)
                        pf = self._extract_priority_fields(result[field])

                        proposal = OptimizationProposal(
                            id=self.vtex._generate_proposal_id(),
                            product_id=product_id,
                            optimization_type=field,
                            field_name=field,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field].get("reasoning", ""),
                            status=OptimizationStatus.PENDING,
                            created_at=datetime.utcnow().isoformat(),
                            content_type="product",
                            priority=pf.get("priority"),
                            impact=pf.get("impact"),
                            effort=pf.get("effort"),
                            target_keyword=target_keyword,
                            pre_metrics=pre_metrics_snapshot,
                            transparencia=self._transparencia(original, result[field]["value"], atributos, keywords_mercado),
                        )
                        self.vtex._proposals[proposal.id] = proposal
                        proposals.append(proposal)

        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de produto VTEX: {e}")

        return proposals

    # ==================== CATEGORIAS ====================

    async def analyze_category(self, category_id: int) -> Dict[str, Any]:
        """Analisa uma categoria e retorna métricas de SEO"""
        category = await self.vtex.get_category(category_id)
        products = await self.vtex.get_category_products(category_id, limit=5)

        issues = []
        score = 100

        if not category.name:
            issues.append({"type": "missing_title", "message": "Categoria sem nome", "severity": "critical"})
            score -= 30
        if not category.title:
            issues.append({"type": "missing_seo_title", "message": "Title tag da categoria não definido", "severity": "warning"})
            score -= 15
        if not category.description:
            issues.append({"type": "missing_category_description", "message": "Categoria sem descrição (usada como meta description na VTEX)", "severity": "warning"})
            score -= 20
        elif len(category.description) < 50:
            issues.append({"type": "short_category_description", "message": "Descrição da categoria muito curta", "severity": "info"})
            score -= 10
        if not category.keywords:
            issues.append({"type": "missing_tags", "message": "Categoria sem palavras-chave", "severity": "info"})
            score -= 5

        recommendations = []
        if not category.title:
            recommendations.append("Adicione um Title tag otimizado à categoria")
        if not category.description:
            recommendations.append("Adicione uma descrição (é a meta description da página de categoria na VTEX)")

        return {
            "category": category.model_dump(),
            "products_count": len(products),
            "products_sample": [p.model_dump() for p in products],
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "type": "category",
        }

    async def optimize_category(
        self,
        category_id: int,
        target_keyword: str = None,
        user: dict = None,
        page_url: str = None,
    ) -> List[OptimizationProposal]:
        """Gera propostas de otimização para uma categoria usando IA"""
        if not self.ai_client:
            logger.warning("OpenAI API key não configurada — otimização de IA indisponível; retornando lista vazia")
            return []

        category = await self.vtex.get_category(category_id)
        products = await self.vtex.get_category_products(category_id, limit=10)
        products_context = "\n".join([f"- {p.name}" for p in products[:10]]) if products else "Nenhum produto"

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
            "title": category.title or category.name,
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

        prompt = f"""Analise esta categoria de e-commerce VTEX e sugira otimizações de SEO.

CATEGORIA:
- Nome: {category.name}
- Title tag atual: {category.title or 'Não tem'}
- Descrição (meta description da categoria na VTEX): {category.description or 'Não tem'}
- Palavras-chave: {category.keywords or 'Não tem'}

PRODUTOS DA CATEGORIA:
{products_context}{extra_blocks}

Gere um JSON com otimizações. Para CADA campo inclua priority, impact e effort:
{{
    "name": {{"value": "nome otimizado da categoria", "reasoning": "explicação", "priority": "high|medium|low", "impact": "ranking|ctr|conversao|visibilidade", "effort": "low|medium|high"}},
    "seo_title": {{"value": "title tag otimizado (50-60 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "seo_description": {{"value": "meta descrição otimizada (120-150 chars)", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}},
    "keywords": {{"value": "palavra1, palavra2, palavra3", "reasoning": "explicação", "priority": "...", "impact": "...", "effort": "..."}}
}}"""

        proposals = []
        original_map = {
            "name": category.name,
            "seo_title": category.title,
            "seo_description": category.description,
            "keywords": category.keywords,
        }

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
            result = parse_ai_json(content, "categoria VTEX")
            if result:

                for field in ["name", "seo_title", "seo_description", "keywords"]:
                    if field in result and isinstance(result[field], dict) and result[field].get("value"):
                        original = original_map.get(field)
                        pf = self._extract_priority_fields(result[field])

                        proposal = OptimizationProposal(
                            id=self.vtex._generate_proposal_id(),
                            product_id=category_id,
                            optimization_type=f"category_{field}",
                            field_name=field,
                            original_value=original,
                            proposed_value=result[field]["value"],
                            reasoning=result[field].get("reasoning", ""),
                            status=OptimizationStatus.PENDING,
                            created_at=datetime.utcnow().isoformat(),
                            content_type="category",
                            priority=pf.get("priority"),
                            impact=pf.get("impact"),
                            effort=pf.get("effort"),
                            target_keyword=target_keyword,
                            pre_metrics=pre_metrics_snapshot,
                            transparencia=self._transparencia(original, result[field]["value"], atributos, keywords_mercado),
                        )
                        self.vtex._proposals[proposal.id] = proposal
                        proposals.append(proposal)

        except Exception as e:
            logger.error(f"Erro ao gerar otimizações de categoria VTEX: {e}")

        return proposals
