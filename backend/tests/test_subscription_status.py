"""Tests for subscription status resolution (entitlement vs UX status)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.billing.service import BillingService


@pytest.mark.asyncio
async def test_get_subscription_prefers_full_access():
    repo = MagicMock()
    repo.get_active_subscription_for_user = AsyncMock(
        return_value={
            "status": "active",
            "plan_id": "pro",
            "billing_cycle": "monthly",
            "asaas_subscription_id": "sub_1",
            "asaas_customer_id": "cus_1",
            "current_period_end": None,
            "trial_ends_at": None,
            "updated_at": "2026-08-12T00:00:00Z",
        }
    )
    repo.get_valid_trial_for_user = AsyncMock()
    repo.get_latest_subscription_for_user = AsyncMock()
    repo.get_pending_checkout_for_user = AsyncMock()

    service = BillingService(repo=repo)
    result = await service.get_subscription_for_user("user-1")

    assert result.status == "active"
    assert result.accessLevel == "full"
    assert result.planId == "pro"
    repo.get_valid_trial_for_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_subscription_returns_trial_access():
    repo = MagicMock()
    repo.get_active_subscription_for_user = AsyncMock(return_value=None)
    repo.get_valid_trial_for_user = AsyncMock(
        return_value={
            "status": "trialing",
            "plan_id": "start",
            "billing_cycle": "monthly",
            "trial_ends_at": "2099-01-01T00:00:00+00:00",
            "updated_at": "2026-08-12T00:00:00Z",
        }
    )
    repo.get_latest_subscription_for_user = AsyncMock()
    repo.get_pending_checkout_for_user = AsyncMock()

    service = BillingService(repo=repo)
    result = await service.get_subscription_for_user("user-1")

    assert result.status == "trialing"
    assert result.accessLevel == "trial"
    assert result.planId == "start"


@pytest.mark.asyncio
async def test_get_subscription_pending_from_checkout():
    repo = MagicMock()
    repo.get_active_subscription_for_user = AsyncMock(return_value=None)
    repo.get_valid_trial_for_user = AsyncMock(return_value=None)
    repo.get_latest_subscription_for_user = AsyncMock(return_value=None)
    repo.get_pending_checkout_for_user = AsyncMock(
        return_value={
            "status": "pending",
            "plan_id": "scale",
            "billing_cycle": "annual",
            "updated_at": "2026-08-12T00:00:00Z",
        }
    )

    service = BillingService(repo=repo)
    result = await service.get_subscription_for_user("user-1")

    assert result.status == "pending"
    assert result.accessLevel == "none"
    assert result.planId == "scale"


@pytest.mark.asyncio
async def test_start_trial_creates_once():
    repo = MagicMock()
    repo.get_active_subscription_for_user = AsyncMock(return_value=None)
    repo.get_valid_trial_for_user = AsyncMock(return_value=None)
    repo.user_has_used_trial = AsyncMock(return_value=False)
    repo.create_trial_subscription = AsyncMock(
        return_value={
            "status": "trialing",
            "plan_id": "pro",
            "billing_cycle": "monthly",
            "trial_ends_at": "2099-01-08T00:00:00+00:00",
            "updated_at": "2026-08-12T00:00:00Z",
        }
    )

    service = BillingService(repo=repo)
    result = await service.start_trial(user_id="user-1", plan_id="pro")

    assert result.accessLevel == "trial"
    assert result.planId == "pro"
    repo.create_trial_subscription.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_trial_rejects_reuse():
    from app.billing.service import BillingValidationError

    repo = MagicMock()
    repo.get_active_subscription_for_user = AsyncMock(return_value=None)
    repo.get_valid_trial_for_user = AsyncMock(return_value=None)
    repo.user_has_used_trial = AsyncMock(return_value=True)

    service = BillingService(repo=repo)
    with pytest.raises(BillingValidationError):
        await service.start_trial(user_id="user-1", plan_id="pro")
