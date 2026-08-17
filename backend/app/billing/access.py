"""Autorização por assinatura.

- full (active|past_due): APIs de produto
- trial (trialing válido): mesmas APIs — FE bloqueia Termos/Histórico/Panorama
- Conta autenticada ≠ acesso ao produto
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

# Assinatura paga
FULL_ACCESS_STATUSES: Set[str] = {"active", "past_due"}

# UX ampla (pago + trial)
ACTIVE_SUBSCRIPTION_STATUSES: Set[str] = FULL_ACCESS_STATUSES | {"trialing"}

SUBSCRIPTION_REQUIRED_MESSAGE = (
    "Assinatura ativa necessária para acessar este recurso. "
    "Crie ou reative sua assinatura para continuar."
)

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
    "/api/shopify/oauth-redirect",
    "/api/nuvemshop/oauth-redirect",
    "/api/nuvemshop/auth",
    "/api/gsc/callback",
)


def path_requires_subscription(path: str) -> bool:
    """True se o path exige assinatura paga ou trial válido."""
    if not path.startswith("/api/"):
        return False
    if path in _EXEMPT_EXACT:
        return False
    for prefix in _EXEMPT_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return False
    return True


def is_entitled_status(status: Optional[str]) -> bool:
    """Status que conta como 'ativo' na UX ampla (inclui trialing)."""
    if not status:
        return False
    return status in ACTIVE_SUBSCRIPTION_STATUSES


def is_full_access_status(status: Optional[str]) -> bool:
    if not status:
        return False
    return status in FULL_ACCESS_STATUSES


async def user_has_active_subscription(user_id: str) -> bool:
    """True se o usuário pode chamar APIs de produto (pago full ou trial válido)."""
    repo = BillingRepository()
    row = await repo.get_active_subscription_for_user(user_id)
    if row and is_full_access_status(row.get("status")):
        return True
    trial = await repo.get_valid_trial_for_user(user_id)
    return bool(trial)


async def require_active_subscription(
    user: dict = Depends(get_current_user),
) -> dict:
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
    """Bloqueia APIs de produto sem assinatura paga nem trial válido."""
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path
    if not path_requires_subscription(path):
        return await call_next(request)

    credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
    if not credentials:
        return await call_next(request)

    try:
        payload = _decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return await call_next(request)

        if not await user_has_active_subscription(user_id):
            logger.info(
                "Acesso bloqueado sem assinatura/trial: user=%s path=%s",
                user_id,
                path,
            )
            return subscription_denied_response()
    except HTTPException as exc:
        if exc.status_code in (401, 503):
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
