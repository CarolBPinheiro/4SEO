"""Tests for platform admin allowlist (no RBAC)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.admin.deps import is_platform_admin, require_platform_admin
from app.billing.access import path_requires_subscription


class TestAdminAllowlist:
    def test_not_admin_when_empty_config(self, monkeypatch):
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
        assert is_platform_admin({"email": "owner@4seo.app", "user_id": "u1"}) is False

    def test_admin_by_email(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "owner@4seo.app, ops@4seo.app")
        monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
        assert is_platform_admin({"email": "Owner@4seo.app", "user_id": "u1"}) is True
        assert is_platform_admin({"email": "user@example.com", "user_id": "u2"}) is False

    def test_admin_by_user_id(self, monkeypatch):
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        monkeypatch.setenv("ADMIN_USER_IDS", "abc-123")
        assert is_platform_admin({"email": "x@y.com", "user_id": "ABC-123"}) is True

    @pytest.mark.asyncio
    async def test_require_admin_forbidden(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "owner@4seo.app")
        with pytest.raises(HTTPException) as exc:
            await require_platform_admin(
                {"email": "user@example.com", "user_id": "u1"}
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_ok(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "owner@4seo.app")
        user = await require_platform_admin(
            {"email": "owner@4seo.app", "user_id": "u1"}
        )
        assert user["email"] == "owner@4seo.app"


class TestAdminPathExemptFromSubscription:
    def test_admin_api_does_not_require_subscription(self):
        assert path_requires_subscription("/api/admin/users") is False
        assert path_requires_subscription("/api/admin/me") is False
        assert path_requires_subscription("/api/termos") is True
