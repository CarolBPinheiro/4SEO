"""
SiteCan - Crawler SEO Plataforma-Agnóstico
Motor: Crawlee for Python (BeautifulSoupCrawler).

Mantém a interface pública `crawl_site(url, max_pages)` usada por
`app.services.ScanService` e por endpoints que disparam scans.
"""
from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urldefrag, urlparse

import httpx

from app.seo_analysis import analyze_seo_html

logger = logging.getLogger(__name__)

# Limite de tamanho de sitemap para evitar abuso
_MAX_SITEMAP_BYTES = 5 * 1024 * 1024

# URLs que não devem ser crawleadas
_SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".rar", ".tar", ".gz",
    ".css", ".js", ".json", ".xml",
    ".mp3", ".mp4", ".avi", ".mov",
    ".woff", ".woff2", ".ttf", ".eot",
)
_SKIP_PATHS = (
    "/cart", "/checkout", "/account", "/login", "/register",
    "/admin", "/api/", "/wp-admin", "/wp-json",
    "/search", "/busca",
    "/cdn-cgi/", "/_next/", "/static/",
    "/wishlist", "/compare", "/order",
)
_USER_AGENT = "SiteCan-SEO-Crawler/1.0 (+https://sitecan.com.br/bot)"


def _domain_key(host: str) -> str:
    """Normaliza host para comparação: remove 'www.' e lowercase."""
    h = (host or "").lower().strip()
    if h.startswith("www."):
        h = h[4:]
    return h


def _should_crawl(url: str, domain: str) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
        if p.netloc and _domain_key(p.netloc) != _domain_key(domain):
            return False
        path = (p.path or "/").lower()
        if any(path.endswith(ext) for ext in _SKIP_EXTENSIONS):
            return False
        url_l = url.lower()
        if any(s in url_l for s in _SKIP_PATHS):
            return False
        return True
    except Exception:
        return False


def _normalize(url: str, base_url: str, domain: str) -> Optional[str]:
    try:
        url, _ = urldefrag(url)
        if not url.startswith(("http://", "https://")):
            url = urljoin(base_url, url)
        p = urlparse(url)
        if _domain_key(p.netloc) != _domain_key(domain):
            return None
        path = p.path.rstrip("/") or "/"
        return f"{p.scheme}://{p.netloc}{path}"
    except Exception:
        return None


async def _discover_sitemap_urls(
    client: httpx.AsyncClient,
    base_url: str,
    domain: str,
    max_pages: int,
) -> List[str]:
    """Lê /robots.txt + sitemap.xml padrão, retorna URLs encontradas."""
    discovered: List[str] = []
    seen: Set[str] = set()

    sitemap_locations = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/sitemap-index.xml",
    ]

    # robots.txt → Sitemap directives
    try:
        r = await client.get(f"{base_url}/robots.txt")
        if r.status_code == 200:
            for line in r.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sm = line.split(":", 1)[1].strip()
                    if sm and sm not in sitemap_locations:
                        sitemap_locations.insert(0, sm)
    except Exception:
        pass

    async def parse_sitemap(sm_url: str, depth: int = 0):
        if depth > 3 or len(discovered) >= max_pages * 3:
            return
        try:
            r = await client.get(sm_url)
            if r.status_code != 200 or len(r.content) > _MAX_SITEMAP_BYTES:
                return
            try:
                root = ET.fromstring(r.text)
            except ET.ParseError:
                return
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            # Sitemap index → recursivo
            for s in root.findall(".//sm:sitemap/sm:loc", ns):
                if s.text:
                    await parse_sitemap(s.text.strip(), depth + 1)
            # URLs
            for u in root.findall(".//sm:url/sm:loc", ns):
                if u.text:
                    nu = _normalize(u.text.strip(), base_url, domain)
                    if nu and nu not in seen and _should_crawl(nu, domain):
                        seen.add(nu)
                        discovered.append(nu)
            # Fallback sem namespace
            for el in root.iter():
                if el.tag.endswith("loc") and el.text:
                    nu = _normalize(el.text.strip(), base_url, domain)
                    if nu and nu not in seen and _should_crawl(nu, domain):
                        seen.add(nu)
                        discovered.append(nu)
        except Exception:
            pass

    for sm in sitemap_locations:
        await parse_sitemap(sm)
        if len(discovered) >= max_pages:
            break

    base_norm = _normalize(base_url, base_url, domain)
    if base_norm and base_norm not in seen:
        discovered.insert(0, base_norm)

    return discovered[: max_pages * 3]


