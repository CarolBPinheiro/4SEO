"""Orquestração do painel administrativo."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.admin.deps import get_admin_emails, get_admin_user_ids
from app.admin.repository import AdminRepository
from app.admin.schemas import (
    AdminHealthResponse,
    AdminOverviewResponse,
    AdminUserDetailResponse,
    AdminUserListItem,
    AdminUserListResponse,
)
from app.billing.access import is_entitled_status


def _period_days(period: str) -> int:
    mapping = {"7d": 7, "30d": 30, "90d": 90, "12m": 365}
    return mapping.get(period, 30)


class AdminService:
    def __init__(self, repo: Optional[AdminRepository] = None) -> None:
        self.repo = repo or AdminRepository()

    async def overview(self, period: str = "30d") -> AdminOverviewResponse:
        days = _period_days(period)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        since_iso = since.isoformat()

        status_counts = await self.repo.count_subscriptions_by_status()
        entitled_ids: set[str] = set()
        all_subs = await self.repo.list_subscriptions(limit=500, offset=0)
        for sub in all_subs:
            uid = sub.get("user_id")
            if uid and is_entitled_status(sub.get("status")):
                entitled_ids.add(uid)

        users, users_total = await self.repo.list_auth_users(page=1, per_page=100)
        # Auth Admin pode paginar; para overview usamos total + amostra da 1ª página
        new_users = 0
        for u in users:
            created = u.get("created_at")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if created_dt >= since:
                        new_users += 1
                except ValueError:
                    pass

        subs_period = await self.repo.subscriptions_created_since(since_iso)
        series_map: Dict[str, Dict[str, int]] = {}
        for sub in subs_period:
            created = (sub.get("created_at") or "")[:10]
            if not created:
                continue
            bucket = series_map.setdefault(created, {"newSubscriptions": 0, "canceled": 0})
            bucket["newSubscriptions"] += 1
            if (sub.get("status") or "").lower() in {"canceled", "inactive"}:
                bucket["canceled"] += 1

        series = [
            {"date": day, **counts}
            for day, counts in sorted(series_map.items())
        ]

        with_sub = len(entitled_ids)
        without = max(users_total - with_sub, 0)

        return AdminOverviewResponse(
            usersTotal=users_total,
            usersNewInPeriod=new_users,
            usersWithActiveSubscription=with_sub,
            usersWithoutSubscription=without,
            subscriptionsByStatus=status_counts,
            subscriptionsNewInPeriod=len(subs_period),
            estimatedMrr=await self.repo.sum_active_mrr_estimate(),
            sitesTotal=await self.repo.count_sites(),
            unprocessedWebhooks=await self.repo.count_unprocessed_webhooks(),
            series=series,
            periodDays=days,
        )

    def _map_user_item(
        self, user: Dict[str, Any], sub: Optional[Dict[str, Any]]
    ) -> AdminUserListItem:
        return AdminUserListItem(
            id=user.get("id") or "",
            email=user.get("email"),
            createdAt=user.get("created_at"),
            lastSignInAt=user.get("last_sign_in_at"),
            emailConfirmedAt=user.get("email_confirmed_at"),
            banned=bool(user.get("banned_until")),
            subscriptionStatus=(sub or {}).get("status") or "none",
            planId=(sub or {}).get("plan_id"),
            asaasCustomerId=(sub or {}).get("asaas_customer_id"),
            asaasSubscriptionId=(sub or {}).get("asaas_subscription_id"),
        )

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
        subs = await self.repo.list_subscriptions(limit=500, offset=0)
        by_user: Dict[str, Dict[str, Any]] = {}
        for sub in subs:
            uid = sub.get("user_id")
            if not uid:
                continue
            prev = by_user.get(uid)
            if not prev or (sub.get("updated_at") or "") > (prev.get("updated_at") or ""):
                by_user[uid] = sub

        items = [self._map_user_item(u, by_user.get(u.get("id"))) for u in users]

        if subscription_filter == "active":
            items = [i for i in items if is_entitled_status(i.subscriptionStatus)]
        elif subscription_filter == "none":
            items = [i for i in items if i.subscriptionStatus in {"none", "", None}]
        elif subscription_filter and subscription_filter != "all":
            items = [i for i in items if i.subscriptionStatus == subscription_filter]

        return AdminUserListResponse(
            items=items, page=page, perPage=per_page, total=total
        )

    async def user_detail(self, user_id: str) -> Optional[AdminUserDetailResponse]:
        user = await self.repo.get_auth_user(user_id)
        if not user:
            return None
        subs = await self.repo.get_subscriptions_for_user(user_id)
        checkouts = await self.repo.get_checkouts_for_user(user_id)

        timeline: List[Dict[str, Any]] = []
        if user.get("created_at"):
            timeline.append(
                {
                    "at": user["created_at"],
                    "type": "account_created",
                    "label": "Conta criada",
                }
            )
        for c in checkouts:
            timeline.append(
                {
                    "at": c.get("created_at"),
                    "type": "checkout",
                    "label": f"Checkout {c.get('status')} ({c.get('plan_id')})",
                    "ref": c.get("external_reference"),
                }
            )
        for s in subs:
            timeline.append(
                {
                    "at": s.get("created_at") or s.get("updated_at"),
                    "type": "subscription",
                    "label": f"Assinatura {s.get('status')} ({s.get('plan_id')})",
                    "asaasSubscriptionId": s.get("asaas_subscription_id"),
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
        )

    async def health(self) -> AdminHealthResponse:
        db_ok = await self.repo.probe_database()
        asaas_key = bool((os.getenv("ASAAS_API_KEY") or "").strip())
        asaas_url = (os.getenv("ASAAS_BASE_URL") or "").strip() or None
        docs_off = (os.getenv("DISABLE_API_DOCS") or "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        env_prod = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "").lower() == "production"
        return AdminHealthResponse(
            app="ok",
            database="ok" if db_ok else "error",
            asaasConfigured=asaas_key,
            asaasBaseUrl=asaas_url,
            webhookTokenConfigured=bool((os.getenv("ASAAS_WEBHOOK_TOKEN") or "").strip()),
            adminAllowlistConfigured=bool(get_admin_emails() or get_admin_user_ids()),
            unprocessedWebhooks=await self.repo.count_unprocessed_webhooks(),
            recentWebhooks=await self.repo.recent_webhooks(20),
            docsExposed=not (docs_off or env_prod),
        )
