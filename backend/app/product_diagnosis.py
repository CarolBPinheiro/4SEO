"""
Diagnóstico SEO contextual de produtos (e conteúdos similares).

Substitui o checklist puramente aritmético (len/existência de campos) por uma
análise acionável: problemas dinâmicos, justificativa de score e campos
recomendados para otimização.

Quando a OpenAI não está disponível ou falha, cai em um fallback heurístico
enriquecido (ainda determinístico, mas com mensagens objetivas de impacto).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.ai_config import AI_MODEL, completion_params, parse_ai_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_DIAGNOSIS = """Você é um ENGENHEIRO DE SEO SÊNIOR especializado em e-commerce brasileiro.

Sua tarefa é DIAGNOSTICAR um produto (ou conteúdo de loja) — NÃO gerar textos otimizados ainda.

Avalie qualidade, relevância, clareza, completude, SEO on-page e potencial de conversão.
Use sinais técnicos (tamanho de campos, ausência de meta tags etc.) apenas como CONTEXTO —
eles NÃO devem ser o único critério. Um título com 50 caracteres ainda pode ser ruim;
uma descrição longa ainda pode ser vazia de valor.

Responda SEMPRE em português brasileiro e SOMENTE com JSON válido no formato:
{
  "score": 0-100,
  "score_justification": "2-4 frases explicando a pontuação",
  "summary": "resumo curto do diagnóstico",
  "issues": [
    {
      "type": "snake_case_id",
      "title": "Título curto do problema",
      "severity": "critical|warning|info",
      "why": "por que isso é um problema neste produto",
      "impact": "impacto em SEO/CTR/conversão/descoberta",
      "recommendation": "o que a IA recomenda fazer",
      "suggested_fields": ["title", "description", "seo_title", "seo_description", "tags", "image_alt"]
    }
  ],
  "opportunities": ["oportunidade opcional sem ser bug grave"],
  "recommended_actions": ["seo_title", "seo_description", "tags"]
}