async def crawl_site(url: str, max_pages: int = 100) -> Dict[str, Any]:
    """
    Crawl completo de um site usando Crawlee BeautifulSoupCrawler.

    Args:
        url: URL base do site
        max_pages: limite de páginas (default 100)

    Returns:
        Dict com base_url, pages_found, pages_crawled, pages_failed,
        pages_analyzed, average_score, total_issues, issues_summary,
        duration_seconds, pages.
    """
    start = datetime.utcnow()

    base_url = url.rstrip("/")
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    parsed = urlparse(base_url)
    domain = parsed.netloc

    # Segue redirect do base_url: atualiza base_url/domain para o destino final
    # (evita falhas quando o site redireciona http→https ou adiciona www.).
    try:
        headers_probe = {"User-Agent": _USER_AGENT}
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(10.0),
            headers=headers_probe,
        ) as _probe:
            pr = await _probe.get(base_url)
            final_url = str(pr.url)
            p2 = urlparse(final_url)
            if p2.netloc and p2.netloc != domain:
                logger.info(f"[crawl_site] base redirect: {domain} → {p2.netloc}")
                base_url = f"{p2.scheme}://{p2.netloc}"
                domain = p2.netloc
    except Exception as e:
        logger.debug(f"[crawl_site] redirect probe falhou: {e}")

    # Tenta importar Crawlee (opcional). Se não disponível, usa fallback httpx+bs4 com BFS,
    # que é nosso motor principal em produção (leve, sem dependências pesadas).
    BeautifulSoupCrawler = None
    ConcurrencySettings = None
    _has_crawlee = False
    try:
        from crawlee.crawlers import BeautifulSoupCrawler as _BSC  # type: ignore
        from crawlee import ConcurrencySettings as _CS  # type: ignore
        BeautifulSoupCrawler = _BSC
        ConcurrencySettings = _CS
        _has_crawlee = True
        logger.info("[crawl_site] usando engine=crawlee")
    except Exception:
        try:
            from crawlee.beautifulsoup_crawler import BeautifulSoupCrawler as _BSC  # type: ignore
            from crawlee import ConcurrencySettings as _CS  # type: ignore
            BeautifulSoupCrawler = _BSC
            ConcurrencySettings = _CS
            _has_crawlee = True
            logger.info("[crawl_site] usando engine=crawlee (legacy)")
        except Exception:
            logger.info("[crawl_site] usando engine=fallback (httpx+bs4 BFS)")
            _has_crawlee = False

    pages: List[Dict[str, Any]] = []
    failed: Set[str] = set()
    crawled: Set[str] = set()

    # 1. Descobrir URLs via sitemap
    headers = {"User-Agent": _USER_AGENT}
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(15.0),
        headers=headers,
    ) as discovery_client:
        seed_urls = await _discover_sitemap_urls(
            discovery_client, base_url, domain, max_pages
        )

    seed_urls = seed_urls[: max_pages * 3] or [base_url]

    # 2. Crawl
    if _has_crawlee:
        try:
            crawler = BeautifulSoupCrawler(
                max_requests_per_crawl=max_pages,
                concurrency_settings=ConcurrencySettings(
                    desired_concurrency=5,
                    max_concurrency=5,
                ),
                request_handler_timeout=timedelta(seconds=15),
            )

            @crawler.router.default_handler
            async def handler(context: "BeautifulSoupCrawlingContext") -> None:
                req_url = str(context.request.loaded_url or context.request.url)
                if not _should_crawl(req_url, domain):
                    return
                try:
                    html = str(context.soup)
                    status_code = (
                        context.http_response.status_code
                        if hasattr(context, "http_response") and context.http_response
                        else 200
                    )
                    analysis = analyze_seo_html(html, base_url, domain=domain)
                    pages.append({
                        "url": req_url,
                        "status_code": status_code,
                        "title": analysis.get("title"),
                        "meta_description": analysis.get("meta_description"),
                        "h1": analysis.get("h1"),
                        "issues": analysis.get("all_issues") or analysis.get("issues") or {},
                        "score": int(analysis.get("score") or 0),
                    })
                    crawled.add(req_url)
                    # Enfileira links internos respeitando filtros
                    try:
                        await context.enqueue_links(
                            strategy="same-domain",
                        )
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"Crawlee handler error em {req_url}: {e}")
                    failed.add(req_url)

            await crawler.run(seed_urls[:max_pages])
        except Exception as e:
            logger.exception(f"Crawlee falhou; caindo para fallback. Erro: {e}")
            _has_crawlee = False

    if not _has_crawlee:
        # Fallback httpx + bs4 com BFS: partindo de seed_urls, enfileira links internos
        # descobertos em cada página até atingir max_pages.
        from bs4 import BeautifulSoup

        sem = asyncio.Semaphore(5)
        seen: Set[str] = set()
        queue: List[str] = []
        for u in seed_urls:
            nu = _normalize(u, base_url, domain)
            if nu and nu not in seen:
                seen.add(nu)
                queue.append(nu)
        if not queue:
            base_norm = _normalize(base_url, base_url, domain)
            if base_norm:
                seen.add(base_norm)
                queue.append(base_norm)

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0),
            headers=headers,
        ) as client:
            async def fetch_one(u: str) -> List[str]:
                """Baixa uma URL, analisa e retorna novos links internos descobertos."""
                if len(pages) >= max_pages:
                    return []
                try:
                    async with sem:
                        r = await client.get(u)
                    ct = r.headers.get("content-type", "").lower()
                    if "text/html" not in ct:
                        return []
                    analysis = analyze_seo_html(r.text, base_url, domain=domain)
                    pages.append({
                        "url": str(r.url),
                        "status_code": r.status_code,
                        "title": analysis.get("title"),
                        "meta_description": analysis.get("meta_description"),
                        "h1": analysis.get("h1"),
                        "issues": analysis.get("all_issues") or analysis.get("issues") or {},
                        "score": int(analysis.get("score") or 0),
                    })
                    crawled.add(u)
                    # Extrai links internos desta página
                    new_links: List[str] = []
                    try:
                        soup = BeautifulSoup(r.text, "lxml")
                    except Exception:
                        soup = BeautifulSoup(r.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                            continue
                        nu = _normalize(href, str(r.url), domain)
                        if nu and nu not in seen and _should_crawl(nu, domain):
                            new_links.append(nu)
                    return new_links
                except Exception as e:
                    logger.debug(f"fallback fetch falhou {u}: {e}")
                    failed.add(u)
                    return []

            # BFS por ondas de concorrência
            while queue and len(pages) < max_pages:
                batch = queue[:20]
                queue = queue[20:]
                results = await asyncio.gather(
                    *[fetch_one(u) for u in batch], return_exceptions=True
                )
                for res in results:
                    if isinstance(res, list):
                        for nu in res:
                            if nu not in seen and len(seen) < max_pages * 3:
                                seen.add(nu)
                                queue.append(nu)

    logger.info(
        f"[crawl_site] {base_url} engine={'crawlee' if _has_crawlee else 'fallback'} "
        f"analyzed={len(pages)} failed={len(failed)}"
    )

    # 3. Sumarização
    issues_summary: Dict[str, int] = {}
    for p in pages:
        for k, v in (p.get("issues") or {}).items():
            if v:
                issues_summary[k] = issues_summary.get(k, 0) + 1

    total_score = sum(int(p.get("score") or 0) for p in pages)
    avg_score = round(total_score / len(pages)) if pages else 0
    duration = (datetime.utcnow() - start).total_seconds()

    return {
        "base_url": base_url,
        "pages_found": len(seed_urls),
        "pages_crawled": len(crawled),
        "pages_failed": len(failed),
        "pages_analyzed": len(pages),
        "average_score": avg_score,
        "total_issues": sum(issues_summary.values()),
        "issues_summary": issues_summary,
        "duration_seconds": round(duration, 2),
        "pages": pages,
    }
