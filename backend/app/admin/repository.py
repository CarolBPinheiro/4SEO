"""Persistência admin via service role (PostgREST + Auth Admin API)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx

from app.supabase_client import SUPABASE_URL, SUPABASE_KEY, get_supabase

logger = logging.getLogger(__name__)


class AdminRepository:
    def __init__(self) -> None:
        self.db = get_supabase()
        self.url = (SUPABASE_URL or "").rstrip("/")
        self.service_key = SUPABASE_KEY or ""

    async def insert_audit(
        self,
        *,
        actor_user_id: Optional[str],
        actor_email: Optional[str],
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            await self.db._request(
                "POST",
                "admin_audit_log",
                data={
                    "actor_user_id": actor_user_id,
                    "actor_email": actor_email,
                    "action": action,
                    "target_type": target_type,
                    "target_id": target_id,
                    "meta": meta or {},
                },
            )
        except Exception:
            logger.exception("Falha ao gravar admin_audit_log action=%s", action)

    async def list_audit(self, limit: int = 50) -> List[Dict[str, Any]]:
        result = await self.db._request(
            "GET",
            "admin_audit_log",
            params={
                "select": "*",
                "order": "created_at.desc",
                "limit": str(min(max(limit, 1), 200)),
            },
        )
        return result if isinstance(result, list) else []

    async def count_subscriptions_by_status(self) -> Dict[str, int]:
        result = await self.db._request(
            "GET",
            "subscriptions",
            params={"select": "status"},
        )
        counts: Dict[str, int] = {}
        if isinstance(result, list):
            for row in result:
                status = (row.get("status") or "unknown").lower()
                counts[status] = counts.get(status, 0) + 1
        return counts

    async def sum_active_mrr_estimate(self) -> float:
        """Soma amount das assinaturas active|trialing|past_due (não normaliza ciclo)."""
        result = await self.db._request(
            "GET",
            "subscriptions",
            params={
                "select": "amount,billing_cycle,status",
                "status": "in.(active,trialing,past_due)",
            },
        )
        total = 0.0
        if isinstance(result, list):
            for row in result:
                try:
                    amount = float(row.get("amount") or 0)
                except (TypeError, ValueError):
                    amount = 0.0
                cycle = (row.get("billing_cycle") or "monthly").lower()
                if cycle == "annual":
                    total += amount / 12.0
                elif cycle == "semiannual":
                    total += amount / 6.0
                else:
                    total += amount
        return round(total, 2)

    async def list_subscriptions(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, str] = {
            "select": "*",
            "order": "created_at.desc",
            "limit": str(min(max(limit, 1), 100)),
            "offset": str(max(offset, 0)),
        }
        if status and status != "all":
            params["status"] = f"eq.{status}"
        result = await self.db._request("GET", "subscriptions", params=params)
        return result if isinstance(result, list) else []

    async def get_subscriptions_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        result = await self.db._request(
            "GET",
            "subscriptions",
            params={
                "user_id": f"eq.{user_id}",
                "select": "*",
                "order": "updated_at.desc",
            },
        )
        return result if isinstance(result, list) else []

    async def get_checkouts_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        result = await self.db._request(
            "GET",
            "billing_checkouts",
            params={
                "user_id": f"eq.{user_id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": "20",
            },
        )
        return result if isinstance(result, list) else []

    async def subscriptions_created_since(self, since_iso: str) -> List[Dict[str, Any]]:
        result = await self.db._request(
            "GET",
            "subscriptions",
            params={
                "select": "id,status,plan_id,amount,created_at,user_id",
                "created_at": f"gte.{since_iso}",
                "order": "created_at.asc",
            },
        )
        return result if isinstance(result, list) else []

    async def recent_webhooks(self, limit: int = 30) -> List[Dict[str, Any]]:
        result = await self.db._request(
            "GET",
            "billing_webhook_events",
            params={
                "select": "event_id,event_type,received_at,processed_at",
                "order": "received_at.desc",
                "limit": str(min(max(limit, 1), 100)),
            },
        )
        return result if isinstance(result, list) else []

    async def count_unprocessed_webhooks(self) -> int:
        result = await self.db._request(
            "GET",
            "billing_webhook_events",
            params={
                "select": "event_id",
                "processed_at": "is.null",
                "limit": "500",
            },
        )
        if isinstance(result, list):
            return len(result)
        return 0

    async def count_sites(self) -> int:
        result = await self.db._request(
            "GET",
            "sites",
            params={"select": "id", "limit": "1000"},
        )
        return len(result) if isinstance(result, list) else 0

    async def list_auth_users(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        email_query: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Lista usuários via Supabase Auth Admin API."""
        if not self.url or not self.service_key:
            raise RuntimeError("Supabase service role não configurado")

        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        params: Dict[str, Any] = {
            "page": page,
            "per_page": min(max(per_page, 1), 100),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self.url}/auth/v1/admin/users",
                headers=headers,
                params=params,
            )
            if res.status_code >= 400:
                logger.error("Auth admin list users failed: %s", res.status_code)
                raise RuntimeError("Falha ao listar usuários no Auth")
            payload = res.json()
            users = payload.get("users") if isinstance(payload, dict) else payload
            if not isinstance(users, list):
                users = []
            total = int(payload.get("total", len(users))) if isinstance(payload, dict) else len(users)

        if email_query:
            q = email_query.strip().lower()
            users = [
                u
                for u in users
                if q in ((u.get("email") or "").lower())
            ]

        return users, total

    async def get_auth_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not self.url or not self.service_key:
            raise RuntimeError("Supabase service role não configurado")
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(
                f"{self.url}/auth/v1/admin/users/{quote(user_id)}",
                headers=headers,
            )
            if res.status_code == 404:
                return None
            if res.status_code >= 400:
                raise RuntimeError("Falha ao buscar usuário no Auth")
            return res.json()

    async def probe_database(self) -> bool:
        try:
            await self.db._request(
                "GET",
                "subscriptions",
                params={"select": "id", "limit": "1"},
            )
            return True
        except Exception:
            return False