Regras:
- Liste APENAS problemas reais para ESTE produto (quantidade dinâmica; pode ser 0).
- suggested_fields e recommended_actions usam apenas: title, description, seo_title, seo_description, tags, image_alt.
- score deve refletir o diagnóstico (não invente 55 por padrão).
- NÃO invente atributos do produto que não estejam nos dados.
"""

_ALLOWED_FIELDS = frozenset(
    {"title", "description", "seo_title", "seo_description", "tags", "image_alt"}
)
_ALLOWED_SEVERITY = frozenset({"critical", "warning", "info", "important"})


def _strip_html(text: Optional[str]) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", clean).strip()


def build_product_signals(product: Dict[str, Any]) -> Dict[str, Any]:
    """Sinais técnicos objetivos (contexto para IA / fallback)."""
    title = (product.get("title") or product.get("name") or "").strip()
    description_raw = product.get("description") or product.get("body_html") or ""
    description = _strip_html(description_raw)
    seo_title = (product.get("seo_title") or "").strip()
    seo_description = (product.get("seo_description") or "").strip()
    tags = product.get("tags") or product.get("keywords") or ""
    if isinstance(tags, list):
        tags_str = ", ".join(str(t) for t in tags if t)
        tag_count = len([t for t in tags if t])
    else:
        tags_str = str(tags).strip()
        tag_count = len([t for t in tags_str.split(",") if t.strip()]) if tags_str else 0

    images_without_alt = int(product.get("images_without_alt") or 0)
    brand = (product.get("brand") or "").strip()
    categories = product.get("categories") or []
    if isinstance(categories, list):
        cat_labels = []
        for c in categories:
            if isinstance(c, dict):
                name = c.get("name")
                if isinstance(name, dict):
                    cat_labels.append(name.get("pt") or name.get("en") or "")
                elif name:
                    cat_labels.append(str(name))
            elif c:
                cat_labels.append(str(c))
        categories_str = ", ".join(x for x in cat_labels if x)
    else:
        categories_str = str(categories)

    return {
        "title": title,
        "title_len": len(title),
        "description": description[:2000],
        "description_len": len(description),
        "seo_title": seo_title,
        "seo_title_len": len(seo_title),
        "seo_description": seo_description,
        "seo_description_len": len(seo_description),
        "tags": tags_str,
        "tag_count": tag_count,
        "brand": brand,
        "categories": categories_str,
        "images_without_alt": images_without_alt,
        "has_h2": "<h2" in description_raw.lower() if description_raw else False,
        "has_list": ("<ul" in description_raw.lower() or "<ol" in description_raw.lower())
        if description_raw
        else False,
    }


def _issue(
    type_: str,
    title: str,
    severity: str,
    why: str,
    impact: str,
    recommendation: str,
    fields: List[str],
) -> Dict[str, Any]:
    return {
        "type": type_,
        "title": title,
        "severity": severity,
        "message": f"{title} — {why}",
        "why": why,
        "impact": impact,
        "recommendation": recommendation,
        "suggested_fields": [f for f in fields if f in _ALLOWED_FIELDS],
    }


def heuristic_diagnosis(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback determinístico quando a IA não está disponível.
    Produz issues com why/impact/recommendation (não só 'campo X ausente').
    """
    s = build_product_signals(product)
    issues: List[Dict[str, Any]] = []
    score = 100
    actions: List[str] = []

    if not s["title"]:
        issues.append(
            _issue(
                "missing_title",
                "Título ausente",
                "critical",
                "O produto não tem nome/título. Sem isso o Google e a loja não identificam o item.",
                "Impede indexação útil e derruba conversão na vitrine.",
                "Definir um título descritivo com categoria, produto e atributos principais.",
                ["title"],
            )
        )
        score -= 30
        actions.append("title")
    elif s["title_len"] < 25 or len(s["title"].split()) < 3:
        issues.append(
            _issue(
                "weak_title",
                "Título pouco descritivo",
                "warning",
                f"O título atual (“{s['title']}”) é genérico ou curto ({s['title_len']} caracteres) e pouco orientado a busca.",
                "Reduz relevância orgânica e CTR nos resultados de busca.",
                "Expandir com atributos relevantes (material, público, modelo) sem keyword stuffing.",
                ["title", "seo_title"],
            )
        )
        score -= 12
        actions.extend(["title", "seo_title"])

    if not s["description"]:
        issues.append(
            _issue(
                "missing_description",
                "Descrição ausente",
                "critical",
                "Não há descrição com benefícios, especificações ou uso do produto.",
                "Prejudica SEO on-page e a decisão de compra.",
                "Escrever descrição completa com características objetivas e estrutura (parágrafos/listas).",
                ["description"],
            )
        )
        score -= 25
        actions.append("description")
    elif s["description_len"] < 120:
        issues.append(
            _issue(
                "weak_description",
                "Descrição insuficiente",
                "warning",
                f"A descrição tem apenas {s['description_len']} caracteres e deixa de cobrir informações que o cliente precisa.",
                "Perde ranqueamento para queries de cauda longa e reduz conversão.",
                "Incluir materiais, diferenciais, público-alvo e especificações técnicas quando disponíveis.",
                ["description"],
            )
        )
        score -= 12
        actions.append("description")

    if not s["seo_title"]:
        issues.append(
            _issue(
                "missing_seo_title",
                "Meta título não definido",
                "warning",
                "Sem meta título, a SERP usa o nome do produto — muitas vezes inadequado para CTR.",
                "Pior CTR e menos cliques orgânicos.",
                "Criar meta título de 50–60 caracteres com keyword principal no início.",
                ["seo_title"],
            )
        )
        score -= 12
        actions.append("seo_title")

    if not s["seo_description"]:
        issues.append(
            _issue(
                "missing_seo_description",
                "Meta descrição não definida",
                "warning",
                "Não há texto persuasivo controlado para o snippet do Google.",
                "Reduz CTR e desperdiça impressões orgânicas.",
                "Escrever meta descrição de 120–160 caracteres com benefício e CTA natural.",
                ["seo_description"],
            )
        )
        score -= 12
        actions.append("seo_description")
    elif s["seo_description_len"] < 70:
        issues.append(
            _issue(
                "short_seo_description",
                "Meta descrição curta demais",
                "info",
                f"A meta descrição tem {s['seo_description_len']} caracteres e transmite pouco valor no snippet.",
                "CTR abaixo do potencial.",
                "Expandir para 120–160 caracteres mantendo keyword e CTA.",
                ["seo_description"],
            )
        )
        score -= 5
        actions.append("seo_description")

    if s["tag_count"] == 0:
        issues.append(
            _issue(
                "missing_tags",
                "Ausência de tags/palavras-chave",
                "info",
                "Sem tags o produto fica mais difícil de descobrir na busca interna e em filtros da loja.",
                "Menos descoberta e menor cobertura de termos relacionados.",
                "Adicionar tags relevantes ao segmento e atributos do produto.",
                ["tags"],
            )
        )
        score -= 6
        actions.append("tags")

    if s["images_without_alt"] > 0:
        issues.append(
            _issue(
                "missing_image_alt",
                "Imagens sem texto alternativo",
                "warning",
                f"{s['images_without_alt']} imagem(ns) sem alt text.",
                "Prejudica acessibilidade e SEO de imagens.",
                "Descrever cada imagem com o produto e atributos visuais objetivos.",
                ["image_alt"],
            )
        )
        score -= min(15, 5 * min(s["images_without_alt"], 3))
        actions.append("image_alt")

    score = max(0, min(100, score))
    actions = list(dict.fromkeys(a for a in actions if a in _ALLOWED_FIELDS))

    if score >= 80:
        justification = (
            "O produto já apresenta base sólida de conteúdo e metadados. "
            "Restam ajustes pontuais para maximizar relevância e CTR."
        )
    elif score >= 50:
        justification = (
            "O produto tem informações básicas, mas apresenta lacunas relevantes em SEO, "
            "clareza comercial ou descoberta. Corrigir os pontos listados tende a elevar "
            "visibilidade e conversão."
        )
    else:
        justification = (
            "O produto está com conteúdo insuficiente ou metadados críticos ausentes. "
            "Sem essas correções, o potencial orgânico e de conversão permanece limitado."
        )

    return {
        "score": score,
        "score_justification": justification,
        "summary": f"{len(issues)} problema(s) identificados na análise do produto.",
        "issues": issues,
        "opportunities": [],
        "recommended_actions": actions,
        "recommendations": [i["recommendation"] for i in issues],
        "signals": s,
        "source": "heuristic",
    }


