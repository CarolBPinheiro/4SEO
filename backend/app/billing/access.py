"""Autorização por assinatura ativa (fonte: tabela subscriptions / Asaas).

Conta autenticada ≠ acesso aos recursos. Apenas status em
ACTIVE_SUBSCRIPTION_STATUSES libera APIs de produto.
"""

from __future__ import annotations

import logging
from typing import Optional, Set

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import get_current_user, security, _decode_token
from app.billing.repository import BillingRepository

logger = logging.getLogger(__name__)

# Alinhado a BillingRepository.get_active_subscription_for_user
ACTIVE_SUBSCRIPTION_STATUSES: Set[str] = {"active", "trialing", "past_due"}

SUBSCRIPTION_REQUIRED_MESSAGE = (
    "Assinatura ativa necessária para acessar este recurso. "
    "Crie ou reative sua assinatura para continuar."
)

# Prefixos/paths que nunca exigem assinatura (públicos, billing, OAuth callbacks).
_EXEMPT_EXACT = frozenset(
    {
        "/api/health",
        "/health",
        "/api/info",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)

_EXEMPT_PREFIXES = (
    "/api/billing",
    "/billing",
    "/api/webhooks",
    "/webhooks",
    "/api/admin",
    # Callbacks OAuth de plataformas (redirect do browser, sem Bearer tipicamente)
    "/api/shopify/oauth-redirect",
    "/api/nuvemshop/oauth-redirect",
    "/api/nuvemshop/auth",
    "/api/gsc/callback",
)

def path_requires_subscription(path: str) -> bool:
    """True se o path de API de produto exige assinatura ativa.

    Billing e health ficam isentos. Demais /api/* (incl. dashboard) exigem
    assinatura — o frontend monta o dashboard zerado sem chamar essas APIs.
    """
    if not path.startswith("/api/"):
        return False
    if path in _EXEMPT_EXACT:
        return False
    for prefix in _EXEMPT_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return False
    return True


def is_entitled_status(status: Optional[str]) -> bool:
    if not status:
        return False
    return status in ACTIVE_SUBSCRIPTION_STATUSES


async def user_has_active_subscription(user_id: str) -> bool:
    repo = BillingRepository()
    row = await repo.get_active_subscription_for_user(user_id)
    return bool(row and is_entitled_status(row.get("status")))


async def require_active_subscription(
    user: dict = Depends(get_current_user),
) -> dict:
    """Dependency FastAPI: JWT válido + assinatura ativa."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    if not await user_has_active_subscription(user_id):
        raise HTTPException(
            status_code=402,
            detail=SUBSCRIPTION_REQUIRED_MESSAGE,
        )
    return user


def subscription_denied_response() -> JSONResponse:
    return JSONResponse(
        status_code=402,
        content={
            "error": True,
            "detail": SUBSCRIPTION_REQUIRED_MESSAGE,
            "code": "subscription_required",
        },
    )


async def enforce_subscription_middleware(request: Request, call_next):
    """Bloqueia APIs de produto sem assinatura ativa (centralizado)."""
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path
    if not path_requires_subscription(path):
        return await call_next(request)

    credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
    if not credentials:
        # Sem token: deixa o Depends(get_current_user) da rota responder 401
        return await call_next(request)

    try:
        payload = _decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return await call_next(request)

        if not await user_has_active_subscription(user_id):
            logger.info(
                "Acesso bloqueado sem assinatura ativa: user=%s path=%s",
                user_id,
                path,
            )
            return subscription_denied_response()
    except HTTPException as exc:
        if exc.status_code in (401, 503):
            # Token inválido/expirado: rota responde normalmente
            return await call_next(request)
        raise
    except Exception:
        logger.exception("Falha ao validar assinatura no middleware path=%s", path)
        return JSONResponse(
            status_code=503,
            content={
                "error": True,
                "detail": "Não foi possível validar a assinatura. Tente novamente.",
            },
        )

    return await call_next(request)
