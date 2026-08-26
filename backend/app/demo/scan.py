"""Scan fixture: páginas e issues sem HTTP externo."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.demo.catalog import ARTICLES, PAGES, PRODUCTS
from app.seo_analysis import ISSUE_CONFIG


def _score(issues: Dict[str, Any]) -> int:
    penalty = 0
    for code, present in issues.items():
        if present and code in ISSUE_CONFIG:
            penalty += int(ISSUE_CONFIG[code]["penalty"])
    return max(0, 100 - penalty)


def _page_record(
    url: str,
    title: str,
    meta: Optional[str],
    h1: Optional[str],
    extra_issues: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    issues: Dict[str, Any] = {
        "missing_title": not bool(title),
        "title_too_short": bool(title) and len(title) < 30,
        "title_too_long": bool(title) and len(title) > 60,
        "missing_meta_description": not bool(meta),
        "meta_description_short": bool(meta) and len(meta) < 120,
        "meta_description_long": bool(meta) and len(meta) > 160,
        "missing_h1": not bool(h1),
        "multiple_h1": False,
        "missing_h2": True,
        "missing_canonical": True,
        "missing_img_alt": False,
        "missing_og_tags": True,
        "missing_schema": True,
        "few_internal_links": True,
    }
    if extra_issues:
        issues.update(extra_issues)
    issues = {k: v for k, v in issues.items() if v}
    return {
        "url": url,
        "status_code": 200,
        "title": title,
        "meta_description": meta,
        "h1": h1,
        "issues": issues,
        "score": _score(issues),
    }


def crawl_demo_site(base_url: str, max_pages: int = 30) -> Dict[str, Any]:
    start = datetime.now(timezone.utc)
    root = (base_url or "https://demo-4seo.lojavirtualnuvem.com.br").rstrip("/")
    pages: List[Dict[str, Any]] = []

    pages.append(
        _page_record(
            f"{root}/",
            "Loja Demo 4SEO",
            "Loja Demo",
            "Loja Demo 4SEO",
            extra_issues={"title_too_short": True, "meta_description_short": True},
        )
    )
    for product in PRODUCTS:
        url = f"{root}/products/{product['handle']}"
        extra = {
            "missing_img_alt": any(not img.get("alt") for img in product.get("images") or []),
            "multiple_h1": "<h1>" in (product.get("body_html") or "")
            and (product.get("body_html") or "").lower().count("<h1") > 1,
        }
        pages.append(
            _page_record(
                url,
                product.get("seo_title") or product.get("title") or "",
                product.get("seo_description") or "",
                product.get("title") or "",
                extra_issues=extra,
            )
        )
    for page in PAGES:
        pages.append(
            _page_record(
                f"{root}/pages/{page['handle']}",
                page.get("seo_title") or page.get("title") or "",
                page.get("seo_description") or "",
                page.get("title") or "",
                extra_issues={
                    "multiple_h1": (page.get("body_html") or "").lower().count("<h1") > 1,
                },
            )
        )
    for article in ARTICLES:
        pages.append(
            _page_record(
                f"{root}/blogs/blog/{article['handle']}",
                article.get("seo_title") or article.get("title") or "",
                article.get("seo_description") or "",
                article.get("title") or "",
            )
        )

    pages = pages[: max(1, int(max_pages or 30))]
    avg = round(sum(p["score"] for p in pages) / len(pages)) if pages else 0
    summary: Dict[str, int] = {}
    for page in pages:
        for code, present in (page.get("issues") or {}).items():
            if present:
                summary[code] = summary.get(code, 0) + 1
    duration = (datetime.now(timezone.utc) - start).total_seconds()
    return {
        "base_url": root,
        "pages_found": len(pages),
        "pages_crawled": len(pages),
        "pages_failed": 0,
        "pages_analyzed": len(pages),
        "average_score": avg,
        "total_issues": sum(summary.values()),
        "issues_summary": summary,
        "duration_seconds": duration,
        "pages": pages,
    }
