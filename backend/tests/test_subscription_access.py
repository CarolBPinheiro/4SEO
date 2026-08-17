"""Tests for subscription access control (auth ≠ entitlement)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.billing.access import (
    is_entitled_status,
    path_requires_subscription,
    enforce_subscription_middleware,
)


class TestPathRequiresSubscription:
    def test_billing_and_health_exempt(self):
        assert path_requires_subscription("/api/health") is False
        assert path_requires_subscription("/api/billing/subscription") is False
        assert path_requires_subscription("/api/billing/claim-checkout") is False
        assert path_requires_subscription("/api/webhooks/asaas") is False

    def test_product_apis_require_subscription(self):
        assert path_requires_subscription("/api/dashboard/summary") is True
        assert path_requires_subscription("/api/termos") is True
        assert path_requires_subscription("/api/integrations/status") is True
        assert path_requires_subscription("/api/nuvemshop/products") is True
        assert path_requires_subscription("/api/panorama") is True
        assert path_requires_subscription("/api/historico") is True

    def test_oauth_callbacks_exempt(self):
        assert path_requires_subscription("/api/shopify/oauth-redirect") is False
        assert path_requires_subscription("/api/nuvemshop/oauth-redirect") is False
        assert path_requires_subscription("/api/gsc/callback") is False


class TestEntitledStatus:
    def test_active_statuses(self):
        assert is_entitled_status("active") is True
        assert is_entitled_status("trialing") is True
        assert is_entitled_status("past_due") is True

    def test_inactive_statuses(self):
        assert is_entitled_status("canceled") is False
        assert is_entitled_status("expired") is False
        assert is_entitled_status("none") is False
        assert is_entitled_status(None) is False

    def test_full_access_excludes_trialing(self):
        from app.billing.access import is_full_access_status

        assert is_full_access_status("active") is True
        assert is_full_access_status("past_due") is True
        assert is_full_access_status("trialing") is False
        assert is_full_access_status("none") is False

    @pytest.mark.asyncio
    async def test_product_access_allows_valid_trial(self):
        from app.billing.access import user_has_active_subscription

        with patch(
            "app.billing.access.BillingRepository"
        ) as repo_cls:
            instance = repo_cls.return_value
            instance.get_active_subscription_for_user = AsyncMock(return_value=None)
            instance.get_valid_trial_for_user = AsyncMock(
                return_value={"id": "t1", "status": "trialing"}
            )
            assert await user_has_active_subscription("user-1") is True

    @pytest.mark.asyncio
    async def test_product_access_denies_without_full_or_trial(self):
        from app.billing.access import user_has_active_subscription

        with patch(
            "app.billing.access.BillingRepository"
        ) as repo_cls:
            instance = repo_cls.return_value
            instance.get_active_subscription_for_user = AsyncMock(return_value=None)
            instance.get_valid_trial_for_user = AsyncMock(return_value=None)
            assert await user_has_active_subscription("user-1") is False


@pytest.fixture
def gated_app():
    app = FastAPI()

    @app.middleware("http")
    async def gate(request, call_next):
        return await enforce_subscription_middleware(request, call_next)

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    @app.get("/api/billing/subscription")
    async def billing_sub():
        return {"status": "none"}

    @app.get("/api/termos")
    async def termos():
        return {"items": []}

    return app


class TestSubscriptionMiddleware:
    def test_health_open(self, gated_app):
        client = TestClient(gated_app)
        assert client.get("/api/health").status_code == 200

    def test_billing_open_without_token(self, gated_app):
        client = TestClient(gated_app)
        assert client.get("/api/billing/subscription").status_code == 200

    def test_product_without_token_passes_to_route(self, gated_app):
        """Sem Bearer, middleware não bloqueia — a rota (ou 404) decide."""
        client = TestClient(gated_app)
        assert client.get("/api/termos").status_code == 200

    def test_product_with_token_without_subscription_returns_402(self, gated_app):
        client = TestClient(gated_app)

        with patch("app.billing.access._decode_token", return_value={"sub": "user-1"}), patch(
            "app.billing.access.user_has_active_subscription",
            new_callable=AsyncMock,
            return_value=False,
        ):
            res = client.get(
                "/api/termos",
                headers={"Authorization": "Bearer fake.jwt.token"},
            )
        assert res.status_code == 402
        body = res.json()
        assert body.get("code") == "subscription_required"

    def test_product_with_active_subscription_allows(self, gated_app):
        client = TestClient(gated_app)

        with patch("app.billing.access._decode_token", return_value={"sub": "user-1"}), patch(
            "app.billing.access.user_has_active_subscription",
            new_callable=AsyncMock,
            return_value=True,
        ):
            res = client.get(
                "/api/termos",
                headers={"Authorization": "Bearer fake.jwt.token"},
            )
        assert res.status_code == 200
        assert res.json() == {"items": []}
