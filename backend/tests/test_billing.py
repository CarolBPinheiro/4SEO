"""
Tests for billing module (Asaas checkout + webhooks).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.billing.plans import get_plan_price, is_billing_cycle, is_plan_id, to_asaas_cycle
from app.billing.rate_limit import InMemoryRateLimiter
from app.billing.router import router as billing_router
from app.billing.service import (
    BillingService,
    BillingUnavailableError,
    BillingValidationError,
    verify_webhook_token,
)


class TestPlansCatalog:
    def test_canonical_prices_match_frontend_pro_monthly(self):
        assert get_plan_price("pro", "monthly")["total"] == 199.0

    def test_asaas_cycle_mapping(self):
        assert to_asaas_cycle("monthly") == "MONTHLY"
        assert to_asaas_cycle("semiannual") == "SEMIANNUALLY"
        assert to_asaas_cycle("annual") == "YEARLY"

    def test_invalid_ids(self):
        assert not is_plan_id("enterprise")
        assert not is_billing_cycle("weekly")


class TestRateLimiter:
    def test_allows_until_limit(self):
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        assert limiter.allow("a") is True
        assert limiter.allow("a") is True
        assert limiter.allow("a") is False
        assert limiter.allow("b") is True


class TestWebhookToken:
    def test_rejects_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("ASAAS_WEBHOOK_TOKEN", raising=False)
        assert verify_webhook_token("anything") is False

    def test_accepts_matching_token(self, monkeypatch):
        monkeypatch.setenv("ASAAS_WEBHOOK_TOKEN", "whsec_test_token_32chars_minimum!!")
        assert verify_webhook_token("whsec_test_token_32chars_minimum!!") is True
        assert verify_webhook_token("wrong") is False


@pytest.fixture
def billing_app(monkeypatch):
    monkeypatch.setenv("ASAAS_WEBHOOK_TOKEN", "whsec_test_token_32chars_minimum!!")
    monkeypatch.setenv("ASAAS_API_KEY", "test_asaas_key")
    monkeypatch.setenv("ASAAS_BASE_URL", "https://api-sandbox.asaas.com/v3")
    monkeypatch.setenv("APP_PUBLIC_URL", "http://localhost:3000")

    app = FastAPI()
    app.include_router(billing_router)
    return app


class TestCheckoutEndpoint:
    def test_rejects_invalid_plan(self, billing_app):
        client = TestClient(billing_app)
        response = client.post(
            "/billing/checkout",
            json={"planId": "invalid", "billingCycle": "monthly"},
        )
        assert response.status_code == 400
        assert "message" in response.json()

    def test_returns_503_without_api_key(self, billing_app, monkeypatch):
        monkeypatch.delenv("ASAAS_API_KEY", raising=False)
        client = TestClient(billing_app)
        response = client.post(
            "/billing/checkout",
            json={"planId": "pro", "billingCycle": "monthly"},
        )
        assert response.status_code == 503

    def test_creates_checkout_session(self, billing_app):
        mock_repo = MagicMock()
        mock_repo.create_checkout_record = AsyncMock(return_value={})
        captured: dict = {}

        async def fake_create(payload):
            captured["payload"] = payload
            return {
                "id": "chk_test_123",
                "link": "https://sandbox.asaas.com/checkoutSession/show/chk_test_123",
                "minutesToExpire": 60,
            }

        with patch("app.billing.service.asaas_client.create_checkout", side_effect=fake_create), patch(
            "app.billing.router.BillingService",
            return_value=BillingService(repo=mock_repo),
        ):
            client = TestClient(billing_app)
            response = client.post(
                "/billing/checkout",
                json={"planId": "pro", "billingCycle": "monthly"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["checkoutId"] == "chk_test_123"
        assert body["checkoutUrl"].startswith("https://")
        assert "expiresAt" in body
        assert captured["payload"]["billingTypes"] == ["CREDIT_CARD"]
        assert captured["payload"]["chargeTypes"] == ["RECURRENT"]
        mock_repo.create_checkout_record.assert_awaited()


class TestWebhookEndpoint:
    def test_rejects_missing_token(self, billing_app):
        client = TestClient(billing_app)
        response = client.post("/webhooks/asaas", json={"id": "evt_1", "event": "CHECKOUT_PAID"})
        assert response.status_code == 401

    def test_idempotent_processing(self, billing_app):
        mock_repo = MagicMock()
        mock_repo.try_insert_webhook_event = AsyncMock(return_value=False)
        mock_repo.mark_webhook_processed = AsyncMock()
        mock_repo.update_checkout_by_asaas_id = AsyncMock()

        with patch(
            "app.billing.router.BillingService",
            return_value=BillingService(repo=mock_repo),
        ):
            client = TestClient(billing_app)
            response = client.post(
                "/webhooks/asaas",
                headers={"asaas-access-token": "whsec_test_token_32chars_minimum!!"},
                json={
                    "id": "evt_dup",
                    "event": "CHECKOUT_PAID",
                    "checkout": {"id": "chk_1"},
                },
            )

        assert response.status_code == 200
        mock_repo.update_checkout_by_asaas_id.assert_not_awaited()

    def test_checkout_paid_activates_subscription(self, billing_app):
        mock_repo = MagicMock()
        mock_repo.try_insert_webhook_event = AsyncMock(return_value=True)
        mock_repo.mark_webhook_processed = AsyncMock()
        mock_repo.update_checkout_by_asaas_id = AsyncMock()
        mock_repo.get_checkout_by_asaas_id = AsyncMock(
            return_value={
                "asaas_checkout_id": "chk_1",
                "plan_id": "pro",
                "billing_cycle": "monthly",
                "amount": 199.0,
                "user_id": None,
            }
        )
        mock_repo.activate_subscription_from_checkout = AsyncMock(return_value={})

        with patch(
            "app.billing.router.BillingService",
            return_value=BillingService(repo=mock_repo),
        ):
            client = TestClient(billing_app)
            response = client.post(
                "/webhooks/asaas",
                headers={"asaas-access-token": "whsec_test_token_32chars_minimum!!"},
                json={
                    "id": "evt_paid",
                    "event": "CHECKOUT_PAID",
                    "checkout": {"id": "chk_1", "customer": "cus_1"},
                },
            )

        assert response.status_code == 200
        mock_repo.activate_subscription_from_checkout.assert_awaited()
        mock_repo.mark_webhook_processed.assert_awaited_with("evt_paid")


class TestAsaasErrorParsing:
    def test_invalid_environment_message(self):
        from app.billing.asaas_client import _safe_asaas_error_message

        class _Resp:
            def json(self):
                return {
                    "errors": [
                        {
                            "code": "invalid_environment",
                            "description": "A chave de API informada não pertence a este ambiente",
                        }
                    ]
                }

        message, code = _safe_asaas_error_message(_Resp())  # type: ignore[arg-type]
        assert code == "invalid_environment"
        assert "sandbox vs produção" in message


class TestBillingServiceValidation:
    @pytest.mark.asyncio
    async def test_invalid_plan_raises(self):
        service = BillingService(repo=MagicMock())
        with pytest.raises(BillingValidationError):
            await service.create_checkout_session(
                plan_id="nope", billing_cycle="monthly"
            )

    @pytest.mark.asyncio
    async def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("ASAAS_API_KEY", raising=False)
        service = BillingService(repo=MagicMock())
        with pytest.raises(BillingUnavailableError):
            await service.create_checkout_session(
                plan_id="pro", billing_cycle="monthly"
            )

    @pytest.mark.asyncio
    async def test_claim_checkout_attaches_user(self):
        mock_repo = MagicMock()
        mock_repo.get_checkout_by_external_reference = AsyncMock(
            return_value={
                "asaas_checkout_id": "chk_1",
                "status": "paid",
                "plan_id": "pro",
                "billing_cycle": "monthly",
                "amount": 199.0,
                "user_id": None,
            }
        )
        mock_repo.attach_user_to_checkout = AsyncMock()
        mock_repo.attach_user_to_subscription_by_checkout = AsyncMock()
        mock_repo.get_active_subscription_for_user = AsyncMock(
            side_effect=[
                None,
                {
                    "status": "active",
                    "plan_id": "pro",
                    "billing_cycle": "monthly",
                    "asaas_subscription_id": None,
                    "asaas_customer_id": None,
                    "current_period_end": None,
                    "updated_at": "2026-01-01T00:00:00Z",
                },
            ]
        )
        mock_repo.activate_subscription_from_checkout = AsyncMock(return_value={})

        service = BillingService(repo=mock_repo)
        result = await service.claim_checkout_for_user(
            user_id="user-1",
            external_reference="4seo_pro_monthly_abc123",
        )
        assert result.status == "active"
        assert result.planId == "pro"
        mock_repo.attach_user_to_checkout.assert_awaited()
        mock_repo.activate_subscription_from_checkout.assert_awaited()
