"""Métricas GSC fictícias usadas quando o token é `demo_*` ou não há OAuth real."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.demo.config import DEMO_GSC_SITE, is_demo_token


def is_demo_gsc_token(access_token: Optional[str]) -> bool:
    return is_demo_token(access_token)


def demo_overview(site_url: Optional[str] = None) -> Dict[str, Any]:
    site = site_url or DEMO_GSC_SITE
    return {
        "impressions": 18420,
        "clicks": 1264,
        "ctr": 6.86,
        "position": 12.4,
        "unique_pages": 24,
        "site_url": site,
        "top_queries": [
            {
                "query": "tênis running feminino",
                "clicks": 312,
                "impressions": 4100,
                "ctr": 7.61,
                "position": 8.2,
            },
            {
                "query": "camiseta algodão",
                "clicks": 198,
                "impressions": 2800,
                "ctr": 7.07,
                "position": 11.1,
            },
            {
                "query": "bolsa tote lona",
                "clicks": 121,
                "impressions": 1900,
                "ctr": 6.37,
                "position": 14.5,
            },
            {
                "query": "tênis casual branco",
                "clicks": 96,
                "impressions": 1600,
                "ctr": 6.0,
                "position": 16.2,
            },
            {
                "query": "loja demo 4seo",
                "clicks": 54,
                "impressions": 420,
                "ctr": 12.86,
                "position": 3.4,
            },
        ],
    }


def demo_sites() -> List[str]:
    return [DEMO_GSC_SITE]


def demo_performance(dimensions: Optional[List[str]] = None) -> Dict[str, Any]:
    overview = demo_overview()
    dims = dimensions or []
    if not dims:
        return {
            "rows": [
                {
                    "clicks": overview["clicks"],
                    "impressions": overview["impressions"],
                    "ctr": overview["ctr"] / 100,
                    "position": overview["position"],
                }
            ]
        }
    if "query" in dims:
        return {
            "rows": [
                {
                    "keys": [q["query"]],
                    "clicks": q["clicks"],
                    "impressions": q["impressions"],
                    "ctr": q["ctr"] / 100,
                    "position": q["position"],
                }
                for q in overview["top_queries"]
            ]
        }
    if "page" in dims:
        return {
            "rows": [
                {
                    "keys": [f"{DEMO_GSC_SITE}/products/tenis-run"],
                    "clicks": 280,
                    "impressions": 3600,
                    "ctr": 0.077,
                    "position": 9.1,
                },
                {
                    "keys": [f"{DEMO_GSC_SITE}/products/camiseta-basica-azul"],
                    "clicks": 190,
                    "impressions": 2500,
                    "ctr": 0.076,
                    "position": 12.0,
                },
            ]
        }
    return {"rows": []}


def demo_page_performance(page_url: str) -> Dict[str, Any]:
    return {
        "page_url": page_url,
        "found": True,
        "clicks": 88,
        "impressions": 1400,
        "ctr": 6.29,
        "position": 13.8,
        "top_queries": demo_overview()["top_queries"][:3],
    }
