"""
SearchAPI.io Integration
Replaces pytrends with SearchAPI.io Google Trends API.
Works reliably from any server (no Google IP blocking).
"""
import os
import logging
import time
from typing import List, Dict, Any, Tuple

import httpx

logger = logging.getLogger(__name__)

SEARCHAPI_KEY = os.getenv("SEARCHAPI_KEY", "")
SEARCHAPI_BASE = "https://www.searchapi.io/api/v1/search"

# Cache em memória para trending now (evita gastar crédito a cada reload).
_TRENDING_CACHE_TTL_SECONDS = 30 * 60  # 30 minutos
_trending_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


async def _fetch_timeseries(keywords: List[str], geo: str, timeframe: str) -> Dict[str, Any]:
    """Fetch Interest Over Time from SearchAPI.io"""
    params = {
        "engine": "google_trends",
        "q": ",".join(keywords),
        "data_type": "TIMESERIES",
        "geo": geo,
        "time": timeframe,
        "api_key": SEARCHAPI_KEY,
    }
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(SEARCHAPI_BASE, params=params)
        r.raise_for_status()
        return r.json()


async def _fetch_related(keyword: str, geo: str, timeframe: str) -> Dict[str, Any]:
    """Fetch Related Queries from SearchAPI.io"""
    params = {
        "engine": "google_trends",
        "q": keyword,
        "data_type": "RELATED_QUERIES",
        "geo": geo,
        "time": timeframe,
        "api_key": SEARCHAPI_KEY,
    }
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(SEARCHAPI_BASE, params=params)
        r.raise_for_status()
        return r.json()


