"""Cliente HTTP Asaas com timeout e retry com backoff.

Documentação: https://docs.asaas.com/reference/create-new-checkout
Auth: header `access_token` com a API Key.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api-sandbox.asaas.com/v3"
DEFAULT_TIMEOUT_S = 20.0
MAX_ATTEMPTS = 3
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class AsaasConfigError(RuntimeError):
    """Configuração Asaas ausente ou inválida."""


class AsaasApiError(RuntimeError):
    """Falha ao chamar a API Asaas."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        asaas_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.asaas_code = asaas_code


def _api_key() -> str:
    return (os.getenv("ASAAS_API_KEY") or "").strip()


def _base_url() -> str:
    raw = (os.getenv("ASAAS_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
    return raw


def is_asaas_configured() -> bool:
    return bool(_api_key())


def _safe_asaas_error_message(response: httpx.Response) -> tuple[str, Optional[str]]:
    """Extrai mensagem pública do Asaas sem vazar payloads sensíveis."""
    asaas_code: Optional[str] = None
    try:
        data = response.json()
    except Exception:
        return "Falha ao criar checkout no Asaas.", None

    errors: List[Any] = []
    if isinstance(data, dict):
        raw_errors = data.get("errors")
        if isinstance(raw_errors, list):
            errors = raw_errors

    descriptions: List[str] = []
    for item in errors:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        desc = str(item.get("description") or "").strip()
        if code and not asaas_code:
            asaas_code = code
        if desc:
            descriptions.append(desc)

    if asaas_code == "invalid_environment":
        return (
            "Chave Asaas incompatível com o ambiente configurado "
            "(sandbox vs produção). Ajuste ASAAS_API_KEY e ASAAS_BASE_URL.",
            asaas_code,
        )

    if descriptions:
        return descriptions[0][:280], asaas_code

    return "Falha ao criar checkout no Asaas.", asaas_code


async def create_checkout(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST /v3/checkouts — cria sessão de checkout hospedada."""
    api_key = _api_key()
    if not api_key:
        raise AsaasConfigError(
            "ASAAS_API_KEY não configurada. Defina no backend/.env."
        )

    url = f"{_base_url()}/checkouts"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": api_key,
        "User-Agent": "4SEO-Billing/1.0",
    }
    timeout = httpx.Timeout(DEFAULT_TIMEOUT_S, connect=10.0)
    last_error: Optional[Exception] = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

            if response.status_code in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS:
                delay = min(2 ** (attempt - 1), 4)
                logger.warning(
                    "Asaas checkout retryable status=%s attempt=%s; backoff=%ss",
                    response.status_code,
                    attempt,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 400:
                message, asaas_code = _safe_asaas_error_message(response)
                logger.error(
                    "Asaas checkout failed status=%s code=%s body_len=%s",
                    response.status_code,
                    asaas_code or "unknown",
                    len(response.text or ""),
                )
                raise AsaasApiError(
                    message,
                    status_code=response.status_code,
                    asaas_code=asaas_code,
                )

            data = response.json()
            if not isinstance(data, dict):
                raise AsaasApiError("Resposta inválida do Asaas.")
            return data

        except AsaasApiError:
            raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt >= MAX_ATTEMPTS:
                break
            delay = min(2 ** (attempt - 1), 4)
            logger.warning(
                "Asaas checkout network error attempt=%s; backoff=%ss err=%s",
                attempt,
                delay,
                type(exc).__name__,
            )
            await asyncio.sleep(delay)

    logger.error(
        "Asaas checkout exhausted retries: %s",
        type(last_error).__name__ if last_error else "unknown",
    )
    raise AsaasApiError(
        "Serviço Asaas indisponível. Tente novamente em instantes.",
        status_code=503,
    )
