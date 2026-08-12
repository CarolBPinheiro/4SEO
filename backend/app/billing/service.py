"""Regras de negócio do billing (checkout Asaas + webhooks)."""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.billing import asaas_client
from app.billing.plans import (
    get_cycle,
    get_plan,
    get_plan_price,
    is_billing_cycle,
    is_plan_id,
    to_asaas_cycle,
)
from app.billing.repository import BillingRepository
from app.billing.schemas import CreateCheckoutResponse, SubscriptionResponse

logger = logging.getLogger(__name__)

MINUTES_TO_EXPIRE = 60


def _app_public_url() -> str:
    return (
        os.getenv("APP_PUBLIC_URL")
        or os.getenv("MARKETING_URL")
        or "http://localhost:3000"
    ).rstrip("/")


def _next_due_date_iso() -> str:
    # nextDueDate no dia seguinte (timezone-aware UTC → date)
    return (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")


class BillingService:
    def __init__(self, repo: Optional[BillingRepository] = None):
        self.repo = repo or BillingRepository()

    async def create_checkout_session(
        self,
        *,
        plan_id: str,
        billing_cycle: str,
        user_id: Optional[str] = None,
    ) -> CreateCheckoutResponse:
        if not is_plan_id(plan_id) or not is_billing_cycle(billing_cycle):
            raise BillingValidationError("Plano ou ciclo de cobrança inválido.")

        if not asaas_client.is_asaas_configured():
            raise BillingUnavailableError(
                "Billing Asaas não configurado. Defina ASAAS_API_KEY no servidor."
            )

        plan = get_plan(plan_id)
        cycle = get_cycle(billing_cycle)
        price = get_plan_price(plan_id, billing_cycle)
        external_reference = f"4seo_{plan_id}_{billing_cycle}_{uuid.uuid4().hex[:12]}"
        public_url = _app_public_url()
        success_url = f"{public_url}/checkout/sucesso?ref={external_reference}"
        cancel_url = f"{public_url}/checkout/cancelado?ref={external_reference}"
        expired_url = f"{public_url}/checkout/expirado?ref={external_reference}"

        payload: Dict[str, Any] = {
            "billingTypes": ["CREDIT_CARD", "PIX"],
            "chargeTypes": ["RECURRENT"],
            "minutesToExpire": MINUTES_TO_EXPIRE,
            "externalReference": external_reference,
            "callback": {
                "successUrl": success_url,
                "cancelUrl": cancel_url,
                "expiredUrl": expired_url,
            },
            "items": [
                {
                    "name": f"4SEO {plan['name']}",
                    "description": (
                        f"Assinatura {cycle['label'].lower()} 4SEO {plan['name']}"
                    ),
                    "quantity": 1,
                    "value": float(price["total"]),
                }
            ],
            "subscription": {
                "cycle": to_asaas_cycle(billing_cycle),
                "nextDueDate": _next_due_date_iso(),
            },
        }

        try:
            asaas_response = await asaas_client.create_checkout(payload)
        except asaas_client.AsaasConfigError as exc:
            raise BillingUnavailableError(str(exc)) from exc
        except asaas_client.AsaasApiError as exc:
            status = exc.status_code or 502
            if status >= 500 or status == 429:
                raise BillingUpstreamError(str(exc)) from exc
            raise BillingUpstreamError(str(exc), status_code=502) from exc

        checkout_id = str(asaas_response.get("id") or "").strip()
        checkout_url = str(asaas_response.get("link") or "").strip()
        if not checkout_id or not checkout_url:
            logger.error("Asaas checkout response missing id/link")
            raise BillingUpstreamError("Resposta incompleta do Asaas.")

        minutes = int(asaas_response.get("minutesToExpire") or MINUTES_TO_EXPIRE)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=minutes)
        ).isoformat()

        record = {
            "external_reference": external_reference,
            "asaas_checkout_id": checkout_id,
            "checkout_url": checkout_url,
            "plan_id": plan_id,
            "billing_cycle": billing_cycle,
            "amount": float(price["total"]),
            "status": "pending",
            "expires_at": expires_at,
            "user_id": user_id,
        }
        try:
            await self.repo.create_checkout_record(record)
        except Exception:
            # Checkout já criado no Asaas — não falhar o redirect do usuário
            logger.exception(
                "Falha ao persistir billing_checkouts para %s", checkout_id
            )

        return CreateCheckoutResponse(
            checkoutUrl=checkout_url,
            checkoutId=checkout_id,
            expiresAt=expires_at,
        )

    async def get_subscription_for_user(self, user_id: str) -> SubscriptionResponse:
        row = await self.repo.get_active_subscription_for_user(user_id)
        if not row:
            return SubscriptionResponse(status="none")
        return SubscriptionResponse(
            status=row.get("status") or "none",
            planId=row.get("plan_id"),
            billingCycle=row.get("billing_cycle"),
            asaasSubscriptionId=row.get("asaas_subscription_id"),
            asaasCustomerId=row.get("asaas_customer_id"),
            currentPeriodEnd=row.get("current_period_end"),
            updatedAt=row.get("updated_at"),
        )

    async def claim_checkout_for_user(
        self, *, user_id: str, external_reference: str
    ) -> SubscriptionResponse:
        """Vincula checkout/assinatura anônimos ao usuário autenticado."""
        ref = (external_reference or "").strip()
        if not ref or not ref.startswith("4seo_"):
            raise BillingValidationError("Referência de checkout inválida.")

        checkout = await self.repo.get_checkout_by_external_reference(ref)
        if not checkout:
            raise BillingValidationError("Checkout não encontrado.")

        if checkout.get("user_id") and checkout["user_id"] != user_id:
            raise BillingValidationError(
                "Este checkout já está vinculado a outra conta."
            )

        await self.repo.attach_user_to_checkout(
            asaas_checkout_id=checkout["asaas_checkout_id"],
            user_id=user_id,
        )
        await self.repo.attach_user_to_subscription_by_checkout(
            asaas_checkout_id=checkout["asaas_checkout_id"],
            user_id=user_id,
        )

        # Se já pago e ainda não há assinatura, materializa
        if checkout.get("status") == "paid":
            existing = await self.repo.get_active_subscription_for_user(user_id)
            if not existing:
                await self.repo.activate_subscription_from_checkout(
                    checkout={**checkout, "user_id": user_id},
                    asaas_customer_id=None,
                    asaas_subscription_id=None,
                    status="active",
                )

        return await self.get_subscription_for_user(user_id)

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        event_id = str(payload.get("id") or "").strip()
        event_type = str(payload.get("event") or "").strip()
        if not event_id or not event_type:
            raise BillingValidationError("Webhook sem id ou event.")

        inserted = await self.repo.try_insert_webhook_event(
            event_id, event_type, payload
        )
        if not inserted:
            return

        try:
            await self._dispatch_event(event_type, payload)
            await self.repo.mark_webhook_processed(event_id)
        except Exception:
            logger.exception("Falha ao processar webhook Asaas event=%s", event_type)
            # Já respondemos 200 após persistir; reprocessamento manual possível
            raise

    async def _dispatch_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        checkout = payload.get("checkout") or {}
        payment = payload.get("payment") or {}
        subscription = payload.get("subscription") or {}

        if event_type in {
            "CHECKOUT_PAID",
            "CHECKOUT_CREATED",
            "CHECKOUT_CANCELED",
            "CHECKOUT_EXPIRED",
        }:
            await self._handle_checkout_event(event_type, checkout)
            return

        if event_type in {
            "SUBSCRIPTION_CREATED",
            "SUBSCRIPTION_UPDATED",
            "SUBSCRIPTION_INACTIVATED",
            "SUBSCRIPTION_DELETED",
            "SUBSCRIPTION_RENEWED",
        }:
            await self._handle_subscription_event(event_type, subscription, payment)
            return

        if event_type in {
            "PAYMENT_CONFIRMED",
            "PAYMENT_RECEIVED",
            "PAYMENT_OVERDUE",
            "PAYMENT_REFUNDED",
            "PAYMENT_DELETED",
        }:
            await self._handle_payment_event(event_type, payment)
            return

        logger.info("Webhook Asaas ignorado (não tratado): %s", event_type)

    async def _handle_checkout_event(
        self, event_type: str, checkout: Dict[str, Any]
    ) -> None:
        asaas_checkout_id = str(checkout.get("id") or "").strip()
        if not asaas_checkout_id:
            return

        status_map = {
            "CHECKOUT_CREATED": "pending",
            "CHECKOUT_PAID": "paid",
            "CHECKOUT_CANCELED": "canceled",
            "CHECKOUT_EXPIRED": "expired",
        }
        local_status = status_map.get(event_type, "pending")
        await self.repo.update_checkout_by_asaas_id(
            asaas_checkout_id, {"status": local_status}
        )

        if event_type != "CHECKOUT_PAID":
            return

        local = await self.repo.get_checkout_by_asaas_id(asaas_checkout_id)
        if not local:
            logger.warning(
                "CHECKOUT_PAID sem registro local checkout_id=%s", asaas_checkout_id
            )
            return

        customer = checkout.get("customer")
        customer_id = customer if isinstance(customer, str) else None
        sub = checkout.get("subscription") or {}
        # A assinatura criada pelo checkout pode chegar só em eventos SUBSCRIPTION_*
        sub_id = sub.get("id") if isinstance(sub, dict) else None

        await self.repo.activate_subscription_from_checkout(
            checkout=local,
            asaas_customer_id=customer_id,
            asaas_subscription_id=sub_id,
            status="active",
        )

    async def _handle_subscription_event(
        self,
        event_type: str,
        subscription: Dict[str, Any],
        payment: Dict[str, Any],
    ) -> None:
        sub_id = str(subscription.get("id") or "").strip()
        if not sub_id:
            return

        status_map = {
            "SUBSCRIPTION_CREATED": "active",
            "SUBSCRIPTION_UPDATED": "active",
            "SUBSCRIPTION_RENEWED": "active",
            "SUBSCRIPTION_INACTIVATED": "inactive",
            "SUBSCRIPTION_DELETED": "canceled",
        }
        status = status_map.get(event_type, "active")
        extra: Dict[str, Any] = {}
        customer = subscription.get("customer")
        if isinstance(customer, str):
            extra["asaas_customer_id"] = customer
        await self.repo.update_subscription_status_by_asaas_id(sub_id, status, extra)

        # Se ainda não há linha (checkout pago sem sub id), cria a partir do payment.externalReference
        # via update no-op já feito; criação completa fica no CHECKOUT_PAID.

    async def _handle_payment_event(
        self, event_type: str, payment: Dict[str, Any]
    ) -> None:
        sub_id = str(payment.get("subscription") or "").strip()
        if not sub_id:
            return
        if event_type in {"PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"}:
            await self.repo.update_subscription_status_by_asaas_id(sub_id, "active")
        elif event_type == "PAYMENT_OVERDUE":
            await self.repo.update_subscription_status_by_asaas_id(sub_id, "past_due")
        elif event_type in {"PAYMENT_REFUNDED", "PAYMENT_DELETED"}:
            await self.repo.update_subscription_status_by_asaas_id(sub_id, "canceled")


class BillingValidationError(ValueError):
    pass


class BillingUnavailableError(RuntimeError):
    pass


class BillingUpstreamError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def verify_webhook_token(header_value: Optional[str]) -> bool:
    expected = (os.getenv("ASAAS_WEBHOOK_TOKEN") or "").strip()
    if not expected:
        logger.error("ASAAS_WEBHOOK_TOKEN não configurado")
        return False
    provided = (header_value or "").strip()
    if not provided:
        return False
    return secrets.compare_digest(provided, expected)
