"""Orquestração do painel administrativo."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.admin.asaas_ops import asaas_ready, cancel_asaas_subscription, update_asaas_subscription
from app.admin.deps import get_admin_emails, get_admin_user_ids
from app.admin.metrics import (
    build_overview_metrics,
    catalog_price,
    change_kind,
    parse_dt,
    period_days,
    period_window,
    plan_name,
)
from app.admin.repository import AdminRepository
from app.admin.schemas import (
    AdminHealthResponse,
    AdminOverviewResponse,
    AdminTicketListResponse,
    AdminUserDetailResponse,
    AdminUserListItem,
    AdminUserListResponse,
)
from app.admin.tickets import (
    TICKET_PRIORITIES,
    TICKET_STATUSES,
    extract_ticket_fields,
    normalize_priority,
    normalize_status,
    summarize_ticket_counts,
)
from app.billing.access import is_entitled_status
from app.billing.asaas_client import AsaasApiError, AsaasConfigError
from app.billing.plans import is_billing_cycle, is_plan_id, to_asaas_cycle

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class AdminActionError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def is_uuid(value: str) -> bool:
    return bool(UUID_RE.match(value or ""))


class AdminService:
    def __init__(self, repo: Optional[AdminRepository] = None) -> None:
        self.repo = repo or AdminRepository()

    async def overview(self, period: str = "30d") -> AdminOverviewResponse:
        days = period_days(period)
        since, now = period_window(period)
        subscriptions = await self.repo.list_all_subscriptions()
        _sample, users_total = await self.repo.list_auth_users(page=1, per_page=1)
        metrics = build_overview_metrics(
            subscriptions=subscriptions,
            users_total=users_total,
            new_users=await self._count_new_users(since),
            sites_total=await self.repo.count_sites(),
            unprocessed_webhooks=await self.repo.count_unprocessed_webhooks(),
            tickets_by_status=summarize_ticket_counts(await self.repo.list_tickets(limit=400)),
            since=since,
            now=now,
            period_days_count=days,
        )
        return AdminOverviewResponse(**metrics)

    async def _count_new_users(self, since: datetime) -> int:
        count = 0
        page = 1
        while page <= 20:
            users, total = await self.repo.list_auth_users(page=page, per_page=100)
            if not users:
                break
            for user in users:
                created = parse_dt(user.get("created_at"))
                if created and created >= since:
                    count += 1
            if page * 100 >= total:
                break
            page += 1
        return count

    def _map_user_item(
        self, user: Dict[str, Any], sub: Optional[Dict[str, Any]]
    ) -> AdminUserListItem:
        amount = None
        if sub and sub.get("amount") is not None:
            try:
                amount = float(sub.get("amount") or 0)
            except (TypeError, ValueError):
                amount = None
        return AdminUserListItem(
            id=user.get("id") or "",
            email=user.get("email"),
            createdAt=user.get("created_at"),
            lastSignInAt=user.get("last_sign_in_at"),
            emailConfirmedAt=user.get("email_confirmed_at"),
            banned=bool(user.get("banned_until")),
            subscriptionStatus=(sub or {}).get("status") or "none",
            planId=(sub or {}).get("plan_id"),
            billingCycle=(sub or {}).get("billing_cycle"),
            amount=amount,
            currentPeriodEnd=(sub or {}).get("current_period_end"),
            asaasCustomerId=(sub or {}).get("asaas_customer_id"),
            asaasSubscriptionId=(sub or {}).get("asaas_subscription_id"),
        )

    async def _latest_subs_by_user(self) -> Dict[str, Dict[str, Any]]:
        by_user: Dict[str, Dict[str, Any]] = {}
        for sub in await self.repo.list_all_subscriptions():
            uid = sub.get("user_id")
            if not uid:
                continue
            prev = by_user.get(uid)
            if not prev or (sub.get("updated_at") or "") > (prev.get("updated_at") or ""):
                by_user[uid] = sub
        return by_user

    async def list_users(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        q: Optional[str] = None,
        subscription_filter: Optional[str] = None,
    ) -> AdminUserListResponse:
        users, total = await self.repo.list_auth_users(
            page=page, per_page=per_page, email_query=q
        )
        by_user = await self._latest_subs_by_user()
        items = [self._map_user_item(u, by_user.get(u.get("id"))) for u in users]
        if subscription_filter == "active":
            items = [i for i in items if is_entitled_status(i.subscriptionStatus)]
        elif subscription_filter == "none":
            items = [i for i in items if i.subscriptionStatus in {"none", "", None}]
        elif subscription_filter and subscription_filter != "all":
            items = [i for i in items if i.subscriptionStatus == subscription_filter]
        return AdminUserListResponse(items=items, page=page, perPage=per_page, total=total)

    async def user_detail(self, user_id: str) -> Optional[AdminUserDetailResponse]:
        if not is_uuid(user_id):
            return None
        user = await self.repo.get_auth_user(user_id)
        if not user:
            return None
        subs = await self.repo.get_subscriptions_for_user(user_id)
        checkouts = await self.repo.get_checkouts_for_user(user_id)
        events = await self.repo.list_subscription_events(user_id=user_id)
        tickets = await self.repo.list_tickets_for_user(user_id)
        timeline: List[Dict[str, Any]] = []
        if user.get("created_at"):
            timeline.append(
                {"at": user["created_at"], "type": "account_created", "label": "Conta criada"}
            )
        for checkout in checkouts:
            timeline.append(
                {
                    "at": checkout.get("created_at"),
                    "type": "checkout",
                    "label": f"Checkout {checkout.get('status')} ({checkout.get('plan_id')})",
                    "ref": checkout.get("external_reference"),
                }
            )
        for sub in subs:
            timeline.append(
                {
                    "at": sub.get("created_at") or sub.get("updated_at"),
                    "type": "subscription",
                    "label": f"Assinatura {sub.get('status')} ({sub.get('plan_id')})",
                    "asaasSubscriptionId": sub.get("asaas_subscription_id"),
                }
            )
        for event in events:
            timeline.append(
                {
                    "at": event.get("created_at"),
                    "type": event.get("action") or "plan_event",
                    "label": self._event_label(event),
                    "reason": event.get("reason"),
                }
            )
        timeline.sort(key=lambda e: e.get("at") or "", reverse=True)
        return AdminUserDetailResponse(
            id=user.get("id") or user_id,
            email=user.get("email"),
            createdAt=user.get("created_at"),
            lastSignInAt=user.get("last_sign_in_at"),
            emailConfirmedAt=user.get("email_confirmed_at"),
            banned=bool(user.get("banned_until")),
            subscriptions=subs,
            checkouts=checkouts,
            timeline=timeline,
            planEvents=events,
            tickets=tickets,
        )

    def _event_label(self, event: Dict[str, Any]) -> str:
        action = event.get("action") or "evento"
        if action == "cancel":
            return f"Cancelamento ({event.get('from_plan') or 'plano'})"
        kind = change_kind(event.get("from_plan"), event.get("to_plan"))
        verb = {"upgrade": "Upgrade", "downgrade": "Downgrade"}.get(kind, "Mudança de plano")
        return f"{verb}: {event.get('from_plan') or '—'} → {event.get('to_plan') or '—'}"

    async def list_subscriptions_page(
        self,
        *,
        status: Optional[str] = None,
        plan_id: Optional[str] = None,
        expiring_days: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        all_items = await self.repo.list_all_subscriptions()
        emails = await self.repo.auth_email_map()
        now = datetime.now(timezone.utc)
        filtered: List[Dict[str, Any]] = []
        for sub in all_items:
            st = (sub.get("status") or "").lower()
            if status and status not in {"all", None} and st != status:
                continue
            if plan_id and sub.get("plan_id") != plan_id:
                continue
            if expiring_days:
                ends = parse_dt(sub.get("current_period_end") or sub.get("trial_ends_at"))
                if not ends:
                    continue
                delta = (ends - now).total_seconds()
                if delta < 0 or delta > expiring_days * 86400:
                    continue
            item = dict(sub)
            uid = sub.get("user_id")
            item["user_email"] = emails.get(str(uid)) if uid else None
            item["plan_name"] = plan_name(sub.get("plan_id"))
            filtered.append(item)
        total = len(filtered)
        start = max((page - 1) * per_page, 0)
        return {
            "items": filtered[start : start + per_page],
            "page": page,
            "perPage": per_page,
            "total": total,
        }

    async def change_plan(
        self,
        subscription_id: str,
        *,
        plan_id: str,
        billing_cycle: Optional[str],
        reason: Optional[str],
        admin: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not is_uuid(subscription_id):
            raise AdminActionError("Assinatura inválida.")
        if not is_plan_id(plan_id):
            raise AdminActionError("Plano inválido.")
        sub = await self.repo.get_subscription(subscription_id)
        if not sub:
            raise AdminActionError("Assinatura não encontrada.", 404)
        cycle = billing_cycle or sub.get("billing_cycle") or "monthly"
        if not is_billing_cycle(cycle):
            raise AdminActionError("Ciclo de cobrança inválido.")
        amount = catalog_price(plan_id, cycle)
        asaas_id = (sub.get("asaas_subscription_id") or "").strip()
        if asaas_id:
            if not asaas_ready():
                raise AdminActionError("Asaas não configurado para alterar plano pago.", 503)
            try:
                await update_asaas_subscription(
                    asaas_id,
                    value=amount,
                    cycle=to_asaas_cycle(cycle),
                    description=f"4SEO {plan_name(plan_id)}",
                )
            except AsaasConfigError as exc:
                raise AdminActionError(str(exc), 503) from exc
            except AsaasApiError as exc:
                raise AdminActionError(str(exc), 502) from exc
        updated = await self.repo.update_subscription(
            subscription_id,
            {"plan_id": plan_id, "billing_cycle": cycle, "amount": amount},
        )
        await self.repo.insert_subscription_event(
            {
                "subscription_id": subscription_id,
                "user_id": sub.get("user_id"),
                "action": change_kind(sub.get("plan_id"), plan_id),
                "from_plan": sub.get("plan_id"),
                "to_plan": plan_id,
                "from_cycle": sub.get("billing_cycle"),
                "to_cycle": cycle,
                "reason": (reason or "").strip() or None,
                "actor_user_id": admin.get("user_id"),
                "actor_email": admin.get("email"),
            }
        )
        await self.repo.insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.subscription.change_plan",
            target_type="subscription",
            target_id=subscription_id,
            meta={"from": sub.get("plan_id"), "to": plan_id, "cycle": cycle},
        )
        return updated or sub

    async def cancel_subscription(
        self,
        subscription_id: str,
        *,
        reason: str,
        admin: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not is_uuid(subscription_id):
            raise AdminActionError("Assinatura inválida.")
        reason_clean = (reason or "").strip()
        if len(reason_clean) < 3:
            raise AdminActionError("Informe o motivo do cancelamento.")
        sub = await self.repo.get_subscription(subscription_id)
        if not sub:
            raise AdminActionError("Assinatura não encontrada.", 404)
        asaas_id = (sub.get("asaas_subscription_id") or "").strip()
        if asaas_id:
            if not asaas_ready():
                raise AdminActionError("Asaas não configurado para cancelar plano pago.", 503)
            try:
                await cancel_asaas_subscription(asaas_id)
            except AsaasConfigError as exc:
                raise AdminActionError(str(exc), 503) from exc
            except AsaasApiError as exc:
                raise AdminActionError(str(exc), 502) from exc
        updated = await self.repo.update_subscription(subscription_id, {"status": "canceled"})
        await self.repo.insert_subscription_event(
            {
                "subscription_id": subscription_id,
                "user_id": sub.get("user_id"),
                "action": "cancel",
                "from_plan": sub.get("plan_id"),
                "to_plan": sub.get("plan_id"),
                "from_cycle": sub.get("billing_cycle"),
                "to_cycle": sub.get("billing_cycle"),
                "reason": reason_clean,
                "actor_user_id": admin.get("user_id"),
                "actor_email": admin.get("email"),
            }
        )
        await self.repo.insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.subscription.cancel",
            target_type="subscription",
            target_id=subscription_id,
            meta={"reason": reason_clean, "plan": sub.get("plan_id")},
        )
        return updated or sub

    async def list_tickets(self) -> AdminTicketListResponse:
        items = await self.repo.list_tickets(limit=400)
        emails = await self.repo.auth_email_map()
        by_user = await self._latest_subs_by_user()
        enriched: List[Dict[str, Any]] = []
        for row in items:
            item = dict(row)
            uid = row.get("user_id")
            if uid and not item.get("user_email"):
                item["user_email"] = emails.get(str(uid))
            if uid and not item.get("plan_id"):
                sub = by_user.get(str(uid))
                if sub:
                    item["plan_id"] = sub.get("plan_id")
            item["plan_name"] = plan_name(item.get("plan_id"))
            item["status"] = normalize_status(str(item.get("status") or "new"))
            item["priority"] = normalize_priority(str(item.get("priority") or "medium"))
            enriched.append(item)
        return AdminTicketListResponse(items=enriched, counts=summarize_ticket_counts(enriched))

    async def patch_ticket(
        self,
        ticket_id: str,
        *,
        status: Optional[str],
        priority: Optional[str],
        admin: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not is_uuid(ticket_id):
            raise AdminActionError("Chamado inválido.")
        ticket = await self.repo.get_ticket(ticket_id)
        if not ticket:
            raise AdminActionError("Chamado não encontrado.", 404)
        patch: Dict[str, Any] = {}
        if status:
            normalized = normalize_status(status)
            if normalized not in TICKET_STATUSES:
                raise AdminActionError("Status de chamado inválido.")
            patch["status"] = normalized
            patch["resolved_at"] = (
                datetime.now(timezone.utc).isoformat() if normalized == "resolved" else None
            )
        if priority:
            normalized_p = normalize_priority(priority)
            if normalized_p not in TICKET_PRIORITIES:
                raise AdminActionError("Prioridade inválida.")
            patch["priority"] = normalized_p
        if not patch:
            raise AdminActionError("Nada para atualizar.")
        updated = await self.repo.update_ticket(ticket_id, patch)
        await self.repo.insert_audit(
            actor_user_id=admin.get("user_id"),
            actor_email=admin.get("email"),
            action="admin.ticket.update",
            target_type="ticket",
            target_id=ticket_id,
            meta=patch,
        )
        return updated or ticket

    async def ingest_typebot_ticket(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        fields = extract_ticket_fields(payload)
        result_id = fields.get("typebot_result_id")
        if result_id:
            existing = await self.repo.get_ticket_by_typebot_id(str(result_id))
            if existing:
                return existing
        user_id = fields.get("user_id")
        if user_id and not is_uuid(str(user_id)):
            user_id = None
        email = fields.get("user_email")
        if not user_id and email:
            user_id = await self.repo.find_user_id_by_email(str(email))
        plan_id = fields.get("plan_id")
        if user_id and not plan_id:
            subs = await self.repo.get_subscriptions_for_user(str(user_id))
            if subs:
                plan_id = subs[0].get("plan_id")
        return await self.repo.insert_ticket(
            {
                "typebot_result_id": result_id,
                "user_id": user_id,
                "user_email": email,
                "user_name": fields.get("user_name"),
                "plan_id": plan_id,
                "subject": fields.get("subject") or "Chamado Typebot",
                "message": fields.get("message"),
                "priority": fields.get("priority") or "medium",
                "status": "new",
                "payload": payload,
            }
        )

    async def health(self) -> AdminHealthResponse:
        db_ok = await self.repo.probe_database()
        asaas_key = bool((os.getenv("ASAAS_API_KEY") or "").strip())
        asaas_url = (os.getenv("ASAAS_BASE_URL") or "").strip() or None
        docs_off = (os.getenv("DISABLE_API_DOCS") or "").strip().lower() in {"1", "true", "yes"}
        env_prod = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "").lower() == "production"
        tickets = await self.repo.list_tickets(limit=400)
        counts = summarize_ticket_counts(tickets)
        status_counts = await self.repo.count_subscriptions_by_status()
        return AdminHealthResponse(
            app="ok",
            database="ok" if db_ok else "error",
            asaasConfigured=asaas_key,
            asaasBaseUrl=asaas_url,
            webhookTokenConfigured=bool((os.getenv("ASAAS_WEBHOOK_TOKEN") or "").strip()),
            typebotWebhookConfigured=bool((os.getenv("TYPEBOT_WEBHOOK_SECRET") or "").strip()),
            adminAllowlistConfigured=bool(get_admin_emails() or get_admin_user_ids()),
            unprocessedWebhooks=await self.repo.count_unprocessed_webhooks(),
            recentWebhooks=await self.repo.recent_webhooks(20),
            docsExposed=not (docs_off or env_prod),
            sitesTotal=await self.repo.count_sites(),
            pastDueSubscriptions=int(status_counts.get("past_due", 0)),
            ticketsOpen=int(counts.get("new", 0))
            + int(counts.get("in_progress", 0))
            + int(counts.get("waiting_customer", 0)),
        )
