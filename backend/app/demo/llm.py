"""Propostas de SEO canned quando DEMO_MODE está on e não há OPENAI_API_KEY."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.demo.config import is_demo_mode


def should_use_canned_llm() -> bool:
    return is_demo_mode()


def _clip(text: str, size: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= size:
        return text
    return text[: size - 1].rstrip() + "…"


def build_canned_fields(
    *,
    title: str,
    description: Optional[str],
    category: Optional[str],
    brand: Optional[str],
    seo_title: Optional[str],
    seo_description: Optional[str],
) -> List[Dict[str, Any]]:
    """Campos genéricos (title/description/seo_*) prontos para virar propostas."""
    cat = (category or "Produto").strip()
    br = (brand or "Loja Demo").strip()
    name = (title or "Produto").strip()
    desc = (description or "").strip() or f"{name} da linha {cat}."

    proposed_title = _clip(f"{cat} {name} {br}".replace("  ", " "), 70)
    proposed_seo_title = _clip(f"{name} | {cat} {br}", 60)
    proposed_seo_desc = _clip(
        f"Compre {name} em {cat}. {br} na Loja Demo 4SEO com frete rápido e troca fácil.",
        155,
    )
    proposed_desc = (
        f"<h2>{name}</h2><p>{desc}</p>"
        f"<ul><li>Categoria: {cat}</li><li>Marca: {br}</li></ul>"
    )

    fields: List[Dict[str, Any]] = []
    if not title or len(title) < 30 or len(title) > 60:
        fields.append(
            {
                "optimization_type": "title",
                "field_name": "title",
                "original_value": title or None,
                "proposed_value": proposed_title,
                "reasoning": "Título reestruturado no sandbox (sem OpenAI) para 30–60 caracteres.",
            }
        )
    if not description or len(description) < 80:
        fields.append(
            {
                "optimization_type": "description",
                "field_name": "description",
                "original_value": description or None,
                "proposed_value": proposed_desc,
                "reasoning": "Descrição ampliada no sandbox para contextualizar categoria e marca.",
            }
        )
    if not seo_title or len(seo_title) < 30:
        fields.append(
            {
                "optimization_type": "seo_title",
                "field_name": "seo_title",
                "original_value": seo_title or None,
                "proposed_value": proposed_seo_title,
                "reasoning": "Title tag gerada no sandbox a partir do nome + categoria.",
            }
        )
    if not seo_description or len(seo_description) < 120:
        fields.append(
            {
                "optimization_type": "seo_description",
                "field_name": "seo_description",
                "original_value": seo_description or None,
                "proposed_value": proposed_seo_desc,
                "reasoning": "Meta description gerada no sandbox (120–160 caracteres).",
            }
        )
    if not fields:
        fields.append(
            {
                "optimization_type": "seo_title",
                "field_name": "seo_title",
                "original_value": seo_title,
                "proposed_value": proposed_seo_title,
                "reasoning": "Ajuste fino de title tag no sandbox.",
            }
        )
    return fields


def attach_nuvemshop_style_proposals(
    client: Any,
    proposal_cls: Any,
    status_cls: Any,
    *,
    product_id: int,
    fields: List[Dict[str, Any]],
    content_type: str = "product",
) -> List[Any]:
    proposals = []
    for field in fields:
        proposal = proposal_cls(
            id=client._generate_proposal_id(),
            product_id=int(product_id),
            optimization_type=field["optimization_type"],
            field_name=field["field_name"],
            original_value=field.get("original_value"),
            proposed_value=field["proposed_value"],
            reasoning=field["reasoning"],
            status=status_cls.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            content_type=content_type,
            priority="medium",
            impact="ctr",
            effort="low",
        )
        client._proposals[proposal.id] = proposal
        proposals.append(proposal)
    return proposals


async def canned_shopify_product(optimizer: Any, product_id: int) -> List[Any]:
    product = await optimizer.shopify.get_product(product_id)
    metafields = await optimizer.shopify.get_product_metafields(product_id)
    fields = build_canned_fields(
        title=product.title or "",
        description=product.body_html,
        category=product.product_type,
        brand=product.vendor,
        seo_title=metafields.get("seo_title"),
        seo_description=metafields.get("seo_description"),
    )
    proposals = []
    type_map = {
        "title": ("title", "title"),
        "description": ("description", "body_html"),
        "seo_title": ("seo_title", "seo_title"),
        "seo_description": ("seo_description", "seo_description"),
    }
    for field in fields:
        opt, fname = type_map.get(
            field["optimization_type"],
            (field["optimization_type"], field["field_name"]),
        )
        proposal = await optimizer.shopify.create_optimization_proposal(
            product_id=product.id,
            optimization_type=opt,
            field_name=fname,
            original_value=field.get("original_value"),
            proposed_value=field["proposed_value"],
            reasoning=field["reasoning"],
        )
        proposals.append(proposal)
    for img in product.images or []:
        if not img.get("alt"):
            proposal = await optimizer.shopify.create_optimization_proposal(
                product_id=product.id,
                optimization_type="image_alt",
                field_name="image_alt",
                original_value=None,
                proposed_value=f"{product.title} — foto do produto",
                reasoning="Alt text gerado no sandbox (sem OpenAI).",
                image_id=img.get("id"),
            )
            proposals.append(proposal)
    return proposals


async def canned_nuvemshop_product(optimizer: Any, product_id: int) -> List[Any]:
    from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus

    product = await optimizer.nuvemshop.get_product(product_id)
    fields = build_canned_fields(
        title=product.name or "",
        description=product.description,
        category=None,
        brand=product.brand,
        seo_title=product.seo_title,
        seo_description=product.seo_description,
    )
    for field in fields:
        if field["optimization_type"] == "title":
            field["field_name"] = "name"
            field["optimization_type"] = "name"
    proposals = attach_nuvemshop_style_proposals(
        optimizer.nuvemshop,
        OptimizationProposal,
        OptimizationStatus,
        product_id=product_id,
        fields=fields,
    )
    for img in product.images or []:
        alt = img.get("alt") or ""
        if isinstance(alt, dict):
            alt = alt.get("pt") or ""
        if alt:
            continue
        extra = attach_nuvemshop_style_proposals(
            optimizer.nuvemshop,
            OptimizationProposal,
            OptimizationStatus,
            product_id=product_id,
            fields=[
                {
                    "optimization_type": "image_alt",
                    "field_name": f"image_alt_{img.get('id')}",
                    "original_value": None,
                    "proposed_value": f"{product.name} — foto do produto",
                    "reasoning": "Alt text gerado no sandbox (sem OpenAI).",
                }
            ],
        )
        proposals.extend(extra)
    return proposals


async def canned_vtex_product(optimizer: Any, product_id: int) -> List[Any]:
    from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus

    product = await optimizer.vtex.get_product(product_id)
    fields = build_canned_fields(
        title=product.name or "",
        description=product.description,
        category=None,
        brand=product.brand,
        seo_title=product.title,
        seo_description=product.seo_description,
    )
    for field in fields:
        if field["optimization_type"] == "title":
            field["field_name"] = "name"
            field["optimization_type"] = "name"
    return attach_nuvemshop_style_proposals(
        optimizer.vtex,
        OptimizationProposal,
        OptimizationStatus,
        product_id=product_id,
        fields=fields,
    )


async def canned_lojaintegrada_product(optimizer: Any, product_id: int) -> List[Any]:
    from app.integrations.nuvemshop import OptimizationProposal, OptimizationStatus

    product = await optimizer.li.get_product(product_id)
    fields = build_canned_fields(
        title=product.name or "",
        description=product.description,
        category=None,
        brand=None,
        seo_title=product.seo_title,
        seo_description=product.seo_description,
    )
    for field in fields:
        if field["optimization_type"] == "title":
            field["field_name"] = "name"
            field["optimization_type"] = "name"
    return attach_nuvemshop_style_proposals(
        optimizer.li,
        OptimizationProposal,
        OptimizationStatus,
        product_id=product_id,
        fields=fields,
    )
