"""Testes unitários do painel admin (métricas e Typebot)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.admin.metrics import (
    build_overview_metrics,
    catalog_price,
    change_kind,
    monthly_amount,
    plan_name,
    status_bucket,
)
from app.admin.tickets import extract_ticket_fields, normalize_priority, normalize_status
from app.billing.access import path_requires_subscription


def test_monthly_amount_normalizes_cycles():
    assert monthly_amount(1200, "annual") == 100.0
    assert monthly_amount(600, "semiannual") == 100.0
    assert monthly_amount(300, "quarterly") == 100.0
    assert monthly_amount(100, "monthly") == 100.0


def test_change_kind_upgrade_downgrade():
    assert change_kind("start", "scale") == "upgrade"
    assert change_kind("scale", "pro") == "downgrade"
    assert change_kind("pro", "pro") == "lateral"


def test_plan_name_and_status_bucket():
    assert plan_name("pro") == "Pro"
    assert status_bucket("trialing") == "active"
    assert status_bucket("canceled") == "canceled"
    assert status_bucket("inactive") == "inactive"


def test_catalog_price_start_monthly():
    assert catalog_price("start", "monthly") == 89.0


def test_overview_metrics_counts_and_mrr():
    now = datetime(2026, 8, 26, tzinfo=timezone.utc)
    since = now - timedelta(days=30)
    metrics = build_overview_metrics(
        subscriptions=[
            {
                "id": "s1",
                "user_id": "u1",
                "plan_id": "pro",
                "billing_cycle": "monthly",
                "status": "active",
                "amount": 199,
                "created_at": (now - timedelta(days=2)).isoformat(),
                "updated_at": now.isoformat(),
                "current_period_end": (now + timedelta(days=5)).isoformat(),
            },
            {
                "id": "s2",
                "user_id": "u2",
                "plan_id": "start",
                "billing_cycle": "monthly",
                "status": "canceled",
                "amount": 89,
                "created_at": (now - timedelta(days=10)).isoformat(),
                "updated_at": (now - timedelta(days=1)).isoformat(),
            },
        ],
        users_total=10,
        new_users=3,
        sites_total=4,
        unprocessed_webhooks=2,
        tickets_by_status={"new": 1, "in_progress": 1, "waiting_customer": 0, "resolved": 3},
        since=since,
        now=now,
        period_days_count=30,
    )
    assert metrics["subscribersActive"] == 1
    assert metrics["subscribersCanceled"] == 1
    assert metrics["estimatedMrr"] == 199.0
    assert metrics["ticketsOpen"] == 2
    assert metrics["unprocessedWebhooks"] == 2
    assert any(alert["code"] == "webhooks_pending" for alert in metrics["alerts"])
    assert any(item["userId"] == "u1" for item in metrics["expiringSoon"])


def test_extract_ticket_fields_from_typebot_answers():
    fields = extract_ticket_fields(
        {
            "resultId": "res-1",
            "answers": [
                {"variableName": "email", "value": "cliente@loja.com"},
                {"variableName": "assunto", "value": "Erro no GSC"},
                {"variableName": "mensagem", "value": "Não consigo conectar."},
                {"variableName": "prioridade", "value": "alta"},
                {"variableName": "plano", "value": "pro"},
            ],
        }
    )
    assert fields["typebot_result_id"] == "res-1"
    assert fields["user_email"] == "cliente@loja.com"
    assert fields["subject"] == "Erro no GSC"
    assert fields["priority"] == "high"
    assert fields["plan_id"] == "pro"


def test_normalize_ticket_enums():
    assert normalize_status("em atendimento") == "in_progress"
    assert normalize_status("resolvido") == "resolved"
    assert normalize_priority("urgente") == "urgent"
    assert normalize_priority("baixa") == "low"


def test_typebot_webhook_path_is_exempt_from_subscription():
    assert path_requires_subscription("/api/webhooks/typebot") is False
    assert path_requires_subscription("/webhooks/typebot") is False
    assert path_requires_subscription("/api/admin/tickets") is False
