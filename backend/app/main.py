"""
SiteCan MVP - Backend com Supabase
API REST usando Supabase como banco de dados
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from app.demo.config import DemoModeError, assert_demo_safe, demo_info_payload

try:
    assert_demo_safe()
except DemoModeError:
    raise

import httpx
from bs4 import BeautifulSoup
from app.seo_analysis import analyze_seo_html, ISSUE_CONFIG
from fastapi import FastAPI, HTTPException, Request, Query, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from app.auth import get_current_user, get_optional_user
from app.billing import router as billing_router
from app.billing.access import enforce_subscription_middleware
from app.admin import router as admin_router
from app.demo.router import router as demo_router


logger = logging.getLogger(__name__)


def format_error(detail, status_code=400, context=None):
    err = {"error": True, "detail": str(detail)}
    if context:
        err["context"] = context
    return JSONResponse(status_code=status_code, content=err)

from pydantic import BaseModel
from app.services import (
    get_site_service, get_scan_service, get_task_service,
    get_page_service, get_keyword_service,
)

# -------------------------
# Config
# -------------------------
_HARDCODED_ORIGINS = [
    "https://4seo.app",
    "https://www.4seo.app",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:3000",
]
_env_origins = os.getenv("CORS_ORIGINS", "")
_extra = [o.strip() for o in _env_origins.split(",") if o.strip() and o.strip() != "*"]
ALLOWED_ORIGINS = list(set(_extra + _HARDCODED_ORIGINS))
DEFAULT_MAX_PAGES = int(os.getenv("MAX_PAGES_PER_SCAN", "20"))

# -------------------------
# Schemas
# -------------------------
class SiteCreateRequest(BaseModel):
    base_url: str
    platform: Optional[str] = None


class SiteOut(BaseModel):
    id: str
    base_url: str
    platform: Optional[str] = None


class PageOut(BaseModel):
    id: str
    url: str
    status_code: int
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: Optional[str] = None
    issues: Dict[str, Any]  # Pode ser bool ou int (ex: img_alt_count)
    seo_score: int
    total_score: Optional[int] = None


class TaskOut(BaseModel):
    task_id: str
    page_url: str
    message: str
    type: Optional[str] = None
    status: Optional[str] = None


class ScanResponse(BaseModel):
    pages_scanned: int
    tasks_created: int
    score: int
    pages_found: Optional[int] = None
    duration_seconds: Optional[float] = None
    issues_summary: Optional[Dict[str, int]] = None


class OptimizeRequest(BaseModel):
    product_name: str
    product_description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None





async def fetch_html(url: str) -> tuple[str, Dict[str, Any]]:
    """Busca HTML de uma URL"""
    headers = {"User-Agent": "SiteCan-SEO/1.0", "Accept": "text/html"}
    timeout = httpx.Timeout(15.0, connect=10.0)
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
        r = await client.get(url)
        meta = {"final_url": str(r.url), "status_code": r.status_code}
        if r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"HTTP {r.status_code}")
        return r.text, meta


# -------------------------
# App
# -------------------------
_disable_docs = (os.getenv("DISABLE_API_DOCS") or "").strip().lower() in {
    "1",
    "true",
    "yes",
}
_is_production = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "").lower() == "production"
_docs_url = None if (_disable_docs or _is_production) else "/docs"
_openapi_url = None if (_disable_docs or _is_production) else "/openapi.json"
_redoc_url = None if (_disable_docs or _is_production) else "/redoc"

app = FastAPI(
    title="4SEO API",
    version="1.0.0",
    docs_url=_docs_url,
    openapi_url=_openapi_url,
    redoc_url=_redoc_url,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Billing (Asaas) — contrato: /billing/* e /webhooks/asaas
# Prefixo /api espelha as mesmas rotas para o proxy do Vite (VITE_API_BASE_URL=/api)
app.include_router(billing_router)
app.include_router(billing_router, prefix="/api")
app.include_router(admin_router)
app.include_router(admin_router, prefix="/api")
app.include_router(demo_router)


@app.middleware("http")
async def subscription_gate(request: Request, call_next):
    """Conta autenticada ≠ recursos: exige assinatura ativa nas APIs de produto."""
    return await enforce_subscription_middleware(request, call_next)


@app.middleware("http")
async def ensure_cors_on_errors(request: Request, call_next):
    """Garante headers CORS mesmo em respostas de erro (bug do Starlette)."""
    try:
        response = await call_next(request)
    except Exception as exc:
        # Se call_next falhar, cria resposta 500 com CORS (sem vazar detalhes internos)
        logger.exception(
            "Middleware caught unhandled error on %s %s: %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc,
        )
        response = JSONResponse(
            status_code=500,
            content={"error": True, "detail": "Erro interno do servidor"},
        )
    origin = request.headers.get("origin")
    if origin and "access-control-allow-origin" not in response.headers:
        if origin in ALLOWED_ORIGINS:
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
            response.headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["access-control-allow-headers"] = "Authorization, Content-Type, Accept"
    return response

# Handler global para exceções HTTP
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    origin = request.headers.get("origin", "")
    resp = format_error(exc.detail, status_code=exc.status_code)
    if origin and origin in ALLOWED_ORIGINS:
        resp.headers["access-control-allow-origin"] = origin
        resp.headers["access-control-allow-credentials"] = "true"
    return resp

# Handler global para exceções genéricas
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception on %s %s: %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc,
    )
    origin = request.headers.get("origin", "")
    resp = format_error("Erro interno do servidor", status_code=500)
    if origin and origin in ALLOWED_ORIGINS:
        resp.headers["access-control-allow-origin"] = origin
        resp.headers["access-control-allow-credentials"] = "true"
    return resp


@app.get("/api/health")
async def health():
    """Health check"""
    return {"status": "ok", "mode": "supabase", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/info")
async def api_info():
    """Retorna informações da API e status da IA"""
    openai_key = os.getenv("OPENAI_API_KEY", "")
    asaas_key = os.getenv("ASAAS_API_KEY", "")
    return {
        "version": "1.0.0",
        "mode": "supabase",
        "ai": {
            "enabled": bool(openai_key),
            "model": os.getenv("AI_MODEL", "gpt-5-mini"),
            "provider": "OpenAI" if openai_key else "Fallback (sem IA)",
        },
        "billing": {
            "enabled": bool(asaas_key.strip()),
            "provider": "Asaas" if asaas_key.strip() else None,
            "checkoutPath": "/billing/checkout",
            "webhookPath": "/webhooks/asaas",
        },
        "supported_models": [
            {"name": "gpt-5-mini", "provider": "OpenAI", "cost": "$0.25/1M tokens", "recommended": True},
            {"name": "gpt-5", "provider": "OpenAI", "cost": "$1.25/1M tokens", "quality": "Premium"},
            {"name": "gpt-4o-mini", "provider": "OpenAI", "cost": "$0.15/1M tokens"},
            {"name": "gpt-4o", "provider": "OpenAI", "cost": "$2.50/1M tokens"},
        ],
        "setup_instructions": "Adicione OPENAI_API_KEY no arquivo .env para habilitar IA",
        "demo": demo_info_payload(),
    }


# -------------------------
# Helpers de ownership / integrações
# -------------------------
# Plataformas de integração real (lojas conectadas). Sites fora desta lista
# são análises por URL e não bloqueiam o slot de integração.
INTEGRATION_PLATFORMS = ("shopify", "nuvemshop", "vtex", "lojaintegrada")

# Caches globais de clientes VTEX / Loja Integrada (mesmo padrão Shopify/Nuvemshop)
# VTEX: keyed por account_name; LI: keyed por store_key (hash curto da chave_api)
_vtex_clients_cache: Dict[str, Any] = {}
_li_clients_cache: Dict[str, Any] = {}


async def get_or_restore_vtex_client(account_name: str, user: dict) -> Any:
    """Retorna cliente VTEX do cache ou reconstrói a partir do user_integrations"""
    key = (account_name or "").strip().lower()
    cached = _vtex_clients_cache.get(key)
    if cached:
        if cached.get("user_id") != user["user_id"]:
            return None
        return cached
    try:
        from app.supabase_client import get_supabase_for_user
        db = get_supabase_for_user(user["token"])
        integration = await db.get_integration(user["user_id"])
        if integration and integration.get("platform") == "vtex" and integration.get("access_token"):
            meta = integration.get("metadata") or {}
            from app.integrations.vtex import create_vtex_client
            from app.integrations.vtex_optimizer import VtexSEOOptimizer
            client = create_vtex_client(
                account_name=meta.get("account_name") or integration.get("store_url", ""),
                app_key=meta.get("app_key", ""),
                app_token=integration["access_token"],
            )
            optimizer = VtexSEOOptimizer(client)
            _vtex_clients_cache[client.account_name] = {
                "client": client, "optimizer": optimizer, "user_id": user["user_id"],
            }
            return _vtex_clients_cache.get(key)
    except Exception as e:
        logger.warning(f"Failed to restore VTEX client from DB: {e}")
    return None


async def get_or_restore_lojaintegrada_client(store_key: str, user: dict) -> Any:
    """Retorna cliente Loja Integrada do cache ou reconstrói a partir do user_integrations"""
    cached = _li_clients_cache.get(store_key)
    if cached:
        if cached.get("user_id") != user["user_id"]:
            return None
        return cached
    try:
        from app.supabase_client import get_supabase_for_user
        db = get_supabase_for_user(user["token"])
        integration = await db.get_integration(user["user_id"])
        if integration and integration.get("platform") == "lojaintegrada" and integration.get("access_token"):
            from app.integrations.lojaintegrada import create_lojaintegrada_client
            from app.integrations.lojaintegrada_optimizer import LojaIntegradaSEOOptimizer
            client = create_lojaintegrada_client(integration["access_token"])
            optimizer = LojaIntegradaSEOOptimizer(client)
            _li_clients_cache[client.store_key] = {
                "client": client, "optimizer": optimizer, "user_id": user["user_id"],
            }
            return _li_clients_cache.get(store_key) or _li_clients_cache.get(client.store_key)
    except Exception as e:
        logger.warning(f"Failed to restore Loja Integrada client from DB: {e}")
    return None


async def _ensure_site_owner(db, site_id: str, user_id: str) -> dict:
    """Garante que o site pertence ao usuário atual. Retorna o site ou levanta 404."""
    site = await db.get_site(site_id)
    if not site or str(site.get("user_id", "")) != str(user_id):
        raise HTTPException(status_code=404, detail="Site não encontrado")
    return site


async def _delete_url_only_sites(db, user_id: str) -> None:
    """Remove sites criados apenas para análise por URL (sem integração real).
    Usado antes de conectar uma loja Shopify/Nuvemshop para liberar o slot.
    """
    try:
        sites = await db.list_sites_for_user(user_id, limit=10)
        for s in sites:
            if s.get("platform") not in INTEGRATION_PLATFORMS:
                await db.delete_site(str(s["id"]))
    except Exception as e:
        logger.warning(f"_delete_url_only_sites failed: {e}")


# -------------------------
# Sites
# -------------------------
@app.get("/api/sites")
async def list_sites(user: dict = Depends(get_current_user)):
    """Lista todos os sites do usuário autenticado"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    service = get_site_service(db)
    sites = await service.list_sites(user_id=user["user_id"])
    return [
        SiteOut(
            id=str(s["id"]),
            base_url=s["base_url"],
            platform=s.get("platform")
        ) for s in sites
    ]


@app.post("/api/sites")
async def create_site(payload: SiteCreateRequest, user: dict = Depends(get_current_user)):
    """Cadastra um novo site"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    service = get_site_service(db)
    # Normalize URL: ensure https:// prefix
    url = payload.base_url.strip().rstrip("/")
    if not url.startswith("http"):
        url = f"https://{url}"
    site = await service.create_site(url, payload.platform, user_id=user["user_id"])
    return SiteOut(
        id=str(site["id"]),
        base_url=site["base_url"],
        platform=site.get("platform")
    )


@app.delete("/api/sites/{site_id}")
async def delete_site(site_id: str, user: dict = Depends(get_current_user)):
    """Remove um site (verifica ownership via RLS)"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    service = get_site_service(db)
    await service.delete_site(site_id)
    return {"ok": True}


# -------------------------
# Panorama SEO (Visão consolidada)
# -------------------------
@app.get("/api/panorama")
async def panorama_seo(user: dict = Depends(get_current_user)):
    """
    Visão consolidada de performance orgânica.
    Agrega: GSC data, Crawler (scan) data, Termos de pesquisa.
    """
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])

    sites = await db.list_sites_for_user(user["user_id"], limit=1)
    site = sites[0] if sites else None
    site_id = str(site["id"]) if site else None

    # 1. GSC overview
    gsc_data = None
    try:
        from app.integrations.gsc import get_gsc_tokens, fetch_gsc_overview
        token_data = await get_gsc_tokens(user["user_id"])
        if token_data and token_data.get("access_token"):
            gsc_data = await fetch_gsc_overview(token_data["access_token"], token_data["site_url"])
    except Exception:
        pass

    # 2. Crawler / scan data
    pages = []
    last_scan = None
    tasks_pending = 0
    if site_id:
        pages = await db.list_pages(site_id)
        last_scan = await db.get_latest_scan_run(site_id)
        tasks = await db.list_tasks(site_id, status="pending")
        tasks_pending = len(tasks)

    avg_score = 0
    if pages:
        scores = [p.get("score", 0) for p in pages if p.get("score")]
        avg_score = round(sum(scores) / len(scores)) if scores else 0

    # Issue distribution
    issue_dist: Dict[str, int] = {}
    for p in pages:
        for ik, iv in (p.get("issues") or {}).items():
            if iv:
                issue_dist[ik] = issue_dist.get(ik, 0) + 1

    # Score distribution buckets
    score_buckets = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
    for p in pages:
        s = p.get("score", 0)
        if s >= 80:
            score_buckets["excellent"] += 1
        elif s >= 60:
            score_buckets["good"] += 1
        elif s >= 40:
            score_buckets["fair"] += 1
        else:
            score_buckets["poor"] += 1

    # 3. Termos de pesquisa
    terms = await db.list_search_terms(user["user_id"])
    termos_count = len(terms)

    # 4. Histórico (últimos 30 dias)
    snapshots = await db.list_daily_snapshots(user["user_id"], 30)

    return {
        "connected": site is not None,
        "platform": site.get("platform") if site else None,
        "store_url": site.get("base_url") if site else None,
        # GSC
        "gsc_connected": gsc_data is not None,
        "impressions": gsc_data.get("impressions", 0) if gsc_data else 0,
        "clicks": gsc_data.get("clicks", 0) if gsc_data else 0,
        "ctr": gsc_data.get("ctr", 0) if gsc_data else 0,
        "position": gsc_data.get("position", 0) if gsc_data else 0,
        "top_queries": (gsc_data.get("top_queries", []) if gsc_data else [])[:10],
        # Crawler
        "avg_score": avg_score,
        "total_pages": len(pages),
        "tasks_pending": tasks_pending,
        "issue_distribution": issue_dist,
        "score_distribution": score_buckets,
        "last_scan_at": last_scan.get("completed_at") if last_scan else None,
        # Termos
        "termos_count": termos_count,
        "termos": [{"term": t["term"], "id": t["id"]} for t in terms],
        # Histórico (para sparklines)
        "snapshots": snapshots,
    }