def _normalize_ai_diagnosis(raw: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not raw:
        return fallback

    try:
        score = int(raw.get("score", fallback["score"]))
    except (TypeError, ValueError):
        score = fallback["score"]
    score = max(0, min(100, score))

    issues_in = raw.get("issues") or []
    issues: List[Dict[str, Any]] = []
    if isinstance(issues_in, list):
        for item in issues_in:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("message") or "").strip()
            if not title:
                continue
            severity = str(item.get("severity") or "warning").lower()
            if severity not in _ALLOWED_SEVERITY:
                severity = "warning"
            if severity == "important":
                severity = "warning"
            fields = item.get("suggested_fields") or []
            if not isinstance(fields, list):
                fields = []
            why = str(item.get("why") or "").strip()
            impact = str(item.get("impact") or "").strip()
            recommendation = str(item.get("recommendation") or "").strip()
            type_ = str(item.get("type") or "seo_issue").strip() or "seo_issue"
            issues.append(
                {
                    "type": type_,
                    "title": title,
                    "severity": severity,
                    "message": f"{title}" + (f" — {why}" if why else ""),
                    "why": why,
                    "impact": impact,
                    "recommendation": recommendation,
                    "suggested_fields": [f for f in fields if f in _ALLOWED_FIELDS],
                }
            )

    actions = raw.get("recommended_actions") or []
    if not isinstance(actions, list):
        actions = []
    for issue in issues:
        actions.extend(issue.get("suggested_fields") or [])
    actions = list(dict.fromkeys(a for a in actions if a in _ALLOWED_FIELDS))
    if not actions and not issues:
        actions = fallback.get("recommended_actions") or []

    opportunities = raw.get("opportunities") or []
    if not isinstance(opportunities, list):
        opportunities = []
    opportunities = [str(o).strip() for o in opportunities if str(o).strip()]

    justification = str(raw.get("score_justification") or "").strip() or fallback["score_justification"]
    summary = str(raw.get("summary") or "").strip() or f"{len(issues)} problema(s) identificados."

    return {
        "score": score,
        "score_justification": justification,
        "summary": summary,
        "issues": issues,
        "opportunities": opportunities,
        "recommended_actions": actions,
        "recommendations": [i["recommendation"] for i in issues if i.get("recommendation")],
        "signals": fallback.get("signals") or {},
        "source": "ai",
    }


