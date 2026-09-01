"""Operações Asaas usadas somente pelo painel admin.

Não altera o checkout do produto. O administrador atualiza ou cancela uma
assinatura já existente no Asaas.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

from app.billing.asaas_client import AsaasApiError, AsaasConfigError

logger = logging.getLogger(__name__)

TIMEOUT_S = 20.0


def _api_key() -> str:
    return (os.getenv("ASAAS_API_KEY") or "").strip()


def _base_url() -> str:
    raw = (os.getenv("ASAAS_BASE_URL") or "https://api-sandbox.asaas.com/v3").strip().rstrip("/")
    return raw


def asaas_ready() -> bool:
    return bool(_api_key())


async def _request(
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    api_key = _api_key()
    if not api_key:
        raise AsaasConfigError("ASAAS_API_KEY não configurada.")

    url = f"{_base_url()}{path}"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": api_key,
        "User-Agent": "4SEO-Admin/1.0",
    }
    timeout = httpx.Timeout(TIMEOUT_S, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, url, headers=headers, json=json_body)

    if response.status_code == 404:
        raise AsaasApiError("Assinatura não encontrada no Asaas.", status_code=404)
    if response.status_code >= 400:
        logger.error(
            "Asaas admin %s %s failed status=%s",
            method,
            path,
            response.status_code,
        )
        raise AsaasApiError(
            "Falha ao atualizar assinatura no Asaas.",
            status_code=response.status_code,
        )
    if not response.content:
        return {}
    data = response.json()
    return data if isinstance(data, dict) else {}


async def update_asaas_subscription(
    asaas_subscription_id: str,
    *,
    value: float,
    cycle: str,
    description: str,
) -> Dict[str, Any]:
    return await _request(
        "PUT",
        f"/subscriptions/{asaas_subscription_id}",
        json_body={
            "value": value,
            "cycle": cycle,
            "description": description,
            "updatePendingPayments": True,
        },
    )


async def cancel_asaas_subscription(asaas_subscription_id: str) -> Dict[str, Any]:
    return await _request("DELETE", f"/subscriptions/{asaas_subscription_id}")
