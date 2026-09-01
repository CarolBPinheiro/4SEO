"""Cálculos puros do painel admin — sem I/O, testáveis isoladamente."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.billing.plans import BILLING_CYCLES, PLANS, get_plan_price

PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "12m": 365}

ENTITLED_STATUSES = frozenset({"active", "trialing", "past_due"})
CANCELED_STATUSES = frozenset({"canceled", "cancelled"})
INACTIVE_STATUSES = frozenset({"inactive", "expired", "unpaid", "paused"})

PLAN_RANK = {"start": 0, "pro": 1, "scale": 2}
CYCLE_MONTHS = {item["id"]: item["months"] for item in BILLING_CYCLES}
PLAN_NAMES = {plan["id"]: plan["name"] for plan in PLANS}

EXPIRING_SOON_DAYS = 14


def period_days(period: str) -> int:
    return PERIOD_DAYS.get(period, 30)


def period_window(period: str, now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    current = now or datetime.now(timezone.utc)
    return current - timedelta(days=period_days(period)), current


def parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def monthly_amount(amount: Any, billing_cycle: Any) -> float:
    total = to_float(amount)
    months = CYCLE_MONTHS.get(str(billing_cycle or "monthly").lower(), 1)
    if months <= 0:
        return round(total, 2)
    return round(total / months, 2)


def catalog_price(plan_id: str, billing_cycle: str) -> float:
    price = get_plan_price(plan_id, billing_cycle)
    return float(price["total"])


def plan_name(plan_id: Optional[str]) -> str:
    if not plan_id:
        return "—"
    return PLAN_NAMES.get(plan_id, plan_id)


def plan_rank(plan_id: Optional[str]) -> int:
    return PLAN_RANK.get((plan_id or "").lower(), -1)


def change_kind(from_plan: Optional[str], to_plan: Optional[str]) -> str:
    left, right = plan_rank(from_plan), plan_rank(to_plan)
    if left < 0 or right < 0 or left == right:
        return "lateral"
    return "upgrade" if right > left else "downgrade"


def status_bucket(status: Optional[str]) -> str:
    st = (status or "").strip().lower()
    if st in ENTITLED_STATUSES:
        return "active"
    if st in CANCELED_STATUSES:
        return "canceled"
    if st in INACTIVE_STATUSES or not st:
        return "inactive"
    return "other"


def latest_subscription_by_user(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_user: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        uid = row.get("user_id")
        if not uid:
            continue
        prev = by_user.get(str(uid))
        current = dict(row)
        if not prev:
            by_user[str(uid)] = current
            continue
        prev_ts = prev.get("updated_at") or prev.get("created_at") or ""
        row_ts = current.get("updated_at") or current.get("created_at") or ""
        if str(row_ts) >= str(prev_ts):
            by_user[str(uid)] = current
    return by_user


def _day_key(dt: datetime) -> str:
    return dt.date().isoformat()


def build_day_range(since: datetime, now: datetime) -> List[str]:
    days: List[str] = []
    cursor = since.date()
    end = now.date()
    while cursor <= end:
        days.append(cursor.isoformat())
        cursor = cursor + timedelta(days=1)
        if len(days) > 400:
            break
    return days


def build_alerts(
    *,
    unprocessed_webhooks: int,
    past_due: int,
    expiring_count: int,
    tickets_open: int,
    tickets_new: int,
) -> List[Dict[str, str]]:
    alerts: List[Dict[str, str]] = []
    if unprocessed_webhooks > 0:
        alerts.append(
            {
                "severity": "critical",
                "code": "webhooks_pending",
                "message": f"{unprocessed_webhooks} webhook(s) Asaas sem processar.",
                "href": "/admin/health",
            }
        )
    if past_due > 0:
        alerts.append(
            {
                "severity": "critical",
                "code": "past_due",
                "message": f"{past_due} assinatura(s) inadimplente(s).",
                "href": "/admin/subscriptions",
            }
        )
    if expiring_count > 0:
        alerts.append(
            {
                "severity": "warning",
                "code": "expiring",
                "message": f"{expiring_count} assinatura(s) vencem em até {EXPIRING_SOON_DAYS} dias.",
                "href": "/admin/subscriptions",
            }
        )
    if tickets_new > 0:
        alerts.append(
            {
                "severity": "warning",
                "code": "tickets_new",
                "message": f"{tickets_new} chamado(s) novo(s) aguardando atendimento.",
                "href": "/admin/tickets",
            }
        )
    elif tickets_open > 0:
        alerts.append(
            {
                "severity": "info",
                "code": "tickets_open",
                "message": f"{tickets_open} chamado(s) em aberto.",
                "href": "/admin/tickets",
            }
        )
    return alerts


def build_overview_metrics(
    *,
    subscriptions: List[Dict[str, Any]],
    users_total: int,
    new_users: int,
    sites_total: int,
    unprocessed_webhooks: int,
    tickets_by_status: Dict[str, int],
    since: datetime,
    now: datetime,
    period_days_count: int,
) -> Dict[str, Any]:
    latest = latest_subscription_by_user(subscriptions)

    entitled_ids: set[str] = set()
    canceled_ids: set[str] = set()
    inactive_ids: set[str] = set()
    users_by_plan: Dict[str, int] = {}
    mrr_by_plan: Dict[str, float] = {}
    status_counts: Dict[str, int] = {}
    expiring: List[Dict[str, Any]] = []
    mrr = 0.0
    soon_limit = now + timedelta(days=EXPIRING_SOON_DAYS)

    for uid, sub in latest.items():
        st = (sub.get("status") or "unknown").lower()
        status_counts[st] = status_counts.get(st, 0) + 1
        bucket = status_bucket(st)
        plan_id = str(sub.get("plan_id") or "")
        cycle = str(sub.get("billing_cycle") or "monthly")
        amount = monthly_amount(sub.get("amount"), cycle)

        if bucket == "active":
            entitled_ids.add(uid)
            key = plan_id or "unknown"
            users_by_plan[key] = users_by_plan.get(key, 0) + 1
            mrr_by_plan[key] = round(mrr_by_plan.get(key, 0.0) + amount, 2)
            mrr += amount
            ends = parse_dt(sub.get("current_period_end") or sub.get("trial_ends_at"))
            if ends and now <= ends <= soon_limit:
                expiring.append(
                    {
                        "subscriptionId": sub.get("id"),
                        "userId": uid,
                        "planId": plan_id or None,
                        "planName": plan_name(plan_id),
                        "status": st,
                        "currentPeriodEnd": ends.isoformat(),
                        "amountMonthly": amount,
                    }
                )
        elif bucket == "canceled":
            canceled_ids.add(uid)
        else:
            inactive_ids.add(uid)

    expiring.sort(key=lambda row: row.get("currentPeriodEnd") or "")

    new_in_period: List[Dict[str, Any]] = []
    canceled_in_period: List[Dict[str, Any]] = []
    for sub in subscriptions:
        created = parse_dt(sub.get("created_at"))
        if created and created >= since:
            new_in_period.append(sub)
        st = (sub.get("status") or "").lower()
        if st in CANCELED_STATUSES:
            canceled_at = parse_dt(sub.get("updated_at") or sub.get("created_at"))
            if canceled_at and canceled_at >= since:
                canceled_in_period.append(sub)

    days = build_day_range(since, now)
    buckets: Dict[str, Dict[str, float]] = {
        day: {
            "newSubscriptions": 0,
            "canceled": 0,
            "revenueNew": 0.0,
            "revenueLost": 0.0,
        }
        for day in days
    }
    for sub in new_in_period:
        created = parse_dt(sub.get("created_at"))
        if not created:
            continue
        key = _day_key(created)
        if key not in buckets:
            continue
        buckets[key]["newSubscriptions"] += 1
        buckets[key]["revenueNew"] = round(
            buckets[key]["revenueNew"]
            + monthly_amount(sub.get("amount"), sub.get("billing_cycle")),
            2,
        )
    for sub in canceled_in_period:
        canceled_at = parse_dt(sub.get("updated_at") or sub.get("created_at"))
        if not canceled_at:
            continue
        key = _day_key(canceled_at)
        if key not in buckets:
            continue
        buckets[key]["canceled"] += 1
        buckets[key]["revenueLost"] = round(
            buckets[key]["revenueLost"]
            + monthly_amount(sub.get("amount"), sub.get("billing_cycle")),
            2,
        )

    new_count = len(new_in_period)
    canceled_count = len(canceled_in_period)
    active = len(entitled_ids)
    start_base = max(active - new_count + canceled_count, 0)
    running = start_base
    series: List[Dict[str, Any]] = []
    for day in days:
        bucket = buckets[day]
        running = max(running + int(bucket["newSubscriptions"]) - int(bucket["canceled"]), 0)
        series.append(
            {
                "date": day,
                "newSubscriptions": int(bucket["newSubscriptions"]),
                "canceled": int(bucket["canceled"]),
                "net": int(bucket["newSubscriptions"]) - int(bucket["canceled"]),
                "revenueNew": bucket["revenueNew"],
                "revenueLost": bucket["revenueLost"],
                "subscriberBase": running,
            }
        )

    churn_rate = round((canceled_count / max(start_base, 1)) * 100, 2)
    growth_rate = round((new_count / max(start_base, 1)) * 100, 2)
    arpu = round(mrr / active, 2) if active else 0.0
    tickets_open = (
        int(tickets_by_status.get("new", 0))
        + int(tickets_by_status.get("in_progress", 0))
        + int(tickets_by_status.get("waiting_customer", 0))
    )

    catalog: List[Dict[str, Any]] = []
    for plan in PLANS:
        pid = plan["id"]
        catalog.append(
            {
                "id": pid,
                "name": plan["name"],
                "users": users_by_plan.get(pid, 0),
                "mrr": round(mrr_by_plan.get(pid, 0.0), 2),
                "monthlyPrice": float(plan["pricing"]["monthly"]["total"]),
            }
        )

    subscribers_total = len(latest)
    return {
        "usersTotal": users_total,
        "usersNewInPeriod": new_users,
        "usersWithActiveSubscription": active,
        "usersWithoutSubscription": max(users_total - subscribers_total, 0),
        "subscribersTotal": subscribers_total,
        "subscribersActive": active,
        "subscribersInactive": len(inactive_ids),
        "subscribersCanceled": len(canceled_ids),
        "subscriptionsByStatus": status_counts,
        "subscriptionsNewInPeriod": new_count,
        "subscriptionsCanceledInPeriod": canceled_count,
        "netNewInPeriod": new_count - canceled_count,
        "estimatedMrr": round(mrr, 2),
        "mrrByPlan": {k: round(v, 2) for k, v in mrr_by_plan.items()},
        "usersByPlan": users_by_plan,
        "plans": catalog,
        "arpu": arpu,
        "churnRate": churn_rate,
        "growthRate": growth_rate,
        "sitesTotal": sites_total,
        "unprocessedWebhooks": unprocessed_webhooks,
        "expiringSoon": expiring[:20],
        "ticketsByStatus": tickets_by_status,
        "ticketsOpen": tickets_open,
        "series": series,
        "alerts": build_alerts(
            unprocessed_webhooks=unprocessed_webhooks,
            past_due=status_counts.get("past_due", 0),
            expiring_count=len(expiring),
            tickets_open=tickets_open,
            tickets_new=int(tickets_by_status.get("new", 0)),
        ),
        "periodDays": period_days_count,
    }