def actions_to_optimize_options(actions: List[str]) -> Dict[str, bool]:
    """Converte recommended_actions em flags usadas pelos otimizadores."""
    actions_set = {a for a in (actions or []) if a in _ALLOWED_FIELDS}
    if not actions_set:
        # Sem diagnóstico: comportamento seguro — otimiza o núcleo SEO
        actions_set = {"title", "description", "seo_title", "seo_description", "tags"}
    return {
        "optimize_title": "title" in actions_set,
        "optimize_description": "description" in actions_set,
        "optimize_seo_title": "seo_title" in actions_set,
        "optimize_seo_description": "seo_description" in actions_set,
        "optimize_image_alts": "image_alt" in actions_set,
        "generate_tags": "tags" in actions_set,
    }


async def diagnose_product(
    product: Dict[str, Any],
    *,
    ai_client: Optional[AsyncOpenAI] = None,
    enrichment: Optional[Dict[str, Any]] = None,
    platform: str = "",
) -> Dict[str, Any]:
    """
    Diagnóstico contextual do produto.
    `product` deve expor title/name, description/body_html, seo_*, tags/keywords, etc.
    """
    fallback = heuristic_diagnosis(product)
    if not ai_client:
        logger.info("[diagnosis] sem AI client — usando fallback heurístico (%s)", platform or "n/a")
        return fallback

    signals = fallback["signals"]
    enrichment = enrichment or {}
    extra = []
    if enrichment.get("segmento"):
        extra.append(f"Segmento: {enrichment['segmento']}")
    if enrichment.get("atributos_extraidos"):
        extra.append("Atributos: " + ", ".join(enrichment["atributos_extraidos"][:12]))
    if enrichment.get("keywords_mercado"):
        extra.append("Keywords de mercado: " + ", ".join(enrichment["keywords_mercado"][:10]))
    extra_block = ("\n" + "\n".join(extra)) if extra else ""

    prompt = f"""Diagnostique o SEO deste produto de e-commerce{" (" + platform + ")" if platform else ""}.

DADOS DO PRODUTO:
- Título/Nome: {signals['title'] or '(vazio)'}
- Marca: {signals['brand'] or '(não informada)'}
- Categorias: {signals['categories'] or '(nenhuma)'}
- Descrição (texto): {signals['description'] or '(vazia)'}
- Meta título: {signals['seo_title'] or '(não definido)'}
- Meta descrição: {signals['seo_description'] or '(não definida)'}
- Tags/keywords: {signals['tags'] or '(nenhuma)'}
- Imagens sem alt: {signals['images_without_alt']}
- Sinais técnicos: título={signals['title_len']} chars, descrição={signals['description_len']} chars, meta_title={signals['seo_title_len']} chars, meta_desc={signals['seo_description_len']} chars, tags={signals['tag_count']}, tem_h2={signals['has_h2']}, tem_lista={signals['has_list']}
{extra_block}

Retorne o JSON de diagnóstico conforme o schema do sistema.
Foque no que REALMENTE precisa melhorar neste produto específico."""

    try:
        response = await ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_DIAGNOSIS},
                {"role": "user", "content": prompt},
            ],
            **completion_params(1800, temperature=0.3),
        )
        content = response.choices[0].message.content or ""
        parsed = parse_ai_json(content, f"diagnóstico produto {platform or ''}".strip())
        if not parsed:
            return fallback
        return _normalize_ai_diagnosis(parsed, fallback)
    except Exception as e:
        logger.warning("[diagnosis] falha na IA (%s): %s — fallback heurístico", platform or "n/a", e)
        return fallback
