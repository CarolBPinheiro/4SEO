"""Persistência de billing via Supabase REST (service role)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.supabase_client import SupabaseClient, get_supabase

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BillingRepository:
    def __init__(self, db: Optional[SupabaseClient] = None):
        self.db = db or get_supabase()

    async def create_checkout_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.db._request("POST", "billing_checkouts", data=data)
        if isinstance(result, list) and result:
            return result[0]
        if isinstance(result, dict):
            return result
        return data

    async def update_checkout_by_asaas_id(
        self, asaas_checkout_id: str, patch: Dict[str, Any]
    ) -> None:
        await self.db._request(
            "PATCH",
            f"billing_checkouts?asaas_checkout_id=eq.{asaas_checkout_id}",
            data=patch,
        )

    async def get_checkout_by_asaas_id(
        self, asaas_checkout_id: str
    ) -> Optional[Dict[str, Any]]:
        result = await self.db._request(
            "GET",
            "billing_checkouts",
            params={
                "asaas_checkout_id": f"eq.{asaas_checkout_id}",
                "select": "*",
                "limit": "1",
            },
        )
        if isinstance(result, list) and result:
            return result[0]
        return None

    async def get_checkout_by_external_reference(
        self, external_reference: str
    ) -> Optional[Dict[str, Any]]:
        result = await self.db._request(
            "GET",
            "billing_checkouts",
            params={
                "external_reference": f"eq.{external_reference}",
                "select": "*",
                "limit": "1",
            },
        )
        if isinstance(result, list) and result:
            return result[0]
        return None

    async def attach_user_to_checkout(
        self, *, asaas_checkout_id: str, user_id: str
    ) -> None:
        await self.db._request(
            "PATCH",
            f"billing_checkouts?asaas_checkout_id=eq.{asaas_checkout_id}",
            data={"user_id": user_id, "updated_at": _utc_now_iso()},
        )

    async def attach_user_to_subscription_by_checkout(
        self, *, asaas_checkout_id: str, user_id: str
    ) -> None:
        await self.db._request(
            "PATCH",
            f"subscriptions?asaas_checkout_id=eq.{asaas_checkout_id}",
            data={"user_id": user_id, "updated_at": _utc_now_iso()},
        )
    async def try_insert_webhook_event(
        self, event_id: str, event_type: str, payload: Dict[str, Any]
    ) -> bool:
        """Insere evento para idempotência. Retorna False se já existir."""
        try:
            await self.db._request(
                "POST",
                "billing_webhook_events",
                data={
                    "event_id": event_id,
                    "event_type": event_type,
                    "payload": payload,
                },
            )
            return True
        except Exception as exc:
            msg = str(exc).lower()
            if "409" in msg or "duplicate" in msg or "unique" in msg:
                logger.info("Webhook event already processed: %s", event_id)
                return False
            raise

    async def mark_webhook_processed(self, event_id: str) -> None:
        await self.db._request(
            "PATCH",
            f"billing_webhook_events?event_id=eq.{event_id}",
            data={"processed_at": _utc_now_iso()},
        )

    async def activate_subscription_from_checkout(
        self,
        *,
        checkout: Dict[str, Any],
        asaas_customer_id: Optional[str],
        asaas_subscription_id: Optional[str],
        status: str = "active",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "plan_id": checkout.get("plan_id"),
            "billing_cycle": checkout.get("billing_cycle"),
            "status": status,
            "asaas_checkout_id": checkout.get("asaas_checkout_id"),
            "amount": checkout.get("amount"),
            "currency": "BRL",
            "updated_at": _utc_now_iso(),
        }
        if checkout.get("user_id"):
            payload["user_id"] = checkout["user_id"]
        if asaas_customer_id:
            payload["asaas_customer_id"] = asaas_customer_id
        if asaas_subscription_id:
            payload["asaas_subscription_id"] = asaas_subscription_id

        checkout_id = checkout.get("asaas_checkout_id")
        if checkout_id:
            existing = await self.db._request(
                "GET",
                "subscriptions",
                params={
                    "asaas_checkout_id": f"eq.{checkout_id}",
                    "select": "*",
                    "limit": "1",
                },
            )
            if isinstance(existing, list) and existing:
                updated = await self.db._request(
                    "PATCH",
                    f"subscriptions?id=eq.{existing[0]['id']}",
                    data=payload,
                )
                if isinstance(updated, list) and updated:
                    return updated[0]
                return existing[0]

        created = await self.db._request("POST", "subscriptions", data=payload)
        if isinstance(created, list) and created:
            return created[0]
        return payload

    async def get_active_subscription_for_user(
        self, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Assinatura paga/entitulada (active|past_due). Trial NÃO entra aqui."""
        result = await self.db._request(
            "GET",
            "subscriptions",
            params={
                "user_id": f"eq.{user_id}",
                "status": "in.(active,past_due)",
                "select": "*",
                "order": "updated_at.desc",
                "limit": "1",
            },
        )
        if isinstance(result, list) and result:
            return result[0]
        return None

    async def get_valid_trial_for_user(
        self, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Trial trialing com trial_ends_at no futuro."""
        result = await self.db._request(
            "GET",
            "subscriptions",
            params={
                "user_id": f"eq.{user_id}",
                "status": "eq.trialing",
                "select": "*",
                "order": "updated_at.desc",
                "limit": "1",
            },
        )
        if not isinstance(result, list) or not result:
            return None
        row = result[0]
        ends = row.get("trial_ends_at")
        if not ends:
            return None
        try:
            ends_dt = datetime.fromisoformat(str(ends).replace("Z", "+00:00"))
        except ValueError:
            return None
        if ends_dt.tzinfo is None:
            ends_dt = ends_dt.replace(tzinfo=timezone.utc)
        if ends_dt <= datetime.now(timezone.utc):
            return None
        return row

    async def user_has_used_trial(self, user_id: str) -> bool:
        """Qualquer assinatura que já tenha iniciado trial (impede novo trial)."""
        result = await self.db._request(
            "GET",
            "subscriptions",
            params={
                "user_id": f"eq.{user_id}",
                "trial_started_at": "not.is.null",
                "select": "id",
                "limit": "1",
            },
        )
        return isinstance(result, list) and len(result) > 0

    async def create_trial_subscription(
        self,
        *,
        user_id: str,
        plan_id: str,
        trial_days: int = 7,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        ends = now + timedelta(days=trial_days)
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "status": "trialing",
            "amount": 0,
            "currency": "BRL",
            "trial_started_at": now.isoformat(),
            "trial_ends_at": ends.isoformat(),
            "current_period_end": ends.isoformat(),
            "updated_at": _utc_now_iso(),
        }
        created = await self.db._request("POST", "subscriptions", data=payload)
        if isinstance(created, list) and created:
            return created[0]
        if isinstance(created, dict):
            return created
        return payload

    async def expire_trial_subscription(self, subscription_id: str) -> None:
        await self.db._request(
            "PATCH",
            f"subscriptions?id=eq.{subscription_id}",
            data={"status": "expired", "updated_at": _utc_now_iso()},
        )

    async def get_latest_subscription_for_user(
        self, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Última assinatura do usuário (qualquer status) — para UX de Minha Conta."""
        result = await self.db._request(
            "GET",
            "subscriptions",
            params={
                "user_id": f"eq.{user_id}",
                "select": "*",
                "order": "updated_at.desc",
                "limit": "1",
            },
        )
        if isinstance(result, list) and result:
            return result[0]
        return None

    async def get_pending_checkout_for_user(
        self, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Checkout Asaas ainda pendente vinculado ao usuário."""
        result = await self.db._request(
            "GET",
            "billing_checkouts",
            params={
                "user_id": f"eq.{user_id}",
                "status": "eq.pending",
                "select": "*",
                "order": "updated_at.desc",
                "limit": "1",
            },
        )
        if isinstance(result, list) and result:
            return result[0]
        return None

    async def update_subscription_status_by_asaas_id(
        self,
        asaas_subscription_id: str,
        status: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        patch: Dict[str, Any] = {
            "status": status,
            "updated_at": _utc_now_iso(),
            **(extra or {}),
        }
        await self.db._request(
            "PATCH",
            f"subscriptions?asaas_subscription_id=eq.{asaas_subscription_id}",
            data=patch,
        )
