"""Webhook público do Typebot → chamados do painel admin."""

from __future__ import annotations

import hmac
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from app.admin.repository import AdminRepository
from app.admin.service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-webhooks"])


def _configured_secret() -> str:
    return (os.getenv("TYPEBOT_WEBHOOK_SECRET") or "").strip()


def _extract_provided_secret(
    *,
    header_secret: Optional[str],
    authorization: Optional[str],
    query_token: Optional[str],
) -> str:
    if header_secret and header_secret.strip():
        return header_secret.strip()
    if authorization:
        raw = authorization.strip()
        if raw.lower().startswith("bearer "):
            return raw[7:].strip()
        return raw
    return (query_token or "").strip()


def _secrets_match(provided: str, expected: str) -> bool:
    if not provided or not expected:
        return False
    if len(provided) != len(expected):
        return hmac.compare_digest(provided, provided) and False
    return hmac.compare_digest(provided, expected)


@router.post("/webhooks/typebot")
async def typebot_webhook(
    request: Request,
    x_typebot_secret: Optional[str] = Header(default=None, alias="X-Typebot-Secret"),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None, max_length=200),
):
    expected = _configured_secret()
    if not expected:
        logger.warning("TYPEBOT_WEBHOOK_SECRET ausente — ingestão recusada")
        return JSONResponse(
            status_code=503,
            content={"error": True, "detail": "Webhook Typebot não configurado."},
        )

    provided = _extract_provided_secret(
        header_secret=x_typebot_secret or x_webhook_secret,
        authorization=authorization,
        query_token=token,
    )
    if not _secrets_match(provided, expected):
        return JSONResponse(
            status_code=401,
            content={"error": True, "detail": "Webhook não autorizado."},
        )

    try:
        payload: Any = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": True, "detail": "Payload inválido."},
        )
    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400,
            content={"error": True, "detail": "Payload inválido."},
        )

    service = AdminService()
    try:
        ticket = await service.ingest_typebot_ticket(payload)
    except Exception:
        logger.exception("Falha ao ingestão de chamado Typebot")
        return JSONResponse(
            status_code=503,
            content={
                "error": True,
                "detail": "Não foi possível registrar o chamado. Verifique a migration admin_support_tickets.",
            },
        )

    await AdminRepository().insert_audit(
        actor_user_id=None,
        actor_email="typebot",
        action="admin.ticket.ingest",
        target_type="ticket",
        target_id=str(ticket.get("id") or ""),
        meta={"source": "typebot"},
    )
    return {"ok": True, "id": ticket.get("id"), "status": ticket.get("status")}