# -------------------------
# Dashboard Summary
# -------------------------
@app.get("/api/dashboard/summary")
async def dashboard_summary(refresh: bool = False, user: dict = Depends(get_current_user)):
    """
    Resumo consolidado do Dashboard.
    Combina: último scan, páginas, tasks, GSC overview.
    Compara dados atuais com 30 dias atrás para calcular evolução.
    refresh=true dispara auto-scan da plataforma (Shopify/Nuvemshop).
    """
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])

    # 1. Buscar site do usuário
    sites = await db.list_sites_for_user(user["user_id"], limit=1)
    if not sites:
        return {"connected": False}

    site = sites[0]
    site_id = str(site["id"])

    # 2. Último scan_run
    last_scan = await db.get_latest_scan_run(site_id)

    # 3. Páginas e tasks (Dashboard é 100% leitura do banco — nunca dispara scan)
    pages = await db.list_pages(site_id)
    tasks = await db.list_tasks(site_id, status="pending")

    # 4. Score geral
    avg_score = 0
    if last_scan and last_scan.get("avg_score"):
        avg_score = last_scan["avg_score"]
    elif pages:
        scores = [p.get("score", 0) for p in pages if p.get("score")]
        avg_score = round(sum(scores) / len(scores)) if scores else 0
    # 5. Métricas derivadas do scan
    total_pages = len(pages)

    # Segurança: % de páginas sem noindex e com canonical
    pages_secure = sum(1 for p in pages if not (p.get("issues") or {}).get("noindex_detected") and not (p.get("issues") or {}).get("missing_canonical"))
    security_pct = round((pages_secure / total_pages) * 100) if total_pages else 0

    # Velocidade: basear em issues de img_alt e schema (proxy - sem PageSpeed real)
    pages_fast = sum(1 for p in pages if not (p.get("issues") or {}).get("missing_img_alt") and not (p.get("issues") or {}).get("missing_schema"))
    speed_pct = round((pages_fast / total_pages) * 100) if total_pages else 0

    # Potencial: baseado no score médio
    if avg_score >= 80:
        growth_potential = "Baixo"
    elif avg_score >= 50:
        growth_potential = "Alto"
    else:
        growth_potential = "Muito Alto"

    # 6. GSC data (se conectado)
    gsc_data = None
    try:
        from app.integrations.gsc import get_gsc_tokens, fetch_gsc_overview
        token_data = await get_gsc_tokens(user["user_id"])
        if token_data and token_data.get("access_token"):
            gsc_data = await fetch_gsc_overview(token_data["access_token"], token_data["site_url"])
    except Exception:
        pass  # GSC não conectado ou indisponível

    # 7. Índice Geral (visibilidade) baseado em GSC
    impressions = gsc_data.get("impressions", 0) if gsc_data else 0
    clicks = gsc_data.get("clicks", 0) if gsc_data else 0
    ctr = gsc_data.get("ctr", 0) if gsc_data else 0
    unique_pages_gsc = gsc_data.get("unique_pages", 0) if gsc_data else 0
    top_queries = gsc_data.get("top_queries", []) if gsc_data else []

    # Visibilidade: normalizar CTR (max ~20%) + posição média
    visibility_pct = min(round(ctr * 5), 100) if ctr else 0  # CTR 20% -> 100%

    # 8. Checklist do SEO (da análise de issues)
    issue_counts: Dict[str, int] = {}
    for p in pages:
        issues = p.get("issues") or {}
        for issue_key, has_issue in issues.items():
            if has_issue:
                issue_counts[issue_key] = issue_counts.get(issue_key, 0) + 1

    checklist_map = {
        "missing_title": {"title": "Títulos", "desc_ok": "Todas as páginas possuem títulos otimizados", "desc_bad": "{n} páginas sem título  - isso reduz sua visibilidade"},
        "title_length": {"title": "Tamanho dos títulos", "desc_ok": "Todos os títulos estão no tamanho ideal", "desc_bad": "{n} páginas com título fora do tamanho ideal (30-60 caracteres)"},
        "missing_meta_description": {"title": "Descrições para buscas", "desc_ok": "Todas as páginas possuem meta description", "desc_bad": "{n} páginas sem descrição  - isso reduz cliques"},
        "missing_h1": {"title": "Cabeçalhos H1", "desc_ok": "Todas as páginas possuem H1", "desc_bad": "{n} páginas sem H1  - o Google não entende o conteúdo"},
        "missing_img_alt": {"title": "Textos nas imagens", "desc_ok": "Todas as imagens possuem texto alternativo", "desc_bad": "{n} imagens sem descrição  - o Google não consegue entendê-las"},
        "missing_canonical": {"title": "URLs canônicas", "desc_ok": "Todas as páginas possuem canonical", "desc_bad": "{n} páginas sem canonical  - risco de conteúdo duplicado"},
        "missing_og_tags": {"title": "Tags de compartilhamento", "desc_ok": "Tags Open Graph configuradas", "desc_bad": "{n} páginas sem Open Graph  - compromete compartilhamento"},
        "missing_schema": {"title": "Dados estruturados", "desc_ok": "Schema.org configurado", "desc_bad": "{n} páginas sem Schema  - perde rich snippets no Google"},
    }

    # 8.1 Scan anterior (para deltas no checklist e nos changes)
    try:
        recent_scans = await db.list_recent_scan_runs(site_id, limit=2)
    except Exception:
        recent_scans = [last_scan] if last_scan else []
    prev_scan = recent_scans[1] if len(recent_scans) >= 2 else None
    prev_issues = (prev_scan.get("issues_summary") or {}) if prev_scan else {}

    checklist = []
    for issue_key, meta in checklist_map.items():
        count = issue_counts.get(issue_key, 0)
        prev_count = int(prev_issues.get(issue_key, 0) or 0)
        delta = count - prev_count  # positivo = piorou; negativo = melhorou
        delta_text = ""
        if prev_scan:
            if delta < 0:
                delta_text = f" ↓ {abs(delta)} resolvidos desde o último scan"
            elif delta > 0:
                delta_text = f" ↑ {delta} novos problemas"
        if count == 0:
            checklist.append({
                "title": meta["title"],
                "description": meta["desc_ok"] + delta_text,
                "status": "success",
                "count": 0,
                "delta": delta if prev_scan else 0,
            })
        elif count <= 3:
            checklist.append({
                "title": meta["title"],
                "description": meta["desc_bad"].format(n=count) + delta_text,
                "status": "warning",
                "count": count,
                "delta": delta if prev_scan else 0,
            })
        else:
            checklist.append({
                "title": meta["title"],
                "description": meta["desc_bad"].format(n=count) + delta_text,
                "status": "error",
                "count": count,
                "delta": delta if prev_scan else 0,
            })

    # 9. Evolução real entre scan_runs
    score_change = 0
    pages_change = 0
    visibility_change = 0
    impressions_change = 0
    if prev_scan:
        prev_avg = int(prev_scan.get("avg_score") or 0)
        prev_pages = int(prev_scan.get("pages_scanned") or 0)
        if prev_avg:
            score_change = round(((avg_score - prev_avg) / prev_avg) * 100)
        if prev_pages:
            pages_change = round(((total_pages - prev_pages) / prev_pages) * 100)
    # visibility/impressions: GSC ainda não tem histórico persistido nesse endpoint
    # mantemos 0% até existir snapshot anterior

    # 10. Termos de pesquisa monitorados
    termos_count = await db.count_search_terms(user["user_id"])

    # 11. Otimizações aplicadas (lido do banco — persiste após cold starts)
    applied_optimizations = 0
    pending_optimizations = 0
    try:
        integration = await db.get_integration(user["user_id"])
        if integration:
            meta = integration.get("metadata") or {}
            applied_optimizations = int(meta.get("applied_count") or 0)
    except Exception as e:
        logger.warning(f"[Dashboard] Falha ao ler applied_count: {e}")

    # 12. Score por categoria de conteúdo (classifica pages por URL)
    def _classify(url: str) -> str:
        u = (url or "").lower()
        if "/products/" in u or "/produtos/" in u or "/produto/" in u:
            return "products"
        if "/collections/" in u or "/categorias/" in u or "/categoria/" in u:
            return "collections"
        if "/blog/" in u or "/blogs/" in u or "/post/" in u or "/posts/" in u:
            return "blog"
        if "/pages/" in u or "/page/" in u:
            return "pages"
        return "pages"

    buckets: Dict[str, list] = {"products": [], "collections": [], "pages": [], "blog": []}
    for p in pages:
        score_val = p.get("score") or p.get("seo_score") or 0
        if not score_val:
            continue
        buckets[_classify(p.get("url", ""))].append(int(score_val))
    scores_by_type = {
        k: (round(sum(v) / len(v)) if v else 0)
        for k, v in buckets.items()
    }
    counts_by_type = {k: len(v) for k, v in buckets.items()}

    # 13. Potencial de crescimento contextual
    issue_messages = {
        "missing_meta_description": "Corrigir isso pode aumentar o CTR em até 30%.",
        "missing_title": "Corrigir isso melhora o ranqueamento no Google em até 20%.",
        "title_length": "Ajustar para 30-60 caracteres pode aumentar o CTR em 10-15%.",
        "missing_h1": "Adicionar H1 ajuda o Google a entender o conteúdo principal da página.",
        "missing_img_alt": "Imagens com alt text ranqueiam no Google Imagens e melhoram acessibilidade.",
        "missing_canonical": "Define a versão preferida da página e evita conteúdo duplicado.",
        "missing_og_tags": "Open Graph melhora a aparência ao compartilhar nas redes sociais.",
        "missing_schema": "Schema.org habilita rich snippets (estrelas, preço) na busca.",
    }
    issue_labels = {
        "missing_meta_description": "páginas sem meta description",
        "missing_title": "páginas sem título",
        "title_length": "páginas com título fora do tamanho ideal",
        "missing_h1": "páginas sem H1",
        "missing_img_alt": "imagens sem texto alternativo",
        "missing_canonical": "páginas sem canonical",
        "missing_og_tags": "páginas sem Open Graph",
        "missing_schema": "páginas sem Schema.org",
    }
    if avg_score >= 80:
        growth_label = "Baixo"
    elif avg_score >= 50:
        growth_label = "Alto"
    else:
        growth_label = "Muito Alto"
    # Mapeamento invertido de Potencial SEO (Dashboard V2):
    # score alto = pouco potencial restante; score baixo = muito a ganhar
    #
    # Sem nenhuma página escaneada ainda, avg_score fica 0 só por ausência de
    # dado — NÃO significa "score ruim". Sem esta checagem, o mapeamento caía
    # no ramo <50 e retornava "ALTO/verde" (like "muito a ganhar"), uma
    # afirmação de oportunidade sem nenhum dado real por trás dela, exibida ao
    # mesmo tempo que o banner "site ainda não foi analisado".
    if total_pages == 0:
        potencial_label = "—"
        potencial_color = "cinza"
    elif avg_score >= 80:
        potencial_label = "BAIXO"
        potencial_color = "cinza"
    elif avg_score >= 50:
        potencial_label = "MÉDIO"
        potencial_color = "amarelo"
    else:
        potencial_label = "ALTO"
        potencial_color = "verde"
    top_issue = None
    if issue_counts:
        top_issue = max(issue_counts.items(), key=lambda kv: kv[1])
    if top_issue and top_issue[1] > 0:
        ik, n = top_issue
        growth_potential_text = (
            f"{growth_label} — {n} {issue_labels.get(ik, ik)}. "
            f"{issue_messages.get(ik, '')}"
        ).strip()
    else:
        growth_potential_text = f"{growth_label} — sua loja está bem otimizada."

    return {
        "connected": True,
        # NOVOS nomes (preferenciais para o frontend V2)
        "saude_seo": avg_score,
        "visibilidade_seo": visibility_pct,
        "potencial_seo": growth_potential_text,
        "potencial_seo_label": potencial_label,
        "potencial_seo_color": potencial_color,
        "oportunidades_encontradas": len(tasks),
        "cliques_organicos": clicks,
        # Campos de volumetria contextual
        "volumetria_produtos": {
            "score": scores_by_type.get("products", 0),
            "analisados": counts_by_type.get("products", 0),
        },
        "volumetria_paginas": {
            "score": scores_by_type.get("pages", 0),
            "analisados": total_pages,
        },
        # LEGADO (manter compatibilidade com código existente)
        "store_score": avg_score,
        "security_pct": security_pct,
        "speed_pct": speed_pct,
        "growth_potential": growth_potential_text,
        "growth_potential_label": growth_label,
        "visibility_pct": visibility_pct,
        "impressions": impressions,
        "clicks": clicks,
        "ctr": ctr,
        "unique_pages": unique_pages_gsc,
        "total_pages_scanned": total_pages,
        "pending_tasks": len(tasks),
        "termos_count": termos_count,
        "top_queries": top_queries[:5],
        "checklist": checklist,
        "applied_optimizations": applied_optimizations,
        "pending_optimizations": pending_optimizations,
        "scores_by_type": scores_by_type,
        "counts_by_type": counts_by_type,
        "last_scan": {
            "completed_at": last_scan.get("completed_at") if last_scan else None,
            "pages_scanned": last_scan.get("pages_scanned", 0) if last_scan else 0,
            "tasks_created": last_scan.get("tasks_created", 0) if last_scan else 0,
        },
        "changes": {
            "score": score_change,
            "visibility": visibility_change,
            "impressions": impressions_change,
            "pages": pages_change,
        },
    }


# -------------------------
# Dashboard Oportunidades (filtros inteligentes + matriz de impacto)
# -------------------------
@app.get("/api/dashboard/oportunidades")
async def dashboard_oportunidades(
    impactos: Optional[str] = None,  # ex: "alto,medio"
    tipos: Optional[str] = None,     # ex: "missing_title,missing_meta_description"
    otimizados: Optional[str] = None,  # "sim" ou "nao"
    user: dict = Depends(get_current_user),
):
    """
    Retorna oportunidades de otimização com classificação de impacto.
    Substitui o antigo checklist com filtros inteligentes.

    Filtros via query params:
    - impactos: "alto,medio,baixo" (quais níveis incluir)
    - tipos: "missing_title,missing_meta_description" (issues específicas)
    - otimizados: "sim" (já otimizados) ou "nao" (pendentes)
    """
    from app.supabase_client import get_supabase_for_user
    from app.seo_analysis import ISSUE_CONFIG, ISSUE_IMPACT, ISSUE_LABEL

    db = get_supabase_for_user(user["token"])
    sites = await db.list_sites_for_user(user["user_id"], limit=1)
    if not sites:
        return {"connected": False, "oportunidades": []}

    site = sites[0]
    site_id = str(site["id"])
    pages = await db.list_pages(site_id)
    tasks = await db.list_tasks(site_id)  # todas as tasks, não só pending

    # Parse filters
    impactos_list = [i.strip() for i in (impactos or "").split(",") if i.strip()]
    tipos_list = [t.strip() for t in (tipos or "").split(",") if t.strip()]
    filtrar_otimizados = otimizados  # "sim" ou "nao" ou None (todos)

    # Build task lookup by page_id + issue_type
    task_map: Dict[str, Dict] = {}
    for t in tasks:
        key = f"{t.get('page_id')}_{t.get('issue_type')}"
        if key not in task_map:
            task_map[key] = t

    # 1) Constrói TODAS as oportunidades (sem filtro) para contar os chips corretamente
    todas = []
    for p in pages:
        issues = p.get("issues") or {}
        for issue_code, presente in issues.items():
            if not presente:
                continue
            if issue_code not in ISSUE_CONFIG:
                continue

            impacto = ISSUE_IMPACT.get(issue_code, "medio")
            task = task_map.get(f"{p.get('id')}_{issue_code}")
            esta_otimizado = task.get("status") == "approved" if task else False

            todas.append({
                "page_url": p.get("url", ""),
                "page_id": str(p.get("id", "")),
                "issue_code": issue_code,
                "issue_label": ISSUE_LABEL.get(issue_code, issue_code),
                "impacto": impacto,
                "penalty": ISSUE_CONFIG[issue_code]["penalty"],
                "message": ISSUE_CONFIG[issue_code]["message"],
                "otimizado": esta_otimizado,
                "task_id": str(task["id"]) if task else None,
            })

    # 2) Contagens por categoria (sobre o conjunto completo — badges reais nos chips)
    counts = {"alto": 0, "medio": 0, "baixo": 0, "total": len(todas)}
    tipo_counts: Dict[str, int] = {}
    nao_otim = 0
    ja_otim = 0
    for o in todas:
        counts[o["impacto"]] = counts.get(o["impacto"], 0) + 1
        tipo_counts[o["issue_code"]] = tipo_counts.get(o["issue_code"], 0) + 1
        if o["otimizado"]:
            ja_otim += 1
        else:
            nao_otim += 1

    # 3) Aplica os filtros ativos
    def _passa(o) -> bool:
        if impactos_list and o["impacto"] not in impactos_list:
            return False
        if tipos_list and o["issue_code"] not in tipos_list:
            return False
        if filtrar_otimizados == "sim" and not o["otimizado"]:
            return False
        if filtrar_otimizados == "nao" and o["otimizado"]:
            return False
        return True

    oportunidades = [o for o in todas if _passa(o)]

    # Sort: impacto alto primeiro, depois médio, depois baixo
    ordem = {"alto": 0, "medio": 1, "baixo": 2}
    oportunidades.sort(key=lambda o: ordem.get(o["impacto"], 99))

    # 4) Filtros rápidos exatamente como a spec (Seção 3): Todos | Impacto Alto |
    #    Sem Meta Descrição | Título Curto | Descrição Curta | Não Otimizados | Já Otimizados
    filtros_disponiveis = [
        {"id": "todos", "label": "Todos", "count": counts["total"], "kind": "todos"},
        {"id": "alto", "label": "Impacto Alto", "count": counts["alto"], "kind": "impacto"},
        {"id": "missing_meta_description", "label": "Sem Meta Descrição",
         "count": tipo_counts.get("missing_meta_description", 0), "kind": "tipo"},
        {"id": "title_too_short", "label": "Título Curto",
         "count": tipo_counts.get("title_too_short", 0), "kind": "tipo"},
        {"id": "meta_description_short", "label": "Descrição Curta",
         "count": tipo_counts.get("meta_description_short", 0), "kind": "tipo"},
        {"id": "nao_otimizados", "label": "Não Otimizados", "count": nao_otim, "kind": "otimizado"},
        {"id": "ja_otimizados", "label": "Já Otimizados", "count": ja_otim, "kind": "otimizado"},
    ]

    return {
        "connected": True,
        "oportunidades": oportunidades,
        "counts": counts,
        "filtros_disponiveis": filtros_disponiveis,
    }


# -------------------------
# Validação de propostas (transparência da IA)
# -------------------------
@app.post("/api/validate-proposal")
async def validate_proposal(
    payload: Dict[str, Any],
    user: dict = Depends(get_current_user),
):
    """
    Valida uma proposta existente e retorna metadados de transparência.
    Útil para propostas geradas antes desta atualização que não têm transparencia.
    """
    from app.ai_validation import validar_atributos_descritivos, calcular_cobertura_semantica

    titulo_original = payload.get("titulo_original", "")
    titulo_sugerido = payload.get("titulo_sugerido", "")
    atributos = payload.get("atributos_produto", [])
    keywords = payload.get("keywords_mercado", [])

    return {
        "atributos": validar_atributos_descritivos(titulo_original, titulo_sugerido, atributos),
        "semantica": calcular_cobertura_semantica(titulo_original, titulo_sugerido, keywords),
    }


