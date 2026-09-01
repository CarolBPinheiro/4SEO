"""Testes do login exclusivo do painel admin."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.admin.session import (
    admin_login_configured,
    is_admin_login_email,
    issue_admin_token,
    password_matches,
    verify_admin_token,
)
from app.billing.access import path_requires_subscription


class TestAdminLoginCredentials:
    def test_not_configured_without_password(self, monkeypatch):
        monkeypatch.setenv("ADMIN_LOGIN_EMAIL", "ops@4seo.app")
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        assert admin_login_configured() is False

    def test_email_allowlist(self, monkeypatch):
        monkeypatch.setenv("ADMIN_LOGIN_EMAIL", "ops@4seo.app")
        monkeypatch.setenv("ADMIN_EMAILS", "financeiro@4seo.app")
        monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-admin")
        assert is_admin_login_email("Ops@4seo.app") is True
        assert is_admin_login_email("financeiro@4seo.app") is True
        assert is_admin_login_email("user@example.com") is False

    def test_password_matches(self, monkeypatch):
        monkeypatch.setenv("ADMIN_LOGIN_EMAIL", "ops@4seo.app")
        monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-admin")
        assert password_matches("senha-forte-admin") is True
        assert password_matches("outra") is False


class TestAdminSessionToken:
    def test_issue_and_verify(self, monkeypatch):
        monkeypatch.setenv("ADMIN_LOGIN_EMAIL", "ops@4seo.app")
        monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-admin")
        monkeypatch.setenv("ADMIN_SESSION_SECRET", "x" * 32)
        token = issue_admin_token("ops@4seo.app")
        principal = verify_admin_token(token)
        assert principal["email"] == "ops@4seo.app"
        assert principal["role"] == "platform_admin"

    def test_invalid_token(self, monkeypatch):
        monkeypatch.setenv("ADMIN_LOGIN_EMAIL", "ops@4seo.app")
        monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-admin")
        monkeypatch.setenv("ADMIN_SESSION_SECRET", "x" * 32)
        with pytest.raises(HTTPException) as exc:
            verify_admin_token("token-invalido")
        assert exc.value.status_code == 401


class TestAdminPathExemptFromSubscription:
    def test_admin_api_does_not_require_subscription(self):
        assert path_requires_subscription("/api/admin/users") is False
        assert path_requires_subscription("/api/admin/login") is False
        assert path_requires_subscription("/api/admin/me") is False
        assert path_requires_subscription("/api/termos") is True
