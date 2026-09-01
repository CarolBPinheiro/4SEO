"""Normalização de payloads Typebot → chamado de suporte."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Tuple

TICKET_STATUSES = ("new", "in_progress", "waiting_customer", "resolved")
TICKET_PRIORITIES = ("low", "medium", "high", "urgent")

_EMAIL_KEYS = ("email", "e-mail", "e_mail", "useremail", "user_email", "email_usuario")
_SUBJECT_KEYS = ("assunto", "subject", "titulo", "title", "tema")
_MESSAGE_KEYS = (
    "mensagem",
    "message",
    "messagecontent",
    "descricao",
    "description",
    "details",
    "detalhes",
    "comentario",
    "help",
)
_PRIORITY_KEYS = ("prioridade", "priority", "urgencia", "urgency")
_PLAN_KEYS = ("plano", "plan", "plan_id", "planid", "plano_contratado")
_USER_ID_KEYS = ("user_id", "userid", "user", "uid")
_NAME_KEYS = ("nome", "name", "username", "nome_usuario")

_PRIORITY_MAP = {
    "baixa": "low",
    "low": "low",
    "media": "medium",
    "média": "medium",
    "medium": "medium",
    "normal": "medium",
    "alta": "high",
    "high": "high",
    "urgente": "urgent",
    "urgent": "urgent",
    "critica": "urgent",
    "crítica": "urgent",
    "critical": "urgent",
}


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value).strip()


def _norm_key(key: Any) -> str:
    return (
        str(key or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )


def _flatten(payload: Any, prefix: str = "") -> Dict[str, str]:
    flat: Dict[str, str] = {}
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, Mapping):
                flat.update(_flatten(value, path))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Mapping):
                        name = (
                            item.get("variableName")
                            or item.get("key")
                            or item.get("name")
                            or item.get("blockId")
                            or key
                        )
                        val = item.get("value")
                        if val is None:
                            val = item.get("content")
                        if val is not None:
                            flat[str(name)] = _as_str(val)
                        else:
                            flat.update(_flatten(item, str(name)))
                    else:
                        flat[path] = _as_str(value)
                        break
            else:
                flat[str(key)] = _as_str(value)
                flat[path] = _as_str(value)
    return flat


def _pick(flat: Mapping[str, str], keys: Tuple[str, ...]) -> str:
    wanted = {_norm_key(k) for k in keys}
    for key, value in flat.items():
        if _norm_key(key) in wanted and value:
            return value
    return ""


def normalize_priority(value: str) -> str:
    mapped = _PRIORITY_MAP.get(value.strip().lower())
    if mapped in TICKET_PRIORITIES:
        return mapped
    return "medium"


def normalize_status(value: str) -> str:
    raw = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "novo": "new",
        "open": "new",
        "aberto": "new",
        "em_atendimento": "in_progress",
        "em_andamento": "in_progress",
        "progress": "in_progress",
        "aguardando_cliente": "waiting_customer",
        "waiting": "waiting_customer",
        "resolvido": "resolved",
        "done": "resolved",
        "closed": "resolved",
        "closed_resolved": "resolved",
    }
    mapped = aliases.get(raw, raw)
    return mapped if mapped in TICKET_STATUSES else "new"


def extract_ticket_fields(payload: Any) -> Dict[str, Any]:
    """Extrai campos de um POST Typebot (webhook block, Zapier ou result API)."""
    data = payload if isinstance(payload, dict) else {}
    flat = _flatten(data)

    answers = data.get("answers") if isinstance(data.get("answers"), (list, dict)) else None
    if answers:
        flat.update(_flatten({"answers": answers}))

    email = _pick(flat, _EMAIL_KEYS)
    subject = _pick(flat, _SUBJECT_KEYS)
    message = _pick(flat, _MESSAGE_KEYS)
    if not subject:
        subject = (message[:80] + "…") if len(message) > 80 else (message or "Chamado Typebot")
    if not message:
        message = subject

    result_id = (
        _as_str(data.get("resultId"))
        or _as_str(data.get("result_id"))
        or _as_str(data.get("id"))
        or None
    )
    if result_id == "":
        result_id = None

    return {
        "typebot_result_id": result_id,
        "user_email": email or None,
        "user_id": _pick(flat, _USER_ID_KEYS) or None,
        "user_name": _pick(flat, _NAME_KEYS) or None,
        "plan_id": _pick(flat, _PLAN_KEYS) or None,
        "subject": subject[:200],
        "message": message[:8000],
        "priority": normalize_priority(_pick(flat, _PRIORITY_KEYS)),
    }


def summarize_ticket_counts(rows: List[Mapping[str, Any]]) -> Dict[str, int]:
    counts = {status: 0 for status in TICKET_STATUSES}
    for row in rows:
        status = normalize_status(str(row.get("status") or "new"))
        counts[status] = counts.get(status, 0) + 1
    return counts