# -------------------------
# Scan & Analysis (Crawler Inteligente)
# -------------------------
@app.post("/api/scan")
async def trigger_dashboard_scan(force: bool = False, user: dict = Depends(get_current_user)):
    """
    Dispara um scan em background para o site do usuário (Dashboard "Atualizar").

    - Sem site_id: usa o primeiro site do usuário.
    - Cooldown: rejeita se houver scan completo nos últimos 5min E já existem páginas.
      Use ?force=true para ignorar cooldown.
    - Executa `crawl_site` em background via asyncio.create_task.
    - Frontend deve fazer polling em /api/dashboard/summary.
    """
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])

    sites = await db.list_sites_for_user(user["user_id"], limit=1)
    if not sites:
        raise HTTPException(status_code=400, detail="Nenhum site cadastrado")
    site = sites[0]
    site_id = str(site["id"])
    base_url = site.get("base_url")
    if not base_url:
        raise HTTPException(status_code=400, detail="Site sem base_url")

    logger.info(f"[/api/scan] user={user['user_id']} site={site_id} base_url={base_url!r} force={force}")

    # Já existe um scan em andamento para este site? (ex.: auto-scan de
    # onboarding ainda rodando) — evita disparar um segundo scan concorrente,
    # que duplicaria seo_tasks e criaria scan_runs quase simultâneos.
    from app.services import ScanInProgressError
    running = await db.get_running_scan_run(site_id)
    if running:
        return {
            "status": "already_running",
            "message": "Já existe uma análise em andamento para este site. Aguarde ela terminar.",
        }

    # Cooldown: 5 minutos se já há scan completo + páginas (bypass com force=true)
    if not force:
        last_scan = await db.get_latest_scan_run(site_id)
        existing_pages = await db.list_pages(site_id)
        if last_scan and last_scan.get("completed_at") and len(existing_pages) > 0:
            try:
                completed = datetime.fromisoformat(last_scan["completed_at"].replace("Z", "+00:00"))
                elapsed = (datetime.now(completed.tzinfo) - completed).total_seconds()
                if elapsed < 300:
                    return {
                        "status": "cooldown",
                        "seconds_until_next": int(300 - elapsed),
                        "message": "Aguarde antes de re-escanear",
                    }
            except Exception:
                pass

    # Executa scan em background usando ScanService (que usa crawl_site)
    async def _run_background_scan(_db, _site_id):
        try:
            service = get_scan_service(_db)
            result = await service.run_scan(_site_id, max_pages=100)
            logger.info(
                f"[/api/scan] OK site={_site_id}: pages={result['pages_scanned']} "
                f"score={result['score']} tasks={result['tasks_created']}"
            )
        except ScanInProgressError as e:
            logger.info(f"[/api/scan] Pulado (já em andamento) site={_site_id}: {e}")
        except Exception as e:
            logger.exception(f"[/api/scan] FALHOU site={_site_id}: {e}")

    asyncio.create_task(_run_background_scan(db, site_id))
    return {"status": "started", "site_id": site_id, "base_url": base_url}


@app.get("/api/scan/diagnose")
async def diagnose_scan(user: dict = Depends(get_current_user)):
    """
    Diagnóstico síncrono do crawler — retorna número de páginas que o crawler
    conseguiria descobrir e analisar para o site do usuário, SEM persistir no banco.
    Útil para detectar problemas de conectividade, bloqueio por WAF, ou URL inválida.
    """
    from app.supabase_client import get_supabase_for_user
    from app.crawler import crawl_site as _crawl
    db = get_supabase_for_user(user["token"])
    sites = await db.list_sites_for_user(user["user_id"], limit=1)
    if not sites:
        raise HTTPException(status_code=400, detail="Nenhum site cadastrado")
    site = sites[0]
    base_url = site.get("base_url") or ""
    try:
        from app.demo.config import is_demo_mode
        from app.demo.scan import crawl_demo_site

        if is_demo_mode():
            result = crawl_demo_site(base_url, max_pages=5)
        else:
            result = await _crawl(base_url, max_pages=5)
        return {
            "base_url": base_url,
            "pages_found": result.get("pages_found"),
            "pages_analyzed": result.get("pages_analyzed"),
            "pages_failed": result.get("pages_failed"),
            "avg_score": result.get("average_score"),
            "duration_seconds": result.get("duration_seconds"),
            "first_urls": [p.get("url") for p in (result.get("pages") or [])[:5]],
        }
    except Exception as e:
        logger.exception(f"[diagnose_scan] falhou: {e}")
        return {"base_url": base_url, "error": str(e)}


