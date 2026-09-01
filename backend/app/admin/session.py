"""Sessão exclusiva do painel admin — independente do login de clientes.

Credenciais: ADMIN_LOGIN_EMAIL (e/ou ADMIN_EMAILS) + ADMIN_PASSWORD no ambiente.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import FrozenSet

import jwt
from fastapi import HTTPException

ADMIN_TOKEN_TTL_HOURS = 8
ADMIN_JWT_ISS = "4seo-admin"
ADMIN_JWT_AUD = "platform_admin"


def _parse_emails() -> FrozenSet[str]:
    raw = (os.getenv("ADMIN_EMAILS") or "").strip()
    items = {part.strip().lower() for part in raw.split(",") if part.strip()}
    login = (os.getenv("ADMIN_LOGIN_EMAIL") or "").strip().lower()
    if login:
        items.add(login)
    return frozenset(items)


def get_admin_password() -> str:
    return (os.getenv("ADMIN_PASSWORD") or "").strip()


def admin_login_configured() -> bool:
    return bool(_parse_emails() and get_admin_password())


def is_admin_login_email(email: str) -> bool:
    candidate = (email or "").strip().lower()
    if not candidate:
        return False
    return candidate in _parse_emails()


def _sha256(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _secure_eq(left: str, right: str) -> bool:
    return hmac.compare_digest(_sha256(left), _sha256(right))


def password_matches(provided: str) -> bool:
    expected = get_admin_password()
    if not expected:
        return False
    return _secure_eq(provided or "", expected)


def admin_session_secret() -> str:
    explicit = (os.getenv("ADMIN_SESSION_SECRET") or "").strip()
    if len(explicit) >= 32:
        return explicit
    password = get_admin_password()
    jwt_secret = (os.getenv("SUPABASE_JWT_SECRET") or os.getenv("JWT_SECRET") or "").strip()
    if not password:
        return ""
    return hashlib.sha256(f"4seo-admin|{password}|{jwt_secret}".encode("utf-8")).hexdigest()


def issue_admin_token(email: str) -> str:
    secret = admin_session_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Sessão administrativa não configurada.")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "platform-admin",
        "email": email.strip().lower(),
        "role": "platform_admin",
        "iss": ADMIN_JWT_ISS,
        "aud": ADMIN_JWT_AUD,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ADMIN_TOKEN_TTL_HOURS)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_admin_token(token: str) -> dict:
    secret = admin_session_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Sessão administrativa não configurada.")
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=ADMIN_JWT_AUD,
            issuer=ADMIN_JWT_ISS,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessão administrativa expirada.")
    except (jwt.InvalidTokenError, jwt.exceptions.DecodeError):
        raise HTTPException(status_code=401, detail="Sessão administrativa inválida.")
    email = str(payload.get("email") or "").strip().lower()
    if not is_admin_login_email(email):
        raise HTTPException(status_code=401, detail="Sessão administrativa inválida.")
    return {
        "user_id": None,
        "email": email,
        "role": "platform_admin",
    }