def _parse_timeseries(data: Dict[str, Any], keywords: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Parse SearchAPI TIMESERIES response into the same format pytrends used:
    {keyword: {current, average, peak, trend, history}}
    """
    iot = data.get("interest_over_time", {})
    averages_list = iot.get("averages", [])
    timeline = iot.get("timeline_data", [])

    # Build averages lookup
    avg_map = {}
    for item in averages_list:
        avg_map[item.get("query", "")] = item.get("value", 0)

    trends_data = {}
    for kw in keywords:
        # Extract history values for this keyword
        values = []
        for point in timeline:
            for v in point.get("values", []):
                if v.get("query", "") == kw:
                    values.append(v.get("extracted_value", 0))
                    break

        if values:
            trends_data[kw] = {
                "current": values[-1],
                "average": avg_map.get(kw, round(sum(values) / len(values), 1)),
                "peak": max(values),
                "trend": "up" if len(values) >= 2 and values[-1] > values[-2] else "down",
                "history": values[-30:],
            }
        else:
            # Single keyword queries may not have "query" in values
            all_values = []
            for point in timeline:
                for v in point.get("values", []):
                    all_values.append(v.get("extracted_value", 0))
                    break  # take first value per point

            if all_values and len(keywords) == 1:
                trends_data[kw] = {
                    "current": all_values[-1],
                    "average": avg_map.get(kw, round(sum(all_values) / len(all_values), 1)),
                    "peak": max(all_values),
                    "trend": "up" if len(all_values) >= 2 and all_values[-1] > all_values[-2] else "down",
                    "history": all_values[-30:],
                }

    return trends_data


def _parse_related(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse SearchAPI RELATED_QUERIES response into the same format pytrends used:
    {top: [{query, value}], rising: [{query, value}]}
    """
    rq = data.get("related_queries", {})

    top = []
    for item in rq.get("top", [])[:5]:
        top.append({
            "query": item.get("query", ""),
            "value": item.get("extracted_value", 0),
        })

    rising = []
    for item in rq.get("rising", [])[:5]:
        rising.append({
            "query": item.get("query", ""),
            "value": item.get("extracted_value", 0),
        })

    return {"top": top, "rising": rising}


async def fetch_trends(keywords: List[str], geo: str = "BR", timeframe: str = "today 3-m") -> Dict[str, Any]:
    """
    Fetch Google Trends data via SearchAPI.io.
    Drop-in replacement for pytrends_client.fetch_trends  - same signature and output format.
    """
    if not SEARCHAPI_KEY:
        logger.error("[searchapi] SEARCHAPI_KEY not configured")
        return {
            "keywords": keywords,
            "error": "SEARCHAPI_KEY não configurada no servidor",
            "trends": {},
            "related": {},
            "suggestions": {},
        }

    try:
        # 1. Fetch timeseries (supports up to 5 keywords in one call)
        ts_data = await _fetch_timeseries(keywords, geo, timeframe)
        trends_data = _parse_timeseries(ts_data, keywords)

        # 2. Fetch related queries per keyword
        related_data = {}
        for kw in keywords:
            try:
                rq_data = await _fetch_related(kw, geo, timeframe)
                related_data[kw] = _parse_related(rq_data)
            except Exception as e:
                logger.warning(f"[searchapi] Related queries failed for '{kw}': {e}")
                related_data[kw] = {"top": [], "rising": []}

        return {
            "keywords": keywords,
            "geo": geo,
            "timeframe": timeframe,
            "trends": trends_data,
            "related": related_data,
            "suggestions": {},  # SearchAPI Google Trends doesn't have suggestions endpoint
        }

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        body = e.response.text[:200]
        logger.error(f"[searchapi] HTTP {status}: {body}")
        return {
            "keywords": keywords,
            "error": f"SearchAPI retornou erro HTTP {status}",
            "trends": {},
            "related": {},
            "suggestions": {},
        }
    except Exception as e:
        logger.error(f"[searchapi] Failed for keywords={keywords}: {type(e).__name__}: {e}")
        return {
            "keywords": keywords,
            "error": str(e),
            "trends": {},
            "related": {},
            "suggestions": {},
        }


def classify_search_chance(trend_score: int, related_count: int) -> str:
    """Classify search term sales chance (same logic as before)"""
    if trend_score >= 70 and related_count >= 3:
        return "alta"
    elif trend_score >= 40:
        return "moderada"
    return "baixa"


def _normalize_trending_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza um item de google_trends_trending_now para o frontend."""
    categories = item.get("categories") or []
    if not isinstance(categories, list):
        categories = [str(categories)]
    keywords = item.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    return {
        "position": int(item.get("position") or 0),
        "query": str(item.get("query") or "").strip(),
        "search_volume": int(item.get("search_volume") or 0),
        "percentage_increase": int(item.get("percentage_increase") or 0),
        "categories": [str(c) for c in categories if c],
        "keywords": [str(k) for k in keywords if k][:5],
        "is_active": bool(item.get("is_active", True)),
        "start_date": item.get("start_date"),
    }


def clear_trending_cache() -> None:
    """Limpa o cache de trending (útil em testes)."""
    _trending_cache.clear()


async def fetch_trending_now(
    geo: str = "BR",
    time_window: str = "past_24_hours",
    limit: int = 6,
    *,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Busca pesquisas em alta via SearchAPI (engine=google_trends_trending_now).

    Retorna no máximo `limit` itens normalizados. Cache em memória por 30 min
    por (geo, time_window) para reduzir custo de API.
    """
    geo = (geo or "BR").upper().strip()
    time_window = (time_window or "past_24_hours").strip()
    limit = max(1, min(int(limit or 6), 20))
    cache_key = f"{geo}:{time_window}"

    if use_cache:
        cached = _trending_cache.get(cache_key)
        if cached:
            cached_at, payload = cached
            if time.monotonic() - cached_at < _TRENDING_CACHE_TTL_SECONDS:
                trends = (payload.get("trends") or [])[:limit]
                return {
                    **payload,
                    "trends": trends,
                    "count": len(trends),
                    "cached": True,
                }

    if not SEARCHAPI_KEY:
        logger.error("[searchapi] SEARCHAPI_KEY not configured (trending_now)")
        return {
            "geo": geo,
            "time": time_window,
            "trends": [],
            "count": 0,
            "cached": False,
            "error": "SEARCHAPI_KEY não configurada no servidor",
        }

    params = {
        "engine": "google_trends_trending_now",
        "geo": geo,
        "time": time_window,
        "hl": "pt",
        "api_key": SEARCHAPI_KEY,
    }
    timeout = httpx.Timeout(30.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(SEARCHAPI_BASE, params=params)
            r.raise_for_status()
            data = r.json()

        raw_trends = data.get("trends") or []
        if not isinstance(raw_trends, list):
            raw_trends = []

        normalized: List[Dict[str, Any]] = []
        for item in raw_trends:
            if not isinstance(item, dict):
                continue
            parsed = _normalize_trending_item(item)
            if not parsed["query"]:
                continue
            normalized.append(parsed)

        # Ordena por posição quando disponível; fallback por volume
        normalized.sort(
            key=lambda t: (t["position"] if t["position"] > 0 else 10_000, -t["search_volume"])
        )

        payload: Dict[str, Any] = {
            "geo": geo,
            "time": time_window,
            "trends": normalized,
            "count": len(normalized),
            "cached": False,
        }
        _trending_cache[cache_key] = (time.monotonic(), payload)

        trends = normalized[:limit]
        return {
            **payload,
            "trends": trends,
            "count": len(trends),
            "cached": False,
        }

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        body = e.response.text[:200]
        logger.error(f"[searchapi] trending_now HTTP {status}: {body}")
        return {
            "geo": geo,
            "time": time_window,
            "trends": [],
            "count": 0,
            "cached": False,
            "error": f"SearchAPI retornou erro HTTP {status}",
        }
    except Exception as e:
        logger.error(f"[searchapi] trending_now failed: {type(e).__name__}: {e}")
        return {
            "geo": geo,
            "time": time_window,
            "trends": [],
            "count": 0,
            "cached": False,
            "error": str(e),
        }


async def fetch_serp(keyword: str, geo: str = "BR", num_results: int = 5) -> Dict[str, Any]:
    """
    Fetch top organic results from Google via SearchAPI.io (engine=google).
    Returns structured data about top-ranking pages for competitive analysis.
    """
    if not SEARCHAPI_KEY:
        logger.warning("[searchapi] SEARCHAPI_KEY not configured  - skipping SERP fetch")
        return {"keyword": keyword, "results": [], "error": "SEARCHAPI_KEY não configurada"}

    params = {
        "engine": "google",
        "q": keyword,
        "gl": geo.lower(),
        "hl": "pt",
        "num": num_results,
        "api_key": SEARCHAPI_KEY,
    }
    timeout = httpx.Timeout(30.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(SEARCHAPI_BASE, params=params)
            r.raise_for_status()
            data = r.json()

        organic = data.get("organic_results", [])
        results = []
        for item in organic[:num_results]:
            results.append({
                "position": item.get("position", 0),
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "displayed_link": item.get("displayed_link", ""),
            })

        return {
            "keyword": keyword,
            "results": results,
            "total_results": data.get("search_information", {}).get("total_results", 0),
        }
    except Exception as e:
        logger.error(f"[searchapi] SERP fetch failed for '{keyword}': {e}")
        return {"keyword": keyword, "results": [], "error": str(e)}
