"""DTOs de billing alinhados ao contrato docs/asaas-backend-contract.md."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateCheckoutRequest(BaseModel):
    planId: str
    billingCycle: str


class ClaimCheckoutRequest(BaseModel):
    externalReference: str


class CreateCheckoutResponse(BaseModel):
    checkoutUrl: str
    checkoutId: str
    expiresAt: str


class SubscriptionResponse(BaseModel):
    status: str
    planId: Optional[str] = None
    billingCycle: Optional[str] = None
    asaasSubscriptionId: Optional[str] = None
    asaasCustomerId: Optional[str] = None
    currentPeriodEnd: Optional[str] = None
    updatedAt: Optional[str] = None


class BillingErrorBody(BaseModel):
    message: str
    error: str = Field(default="billing_error")
    statusCode: int
