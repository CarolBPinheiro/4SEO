"""Flag DEMO_MODE e constantes do sandbox local.

DEMO_MODE só é considerado ligado quando ENVIRONMENT != production e as URLs
públicas apontam para localhost. Tokens fictícios usam o prefixo `demo_`.
"""
from __future__ import annotations

import logging
import os
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEMO_TOKEN_PREFIX = "demo_"
DEMO_EMAIL_DOMAIN = "demo.4seo.local"
DEMO_PASSWORD_DEFAULT = "Demo4SEO!local"

DEMO_ACCOUNTS = (
    {"email": f"demo@{DEMO_EMAIL_DOMAIN}", "role": "full", "plan_id": "scale"},
    {"email": f"trial@{DEMO_EMAIL_DOMAIN}", "role": "trial", "plan_id": "start"},
    {"email": f"admin@{DEMO_EMAIL_DOMAIN}", "role": "admin", "plan_id": "scale"},
)

DEMO_STORES = {
    "shopify": {
        "store_url": "demo-4seo.myshopify.com",
        "store_name": "Loja Demo 4SEO",
        "token": "demo_shopify_token",
        "base_url": "https://demo-4seo.myshopify.com",
    },
    "nuvemshop": {
        "store_id": "1001",
        "store_url": "https://demo-4seo.lojavirtualnuvem.com.br",
        "store_name": "Loja Demo 4SEO",
        "token": "demo_nuvemshop_token",
        "base_url": "https://demo-4seo.lojavirtualnuvem.com.br",
    },
    "vtex": {
        "account_name": "demo4seo",
        "store_url": "demo4seo",
        "store_name": "Loja Demo 4SEO",
        "app_key": "demo_vtex_app_key",
        "token": "demo_vtex_app_token",
        "base_url": "https://demo4seo.vtexcommercestable.com.br",
    },
    "lojaintegrada": {
        "store_url": "https://demo-4seo.lojaintegrada.com.br",
        "store_name": "Loja Demo 4SEO",
        "token": "demo_lojaintegrada_key",
        "base_url": "https://demo-4seo.lojaintegrada.com.br",
    },
}

DEMO_GSC_SITE = "https://demo-4seo.lojavirtualnuvem.com.br"
DEMO_GSC_TOKEN = "demo_gsc_access_token"
DEMO_GSC_REFRESH = "demo_gsc_refresh_token"

_TRUE = {"1", "true", "yes", "on"}


class DemoModeError(RuntimeError):
    """DEMO_MODE ligado em ambiente inseguro."""


def _truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in _TRUE


def is_production_env() -> bool:
    env = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "").strip().lower()
    return env == "production"


def is_demo_mode() -> bool:
    return _truthy("DEMO_MODE")


def is_demo_token(token: Optional[str]) -> bool:
    return bool(token) and str(token).startswith(DEMO_TOKEN_PREFIX)


def demo_password() -> str:
    raw = (os.getenv("DEMO_PASSWORD") or "").strip()
    return raw or DEMO_PASSWORD_DEFAULT


def _host_is_local(url: str) -> bool:
    raw = (url or "").strip()
    if not raw:
        return True
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def assert_demo_safe() -> None:
    """Recusa DEMO_MODE fora de development/localhost. No-op se a flag estiver off."""
    if not is_demo_mode():
        return
    if is_production_env():
        raise DemoModeError(
            "DEMO_MODE não pode ser ligado com ENVIRONMENT=production."
        )
    frontend = os.getenv("FRONTEND_URL") or ""
    backend = os.getenv("BACKEND_URL") or ""
    if not _host_is_local(frontend):
        raise DemoModeError(
            "DEMO_MODE exige FRONTEND_URL em localhost (recebido: "
            f"{frontend!r})."
        )
    if not _host_is_local(backend):
        raise DemoModeError(
            "DEMO_MODE exige BACKEND_URL em localhost (recebido: "
            f"{backend!r})."
        )
    logger.warning(
        "DEMO_MODE ativo — sandbox local com dados fictícios. "
        "Não use em produção."
    )


def demo_info_payload() -> dict:
    """Bloco `demo` exposto em GET /api/info (sem senha)."""
    if not is_demo_mode():
        return {"enabled": False}
    return {
        "enabled": True,
        "accounts": [
            {"email": a["email"], "role": a["role"]} for a in DEMO_ACCOUNTS
        ],
        "loginEmail": DEMO_ACCOUNTS[0]["email"],
        "loginPassword": demo_password(),
    }
