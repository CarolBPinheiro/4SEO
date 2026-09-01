"""Acesso administrativo da plataforma — um único tipo, sem RBAC.

Login exclusivo da área /admin: e-mail allowlist + ADMIN_PASSWORD.
Sessão via JWT próprio (não usa a conta de cliente Supabase).
"""

from __future__ import annotations

import logging
from typing import FrozenSet, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.admin.session import is_admin_login_email, verify_admin_token
from app.auth import security

logger = logging.getLogger(__name__)


def get_admin_emails() -> FrozenSet[str]:
    from app.admin.session import _parse_emails

    return _parse_emails()


def get_admin_user_ids() -> FrozenSet[str]:
    return frozenset()


def is_platform_admin(user: dict) -> bool:
    email = (user.get("email") or "").strip().lower()
    return is_admin_login_email(email)


async def require_platform_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Bearer da sessão /admin/login. Sem hierarquia de papéis."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Autenticação administrativa necessária.")
    return verify_admin_token(credentials.credentials)
