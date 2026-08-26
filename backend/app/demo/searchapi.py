"""Trends / SERP fictícios quando DEMO_MODE está on e SEARCHAPI_KEY está vazia."""
from __future__ import annotations

from typing import Any, Dict, List


def demo_trends(keywords: List[str]) -> Dict[str, Any]:
    trends: Dict[str, Any] = {}
    related: Dict[str, Any] = {}
    history = [40, 42, 45, 48, 51, 55, 58, 62, 60, 64, 68, 70]
    for idx, kw in enumerate(keywords or ["seo ecommerce"]):
        bump = (idx % 3) * 4
        values = [min(100, v + bump) for v in history]
        trends[kw] = {
            "current": values[-1],
            "average": round(sum(values) / len(values), 1),
            "peak": max(values),
            "trend": "up",
            "history": values,
        }
        related[kw] = {
            "top": [
                {"query": f"{kw} barato", "value": 100},
                {"query": f"{kw} feminino", "value": 78},
                {"query": f"melhor {kw}", "value": 61},
            ],
            "rising": [
                {"query": f"{kw} 2026", "value": 180},
                {"query": f"{kw} promocao", "value": 140},
            ],
        }
    return {
        "keywords": keywords,
        "trends": trends,
        "related": related,
        "suggestions": {},
    }


def demo_trending_now(geo: str = "BR", time_window: str = "past_24_hours", limit: int = 6) -> Dict[str, Any]:
    items = [
        {
            "position": 1,
            "query": "tênis running feminino",
            "search_volume": 54000,
            "percentage_increase": 42,
            "categories": ["Shopping"],
            "keywords": ["tênis", "running"],
            "is_active": True,
            "start_date": None,
        },
        {
            "position": 2,
            "query": "camiseta algodão oversized",
            "search_volume": 22000,
            "percentage_increase": 28,
            "categories": ["Shopping"],
            "keywords": ["camiseta", "oversized"],
            "is_active": True,
            "start_date": None,
        },
        {
            "position": 3,
            "query": "bolsa tote lona",
            "search_volume": 18000,
            "percentage_increase": 19,
            "categories": ["Shopping"],
            "keywords": ["bolsa"],
            "is_active": True,
            "start_date": None,
        },
        {
            "position": 4,
            "query": "seo para ecommerce",
            "search_volume": 12000,
            "percentage_increase": 15,
            "categories": ["Business"],
            "keywords": ["seo", "ecommerce"],
            "is_active": True,
            "start_date": None,
        },
        {
            "position": 5,
            "query": "meta description produto",
            "search_volume": 8100,
            "percentage_increase": 11,
            "categories": ["Business"],
            "keywords": ["seo"],
            "is_active": True,
            "start_date": None,
        },
        {
            "position": 6,
            "query": "tênis slip on",
            "search_volume": 9600,
            "percentage_increase": 9,
            "categories": ["Shopping"],
            "keywords": ["tênis"],
            "is_active": True,
            "start_date": None,
        },
    ]
    trends = items[: max(1, min(int(limit or 6), 20))]
    return {
        "geo": geo,
        "time": time_window,
        "trends": trends,
        "count": len(trends),
        "cached": False,
    }


def demo_serp(keyword: str, num_results: int = 5) -> Dict[str, Any]:
    results = []
    for i in range(max(1, min(num_results, 5))):
        results.append(
            {
                "position": i + 1,
                "title": f"{keyword.title()} — resultado demo {i + 1}",
                "link": f"https://example.com/demo/{i + 1}",
                "snippet": f"Página de exemplo para {keyword} no sandbox 4SEO.",
            }
        )
    return {"results": results}
