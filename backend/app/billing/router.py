"""Rotas de billing conforme docs/asaas-backend-contract.md.

- POST /billing/checkout
- GET  /billing/subscription
- POST /webhooks/asaas
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.auth import get_current_user, get_optional_user
from app.billing.rate_limit import checkout_limiter, webhook_limiter
from app.billing.schemas import (
    ClaimCheckoutRequest,
    CreateCheckoutRequest,
    CreateCheckoutResponse,
    StartTrialRequest,
)
from app.billing.service import (
    BillingService,
    BillingUnavailableError,
    BillingUpstreamError,
    BillingValidationError,
    verify_webhook_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "error": message,
            "statusCode": status_code,
        },
    )


@router.post(
    "/billing/checkout",
    response_model=CreateCheckoutResponse,
    status_code=201,
)
async def create_checkout(
    body: CreateCheckoutRequest,
    request: Request,
    user: Optional[dict] = Depends(get_optional_user),
):
    ip = _client_ip(request)
    if not checkout_limiter.allow(f"checkout:{ip}"):
        return _error("Muitas tentativas. Aguarde e tente novamente.", 429)

    service = BillingService()
    try:
        session = await service.create_checkout_session(
            plan_id=body.planId,
            billing_cycle=body.billingCycle,
            user_id=user.get("user_id") if user else None,
        )
        return JSONResponse(
            status_code=201,
            content=session.model_dump(),
        )
    except BillingValidationError as exc:
        return _error(str(exc), 400)
    except BillingUnavailableError as exc:
        return _error(str(exc), 503)
    except BillingUpstreamError as exc:
        return _error(str(exc), exc.status_code)
    except ValueError as exc:
        return _error(str(exc), 400)
    except Exception:
        logger.exception("Erro inesperado em POST /billing/checkout")
        return _error("Erro interno ao criar checkout.", 500)


@router.get("/billing/subscription")
async def get_subscription(user: dict = Depends(get_current_user)):
    service = BillingService()
    try:
        result = await service.get_subscription_for_user(user["user_id"])
        return result.model_dump()
    except Exception:
        logger.exception("Erro inesperado em GET /billing/subscription")
        return _error("Erro interno ao consultar assinatura.", 500)


@router.post("/billing/claim-checkout")
async def claim_checkout(
    body: ClaimCheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Vincula um checkout (ref da URL de sucesso) ao usuário logado."""
    service = BillingService()
    try:
        result = await service.claim_checkout_for_user(
            user_id=user["user_id"],
            external_reference=body.externalReference,
        )
        return result.model_dump()
    except BillingValidationError as exc:
        return _error(str(exc), 400)
    except Exception:
        logger.exception("Erro inesperado em POST /billing/claim-checkout")
        return _error("Erro interno ao vincular checkout.", 500)


@router.post("/billing/start-trial")
async def start_trial(
    body: StartTrialRequest,
    user: dict = Depends(get_current_user),
):
    """Inicia avaliação gratuita de 7 dias (sem cartão), 1x por conta."""
    service = BillingService()
    try:
        result = await service.start_trial(
            user_id=user["user_id"],
            plan_id=body.planId,
        )
        return result.model_dump()
    except BillingValidationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        logger.exception("Erro inesperado em POST /billing/start-trial")
        detail = str(exc)
        if "trial_ends_at" in detail or "trial_started_at" in detail:
            return _error(
                "Schema de trial não aplicado no banco. "
                "Execute supabase/migrations/20260812190000_subscription_trial.sql "
                "no SQL Editor do Supabase.",
                503,
            )
        return _error("Erro interno ao iniciar avaliação.", 500)


@router.post("/webhooks/asaas")
async def asaas_webhook(request: Request):
    ip = _client_ip(request)
    if not webhook_limiter.allow(f"webhook:{ip}"):
        return _error("Rate limit excedido.", 429)

    token = request.headers.get("asaas-access-token")
    if not verify_webhook_token(token):
        return _error("Webhook não autorizado.", 401)

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        return _error("Payload inválido.", 400)

    if not isinstance(payload, dict):
        return _error("Payload inválido.", 400)

    service = BillingService()
    try:
        # Persistência + processamento; Asaas exige 2xx rápido.
        # Processamos de forma síncrona mas leve (só updates de status).
        await service.handle_webhook(payload)
    except BillingValidationError as exc:
        return _error(str(exc), 400)
    except Exception:
        # Já pode ter sido persistido; responde 200 para não interromper a fila
        # se o evento foi gravado — handle_webhook só relança após insert.
        logger.exception("Erro ao processar webhook Asaas")
        return JSONResponse(status_code=200, content={"received": True})

    return JSONResponse(status_code=200, content={"received": True})