@app.post("/api/site-scan/{site_id}")
async def scan_site(site_id: str, max_pages: int = None, user: dict = Depends(get_current_user)):
    """
    Analisa SEO de um site completo
    
    - Lê sitemap.xml automaticamente
    - Crawl recursivo seguindo links internos
    - Limite configurável de páginas
    
    Args:
        site_id: ID do site cadastrado
        max_pages: Máximo de páginas (default: 100)
    """
    try:
        from app.supabase_client import get_supabase_for_user
        db = get_supabase_for_user(user["token"])
        await _ensure_site_owner(db, site_id, user["user_id"])
        service = get_scan_service(db)
        pages_limit = max_pages or DEFAULT_MAX_PAGES
        result = await service.run_scan(site_id, pages_limit)
        
        return ScanResponse(
            pages_scanned=result["pages_scanned"],
            pages_found=result["pages_found"],
            tasks_created=result["tasks_created"],
            score=result["score"],
            duration_seconds=result["duration_seconds"],
            issues_summary=result["issues_summary"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/site-pages/{site_id}")
async def get_site_pages(site_id: str, user: dict = Depends(get_current_user)):
    """Lista páginas analisadas de um site (isolado por usuário)."""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    page_service = get_page_service(db)

    await _ensure_site_owner(db, site_id, user["user_id"])

    pages = await page_service.list_pages(site_id)
    return [
        PageOut(
            id=str(p["id"]),
            url=p["url"],
            status_code=p.get("status_code", 200),
            title=p.get("title"),
            meta_description=p.get("meta_description"),
            h1=p.get("h1"),
            issues=p.get("issues") or {},
            seo_score=p.get("score", 0),
            total_score=p.get("score", 0),
        ) for p in pages
    ]


@app.get("/api/site-review/{site_id}")
async def get_site_review(site_id: str, user: dict = Depends(get_current_user)):
    """Lista tarefas pendentes de um site (isolado por usuário)."""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    task_service = get_task_service(db)

    await _ensure_site_owner(db, site_id, user["user_id"])

    tasks = await task_service.list_tasks(site_id, status="pending")
    return [
        TaskOut(
            task_id=str(t["id"]),
            page_url=t.get("page_url", ""),
            message=t.get("message", ""),
            type=t.get("issue_type"),
            status=t.get("status"),
        ) for t in tasks
    ]


@app.post("/api/site-analyze/{site_id}")
async def analyze_site_with_ai(site_id: str, max_tasks: int = 10, user: dict = Depends(get_current_user)):
    """Gera sugestões de otimização com IA para as tasks pendentes (isolado por usuário)"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    site_service = get_site_service(db)
    task_service = get_task_service(db)
    
    site = await site_service.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site não encontrado")
    
    # Buscar tasks pendentes sem sugestão de IA
    tasks = await task_service.list_tasks(site_id, status="pending")
    
    # Filtrar apenas tasks que ainda não têm sugestão AI
    tasks_to_process = [t for t in tasks if not t.get("ai_generated")][:max_tasks]
    
    if not tasks_to_process:
        return {
            "message": "Nenhuma tarefa pendente para processar",
            "tasks_processed": 0,
            "tasks_found": len(tasks),
        }
    
    # Gerar fixes com IA para cada task
    processed = 0
    for task in tasks_to_process:
        try:
            await task_service.generate_fix(str(task["id"]))
            processed += 1
        except Exception as e:
            logger.error(f"Erro ao gerar fix para task {task['id']}: {e}")
            # Continuar processando outras tasks
    
    return {
        "message": f"{processed} sugestões geradas com IA",
        "tasks_processed": processed,
        "tasks_found": len(tasks_to_process),
    }


@app.post("/api/task-approve/{task_id}")
async def approve_task(task_id: str, user: dict = Depends(get_current_user)):
    """Aprova uma tarefa (isolado por usuário via RLS)"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    service = get_task_service(db)
    await service.approve_task(task_id)
    return {"ok": True}


@app.delete("/api/task-approve/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    """Remove uma tarefa (isolado por usuário via RLS)"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    service = get_task_service(db)
    await service.delete_task(task_id)
    return {"ok": True}



@app.post("/api/keywords")
async def keywords(payload: dict, user: dict = Depends(get_current_user)):
    """Gera keywords a partir de uma URL"""
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL obrigatória")
    
    html, _ = await fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    
    service = get_keyword_service()
    kws = service.extract_keywords(text, limit=20)
    
    return {
        "keywords": kws,
        "disclaimer": "Estimativas heurísticas para demonstração",
    }


# -------------------------
# Integrations Status
# -------------------------
@app.get("/api/integrations/status")
async def integrations_status(user: dict = Depends(get_current_user)):
    """Status da integração do usuário (1 loja por usuário).
    
    Considera 'connected' apenas integrações reais (Shopify/Nuvemshop).
    Sites criados apenas para análise por URL não bloqueiam novas integrações.
    Restaura site a partir de user_integrations se necessário (após login).
    """
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    sites = await db.list_sites_for_user(user["user_id"], limit=10)
    integration_sites = [s for s in sites if s.get("platform") in INTEGRATION_PLATFORMS]

    # Se não há site de integração mas existe registro em user_integrations,
    # restaurar o site para garantir persistência cross-login.
    if not integration_sites:
        try:
            integration = await db.get_integration(user["user_id"])
            if integration and integration.get("platform") in INTEGRATION_PLATFORMS and integration.get("access_token"):
                meta = integration.get("metadata") or {}
                platform = integration["platform"]
                # Loja Integrada: site_url em metadata; store_url é o store_key (hash), não a URL
                if platform == "lojaintegrada":
                    base_url = meta.get("site_url") or ""
                    if not base_url:
                        # Self-healing: tenta re-derivar a URL a partir do cliente / produtos
                        try:
                            cached_li = await get_or_restore_lojaintegrada_client(
                                integration.get("store_url") or "",
                                user,
                            )
                            if cached_li:
                                li_client = cached_li["client"]
                                base_url = (getattr(li_client, "store_url", None) or "").strip()
                                if not base_url:
                                    sample = await li_client.get_all_products(max_items=1)
                                    if sample and sample[0].url:
                                        base_url = sample[0].url.rsplit("/", 1)[0]
                                if base_url:
                                    meta = {**meta, "site_url": base_url}
                                    await db.save_integration(
                                        user_id=user["user_id"],
                                        platform="lojaintegrada",
                                        store_url=integration.get("store_url") or getattr(li_client, "store_key", ""),
                                        access_token=integration["access_token"],
                                        store_name=integration.get("store_name") or "Loja Integrada",
                                        metadata=meta,
                                    )
                        except Exception as heal_err:
                            logger.warning(f"integrations_status LI URL heal failed: {heal_err}")
                else:
                    base_url = meta.get("site_url") or integration.get("store_url", "")
                if base_url and not base_url.startswith("http"):
                    base_url = f"https://{base_url}"

                if base_url:
                    created = await db.create_site(
                        base_url=base_url,
                        platform=integration["platform"],
                        user_id=user["user_id"],
                    )
                    integration_sites = [created]
                elif platform == "lojaintegrada":
                    return {
                        "connected": True,
                        "platform": "lojaintegrada",
                        "store_name": integration.get("store_name", "Loja Integrada"),
                        "shop_url": "",
                        "store_id": integration.get("store_url", ""),
                        "site_id": None,
                    }
        except Exception as e:
            logger.warning(f"integrations_status: failed to restore site from integration: {e}")

    if integration_sites:
        site = integration_sites[0]
        store_name = site.get("store_name", "")
        store_id_value = ""
        try:
            integration = await db.get_integration(user["user_id"])
            if integration:
                store_name = store_name or integration.get("store_name", "")
                store_id_value = integration.get("store_url", "")
        except Exception:
            pass

        return {
            "connected": True,
            "platform": site.get("platform"),
            "store_name": store_name,
            "shop_url": site.get("base_url", ""),
            "store_id": store_id_value,
            "site_id": str(site["id"]),
        }

    return {"connected": False}


@app.delete("/api/integrations/disconnect")
async def integrations_disconnect(user: dict = Depends(get_current_user)):
    """Desconecta a loja do usuário"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    sites = await db.list_sites_for_user(user["user_id"], limit=1)
    
    if not sites:
        return {"ok": True, "message": "Nenhuma loja conectada"}
    
    site = sites[0]

    # Identificador da loja (para limpar caches) vem do user_integrations
    integration_key = ""
    try:
        integration = await db.get_integration(user["user_id"])
        if integration:
            integration_key = integration.get("store_url", "")
    except Exception:
        pass

    await db.delete_site(str(site["id"]))
    # Remove credenciais salvas — sem isso, /api/integrations/status restaura
    # a loja no próximo refresh (get_integration ainda encontra o access_token)
    # e a integração parece "reconectar sozinha" segundos depois. Tenta
    # algumas vezes (falha costuma ser transitória de rede/DB); se persistir,
    # NÃO reporta sucesso — dizer "desconectado" com a credencial ainda viva
    # é exatamente o que produz o loop de reconexão.
    integration_deleted = False
    last_error: Optional[Exception] = None
    for attempt in range(3):
        try:
            await db.delete_integration(user["user_id"])
            integration_deleted = True
            break
        except Exception as e:
            last_error = e
            logger.warning(f"delete_integration failed during disconnect (tentativa {attempt + 1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))

    if not integration_deleted:
        raise HTTPException(
            status_code=500,
            detail=(
                "A loja foi removida, mas houve falha ao apagar as credenciais salvas "
                f"({last_error}). Tente desconectar novamente para evitar que a loja volte a aparecer conectada."
            ),
        )

    # Also clear cached clients if any
    shop_url = site.get("base_url", "")
    platform = site.get("platform", "")
    if platform == "shopify" and shop_url in _shopify_clients:
        del _shopify_clients[shop_url]
    if platform == "nuvemshop":
        store_id = site.get("store_id", "") or integration_key
        if store_id in _nuvemshop_clients:
            del _nuvemshop_clients[store_id]
    if platform == "vtex" and integration_key in _vtex_clients_cache:
        del _vtex_clients_cache[integration_key]
    if platform == "lojaintegrada" and integration_key in _li_clients_cache:
        del _li_clients_cache[integration_key]

    return {"ok": True, "message": "Loja desconectada"}


# -------------------------
# Optimize (LLM)
# -------------------------
class FixRequest(BaseModel):
    issue_type: str
    page_url: str
    page_title: Optional[str] = None
    page_description: Optional[str] = None
    page_h1: Optional[str] = None


class ApplyAllFixesRequest(BaseModel):
    page_url: str
    issues: List[str]
    page_title: Optional[str] = None
    page_description: Optional[str] = None
    page_h1: Optional[str] = None


@app.post("/api/optimize")
async def optimize(payload: OptimizeRequest, user: dict = Depends(get_current_user)):
    """Gera otimização de SEO com IA"""
    try:
        from app.llm_optimizer import optimize_product_seo
        result = await optimize_product_seo(
            product_name=payload.product_name,
            product_description=payload.product_description,
            category=payload.category,
            brand=payload.brand,
        )
        return result
    except ImportError:
        # Fallback sem IA
        return {
            "seo_title": payload.product_name[:60],
            "seo_description": f"Compre {payload.product_name} com o melhor preço."[:155],
            "ai_powered": False,
        }


@app.post("/api/generate-fix")
async def generate_fix(payload: FixRequest, user: dict = Depends(get_current_user)):
    """
    Gera correção SEO específica usando LLM.
    
    Tipos de issue suportados:
    - title_length
    - meta_description_length
    - missing_h1
    - missing_h2
    - missing_schema
    - missing_img_alt
    - missing_canonical
    """
    try:
        from app.llm_optimizer import generate_seo_fix
        result = await generate_seo_fix(
            issue_type=payload.issue_type,
            page_url=payload.page_url,
            page_title=payload.page_title,
            page_description=payload.page_description,
            page_h1=payload.page_h1,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-all-fixes")
async def generate_all_fixes(payload: ApplyAllFixesRequest, user: dict = Depends(get_current_user)):
    """
    Gera todas as correções para uma página.
    
    Retorna código HTML pronto para copiar e aplicar.
    """
    try:
        from app.llm_optimizer import apply_all_fixes
        result = await apply_all_fixes(
            page_url=payload.page_url,
            issues=payload.issues,
            page_title=payload.page_title,
            page_description=payload.page_description,
            page_h1=payload.page_h1,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/task-fix/{task_id}")
async def fix_task_with_ai(task_id: str, user: dict = Depends(get_current_user)):
    """
    Gera correção para uma task específica usando IA (isolado por usuário via RLS).
    
    Busca os dados da task e página relacionada,
    e retorna a correção otimizada.
    """
    try:
        from app.supabase_client import get_supabase_for_user
        db = get_supabase_for_user(user["token"])
        service = get_task_service(db)
        result = await service.generate_fix(task_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gsc/auth-url")
async def gsc_auth_url(user: dict = Depends(get_current_user)):
    """Get Google OAuth URL for Search Console authorization"""
    from app.integrations.gsc import get_gsc_auth_url, GSC_CLIENT_ID
    if not GSC_CLIENT_ID:
        raise HTTPException(status_code=400, detail="GSC not configured. Set GSC_CLIENT_ID in .env")
    url = get_gsc_auth_url(user_id=user["user_id"])
    return {"auth_url": url}


@app.get("/api/gsc/callback")
async def gsc_callback(code: str, state: str = ""):
    """Handle Google OAuth callback  - exchanges code and stores tokens per user"""
    from app.integrations.gsc import exchange_gsc_code, store_gsc_tokens, list_gsc_sites
    if not state:
        raise HTTPException(status_code=400, detail="Missing state (user_id)")

    tokens = await exchange_gsc_code(code)

    # Discover which sites the user has in GSC
    site_url = ""
    try:
        sites = await list_gsc_sites(tokens["access_token"])
        if sites:
            site_url = sites[0]  # Use first site as default
    except Exception:
        pass

    await store_gsc_tokens(user_id=state, tokens=tokens, site_url=site_url)

    # Redirect to frontend integrations page with success
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(url=f"{frontend_url}/integracoes?gsc=connected")


@app.get("/api/gsc/status")
async def gsc_status(user: dict = Depends(get_current_user)):
    """Check if user has GSC connected and return site info"""
    from app.integrations.gsc import get_gsc_tokens
    token_data = await get_gsc_tokens(user["user_id"])
    if not token_data:
        return {"connected": False}
    return {
        "connected": True,
        "site_url": token_data.get("site_url", ""),
        "updated_at": token_data.get("updated_at", ""),
    }


@app.get("/api/gsc/sites")
async def gsc_sites(user: dict = Depends(get_current_user)):
    """List all GSC sites the user has access to"""
    from app.integrations.gsc import get_gsc_tokens, list_gsc_sites
    token_data = await get_gsc_tokens(user["user_id"])
    if not token_data:
        raise HTTPException(status_code=400, detail="GSC não conectado. Autorize primeiro.")
    sites = await list_gsc_sites(token_data["access_token"])
    return {"sites": sites}


@app.put("/api/gsc/site")
async def gsc_set_site(site_url: str, user: dict = Depends(get_current_user)):
    """Set which GSC site to use for this user"""
    from app.integrations.gsc import get_gsc_tokens, store_gsc_tokens
    token_data = await get_gsc_tokens(user["user_id"])
    if not token_data:
        raise HTTPException(status_code=400, detail="GSC não conectado")
    await store_gsc_tokens(
        user_id=user["user_id"],
        tokens={"access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_in": 3600},
        site_url=site_url,
    )
    return {"site_url": site_url}


@app.delete("/api/gsc/disconnect")
async def gsc_disconnect(user: dict = Depends(get_current_user)):
    """Disconnect GSC  - removes stored tokens for this user"""
    from app.integrations.gsc import delete_gsc_tokens
    await delete_gsc_tokens(user["user_id"])
    return {"message": "GSC desconectado"}


@app.get("/api/gsc/overview")
async def gsc_overview(
    user: dict = Depends(get_current_user),
):
    """Get GSC overview using stored tokens (per-user isolation)"""
    from app.integrations.gsc import get_gsc_tokens, fetch_gsc_overview
    token_data = await get_gsc_tokens(user["user_id"])
    if not token_data:
        raise HTTPException(status_code=400, detail="GSC não conectado. Autorize primeiro.")
    try:
        data = await fetch_gsc_overview(token_data["access_token"], token_data["site_url"])
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gsc/performance")
async def gsc_performance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Get GSC performance data using stored tokens (per-user isolation)"""
    from app.integrations.gsc import get_gsc_tokens, fetch_gsc_performance
    token_data = await get_gsc_tokens(user["user_id"])
    if not token_data:
        raise HTTPException(status_code=400, detail="GSC não conectado. Autorize primeiro.")
    try:
        data = await fetch_gsc_performance(
            token_data["access_token"], token_data["site_url"],
            start_date, end_date,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TermosRequest(BaseModel):
    keywords: List[str]
    geo: str = "BR"
    timeframe: str = "today 3-m"


class LookupTermRequest(BaseModel):
    term: str
    geo: str = "BR"
    timeframe: str = "today 3-m"


@app.post("/api/termos/trends")
async def search_trends(payload: TermosRequest, user: dict = Depends(get_current_user)):
    """Fetch Google Trends data for keywords (max 5)"""
    if len(payload.keywords) > 5:
        raise HTTPException(status_code=400, detail="Máximo de 5 termos por consulta")
    if len(payload.keywords) == 0:
        raise HTTPException(status_code=400, detail="Informe pelo menos 1 termo")
    
    from app.integrations.searchapi_client import fetch_trends
    try:
        data = await fetch_trends(payload.keywords, payload.geo, payload.timeframe)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/termos/trending")
async def termos_trending(user: dict = Depends(get_current_user)):
    """
    Top 6 pesquisas em alta no Brasil (últimas 24h) via SearchAPI
    engine=google_trends_trending_now. Não persiste nada.
    """
    from app.integrations.searchapi_client import fetch_trending_now

    return await fetch_trending_now(geo="BR", time_window="past_24_hours", limit=6)


@app.post("/api/termos/lookup")
async def lookup_termo(payload: LookupTermRequest, user: dict = Depends(get_current_user)):
    """
    Consulta um termo no Google Trends (só leitura — não salva em user_search_terms).
    """
    from app.integrations.searchapi_client import fetch_trends, classify_search_chance

    term_text = (payload.term or "").strip()
    if len(term_text) < 2:
        raise HTTPException(status_code=400, detail="Termo deve ter no mínimo 2 caracteres")
    if len(term_text) > 100:
        raise HTTPException(status_code=400, detail="Termo deve ter no máximo 100 caracteres")

    geo = (payload.geo or "BR").upper().strip()
    timeframe = payload.timeframe or "today 3-m"

    data = await fetch_trends([term_text], geo, timeframe)
    if data.get("error") and not (data.get("trends") or {}).get(term_text):
        raise HTTPException(status_code=503, detail=data["error"])

    trends = data.get("trends", {}).get(term_text, {})
    related = data.get("related", {}).get(term_text, {}) or {"top": [], "rising": []}
    current = int(trends.get("current") or 0)
    average = float(trends.get("average") or 0)
    related_top = related.get("top") or []
    chance = classify_search_chance(current, len(related_top))

    return {
        "term": term_text,
        "geo": geo,
        "timeframe": timeframe,
        "chance": chance,
        "current_interest": current,
        "average_interest": average,
        "peak_interest": int(trends.get("peak") or 0),
        "trend": trends.get("trend") or "down",
        "searches_per_month": str(int(average * 224)) if average else "0",
        "conversion_estimate": f"{min(round(current * 0.12, 1), 15.0)}%" if current else "0%",
        "related": related,
        "warning": data.get("error"),
    }


class AddTermRequest(BaseModel):
    term: str


@app.get("/api/termos")
async def list_termos(user: dict = Depends(get_current_user)):
    """Lista termos de pesquisa do usuário com dados do último snapshot"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])
    terms = await db.list_search_terms(user["user_id"])

    # Enriquecer cada termo com dados do snapshot
    from app.integrations.searchapi_client import classify_search_chance
    enriched = []
    for t in terms:
        snap = await db.get_latest_term_snapshot(str(t["id"]))
        iot = snap.get("interest_over_time", {}) if snap else {}
        related = snap.get("related_queries", {}) if snap else {}
        current = iot.get("current", 0)
        average = iot.get("average", 0)
        related_count = len(related.get("top", []))
        chance = classify_search_chance(current, related_count)

        enriched.append({
            **t,
            "chance": chance,
            "current_interest": current,
            "average_interest": average,
            "searches_per_month": str(int(average * 224)) if average else "0",
            "conversion_estimate": f"{min(round(current * 0.12, 1), 15.0)}%" if current else "0%",
            "snapshot": snap,
        })

    return {"terms": enriched, "count": len(enriched), "max": 5}


@app.post("/api/termos")
async def add_termo(payload: AddTermRequest, user: dict = Depends(get_current_user)):
    """Adiciona um novo termo de pesquisa (max 5)"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])

    term_text = payload.term.strip()
    if not term_text or len(term_text) < 2:
        raise HTTPException(status_code=400, detail="Termo deve ter no mínimo 2 caracteres")
    if len(term_text) > 100:
        raise HTTPException(status_code=400, detail="Termo deve ter no máximo 100 caracteres")

    count = await db.count_search_terms(user["user_id"])
    if count >= 5:
        raise HTTPException(status_code=400, detail="Limite de 5 termos atingido. Remova um antes de adicionar.")

    # Verificar duplicata
    existing = await db.list_search_terms(user["user_id"])
    for e in existing:
        if e.get("term", "").lower() == term_text.lower():
            raise HTTPException(status_code=409, detail="Esse termo já está cadastrado")

    term = await db.create_search_term(user["user_id"], term_text)

    # Buscar dados do SearchAPI imediatamente
    trends_error = None
    try:
        from app.integrations.searchapi_client import fetch_trends
        data = await fetch_trends([term_text], "BR", "today 3-m")
        
        if data.get("error"):
            trends_error = data["error"]
            logger.warning(f"[termos] SearchAPI error for '{term_text}': {trends_error}")
        
        trends = data.get("trends", {}).get(term_text, {})
        related = data.get("related", {}).get(term_text, {})
        
        if trends:
            await db.save_term_snapshot(str(term["id"]), user["user_id"], trends, related)
        else:
            logger.warning(f"[termos] No trends data for '{term_text}'  - snapshot not saved")
            trends_error = trends_error or "Google Trends não retornou dados. Tente atualizar mais tarde."
    except Exception as e:
        logger.error(f"[termos] Exception fetching trends for '{term_text}': {e}")
        trends_error = str(e)

    result = {"term": term, "message": "Termo adicionado com sucesso"}
    if trends_error:
        result["trends_warning"] = trends_error
    return result


@app.delete("/api/termos/{term_id}")
async def remove_termo(term_id: str, user: dict = Depends(get_current_user)):
    """Remove um termo de pesquisa"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])

    t = await db.get_search_term(term_id, user["user_id"])
    if not t:
        raise HTTPException(status_code=404, detail="Termo não encontrado")

    await db.delete_search_term(term_id, user["user_id"])
    return {"message": "Termo removido"}


@app.post("/api/termos/refresh")
async def refresh_termos(user: dict = Depends(get_current_user)):
    """Atualiza snapshots de todos os termos do usuário"""
    from app.supabase_client import get_supabase_for_user
    from app.integrations.searchapi_client import fetch_trends
    db = get_supabase_for_user(user["token"])

    terms = await db.list_search_terms(user["user_id"])
    if not terms:
        raise HTTPException(status_code=400, detail="Nenhum termo cadastrado")

    keywords = [t["term"] for t in terms]
    data = await fetch_trends(keywords, "BR", "today 3-m")

    if data.get("error"):
        logger.warning(f"[termos/refresh] SearchAPI error: {data['error']}")

    updated = 0
    for t in terms:
        kw = t["term"]
        trends = data.get("trends", {}).get(kw, {})
        related = data.get("related", {}).get(kw, {})
        if trends:
            await db.save_term_snapshot(str(t["id"]), user["user_id"], trends, related)
            updated += 1
        else:
            logger.warning(f"[termos/refresh] No data for term '{kw}'")

    result = {"updated": updated, "total": len(terms)}
    if data.get("error"):
        result["warning"] = f"Google Trends retornou erro: {data['error']}"
    if updated == 0:
        result["warning"] = result.get("warning", "") + " Nenhum dado atualizado. O Google pode estar bloqueando requisições do servidor."
    return result


@app.post("/api/historico/snapshot")
async def create_daily_snapshot(user: dict = Depends(get_current_user)):
    """Puxa dados do GSC e salva snapshot do dia"""
    from app.supabase_client import get_supabase_for_user
    from app.integrations.gsc import get_gsc_tokens, fetch_gsc_overview
    db = get_supabase_for_user(user["token"])

    try:
        token_data = await get_gsc_tokens(user["user_id"])
    except Exception as e:
        logger.warning(f"[historico/snapshot] GSC tokens lookup failed: {e}")
        raise HTTPException(status_code=400, detail="GSC não conectado. Conecte o Google Search Console primeiro.")

    if not token_data:
        raise HTTPException(status_code=400, detail="GSC não conectado")

    try:
        overview = await fetch_gsc_overview(token_data["access_token"], token_data["site_url"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dados do GSC: {e}")

    from datetime import datetime as dt
    snapshot = await db.save_daily_snapshot(user["user_id"], {
        "date": dt.utcnow().strftime("%Y-%m-%d"),
        "impressions": overview.get("impressions", 0),
        "clicks": overview.get("clicks", 0),
        "ctr": overview.get("ctr", 0),
        "position_avg": overview.get("position", 0),
        "pages_count": overview.get("unique_pages", 0),
    })

    return {"snapshot": snapshot, "message": "Snapshot salvo com sucesso"}


@app.get("/api/historico")
async def list_historico(days: int = 30, user: dict = Depends(get_current_user)):
    """Retorna snapshots do usuário (últimos N dias)"""
    from app.supabase_client import get_supabase_for_user
    db = get_supabase_for_user(user["token"])

    if days not in (30, 60, 90):
        days = 30

    snapshots = await db.list_daily_snapshots(user["user_id"], days)
    return {"snapshots": snapshots, "days": days, "count": len(snapshots)}


from pydantic import BaseModel as PydanticBaseModel
from typing import List as TypeList


class ShopifyConnectRequest(PydanticBaseModel):
    shop_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None


class ShopifyAuthStartRequest(PydanticBaseModel):
    """Inicia OAuth Shopify. O domínio da loja é obrigatório (diferente da Nuvemshop)."""
    shop: str


class ShopifyOptimizeRequest(PydanticBaseModel):
    optimize_title: bool = True
    optimize_description: bool = True
    optimize_seo_title: bool = True
    optimize_seo_description: bool = True
    optimize_image_alts: bool = True
    generate_faq: bool = True
    generate_rich_description: bool = False
    generate_tags: bool = True
    target_keyword: Optional[str] = None
    recommended_actions: Optional[List[str]] = None


class ProposalActionRequest(PydanticBaseModel):
    proposal_ids: TypeList[str]
    action: str  # 'approve', 'reject', 'apply'


# Cache global do cliente Shopify (em produção, usar Redis ou similar)
_shopify_clients: Dict[str, Any] = {}


def get_shopify_client(shop_url: str) -> Any:
    """Retorna cliente Shopify do cache"""
    return _shopify_clients.get(shop_url)


async def get_or_restore_shopify_client(shop_url: str, user: dict) -> Any:
    """Retorna cliente do cache (validando propriedade) ou reconstrói a partir do banco de dados"""
    cached = get_shopify_client(shop_url)
    if cached:
        # Cache sem dono ou de outro usuário nunca é reutilizado.
        if cached.get("user_id") != user["user_id"]:
            return None
        return cached

    # Tentar reconstruir a partir do user_integrations (RLS via token do usuário)
    try:
        from app.supabase_client import get_supabase_for_user
        db = get_supabase_for_user(user["token"])
        integration = await db.get_integration(user["user_id"])
        if integration and integration.get("access_token") and integration.get("store_url"):
            stored_url = integration["store_url"]
            # Normalize for comparison
            norm = lambda u: u.replace("https://", "").replace("http://", "").rstrip("/")
            if norm(stored_url) == norm(shop_url):
                from app.integrations.shopify import create_shopify_client
                from app.integrations.shopify_optimizer import ShopifySEOOptimizer

                client = create_shopify_client(
                    shop_url=stored_url,
                    access_token=integration["access_token"],
                )
                optimizer = ShopifySEOOptimizer(client)
                set_shopify_client(shop_url, client, optimizer, user["user_id"])
                return _shopify_clients.get(shop_url)
    except Exception as e:
        logger.warning(f"Failed to restore Shopify client from DB: {e}")

    return None


def set_shopify_client(shop_url: str, client: Any, optimizer: Any, user_id: str = None):
    """Armazena cliente Shopify no cache, associado ao usuário dono da conexão"""
    _shopify_clients[shop_url] = {"client": client, "optimizer": optimizer, "user_id": user_id}


async def _mark_pages_optimized(db, user_id: str, proposals_data: list, resolve_url) -> None:
    """
    Best-effort: para cada (content_type, product_id) distinto nas propostas
    efetivamente aplicadas, resolve a URL pública do item e marca como
    'approved' as tasks pendentes da página correspondente (do scan genérico
    de pages/seo_tasks) — sem isso, o selo '✓ Otimizado' e o filtro
    'Já Otimizados' do Dashboard nunca refletem uma otimização real aplicada
    via IA (só o rescan completo, ao não detectar mais a issue, a remove da
    lista — mas nunca a marca como otimizada).

    Cobre apenas content_type in ("product", "category") — comum às 4
    integrações. Shopify também tem "collection"/"page"/"article" com nomes de
    método e assinaturas diferentes; fora do escopo deste fix (gap conhecido).

    resolve_url(content_type, product_id) -> Optional[str]. Nunca lança —
    qualquer falha aqui é apenas logada, não deve interromper o apply.
    """
    if not proposals_data:
        return
    try:
        sites = await db.list_sites_for_user(user_id, limit=10)
        integration_sites = [s for s in sites if s.get("platform") in INTEGRATION_PLATFORMS]
        if not integration_sites:
            return
        site_id = str(integration_sites[0]["id"])
    except Exception as e:
        logger.warning(f"_mark_pages_optimized: falha ao localizar site: {e}")
        return

    seen = set()
    for p in proposals_data:
        content_type = (p.get("content_type") or "product") if isinstance(p, dict) else "product"
        product_id = p.get("product_id") if isinstance(p, dict) else None
        if content_type not in ("product", "category") or product_id is None:
            continue
        key = (content_type, product_id)
        if key in seen:
            continue
        seen.add(key)
        try:
            url = await resolve_url(content_type, product_id)
            if not url:
                continue
            page = await db.find_page_by_url(site_id, url)
            if page:
                await db.approve_pending_tasks_for_page(str(page["id"]))
        except Exception as e:
            logger.warning(f"_mark_pages_optimized: falha para {content_type}/{product_id}: {e}")


async def _initial_scan(_db, _site_id: str, _base_url: str):
    """Auto-scan inicial após conectar uma loja (onboarding, roda em background)."""
    from app.services import ScanInProgressError
    try:
        service = get_scan_service(_db)
        result = await service.run_scan(_site_id, max_pages=30)
        logger.info(f"[onboarding] Scan inicial concluído para {_base_url}: {result['pages_scanned']} páginas")
    except ScanInProgressError as e:
        logger.info(f"[onboarding] Scan inicial pulado (já em andamento): {e}")
    except Exception as e:
        logger.warning(f"[onboarding] Scan inicial falhou: {e}")


@app.post("/api/shopify/auth")
async def shopify_auth_start(payload: ShopifyAuthStartRequest, user: dict = Depends(get_current_user)):
    """
    Inicia OAuth Shopify (authorization code grant / offline token).
    Retorna auth_url para redirecionar o lojista à tela de instalação da Shopify.
    Requer o domínio da loja (ex.: minha-loja ou minha-loja.myshopify.com).
    """
    from app.integrations.shopify import ShopifyOAuth, _shopify_oauth_states
    from app.supabase_client import get_supabase_for_user

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{backend_url}/api/shopify/oauth-redirect"

    try:
        result = ShopifyOAuth.generate_auth_url(payload.shop, redirect_uri)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result["state"] in _shopify_oauth_states:
        _shopify_oauth_states[result["state"]]["user_id"] = user["user_id"]
        _shopify_oauth_states[result["state"]]["token"] = user["token"]

    try:
        db = get_supabase_for_user(user["token"])
        await db.save_oauth_state(result["state"], user["user_id"], user["token"])
    except Exception as e:
        logger.warning(f"[Shopify OAuth] Falha ao persistir state no banco: {e}")

    return {
        "auth_url": result["auth_url"],
        "state": result["state"],
        "shop": result["shop"],
    }


@app.get("/api/shopify/oauth-redirect")
async def shopify_oauth_redirect(
    request: Request,
    code: str = None,
    shop: str = None,
    state: str = None,
    hmac: str = None,
    error: str = None,
    error_description: str = None,
):
    """
    Callback OAuth — a Shopify redireciona para cá após autorização.
    Valida HMAC, troca o code por access token offline e salva a integração.
    """
    from urllib.parse import quote
    from fastapi.responses import RedirectResponse
    from app.integrations.shopify import (
        ShopifyOAuth,
        create_shopify_client,
        normalize_shop_domain,
        _shopify_oauth_states,
    )
    from app.integrations.shopify_optimizer import ShopifySEOOptimizer

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080").rstrip("/") + "/analise"

    if error:
        detail = quote(error_description or error)
        logger.error(f"[Shopify OAuth] Erro do provedor: {error}")
        return RedirectResponse(url=f"{frontend_url}?error={detail}")

    if not code or not shop or not state:
        return RedirectResponse(url=f"{frontend_url}?error=missing_oauth_params")

    # Validar HMAC com todos os query params (exceto signature legado se presente)
    query_params = {k: v for k, v in request.query_params.items() if k != "signature"}
    try:
        if not ShopifyOAuth.verify_hmac(query_params):
            logger.error("[Shopify OAuth] HMAC inválido no callback")
            return RedirectResponse(url=f"{frontend_url}?error=invalid_hmac")
    except ValueError as e:
        logger.error(f"[Shopify OAuth] Config OAuth ausente no callback: {e}")
        return RedirectResponse(url=f"{frontend_url}?error=oauth_not_configured")

    state_data = _shopify_oauth_states.get(state) if state else None
    user_id = state_data.get("user_id") if state_data else None
    user_token = state_data.get("token") if state_data else None

    if not user_id and state:
        try:
            from app.supabase_client import SupabaseClient
            db = SupabaseClient()
            persisted = await db.get_oauth_state(state)
            if persisted:
                user_id = persisted["user_id"]
                user_token = persisted["user_token"]
                await db.delete_oauth_state(state)
        except Exception as db_err:
            logger.warning(f"[Shopify OAuth] Falha ao recuperar state do banco: {db_err}")

    try:
        shop_domain = normalize_shop_domain(shop)
        result = await ShopifyOAuth.exchange_code(shop_domain, code, state)

        if not result.get("success"):
            return RedirectResponse(url=f"{frontend_url}?error=exchange_failed")

        access_token = result["access_token"]
        shop_base_url = f"https://{shop_domain}"

        client = create_shopify_client(shop_url=shop_domain, access_token=access_token)
        optimizer = ShopifySEOOptimizer(client)
        connection_result = await client.test_connection()
        if not connection_result.get("success"):
            return RedirectResponse(url=f"{frontend_url}?error=connection_failed")

        store_name = connection_result.get("shop_name") or shop_domain

        if user_id:
            set_shopify_client(shop_base_url, client, optimizer, user_id)
        else:
            logger.warning(
                f"[Shopify OAuth] state perdido — client NÃO cacheado para shop={shop_domain}"
            )

        if user_id and user_token:
            from app.supabase_client import get_supabase_for_user
            db = get_supabase_for_user(user_token)
            existing = await db.list_sites_for_user(user_id, limit=10)
            integration_sites = [s for s in existing if s.get("platform") in INTEGRATION_PLATFORMS]
            other_platform_connected = any(
                s.get("platform") != "shopify" for s in integration_sites
            )
            if other_platform_connected:
                logger.warning(
                    f"[Shopify OAuth] user_id={user_id} já tem outra integração "
                    f"({[s.get('platform') for s in integration_sites]}) — ignorando OAuth."
                )
                return RedirectResponse(url=f"{frontend_url}?error=already_connected")

            created_site = None
            if not integration_sites:
                await _delete_url_only_sites(db, user_id)
                created_site = await db.create_site(
                    base_url=shop_base_url,
                    platform="shopify",
                    user_id=user_id,
                )

            await db.save_integration(
                user_id=user_id,
                platform="shopify",
                store_url=shop_domain,
                access_token=access_token,
                store_name=store_name,
                metadata={"auth": "oauth", "scope": result.get("scope", "")},
            )

            if created_site and created_site.get("id"):
                asyncio.create_task(_initial_scan(db, str(created_site["id"]), shop_base_url))

        encoded_name = quote(store_name) if store_name else ""
        return RedirectResponse(
            url=(
                f"{frontend_url}?connected=true&platform=shopify"
                f"&store_id={quote(shop_domain)}&store_name={encoded_name}"
            )
        )
    except Exception as e:
        logger.error(f"[Shopify OAuth] Erro no callback: {e}", exc_info=True)
        return RedirectResponse(url=f"{frontend_url}?error={quote(str(e))}")


@app.post("/api/shopify/connect")
async def shopify_connect(payload: ShopifyConnectRequest, user: dict = Depends(get_current_user)):
    """
    Conecta uma loja Shopify com access token manual (app customizado legado).
    Preferir o fluxo OAuth em POST /api/shopify/auth.
    Limite: 1 loja por usuário.
    """
    try:
        # Verificar se já tem loja real conectada (Shopify/Nuvemshop)
        from app.supabase_client import get_supabase_for_user
        db = get_supabase_for_user(user["token"])
        existing = await db.list_sites_for_user(user["user_id"], limit=10)
        integration_sites = [s for s in existing if s.get("platform") in INTEGRATION_PLATFORMS]
        if integration_sites:
            raise HTTPException(
                status_code=409,
                detail="Você já possui uma loja conectada. Desconecte a atual antes de conectar outra."
            )
        # Remover sites criados apenas para análise por URL para liberar o slot
        await _delete_url_only_sites(db, user["user_id"])
        
        from app.integrations.shopify import create_shopify_client
        from app.integrations.shopify_optimizer import ShopifySEOOptimizer
        
        client = create_shopify_client(
            shop_url=payload.shop_url,
            api_key=payload.api_key,
            api_secret=payload.api_secret,
            access_token=payload.access_token,
        )
        
        # Testar conexão
        connection_result = await client.test_connection()
        
        if not connection_result.get("success"):
            return format_error(
                f"Falha ao conectar: {connection_result.get('error', 'Erro desconhecido')}",
                status_code=400
            )
        
        # Salvar no Supabase com user_id
        store_name = connection_result.get("shop", {}).get("name", payload.shop_url) if isinstance(connection_result.get("shop"), dict) else payload.shop_url
        shop_base_url = payload.shop_url.strip().rstrip("/")
        if not shop_base_url.startswith("http"):
            shop_base_url = f"https://{shop_base_url}"
        created_site = await db.create_site(
            base_url=shop_base_url,
            platform="shopify",
            user_id=user["user_id"],
        )
        
        # Salvar credenciais no user_integrations para reconexão automática
        await db.save_integration(
            user_id=user["user_id"],
            platform="shopify",
            store_url=payload.shop_url,
            access_token=payload.access_token or payload.api_key,
            store_name=store_name,
            metadata={"api_key": payload.api_key, "api_secret": payload.api_secret} if payload.api_key else {},
        )
        
        # Criar otimizador e armazenar em cache
        # Chave normalizada (shop_base_url, com https://) — a mesma usada por
        # site.base_url e, portanto, pelo disconnect ao limpar o cache. Usar a
        # entrada crua (payload.shop_url) aqui deixava uma entrada órfã que o
        # disconnect nunca encontrava, acessível a qualquer usuário que soubesse
        # o domínio da loja (não é segredo) — ver fix de isolamento acima.
        optimizer = ShopifySEOOptimizer(client)
        set_shopify_client(shop_base_url, client, optimizer, user["user_id"])

        # Auto-scan inicial após conectar (background, não bloqueia resposta).
        # Toda conexão bem-sucedida aqui é nova (409 acima impede reconexão).
        if created_site.get("id"):
            asyncio.create_task(_initial_scan(db, str(created_site["id"]), shop_base_url))

        return {
            "success": True,
            "message": "Conectado com sucesso!",
            "shop": connection_result,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/products")
async def shopify_list_products(shop_url: str, limit: int = 500, user: dict = Depends(get_current_user)):
    """Lista produtos da loja Shopify conectada (paginado, busca todos até o limite)."""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada. Use /api/shopify/connect primeiro.")
    
    try:
        client = cached["client"]
        products = await client.get_all_products(max_items=limit)
        return {
            "products": [p.model_dump() for p in products],
            "total": len(products),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/product/{product_id}/analyze")
async def shopify_analyze_product(shop_url: str, product_id: int, user: dict = Depends(get_current_user)):
    """
    Analisa um produto e retorna problemas de SEO detectados.
    NÃO gera otimizações - apenas diagnóstico.
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        analysis = await optimizer.analyze_product(product_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shopify/product/{product_id}/optimize")
async def shopify_optimize_product(
    shop_url: str, 
    product_id: int, 
    payload: ShopifyOptimizeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Gera propostas de otimização SEO para um produto.
    
    As propostas NÃO são aplicadas automaticamente.
    O usuário deve aprovar cada proposta antes da aplicação.
    
    Returns:
        Lista de propostas de otimização pendentes
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        opts = payload
        if payload.recommended_actions:
            from app.product_diagnosis import actions_to_optimize_options
            mapped = actions_to_optimize_options(payload.recommended_actions)
            proposals = await optimizer.generate_optimizations(
                product_id=product_id,
                optimize_title=mapped.get("optimize_title", False),
                optimize_description=mapped.get("optimize_description", False),
                optimize_seo_title=mapped.get("optimize_seo_title", False),
                optimize_seo_description=mapped.get("optimize_seo_description", False),
                optimize_image_alts=mapped.get("optimize_image_alts", False),
                generate_faq=False,
                generate_rich_description=False,
                generate_tags=mapped.get("generate_tags", False),
                target_keyword=payload.target_keyword,
                user=user,
            )
        else:
            proposals = await optimizer.generate_optimizations(
                product_id=product_id,
                optimize_title=opts.optimize_title,
                optimize_description=opts.optimize_description,
                optimize_seo_title=opts.optimize_seo_title,
                optimize_seo_description=opts.optimize_seo_description,
                optimize_image_alts=opts.optimize_image_alts,
                generate_faq=opts.generate_faq,
                generate_rich_description=opts.generate_rich_description,
                generate_tags=opts.generate_tags,
                target_keyword=opts.target_keyword,
                user=user,
            )
        
        return {
            "success": True,
            "product_id": product_id,
            "proposals": [p.model_dump() for p in proposals],
            "total_proposals": len(proposals),
            "message": f"Geradas {len(proposals)} propostas de otimização. Aprove as desejadas antes de aplicar.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/collections")
async def shopify_list_collections(shop_url: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Lista coleções da loja Shopify"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        collections = await client.get_collections(limit=limit)
        return {
            "collections": [c.model_dump() if hasattr(c, 'model_dump') else c for c in collections],
            "total": len(collections),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/collection/{collection_id}/analyze")
async def shopify_analyze_collection(shop_url: str, collection_id: int, collection_type: str = "custom", user: dict = Depends(get_current_user)):
    """Analisa uma coleção e retorna problemas de SEO"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        analysis = await optimizer.analyze_collection(collection_id, collection_type)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shopify/collection/{collection_id}/optimize")
async def shopify_optimize_collection(shop_url: str, collection_id: int, collection_type: str = "custom", user: dict = Depends(get_current_user)):
    """Gera propostas de otimização para uma coleção"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        proposals = await optimizer.generate_collection_optimizations(collection_id, collection_type)
        return {
            "success": True,
            "collection_id": collection_id,
            "proposals": [p.model_dump() for p in proposals],
            "total_proposals": len(proposals),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/pages")
async def shopify_list_pages(shop_url: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Lista páginas institucionais da loja"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        pages = await client.get_pages(limit=limit)
        return {
            "pages": [p.model_dump() if hasattr(p, 'model_dump') else p for p in pages],
            "total": len(pages),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/page/{page_id}/analyze")
async def shopify_analyze_page(shop_url: str, page_id: int, user: dict = Depends(get_current_user)):
    """Analisa uma página institucional"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        analysis = await optimizer.analyze_page(page_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shopify/page/{page_id}/optimize")
async def shopify_optimize_page(shop_url: str, page_id: int, user: dict = Depends(get_current_user)):
    """Gera propostas de otimização para uma página"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        proposals = await optimizer.generate_page_optimizations(page_id)
        return {
            "success": True,
            "page_id": page_id,
            "proposals": [p.model_dump() for p in proposals],
            "total_proposals": len(proposals),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/blogs")
async def shopify_list_blogs(shop_url: str, user: dict = Depends(get_current_user)):
    """Lista blogs da loja"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        blogs = await client.get_blogs()
        return {
            "blogs": [b.model_dump() if hasattr(b, 'model_dump') else b for b in blogs],
            "total": len(blogs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/articles")
async def shopify_list_articles(shop_url: str, blog_id: int = None, limit: int = 50, user: dict = Depends(get_current_user)):
    """Lista artigos de blog"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        articles = await client.get_articles(blog_id=blog_id, limit=limit)
        return {
            "articles": [a.model_dump() if hasattr(a, 'model_dump') else a for a in articles],
            "total": len(articles),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/article/{blog_id}/{article_id}/analyze")
async def shopify_analyze_article(shop_url: str, blog_id: int, article_id: int, user: dict = Depends(get_current_user)):
    """Analisa um artigo de blog"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        analysis = await optimizer.analyze_article(blog_id, article_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shopify/article/{blog_id}/{article_id}/optimize")
async def shopify_optimize_article(shop_url: str, blog_id: int, article_id: int, user: dict = Depends(get_current_user)):
    """Gera propostas de otimização para um artigo"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        proposals = await optimizer.generate_article_optimizations(blog_id, article_id)
        return {
            "success": True,
            "article_id": article_id,
            "proposals": [p.model_dump() for p in proposals],
            "total_proposals": len(proposals),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/proposals")
async def shopify_list_proposals(shop_url: str, product_id: int = None, status: str = None, user: dict = Depends(get_current_user)):
    """
    Lista propostas de otimização.
    
    Args:
        shop_url: URL da loja
        product_id: Filtrar por produto (opcional)
        status: Filtrar por status: pending, approved, applied, rejected, rolled_back
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    
    if status == "pending":
        proposals = client.get_pending_proposals(product_id)
    else:
        proposals = client.get_all_proposals()
        if product_id:
            proposals = [p for p in proposals if p.product_id == product_id]
        if status:
            proposals = [p for p in proposals if p.status.value == status]
    
    return {
        "proposals": [p.model_dump() for p in proposals],
        "total": len(proposals),
    }


@app.post("/api/shopify/proposals/approve")
async def shopify_approve_proposals(shop_url: str, proposal_ids: TypeList[str] = Query(...), user: dict = Depends(get_current_user)):
    """
    Aprova propostas de otimização.
    As mudanças ainda NÃO são aplicadas - apenas marcadas como aprovadas.
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    approved = 0
    errors = []
    
    for pid in proposal_ids:
        try:
            await client.approve_proposal(pid)
            approved += 1
        except Exception as e:
            errors.append(f"{pid}: {str(e)}")
    
    return {
        "success": len(errors) == 0,
        "approved": approved,
        "errors": errors if errors else None,
        "message": f"{approved} proposta(s) aprovada(s). Use /api/shopify/proposals/apply para aplicar.",
    }


@app.post("/api/shopify/proposals/reject")
async def shopify_reject_proposals(shop_url: str, proposal_ids: TypeList[str] = Query(...), user: dict = Depends(get_current_user)):
    """Rejeita propostas de otimização"""
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    rejected = 0
    errors = []
    
    for pid in proposal_ids:
        try:
            await client.reject_proposal(pid)
            rejected += 1
        except Exception as e:
            errors.append(f"{pid}: {str(e)}")
    
    return {
        "success": len(errors) == 0,
        "rejected": rejected,
        "errors": errors if errors else None,
    }


class ApplyProposalsRequest(BaseModel):
    proposals: Optional[List[dict]] = None


class RollbackDirectRequest(BaseModel):
    record: Dict[str, Any]


@app.post("/api/shopify/proposals/apply")
async def shopify_apply_proposals(shop_url: str, product_id: int = None, body: Optional[ApplyProposalsRequest] = None, user: dict = Depends(get_current_user)):
    """
    Aplica TODAS as propostas aprovadas na loja Shopify.
    
    Cria registros de rollback para permitir reversão posterior.
    Se 'proposals' for enviado no body, aplica direto sem depender de estado em memória.
    
    Args:
        shop_url: URL da loja
        product_id: Aplicar apenas para um produto específico (opcional)
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    optimizer = cached.get("optimizer")
    
    try:
        if body and body.proposals:
            result = await client.apply_proposals_direct(body.proposals)
        else:
            result = await client.apply_approved_proposals(product_id)

        # Persiste contador de otimizações aplicadas no banco (sobrevive a cold starts)
        try:
            from app.supabase_client import get_supabase_for_user
            db_for_count = get_supabase_for_user(user["token"])
            await db_for_count.increment_applied_count(user["user_id"], result.get("applied", 0))

            if body and body.proposals:
                async def _resolve_url(content_type: str, pid: int):
                    if content_type == "product":
                        return (await client.get_product(pid)).url
                    return None
                await _mark_pages_optimized(db_for_count, user["user_id"], body.proposals, _resolve_url)
        except Exception as ce:
            logger.warning(f"increment_applied_count (shopify) falhou: {ce}")

        return {
            **result,
            "message": f"{result.get('applied', 0)} otimização(ões) aplicada(s) com sucesso. Rollback disponível se necessário.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shopify/rollback")
async def shopify_list_rollbacks(shop_url: str, product_id: int = None, user: dict = Depends(get_current_user)):
    """
    Lista mudanças disponíveis para rollback.
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    records = client.get_rollback_records(product_id)
    
    return {
        "records": [r.model_dump() for r in records],
        "rollback_records": [r.model_dump() for r in records],
        "total": len(records),
    }


# IMPORTANTE: Rotas específicas ANTES de rotas com parâmetros para evitar conflito
@app.post("/api/shopify/rollback/direct")
async def shopify_rollback_direct(shop_url: str, body: RollbackDirectRequest, user: dict = Depends(get_current_user)):
    """
    Reverte uma alteração diretamente a partir dos dados do frontend.
    Funciona após cold starts (não depende de estado em memória).
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    try:
        result = await client.rollback_direct(body.record)
        return {**result, "message": "Mudança revertida com sucesso!"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"shopify_rollback_direct falhou: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shopify/rollback/all")
async def shopify_rollback_all(shop_url: str, user: dict = Depends(get_current_user)):
    """
    ROLLBACK TOTAL: Reverte TODAS as mudanças de TODOS os produtos.
    
    ATENCAO: ATENÇÃO: Esta operação reverte todas as otimizações aplicadas.
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    
    try:
        result = await client.rollback_all()
        return {
            **result,
            "message": f"ROLLBACK COMPLETO: {result['rolled_back']} mudança(s) revertida(s)",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shopify/rollback/product/{product_id}")
async def shopify_rollback_product(shop_url: str, product_id: int, user: dict = Depends(get_current_user)):
    """
    Reverte TODAS as mudanças de um produto específico.
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    
    try:
        result = await client.rollback_product(product_id)
        return {
            **result,
            "message": f"{result['rolled_back']} mudança(s) revertida(s) para o produto {product_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shopify/rollback/{rollback_id}")
async def shopify_rollback_single(shop_url: str, rollback_id: str, user: dict = Depends(get_current_user)):
    """
    Reverte uma única mudança específica.
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    
    try:
        result = await client.rollback_single(rollback_id)
        return {
            **result,
            "message": "Mudança revertida com sucesso!",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shopify/optimize-all")
async def shopify_optimize_all_products(
    shop_url: str, 
    limit: int = 50,
    payload: ShopifyOptimizeRequest = None,
    user: dict = Depends(get_current_user)
):
    """
    Gera propostas de otimização para todos os produtos.
    
    As propostas NÃO são aplicadas automaticamente.
    """
    cached = await get_or_restore_shopify_client(shop_url, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        result = await optimizer.optimize_all_products(limit=limit, auto_approve=False)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Cache global do cliente Nuvemshop
_nuvemshop_clients: Dict[str, Any] = {}


def get_nuvemshop_client(store_id: str) -> Any:
    """Retorna cliente Nuvemshop do cache"""
    return _nuvemshop_clients.get(store_id)


def set_nuvemshop_client(store_id: str, client: Any, optimizer: Any, user_id: str = None):
    """Armazena cliente Nuvemshop no cache"""
    _nuvemshop_clients[store_id] = {"client": client, "optimizer": optimizer, "user_id": user_id}


async def get_or_restore_nuvemshop_client(store_id: str, user: dict) -> Any:
    """Retorna cliente do cache ou reconstrói a partir do banco de dados"""
    cached = _nuvemshop_clients.get(store_id)
    if cached:
        if cached.get("user_id") != user["user_id"]:
            return None
        return cached
    # Tentar reconstruir a partir do user_integrations
    try:
        from app.supabase_client import get_supabase_for_user
        db = get_supabase_for_user(user["token"])
        integration = await db.get_integration(user["user_id"])
        if integration and integration.get("platform") == "nuvemshop" and integration.get("access_token"):
            from app.integrations.nuvemshop import create_nuvemshop_client
            from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
            client = create_nuvemshop_client(store_id, integration["access_token"])
            optimizer = NuvemshopOptimizer(client)
            set_nuvemshop_client(store_id, client, optimizer, user["user_id"])
            return _nuvemshop_clients.get(store_id)
    except Exception as e:
        logger.warning(f"Failed to restore Nuvemshop client from DB: {e}")
    return None


class NuvemshopTokenConnectRequest(BaseModel):
    access_token: str
    store_id: str


@app.post("/api/nuvemshop/connect-token")
async def nuvemshop_connect_with_token(request: NuvemshopTokenConnectRequest, user: dict = Depends(get_current_user)):
    """
    Conecta diretamente com access_token e store_id.
    Limite: 1 loja por usuário.
    """
    from app.integrations.nuvemshop import create_nuvemshop_client
    from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
    from app.supabase_client import get_supabase_for_user
    
    # Verificar se já tem loja real conectada (Shopify/Nuvemshop)
    db = get_supabase_for_user(user["token"])
    existing = await db.list_sites_for_user(user["user_id"], limit=10)
    integration_sites = [s for s in existing if s.get("platform") in INTEGRATION_PLATFORMS]
    if integration_sites:
        return format_error("Você já possui uma loja conectada. Desconecte a atual antes de conectar outra.", status_code=409)
    # Remover sites criados apenas para análise por URL para liberar o slot
    await _delete_url_only_sites(db, user["user_id"])
    
    logger.debug(f"[Nuvemshop] Conexão direta - store_id: {request.store_id}")
    
    try:
        # Criar cliente
        client = create_nuvemshop_client(request.store_id, request.access_token)
        
        # Testar conexão
        store_info = await client.test_connection()
        
        if not store_info.get("connected"):
            return format_error("Token inválido ou expirado")
        
        # Obter URL real da loja via API
        store_obj = store_info.get("store")
        store_name_val = store_obj.name if store_obj and hasattr(store_obj, 'name') else f"Loja {request.store_id}"
        real_store_url = store_obj.url if store_obj and hasattr(store_obj, 'url') and store_obj.url else f"https://{request.store_id}"
        
        # Salvar no Supabase com user_id (usar URL real da loja)
        created_site = await db.create_site(
            base_url=real_store_url,
            platform="nuvemshop",
            user_id=user["user_id"],
        )

        # Criar optimizer e cachear com user_id
        optimizer = NuvemshopOptimizer(client)
        set_nuvemshop_client(request.store_id, client, optimizer, user["user_id"])
        await db.save_integration(
            user_id=user["user_id"],
            platform="nuvemshop",
            store_url=request.store_id,
            access_token=request.access_token,
            store_name=store_name_val,
        )

        # Auto-scan inicial após conectar (background, não bloqueia resposta).
        # Toda conexão bem-sucedida aqui é nova (409 acima impede reconexão).
        if created_site.get("id"):
            asyncio.create_task(_initial_scan(db, str(created_site["id"]), real_store_url))
        
        logger.debug(f"[Nuvemshop] Conectado - store: {store_info}")
        
        return {
            "success": True,
            "store_id": request.store_id,
            "store": store_info.get("store"),
            "message": "Conectado com sucesso!"
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return format_error(f"Erro ao conectar: {str(e)}")


@app.get("/api/nuvemshop/auth")
async def nuvemshop_auth_start(user: dict = Depends(get_current_user)):
    """
    Inicia fluxo OAuth - retorna URL para redirecionar o usuário.
    O redirect_uri aponta para nosso backend que fará a troca automática.
    Requer autenticação para vincular a loja ao usuário.
    """
    from app.integrations.nuvemshop import NuvemshopOAuth, _oauth_states
    from app.supabase_client import get_supabase_for_user
    
    # URL do backend (usar variável de ambiente em produção)
    # NOTA: Nuvemshop só aceita HTTPS ou localhost
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    backend_callback = f"{backend_url}/api/nuvemshop/oauth-redirect"
    
    result = NuvemshopOAuth.generate_auth_url(backend_callback)
    
    # Armazenar contexto do usuário no state para recuperar no callback
    if result["state"] in _oauth_states:
        _oauth_states[result["state"]]["user_id"] = user["user_id"]
        _oauth_states[result["state"]]["token"] = user["token"]
    
    # Persistir state no Supabase para sobreviver a reinícios do servidor
    try:
        db = get_supabase_for_user(user["token"])
        await db.save_oauth_state(result["state"], user["user_id"], user["token"])
    except Exception as e:
        logger.warning(f"[Nuvemshop OAuth] Falha ao persistir state no banco: {e}")
    
    return {
        "auth_url": result["auth_url"],
        "state": result["state"]
    }


@app.get("/api/nuvemshop/oauth-redirect")
async def nuvemshop_oauth_redirect(code: str = None, state: str = None, error: str = None):
    """
    Callback OAuth - Nuvemshop redireciona para cá após autorização.
    Troca o code por token e redireciona para o frontend já conectado.
    Salva integração no banco com isolamento por usuário.
    """
    from fastapi.responses import RedirectResponse
    from app.integrations.nuvemshop import NuvemshopOAuth, create_nuvemshop_client, _oauth_states
    from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
    
    # URL do frontend (usar variável de ambiente em produção)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080") + "/analise"
    
    # Se houve erro na autorização
    if error:
        logger.error(f"[Nuvemshop OAuth] Erro: {error}")
        return RedirectResponse(url=f"{frontend_url}?error={error}")
    
    if not code:
        logger.debug("[Nuvemshop OAuth] Código não recebido")
        return RedirectResponse(url=f"{frontend_url}?error=no_code")
    
    logger.debug(f"[Nuvemshop OAuth] Recebido code: {code[:10]}..., state: {state[:10] if state else 'None'}...")
    
    # Recuperar contexto do usuário armazenado no state
    state_data = _oauth_states.get(state or "") if state else None
    user_id = state_data.get("user_id") if state_data else None
    user_token = state_data.get("token") if state_data else None
    
    # Fallback: recuperar do Supabase se memória foi perdida (ex: reinício do servidor)
    if not user_id and state:
        try:
            from app.supabase_client import SupabaseClient
            db = SupabaseClient()
            persisted = await db.get_oauth_state(state)
            if persisted:
                user_id = persisted["user_id"]
                user_token = persisted["user_token"]
                logger.info(f"[Nuvemshop OAuth] State recuperado do Supabase para user_id={user_id}")
                # Limpar state usado
                await db.delete_oauth_state(state)
        except Exception as db_err:
            logger.warning(f"[Nuvemshop OAuth] Falha ao recuperar state do banco: {db_err}")
    
    if not user_id:
        logger.warning("[Nuvemshop OAuth] AVISO: Contexto do usuário não encontrado no state (servidor pode ter reiniciado)")
    
    try:
        # Trocar code por token
        result = await NuvemshopOAuth.exchange_code(code, state or "redirect")
        
        logger.debug(f"[Nuvemshop OAuth] Exchange result: {result}")
        
        if result.get("success"):
            store_id = result["store_id"]
            access_token = result["access_token"]
            
            # Criar e cachear o cliente — só quando sabemos o dono (user_id).
            # Sem isso, um cache-hit por store_id (numérico, enumerável) com
            # user_id=None passaria pela checagem de propriedade em
            # get_or_restore_nuvemshop_client (None é falsy), expondo o client
            # com access_token válido a qualquer usuário autenticado.
            client = create_nuvemshop_client(store_id, access_token)
            optimizer = NuvemshopOptimizer(client)
            if user_id:
                set_nuvemshop_client(store_id, client, optimizer, user_id)
            else:
                logger.warning(
                    f"[Nuvemshop OAuth] state perdido — client NÃO cacheado para store_id={store_id} "
                    "(evita expor a loja a outro usuário). Usuário precisará reconectar."
                )

            # Obter info da loja
            store_info = await client.test_connection()
            store_obj = store_info.get("store")
            store_name = store_obj.name if store_obj and hasattr(store_obj, 'name') else ""
            real_store_url = store_obj.url if store_obj and hasattr(store_obj, 'url') and store_obj.url else f"https://{store_id}"
            
            logger.debug(f"[Nuvemshop OAuth] Conectado! store_id={store_id}, name={store_name}, url={real_store_url}")
            
            # Salvar integração no banco se temos contexto do usuário
            if user_id and user_token:
                try:
                    from app.supabase_client import get_supabase_for_user
                    db = get_supabase_for_user(user_token)
                    
                    # Verificar se já tem loja real (Shopify/Nuvemshop/VTEX/LI) conectada —
                    # limite de 1 integração por usuário. save_integration faz upsert por
                    # user_id: gravar a credencial Nuvemshop por cima de uma integração de
                    # OUTRA plataforma já conectada sobrescreveria user_integrations sem
                    # tocar em sites, órfãando a loja antiga (reconexão automática e
                    # disconnect passariam a usar a credencial errada).
                    existing = await db.list_sites_for_user(user_id, limit=10)
                    integration_sites = [s for s in existing if s.get("platform") in INTEGRATION_PLATFORMS]
                    other_platform_connected = any(
                        s.get("platform") != "nuvemshop" for s in integration_sites
                    )
                    if other_platform_connected:
                        logger.warning(
                            f"[Nuvemshop OAuth] user_id={user_id} já tem outra integração "
                            f"conectada ({[s.get('platform') for s in integration_sites]}) — "
                            "ignorando OAuth Nuvemshop para não sobrescrever a integração existente."
                        )
                        return RedirectResponse(url=f"{frontend_url}?error=already_connected")

                    created_site = None
                    if not integration_sites:
                        await _delete_url_only_sites(db, user_id)
                        created_site = await db.create_site(
                            base_url=real_store_url,
                            platform="nuvemshop",
                            user_id=user_id,
                        )

                    # Salvar credenciais para reconexão automática
                    await db.save_integration(
                        user_id=user_id,
                        platform="nuvemshop",
                        store_url=store_id,
                        access_token=access_token,
                        store_name=store_name or f"Loja {store_id}",
                    )

                    # Auto-scan inicial em background (só em NOVA conexão)
                    if created_site and created_site.get("id"):
                        asyncio.create_task(_initial_scan(db, str(created_site["id"]), real_store_url))
                    logger.debug(f"[Nuvemshop OAuth] Integração salva no banco para user_id={user_id}")
                except Exception as db_err:
                    logger.error(f"[Nuvemshop OAuth] Erro ao salvar no banco: {db_err}")
            
            # Redirecionar para frontend com dados de sucesso (URL encode do nome)
            from urllib.parse import quote
            encoded_name = quote(store_name) if store_name else ""
            
            return RedirectResponse(
                url=f"{frontend_url}?connected=true&store_id={store_id}&store_name={encoded_name}"
            )
        else:
            return RedirectResponse(url=f"{frontend_url}?error=exchange_failed")
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[Nuvemshop OAuth] Erro: {str(e)}")
        from urllib.parse import quote
        return RedirectResponse(url=f"{frontend_url}?error={quote(str(e))}")


class NuvemshopManualCodeRequest(BaseModel):
    code: str


@app.post("/api/nuvemshop/exchange-code")
async def nuvemshop_exchange_code_manual(request: NuvemshopManualCodeRequest, user: dict = Depends(get_current_user)):
    """
    Troca authorization code por access_token manualmente.
    Requer autenticação para vincular a loja ao usuário.
    """
    from app.integrations.nuvemshop import NuvemshopOAuth, create_nuvemshop_client
    from app.integrations.nuvemshop_optimizer import NuvemshopOptimizer
    from app.supabase_client import get_supabase_for_user
    
    logger.debug(f"[Nuvemshop] Troca manual de código: {request.code[:10]}...")
    
    try:
        # Trocar código por token (sem validar state neste caso)
        result = await NuvemshopOAuth.exchange_code(request.code, "manual")
        
        logger.debug(f"[Nuvemshop] Exchange result: {result}")
        
        if result.get("success"):
            # Criar e cachear o cliente com user_id
            client = create_nuvemshop_client(result["store_id"], result["access_token"])
            optimizer = NuvemshopOptimizer(client)
            set_nuvemshop_client(result["store_id"], client, optimizer, user["user_id"])
            
            # Obter informações da loja
            store_info = await client.test_connection()
            
            logger.debug(f"[Nuvemshop] Conectado - store_id: {result['store_id']}, store: {store_info}")
            
            # Obter URL real e nome da loja via API
            store_obj = store_info.get("store")
            store_name = store_obj.name if store_obj and hasattr(store_obj, 'name') else f"Loja {result['store_id']}"
            real_store_url = store_obj.url if store_obj and hasattr(store_obj, 'url') and store_obj.url else f"https://{result['store_id']}"
            
            # Salvar no banco com isolamento por usuário (usar URL real da loja)
            db = get_supabase_for_user(user["token"])
            existing = await db.list_sites_for_user(user["user_id"], limit=10)
            integration_sites = [s for s in existing if s.get("platform") in INTEGRATION_PLATFORMS]
            # Limite de 1 integração por usuário — não sobrescreve user_integrations
            # (upsert por user_id) se outra plataforma já está conectada, senão a loja
            # antiga fica órfã (sites intacto, mas credenciais trocadas por baixo dela).
            other_platform_connected = any(
                s.get("platform") != "nuvemshop" for s in integration_sites
            )
            if other_platform_connected:
                logger.warning(
                    f"[Nuvemshop] user_id={user['user_id']} já tem outra integração "
                    f"conectada ({[s.get('platform') for s in integration_sites]}) — "
                    "ignorando troca manual de código para não sobrescrever a integração existente."
                )
                return format_error(
                    "Você já tem outra loja conectada. Desconecte-a antes de conectar uma loja Nuvemshop.",
                    status_code=409,
                )
            created_site = None
            if not integration_sites:
                await _delete_url_only_sites(db, user["user_id"])
                created_site = await db.create_site(
                    base_url=real_store_url,
                    platform="nuvemshop",
                    user_id=user["user_id"],
                )
            await db.save_integration(
                user_id=user["user_id"],
                platform="nuvemshop",
                store_url=result["store_id"],
                access_token=result["access_token"],
                store_name=store_name,
            )

            # Auto-scan inicial em background (só em NOVA conexão)
            if created_site and created_site.get("id"):
                asyncio.create_task(_initial_scan(db, str(created_site["id"]), real_store_url))
            
            return {
                "success": True,
                "store_id": result["store_id"],
                "store": store_info.get("store"),
                "message": "Conectado com sucesso!"
            }
        else:
            return format_error("Falha na troca do código")
    
    except ValueError as e:
        return format_error(str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return format_error(f"Erro ao trocar código: {str(e)}", status_code=500)


@app.get("/api/nuvemshop/products")
async def nuvemshop_list_products(store_id: str, limit: int = 500, user: dict = Depends(get_current_user)):
    """Lista produtos da loja Nuvemshop (paginado, busca todos até o limite)."""
    from app.integrations.nuvemshop import NuvemshopAuthError
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        logger.error(f"[Nuvemshop Products] Cliente não encontrado/restaurado para store_id={store_id}, user_id={user.get('user_id')}")
        raise HTTPException(status_code=400, detail="Loja não conectada. Reconecte sua loja Nuvemshop.")
    
    try:
        client = cached["client"]
        products = await client.get_all_products(max_items=limit)
        return {
            "products": [p.model_dump() for p in products],
            "total": len(products)
        }
    except NuvemshopAuthError:
        raise HTTPException(status_code=401, detail="Token Nuvemshop inválido ou expirado. Reconecte sua loja.")
    except Exception as e:
        logger.error(f"[Nuvemshop Products] Erro store_id={store_id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@app.get("/api/nuvemshop/product/{product_id}/analyze")
async def nuvemshop_analyze_product(product_id: int, store_id: str, user: dict = Depends(get_current_user)):
    """Analisa um produto e retorna métricas de SEO"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        analysis = await optimizer.analyze_product(product_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/product/{product_id}/optimize")
async def nuvemshop_optimize_product(
    product_id: int,
    store_id: str,
    target_keyword: Optional[str] = None,
    body: Optional[Dict[str, Any]] = Body(default=None),
    user: dict = Depends(get_current_user),
):
    """Gera propostas de otimização para um produto"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        options = None
        kw = target_keyword
        if isinstance(body, dict):
            kw = body.get("target_keyword") or target_keyword
            if body.get("recommended_actions"):
                from app.product_diagnosis import actions_to_optimize_options
                options = actions_to_optimize_options(body["recommended_actions"])
            else:
                flag_keys = (
                    "optimize_title", "optimize_name", "optimize_description",
                    "optimize_seo_title", "optimize_seo_description",
                    "optimize_image_alts", "generate_tags",
                )
                present = {k: bool(body.get(k)) for k in flag_keys if k in body}
                if present:
                    options = present
        proposals = await optimizer.optimize_product(
            product_id, options=options, target_keyword=kw, user=user
        )
        return {
            "proposals": [p.model_dump() for p in proposals],
            "total": len(proposals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nuvemshop/categories")
async def nuvemshop_list_categories(store_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Lista categorias da loja Nuvemshop"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        categories = await client.get_categories(limit=limit)
        return {
            "categories": [c.model_dump() for c in categories],
            "total": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nuvemshop/category/{category_id}/analyze")
async def nuvemshop_analyze_category(category_id: int, store_id: str, user: dict = Depends(get_current_user)):
    """Analisa uma categoria e retorna métricas de SEO"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        analysis = await optimizer.analyze_category(category_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/category/{category_id}/optimize")
async def nuvemshop_optimize_category(category_id: int, store_id: str, target_keyword: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Gera propostas de otimização para uma categoria"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        proposals = await optimizer.optimize_category(category_id, target_keyword=target_keyword, user=user)
        return {
            "proposals": [p.model_dump() for p in proposals],
            "total": len(proposals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nuvemshop/pages")
async def nuvemshop_list_pages(store_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Lista páginas da loja Nuvemshop"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        pages = await client.get_pages(limit=limit)
        return {
            "pages": [p.model_dump() for p in pages],
            "total": len(pages)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Retornar lista vazia ao invés de erro se não houver páginas
        logger.error(f"[Nuvemshop] Erro ao listar páginas: {e}")
        return {
            "pages": [],
            "total": 0,
            "warning": str(e)
        }


@app.get("/api/nuvemshop/page/{page_id}/analyze")
async def nuvemshop_analyze_page(page_id: int, store_id: str, user: dict = Depends(get_current_user)):
    """Analisa uma página e retorna métricas de SEO"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        analysis = await optimizer.analyze_page(page_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/page/{page_id}/optimize")
async def nuvemshop_optimize_page(page_id: int, store_id: str, target_keyword: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Gera propostas de otimização para uma página"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        proposals = await optimizer.optimize_page(page_id, target_keyword=target_keyword, user=user)
        return {
            "proposals": [p.model_dump() for p in proposals],
            "total": len(proposals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nuvemshop/blog/debug")
async def nuvemshop_blog_debug(store_id: str, user: dict = Depends(get_current_user)):
    """Debug endpoint para investigar a API de blogs da Nuvemshop"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    client = cached["client"]
    results = {"store_id": store_id, "tests": []}
    
    # 1. Info da loja (campo blog)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http:
            r = await http.get(f"{client.base_url}/store", headers=client.headers)
            store_data = r.json()
            results["store_blog_field"] = store_data.get("blog")
            results["store_id_from_api"] = store_data.get("id")
            results["tests"].append({"test": "GET /store", "status": r.status_code, "blog_field": store_data.get("blog")})
    except Exception as e:
        results["tests"].append({"test": "GET /store", "error": str(e)})
    
    # 2. Tentar GET /blogs (versioned API)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http:
            url = f"{client.base_url}/blogs"
            r = await http.get(url, headers=client.headers)
            results["tests"].append({"test": f"GET {url}", "status": r.status_code, "body": r.text[:500]})
    except Exception as e:
        results["tests"].append({"test": "GET /blogs (versioned)", "error": str(e)})
    
    # 3. Tentar GET /blogs (v1 API)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http:
            url = f"https://api.nuvemshop.com.br/v1/{store_id}/blogs"
            r = await http.get(url, headers=client.headers)
            results["tests"].append({"test": f"GET {url}", "status": r.status_code, "body": r.text[:500]})
    except Exception as e:
        results["tests"].append({"test": "GET /blogs (v1)", "error": str(e)})
    
    # 4. Tentar GET /blogs/1/posts (versioned API)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http:
            url = f"{client.base_url}/blogs/1/posts"
            r = await http.get(url, headers=client.headers)
            results["tests"].append({"test": f"GET {url}", "status": r.status_code, "body": r.text[:500]})
    except Exception as e:
        results["tests"].append({"test": "GET /blogs/1/posts (versioned)", "error": str(e)})
    
    # 5. Tentar GET /blogs/1/posts (v1 API)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http:
            url = f"https://api.nuvemshop.com.br/v1/{store_id}/blogs/1/posts"
            r = await http.get(url, headers=client.headers)
            results["tests"].append({"test": f"GET {url}", "status": r.status_code, "body": r.text[:500]})
    except Exception as e:
        results["tests"].append({"test": "GET /blogs/1/posts (v1)", "error": str(e)})
    
    # 6. Tentar blog_id = store_id
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http:
            url = f"{client.base_url}/blogs/{store_id}/posts"
            r = await http.get(url, headers=client.headers)
            results["tests"].append({"test": f"GET {url}", "status": r.status_code, "body": r.text[:500]})
    except Exception as e:
        results["tests"].append({"test": f"GET /blogs/{store_id}/posts", "error": str(e)})
    
    return results


@app.get("/api/nuvemshop/blog")
async def nuvemshop_list_blog_posts(store_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Lista posts do blog da loja Nuvemshop"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        
        # Verificar se o blog está ativo na loja
        store = await client.get_store()
        blog_url = getattr(store, 'blog', None)
        
        if not blog_url:
            return {
                "posts": [],
                "total": 0,
                "blog_enabled": False,
                "message": "O blog não está ativado nesta loja. Ative o blog no painel admin da Nuvemshop."
            }
        
        posts = await client.get_blog_posts(limit=limit)
        return {
            "posts": [p.model_dump() for p in posts],
            "total": len(posts),
            "blog_enabled": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nuvemshop/blog/{blog_id}/{post_id}/analyze")
async def nuvemshop_analyze_blog_post(blog_id: int, post_id: int, store_id: str, user: dict = Depends(get_current_user)):
    """Analisa um post do blog e retorna métricas de SEO"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        analysis = await optimizer.analyze_blog_post(blog_id, post_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/blog/{blog_id}/{post_id}/optimize")
async def nuvemshop_optimize_blog_post(blog_id: int, post_id: int, store_id: str, target_keyword: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Gera propostas de otimização para um post do blog"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        optimizer = cached["optimizer"]
        proposals = await optimizer.optimize_blog_post(blog_id, post_id, target_keyword=target_keyword, user=user)
        return {
            "proposals": [p.model_dump() for p in proposals],
            "total": len(proposals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nuvemshop/proposals")
async def nuvemshop_list_proposals(
    store_id: str,
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Lista propostas de otimização"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        proposals = client.get_proposals(status=status, content_type=content_type)
        return {
            "proposals": [p.model_dump() for p in proposals],
            "total": len(proposals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ProposalIdsRequest(BaseModel):
    proposal_ids: List[str]

@app.post("/api/nuvemshop/proposals/approve")
async def nuvemshop_approve_proposals(
    store_id: str,
    body: ProposalIdsRequest,
    user: dict = Depends(get_current_user)
):
    """Aprova propostas selecionadas"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        approved = client.approve_proposals(body.proposal_ids)
        return {"approved": approved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/proposals/reject")
async def nuvemshop_reject_proposals(
    store_id: str,
    body: ProposalIdsRequest,
    user: dict = Depends(get_current_user)
):
    """Rejeita propostas selecionadas"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        rejected = client.reject_proposals(body.proposal_ids)
        return {"rejected": rejected}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/proposals/apply")
async def nuvemshop_apply_proposals(store_id: str, item_id: Optional[int] = None, body: Optional[ApplyProposalsRequest] = None, user: dict = Depends(get_current_user)):
    """Aplica propostas aprovadas na loja Nuvemshop"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        optimizer = cached.get("optimizer")
        # If proposals are provided in body, apply them directly (stateless - no in-memory dependency)
        if body and body.proposals:
            result = await client.apply_proposals_direct(body.proposals)
        else:
            # Fallback to in-memory proposals
            result = await client.apply_approved_proposals(item_id)

        # Persiste contador de otimizações aplicadas no banco (sobrevive a cold starts)
        try:
            from app.supabase_client import get_supabase_for_user
            db_for_count = get_supabase_for_user(user["token"])
            await db_for_count.increment_applied_count(user["user_id"], result.get("applied", 0))

            if body and body.proposals:
                async def _resolve_url(content_type: str, pid: int):
                    if content_type == "product":
                        return (await client.get_product(pid)).url
                    if content_type == "category":
                        return (await client.get_category(pid)).url
                    return None
                await _mark_pages_optimized(db_for_count, user["user_id"], body.proposals, _resolve_url)
        except Exception as ce:
            logger.warning(f"increment_applied_count (nuvemshop) falhou: {ce}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nuvemshop/rollback")
async def nuvemshop_list_rollbacks(store_id: str, content_type: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista registros de rollback disponíveis"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        records = client.get_rollback_records(content_type=content_type)
        return {
            "records": [r.model_dump() for r in records],
            "total": len(records)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/rollback/direct")
async def nuvemshop_rollback_direct(store_id: str, body: RollbackDirectRequest, user: dict = Depends(get_current_user)):
    """
    Reverte uma alteração diretamente a partir dos dados do frontend.
    Funciona após cold starts (não depende de estado em memória).
    """
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        result = await client.rollback_direct(body.record)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"nuvemshop_rollback_direct failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/rollback/all")
async def nuvemshop_rollback_all(store_id: str, user: dict = Depends(get_current_user)):
    """Reverte todas as alterações"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        result = await client.rollback_all()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nuvemshop/rollback/{rollback_id}")
async def nuvemshop_rollback_single(rollback_id: str, store_id: str, user: dict = Depends(get_current_user)):
    """Reverte uma única alteração"""
    cached = await get_or_restore_nuvemshop_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    
    try:
        client = cached["client"]
        result = await client.rollback_single(rollback_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# VTEX
# =========================================================

class VtexConnectRequest(BaseModel):
    account_name: str
    app_key: str
    app_token: str


@app.post("/api/vtex/connect")
async def vtex_connect(payload: VtexConnectRequest, user: dict = Depends(get_current_user)):
    """
    Conecta a uma loja VTEX (App Key + App Token) e testa a conexão.
    Limite: 1 loja por usuário. A appKey precisa de role com os resources de
    Catálogo (Product and SKU Management + Categories Management).
    """
    from app.integrations.vtex import create_vtex_client
    from app.integrations.vtex_optimizer import VtexSEOOptimizer
    from app.supabase_client import get_supabase_for_user

    db = get_supabase_for_user(user["token"])
    existing = await db.list_sites_for_user(user["user_id"], limit=10)
    integration_sites = [s for s in existing if s.get("platform") in INTEGRATION_PLATFORMS]
    if integration_sites:
        return format_error("Você já possui uma loja conectada. Desconecte a atual antes de conectar outra.", status_code=409)
    await _delete_url_only_sites(db, user["user_id"])

    try:
        client = create_vtex_client(
            account_name=payload.account_name,
            app_key=payload.app_key,
            app_token=payload.app_token,
        )
        connection = await client.test_connection()
        if not connection.get("connected"):
            return format_error(
                f"Falha ao conectar à VTEX: {connection.get('error', 'credenciais inválidas ou sem permissão de Catálogo')}",
                status_code=400,
            )

        created_site = await db.create_site(
            base_url=client.store_url,
            platform="vtex",
            user_id=user["user_id"],
        )

        optimizer = VtexSEOOptimizer(client)
        _vtex_clients_cache[client.account_name] = {
            "client": client, "optimizer": optimizer, "user_id": user["user_id"],
        }
        await db.save_integration(
            user_id=user["user_id"],
            platform="vtex",
            store_url=client.account_name,
            access_token=payload.app_token,
            store_name=payload.account_name,
            metadata={"app_key": payload.app_key, "account_name": client.account_name, "environment": client.environment, "site_url": client.store_url},
        )

        # Auto-scan inicial após conectar (background, não bloqueia resposta)
        if created_site.get("id"):
            asyncio.create_task(_initial_scan(db, str(created_site["id"]), client.store_url))

        return {
            "success": True,
            "store_id": client.account_name,
            "store": {"name": payload.account_name, "url": client.store_url},
            "message": "Conectado com sucesso!",
        }
    except Exception as e:
        logger.error(f"[VTEX] Erro ao conectar: {e}")
        return format_error(f"Erro ao conectar: {str(e)}")


@app.get("/api/vtex/products")
async def vtex_list_products(store_id: str, limit: int = 500, user: dict = Depends(get_current_user)):
    """Lista produtos da loja VTEX (busca pública, paginado)."""
    from app.integrations.vtex import VtexAuthError
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada. Reconecte sua loja VTEX.")
    try:
        products = await cached["client"].get_all_products(max_items=limit)
        return {"products": [p.model_dump() for p in products], "total": len(products)}
    except VtexAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vtex/product/{product_id}/analyze")
async def vtex_analyze_product(product_id: int, store_id: str, user: dict = Depends(get_current_user)):
    """Analisa um produto e retorna métricas de SEO"""
    from app.integrations.vtex import VtexNotFoundError
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["optimizer"].analyze_product(product_id)
    except VtexNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vtex/product/{product_id}/optimize")
async def vtex_optimize_product(
    product_id: int,
    store_id: str,
    target_keyword: Optional[str] = None,
    body: Optional[Dict[str, Any]] = Body(default=None),
    user: dict = Depends(get_current_user),
):
    """Gera propostas de otimização para um produto"""
    from app.integrations.vtex import VtexNotFoundError
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        kw = target_keyword
        actions = None
        if isinstance(body, dict):
            kw = body.get("target_keyword") or target_keyword
            actions = body.get("recommended_actions")
        proposals = await cached["optimizer"].optimize_product(
            product_id, target_keyword=kw, user=user, recommended_actions=actions
        )
        return {"proposals": [p.model_dump() for p in proposals], "total": len(proposals)}
    except VtexNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vtex/categories")
async def vtex_list_categories(store_id: str, limit: int = 100, user: dict = Depends(get_current_user)):
    """Lista categorias da loja VTEX (árvore pública achatada)"""
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        categories = await cached["client"].get_all_categories(max_items=limit)
        return {"categories": [c.model_dump() for c in categories], "total": len(categories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vtex/category/{category_id}/analyze")
async def vtex_analyze_category(category_id: int, store_id: str, user: dict = Depends(get_current_user)):
    """Analisa uma categoria e retorna métricas de SEO"""
    from app.integrations.vtex import VtexNotFoundError
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["optimizer"].analyze_category(category_id)
    except VtexNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vtex/category/{category_id}/optimize")
async def vtex_optimize_category(category_id: int, store_id: str, target_keyword: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Gera propostas de otimização para uma categoria"""
    from app.integrations.vtex import VtexNotFoundError
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        proposals = await cached["optimizer"].optimize_category(category_id, target_keyword=target_keyword, user=user)
        return {"proposals": [p.model_dump() for p in proposals], "total": len(proposals)}
    except VtexNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vtex/proposals")
async def vtex_list_proposals(store_id: str, status: Optional[str] = None, content_type: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista propostas de otimização"""
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        proposals = cached["client"].get_proposals(status=status, content_type=content_type)
        return {"proposals": [p.model_dump() for p in proposals], "total": len(proposals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vtex/proposals/approve")
async def vtex_approve_proposals(store_id: str, body: ProposalIdsRequest, user: dict = Depends(get_current_user)):
    """Aprova propostas selecionadas"""
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return {"approved": cached["client"].approve_proposals(body.proposal_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vtex/proposals/reject")
async def vtex_reject_proposals(store_id: str, body: ProposalIdsRequest, user: dict = Depends(get_current_user)):
    """Rejeita propostas selecionadas"""
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return {"rejected": cached["client"].reject_proposals(body.proposal_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vtex/proposals/apply")
async def vtex_apply_proposals(store_id: str, item_id: Optional[int] = None, body: Optional[ApplyProposalsRequest] = None, user: dict = Depends(get_current_user)):
    """Aplica propostas aprovadas na loja VTEX (read-modify-write)"""
    from app.integrations.vtex import VtexNotFoundError
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        client = cached["client"]
        if body and body.proposals:
            result = await client.apply_proposals_direct(body.proposals)
        else:
            result = await client.apply_approved_proposals(item_id)

        try:
            from app.supabase_client import get_supabase_for_user
            db_for_count = get_supabase_for_user(user["token"])
            await db_for_count.increment_applied_count(user["user_id"], result.get("applied", 0))

            if body and body.proposals:
                async def _resolve_url(content_type: str, pid: int):
                    if content_type == "product":
                        return (await client.get_product(pid)).url
                    if content_type == "category":
                        return (await client.get_category(pid)).url
                    return None
                await _mark_pages_optimized(db_for_count, user["user_id"], body.proposals, _resolve_url)
        except Exception as ce:
            logger.warning(f"increment_applied_count (vtex) falhou: {ce}")

        return result
    except VtexNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vtex/rollback")
async def vtex_list_rollbacks(store_id: str, content_type: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista registros de rollback disponíveis"""
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        records = cached["client"].get_rollback_records(content_type=content_type)
        return {"records": [r.model_dump() for r in records], "total": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vtex/rollback/direct")
async def vtex_rollback_direct(store_id: str, body: RollbackDirectRequest, user: dict = Depends(get_current_user)):
    """Reverte uma alteração a partir dos dados do frontend (stateless)"""
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["client"].rollback_direct(body.record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"vtex_rollback_direct failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vtex/rollback/all")
async def vtex_rollback_all(store_id: str, user: dict = Depends(get_current_user)):
    """Reverte todas as alterações"""
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["client"].rollback_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vtex/rollback/{rollback_id}")
async def vtex_rollback_single(rollback_id: str, store_id: str, user: dict = Depends(get_current_user)):
    """Reverte uma única alteração"""
    cached = await get_or_restore_vtex_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["client"].rollback_single(rollback_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# Loja Integrada
# =========================================================

class LojaIntegradaConnectRequest(BaseModel):
    chave_api: str


@app.post("/api/lojaintegrada/connect")
async def lojaintegrada_connect(payload: LojaIntegradaConnectRequest, user: dict = Depends(get_current_user)):
    """
    Conecta a uma loja Loja Integrada (Chave de API da loja) e testa a conexão.
    Limite: 1 loja por usuário. A API da Loja Integrada só está disponível em
    planos pagos. A chave de aplicação (integrador) vem do ambiente do backend.
    """
    from app.integrations.lojaintegrada import create_lojaintegrada_client, LOJAINTEGRADA_APP_KEY
    from app.integrations.lojaintegrada_optimizer import LojaIntegradaSEOOptimizer
    from app.supabase_client import get_supabase_for_user

    if not LOJAINTEGRADA_APP_KEY:
        return format_error(
            "Integração Loja Integrada não configurada no servidor (LOJAINTEGRADA_APP_KEY ausente).",
            status_code=503,
        )

    db = get_supabase_for_user(user["token"])
    existing = await db.list_sites_for_user(user["user_id"], limit=10)
    integration_sites = [s for s in existing if s.get("platform") in INTEGRATION_PLATFORMS]
    if integration_sites:
        return format_error("Você já possui uma loja conectada. Desconecte a atual antes de conectar outra.", status_code=409)
    await _delete_url_only_sites(db, user["user_id"])

    try:
        client = create_lojaintegrada_client(payload.chave_api)
        connection = await client.test_connection()
        if not connection.get("connected"):
            return format_error(
                f"Falha ao conectar à Loja Integrada: {connection.get('error', 'chave de API inválida')} "
                "(lembre-se: a API está disponível apenas em planos pagos)",
                status_code=400,
            )

        # Deriva a URL pública da loja a partir de um produto (a API não expõe a URL da loja)
        store_url = ""
        try:
            sample = await client.get_all_products(max_items=1)
            store_url = client.store_url or (sample[0].url.rsplit("/", 1)[0] if sample and sample[0].url else "")
        except Exception as e:
            logger.warning(f"[LojaIntegrada] Não foi possível derivar a URL da loja: {e}")

        # Sem produtos no catálogo ainda (loja recém-criada), não há URL
        # pública real para descobrir. Criar o site mesmo assim exigiria uma
        # base_url fake (ex.: um domínio inventado) — esse valor ficaria
        # gravado permanentemente e todo scan futuro (manual ou automático)
        # falharia contra um domínio que nunca existiu. Em vez disso, só
        # salvamos a integração agora; GET /api/integrations/status tenta
        # re-derivar a URL a cada checagem (self-healing) e cria o site assim
        # que a loja tiver ao menos um produto com URL pública.
        created_site = None
        if store_url:
            created_site = await db.create_site(
                base_url=store_url,
                platform="lojaintegrada",
                user_id=user["user_id"],
            )

        optimizer = LojaIntegradaSEOOptimizer(client)
        _li_clients_cache[client.store_key] = {
            "client": client, "optimizer": optimizer, "user_id": user["user_id"],
        }
        await db.save_integration(
            user_id=user["user_id"],
            platform="lojaintegrada",
            store_url=client.store_key,
            access_token=payload.chave_api,
            store_name="Loja Integrada",
            metadata={"site_url": store_url},
        )

        # Auto-scan inicial só quando temos site + URL real para rastrear
        if created_site and created_site.get("id") and store_url:
            asyncio.create_task(_initial_scan(db, str(created_site["id"]), store_url))

        return {
            "success": True,
            "store_id": client.store_key,
            "store": {"name": "Loja Integrada", "url": store_url},
            "message": "Conectado com sucesso!" if store_url else (
                "Conectado! Nenhum produto encontrado ainda — assim que sua loja "
                "tiver produtos, a análise de SEO começará automaticamente."
            ),
        }
    except Exception as e:
        logger.error(f"[LojaIntegrada] Erro ao conectar: {e}")
        return format_error(f"Erro ao conectar: {str(e)}")


@app.get("/api/lojaintegrada/products")
async def lojaintegrada_list_products(store_id: str, limit: int = 500, user: dict = Depends(get_current_user)):
    """Lista produtos da loja Loja Integrada (paginação TastyPie)."""
    from app.integrations.lojaintegrada import LojaIntegradaAuthError
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada. Reconecte sua loja Loja Integrada.")
    try:
        products = await cached["client"].get_all_products(max_items=limit)
        return {"products": [p.model_dump() for p in products], "total": len(products)}
    except LojaIntegradaAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lojaintegrada/product/{product_id}/analyze")
async def lojaintegrada_analyze_product(product_id: int, store_id: str, user: dict = Depends(get_current_user)):
    """Analisa um produto e retorna métricas de SEO"""
    from app.integrations.lojaintegrada import LojaIntegradaNotFoundError
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["optimizer"].analyze_product(product_id)
    except LojaIntegradaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lojaintegrada/product/{product_id}/optimize")
async def lojaintegrada_optimize_product(
    product_id: int,
    store_id: str,
    target_keyword: Optional[str] = None,
    body: Optional[Dict[str, Any]] = Body(default=None),
    user: dict = Depends(get_current_user),
):
    """Gera propostas de otimização para um produto"""
    from app.integrations.lojaintegrada import LojaIntegradaNotFoundError
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        kw = target_keyword
        actions = None
        if isinstance(body, dict):
            kw = body.get("target_keyword") or target_keyword
            actions = body.get("recommended_actions")
        proposals = await cached["optimizer"].optimize_product(
            product_id, target_keyword=kw, user=user, recommended_actions=actions
        )
        return {"proposals": [p.model_dump() for p in proposals], "total": len(proposals)}
    except LojaIntegradaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lojaintegrada/categories")
async def lojaintegrada_list_categories(store_id: str, limit: int = 100, user: dict = Depends(get_current_user)):
    """Lista categorias da loja Loja Integrada"""
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        categories = await cached["client"].get_all_categories(max_items=limit)
        return {"categories": [c.model_dump() for c in categories], "total": len(categories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lojaintegrada/category/{category_id}/analyze")
async def lojaintegrada_analyze_category(category_id: int, store_id: str, user: dict = Depends(get_current_user)):
    """Analisa uma categoria e retorna métricas de SEO"""
    from app.integrations.lojaintegrada import LojaIntegradaNotFoundError
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["optimizer"].analyze_category(category_id)
    except LojaIntegradaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lojaintegrada/category/{category_id}/optimize")
async def lojaintegrada_optimize_category(category_id: int, store_id: str, target_keyword: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Gera propostas de otimização para uma categoria"""
    from app.integrations.lojaintegrada import LojaIntegradaNotFoundError
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        proposals = await cached["optimizer"].optimize_category(category_id, target_keyword=target_keyword, user=user)
        return {"proposals": [p.model_dump() for p in proposals], "total": len(proposals)}
    except LojaIntegradaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lojaintegrada/proposals")
async def lojaintegrada_list_proposals(store_id: str, status: Optional[str] = None, content_type: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista propostas de otimização"""
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        proposals = cached["client"].get_proposals(status=status, content_type=content_type)
        return {"proposals": [p.model_dump() for p in proposals], "total": len(proposals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lojaintegrada/proposals/approve")
async def lojaintegrada_approve_proposals(store_id: str, body: ProposalIdsRequest, user: dict = Depends(get_current_user)):
    """Aprova propostas selecionadas"""
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return {"approved": cached["client"].approve_proposals(body.proposal_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lojaintegrada/proposals/reject")
async def lojaintegrada_reject_proposals(store_id: str, body: ProposalIdsRequest, user: dict = Depends(get_current_user)):
    """Rejeita propostas selecionadas"""
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return {"rejected": cached["client"].reject_proposals(body.proposal_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lojaintegrada/proposals/apply")
async def lojaintegrada_apply_proposals(store_id: str, item_id: Optional[int] = None, body: Optional[ApplyProposalsRequest] = None, user: dict = Depends(get_current_user)):
    """Aplica propostas aprovadas na Loja Integrada (SEO via /v1/seo; produto via PUT completo)"""
    from app.integrations.lojaintegrada import LojaIntegradaNotFoundError
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        client = cached["client"]
        if body and body.proposals:
            result = await client.apply_proposals_direct(body.proposals)
        else:
            result = await client.apply_approved_proposals(item_id)

        try:
            from app.supabase_client import get_supabase_for_user
            db_for_count = get_supabase_for_user(user["token"])
            await db_for_count.increment_applied_count(user["user_id"], result.get("applied", 0))

            if body and body.proposals:
                async def _resolve_url(content_type: str, pid: int):
                    if content_type == "product":
                        return (await client.get_product(pid)).url
                    if content_type == "category":
                        return (await client.get_category(pid)).url
                    return None
                await _mark_pages_optimized(db_for_count, user["user_id"], body.proposals, _resolve_url)
        except Exception as ce:
            logger.warning(f"increment_applied_count (lojaintegrada) falhou: {ce}")

        return result
    except LojaIntegradaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lojaintegrada/rollback")
async def lojaintegrada_list_rollbacks(store_id: str, content_type: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista registros de rollback disponíveis"""
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        records = cached["client"].get_rollback_records(content_type=content_type)
        return {"records": [r.model_dump() for r in records], "total": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lojaintegrada/rollback/direct")
async def lojaintegrada_rollback_direct(store_id: str, body: RollbackDirectRequest, user: dict = Depends(get_current_user)):
    """Reverte uma alteração a partir dos dados do frontend (stateless)"""
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["client"].rollback_direct(body.record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"lojaintegrada_rollback_direct failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lojaintegrada/rollback/all")
async def lojaintegrada_rollback_all(store_id: str, user: dict = Depends(get_current_user)):
    """Reverte todas as alterações"""
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["client"].rollback_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lojaintegrada/rollback/{rollback_id}")
async def lojaintegrada_rollback_single(rollback_id: str, store_id: str, user: dict = Depends(get_current_user)):
    """Reverte uma única alteração"""
    cached = await get_or_restore_lojaintegrada_client(store_id, user)
    if not cached:
        raise HTTPException(status_code=400, detail="Loja não conectada")
    try:
        return await cached["client"].rollback_single(rollback_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

