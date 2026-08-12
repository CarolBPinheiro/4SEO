"""Acesso administrativo da plataforma — um único tipo, sem RBAC.

Autorização: allowlist de e-mails em ADMIN_EMAILS (ou ADMIN_USER_IDS).
"""

from __future__ import annotations

import os
import logging
from typing import FrozenSet

from fastapi import Depends, HTTPException

from app.auth import get_current_user

logger = logging.getLogger(__name__)


def _parse_csv_env(name: str) -> FrozenSet[str]:
    raw = os.getenv(name, "") or ""
    items = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return frozenset(items)


def get_admin_emails() -> FrozenSet[str]:
    return _parse_csv_env("ADMIN_EMAILS")


def get_admin_user_ids() -> FrozenSet[str]:
    return _parse_csv_env("ADMIN_USER_IDS")


def is_platform_admin(user: dict) -> bool:
    emails = get_admin_emails()
    ids = get_admin_user_ids()
    if not emails and not ids:
        return False
    email = (user.get("email") or "").strip().lower()
    user_id = (user.get("user_id") or "").strip().lower()
    if email and email in emails:
        return True
    if user_id and user_id in ids:
        return True
    return False


async def require_platform_admin(user: dict = Depends(get_current_user)) -> dict:
    """JWT válido + allowlist. Sem hierarquia de papéis."""
    if not get_admin_emails() and not get_admin_user_ids():
        logger.warning("ADMIN_EMAILS/ADMIN_USER_IDS não configurados — admin bloqueado")
        raise HTTPException(
            status_code=503,
            detail="Painel administrativo não configurado.",
        )
    if not is_platform_admin(user):
        raise HTTPException(status_code=403, detail="Acesso administrativo negado.")
    return user
