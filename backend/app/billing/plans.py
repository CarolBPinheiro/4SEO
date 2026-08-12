"""Catálogo canônico de planos — espelho de lib/billing/plans.ts.

Preços e ciclos são calculados no servidor; nunca confiar em valor enviado pelo cliente.
"""

from __future__ import annotations

from typing import Dict, Literal, TypedDict

BillingCycle = Literal["monthly", "quarterly", "semiannual", "annual"]
PlanId = Literal["start", "pro", "scale"]
AsaasSubscriptionCycle = Literal["MONTHLY", "QUARTERLY", "SEMIANNUALLY", "YEARLY"]


class CyclePricing(TypedDict):
    total: float
    discountPercent: float
    bonusProducts: int


class Plan(TypedDict):
    id: PlanId
    name: str
    pricing: Dict[BillingCycle, CyclePricing]


class BillingCycleOption(TypedDict):
    id: BillingCycle
    label: str
    months: int
    asaasCycle: AsaasSubscriptionCycle


BILLING_CYCLES: tuple[BillingCycleOption, ...] = (
    {"id": "monthly", "label": "Mensal", "months": 1, "asaasCycle": "MONTHLY"},
    {"id": "quarterly", "label": "Trimestral", "months": 3, "asaasCycle": "QUARTERLY"},
    {
        "id": "semiannual",
        "label": "Semestral",
        "months": 6,
        "asaasCycle": "SEMIANNUALLY",
    },
    {"id": "annual", "label": "Anual", "months": 12, "asaasCycle": "YEARLY"},
)

PLANS: tuple[Plan, ...] = (
    {
        "id": "start",
        "name": "Start",
        "pricing": {
            "monthly": {"total": 89.0, "discountPercent": 0, "bonusProducts": 0},
            "quarterly": {"total": 267.0, "discountPercent": 0, "bonusProducts": 20},
            "semiannual": {
                "total": 507.3,
                "discountPercent": 5,
                "bonusProducts": 50,
            },
            "annual": {"total": 961.2, "discountPercent": 10, "bonusProducts": 75},
        },
    },
    {
        "id": "pro",
        "name": "Pro",
        "pricing": {
            "monthly": {"total": 199.0, "discountPercent": 0, "bonusProducts": 0},
            "quarterly": {
                "total": 579.09,
                "discountPercent": 3,
                "bonusProducts": 50,
            },
            "semiannual": {
                "total": 1110.42,
                "discountPercent": 7,
                "bonusProducts": 100,
            },
            "annual": {
                "total": 2149.2,
                "discountPercent": 10,
                "bonusProducts": 150,
            },
        },
    },
    {
        "id": "scale",
        "name": "Scale",
        "pricing": {
            "monthly": {"total": 299.0, "discountPercent": 0, "bonusProducts": 0},
            "quarterly": {
                "total": 852.15,
                "discountPercent": 5,
                "bonusProducts": 50,
            },
            "semiannual": {
                "total": 1614.6,
                "discountPercent": 10,
                "bonusProducts": 100,
            },
            "annual": {
                "total": 3049.8,
                "discountPercent": 15,
                "bonusProducts": 150,
            },
        },
    },
)

_PLAN_BY_ID = {plan["id"]: plan for plan in PLANS}
_CYCLE_BY_ID = {cycle["id"]: cycle for cycle in BILLING_CYCLES}


def is_plan_id(value: str) -> bool:
    return value in _PLAN_BY_ID


def is_billing_cycle(value: str) -> bool:
    return value in _CYCLE_BY_ID


def get_plan(plan_id: str) -> Plan:
    try:
        return _PLAN_BY_ID[plan_id]  # type: ignore[index]
    except KeyError as exc:
        raise ValueError(f"Plano desconhecido: {plan_id}") from exc


def get_cycle(billing_cycle: str) -> BillingCycleOption:
    try:
        return _CYCLE_BY_ID[billing_cycle]  # type: ignore[index]
    except KeyError as exc:
        raise ValueError(f"Ciclo desconhecido: {billing_cycle}") from exc


def get_plan_price(plan_id: str, billing_cycle: str) -> CyclePricing:
    plan = get_plan(plan_id)
    cycle = billing_cycle  # type: ignore[assignment]
    if cycle not in plan["pricing"]:
        raise ValueError(f"Ciclo inválido para o plano: {billing_cycle}")
    return plan["pricing"][cycle]  # type: ignore[index]


def to_asaas_cycle(billing_cycle: str) -> AsaasSubscriptionCycle:
    return get_cycle(billing_cycle)["asaasCycle"]
