#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cria contas e dados do sandbox local (somente *@demo.4seo.local)."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
load_dotenv(BACKEND_ROOT / ".env")
sys.path.insert(0, str(BACKEND_ROOT))

from app.demo.config import (  # noqa: E402
    DEMO_ACCOUNTS,
    DEMO_EMAIL_DOMAIN,
    DEMO_GSC_REFRESH,
    DEMO_GSC_SITE,
    DEMO_GSC_TOKEN,
    DEMO_STORES,
    demo_password,
)
from app.demo.scan import crawl_demo_site  # noqa: E402

BRT = timezone(timedelta(hours=-3))


class SeedError(RuntimeError):
    pass


def _env(name: str) -> str:
    import os

    return (os.getenv(name) or "").strip()


class DemoSeeder:
    def __init__(self) -> None:
        self.url = _env("SUPABASE_URL").rstrip("/")
        self.service_key = _env("SUPABASE_SERVICE_KEY")
        if not self.url or not self.service_key:
            raise SeedError(
                "SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios no backend/.env"
            )
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self.auth_headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }

    def _rest(self, method: str, table: str, *, json_data: Any = None, params: Optional[dict] = None) -> Any:
        with httpx.Client(timeout=30.0) as client:
            resp = client.request(
                method,
                f"{self.url}/rest/v1/{table}",
                headers=self.headers,
                json=json_data,
                params=params,
            )
        if resp.status_code >= 400:
            raise SeedError(f"REST {method} {table} falhou ({resp.status_code}): {resp.text[:500]}")
        if not resp.text:
            return None
        return resp.json()

    def _auth(self, method: str, path: str, *, json_data: Any = None, params: Optional[dict] = None) -> httpx.Response:
        with httpx.Client(timeout=30.0) as client:
            return client.request(
                method,
                f"{self.url}/auth/v1/{path}",
                headers=self.auth_headers,
                json=json_data,
                params=params,
            )

    def list_auth_users(self) -> List[Dict[str, Any]]:
        users: List[Dict[str, Any]] = []
        page = 1
        while True:
            resp = self._auth("GET", "admin/users", params={"page": page, "per_page": 200})
            if resp.status_code >= 400:
                raise SeedError(f"Falha ao listar usuários Auth ({resp.status_code})")
            payload = resp.json()
            batch = payload.get("users") if isinstance(payload, dict) else payload
            if not isinstance(batch, list) or not batch:
                break
            users.extend(batch)
            if len(batch) < 200:
                break
            page += 1
        return users

    def upsert_user(self, email: str, password: str) -> Dict[str, Any]:
        existing = [
            u for u in self.list_auth_users()
            if (u.get("email") or "").lower() == email.lower()
        ]
        if existing:
            user_id = existing[0]["id"]
            resp = self._auth(
                "PUT",
                f"admin/users/{user_id}",
                json_data={"password": password, "email_confirm": True},
            )
            if resp.status_code >= 400:
                raise SeedError(f"Falha ao atualizar senha de {email}: {resp.text[:400]}")
            return resp.json() if resp.text else existing[0]

        resp = self._auth(
            "POST",
            "admin/users",
            json_data={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"demo": True},
            },
        )
        if resp.status_code >= 400:
            raise SeedError(f"Falha ao criar {email}: {resp.text[:400]}")
        return resp.json()

    def delete_demo_users(self) -> int:
        deleted = 0
        for user in self.list_auth_users():
            email = (user.get("email") or "").lower()
            if not email.endswith(f"@{DEMO_EMAIL_DOMAIN}"):
                continue
            user_id = user["id"]
            # billing usa ON DELETE SET NULL — limpar explicitamente antes do Auth
            self._rest("DELETE", f"subscriptions?user_id=eq.{user_id}")
            self._rest("DELETE", f"billing_checkouts?user_id=eq.{user_id}")
            resp = self._auth("DELETE", f"admin/users/{user_id}")
            if resp.status_code >= 400 and resp.status_code != 404:
                raise SeedError(f"Falha ao apagar {email}: {resp.text[:400]}")
            deleted += 1
        return deleted

    def upsert_subscription(
        self,
        user_id: str,
        *,
        plan_id: str,
        status: str,
        trial: bool = False,
    ) -> None:
        existing = self._rest(
            "GET",
            "subscriptions",
            params={"user_id": f"eq.{user_id}", "select": "id", "limit": "1"},
        )
        now = datetime.now(timezone.utc)
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "status": status,
            "amount": 0,
            "currency": "BRL",
            "updated_at": now.isoformat(),
        }
        if trial:
            payload["trial_started_at"] = now.isoformat()
            payload["trial_ends_at"] = (now + timedelta(days=7)).isoformat()
            payload["current_period_end"] = payload["trial_ends_at"]
        else:
            payload["trial_started_at"] = None
            payload["trial_ends_at"] = None
            payload["current_period_end"] = (now + timedelta(days=365)).isoformat()
        if existing:
            self._rest(
                "PATCH",
                f"subscriptions?id=eq.{existing[0]['id']}",
                json_data=payload,
            )
        else:
            self._rest("POST", "subscriptions", json_data=payload)

    def seed_store_and_content(self, user_id: str) -> None:
        cfg = DEMO_STORES["nuvemshop"]
        sites = self._rest(
            "GET",
            "sites",
            params={"user_id": f"eq.{user_id}", "select": "id", "limit": "1"},
        )
        if sites:
            site_id = sites[0]["id"]
            self._rest(
                "PATCH",
                f"sites?id=eq.{site_id}",
                json_data={
                    "base_url": cfg["base_url"],
                    "platform": "nuvemshop",
                },
            )
        else:
            created = self._rest(
                "POST",
                "sites",
                json_data={
                    "user_id": user_id,
                    "base_url": cfg["base_url"],
                    "platform": "nuvemshop",
                },
            )
            site_id = created[0]["id"] if isinstance(created, list) else created["id"]

        self._rest("DELETE", f"user_integrations?user_id=eq.{user_id}")
        self._rest(
            "POST",
            "user_integrations",
            json_data={
                "user_id": user_id,
                "platform": "nuvemshop",
                "store_url": cfg["store_url"],
                "access_token": cfg["token"],
                "store_name": cfg["store_name"],
                "metadata": {"demo": True, "store_id": cfg["store_id"]},
            },
        )

        crawl = crawl_demo_site(cfg["base_url"], max_pages=30)
        self._rest("DELETE", f"pages?site_id=eq.{site_id}")
        self._rest("DELETE", f"seo_tasks?site_id=eq.{site_id}")
        self._rest("DELETE", f"scan_runs?site_id=eq.{site_id}")

        page_ids: Dict[str, str] = {}
        for page in crawl["pages"]:
            row = self._rest(
                "POST",
                "pages",
                json_data={
                    "site_id": site_id,
                    "url": page["url"],
                    "title": page.get("title"),
                    "meta_description": page.get("meta_description"),
                    "h1": page.get("h1"),
                    "issues": page.get("issues") or {},
                    "score": page.get("score") or 0,
                    "last_scanned_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            page_id = row[0]["id"] if isinstance(row, list) else row["id"]
            page_ids[page["url"]] = page_id
            for issue, present in (page.get("issues") or {}).items():
                if not present:
                    continue
                self._rest(
                    "POST",
                    "seo_tasks",
                    json_data={
                        "site_id": site_id,
                        "page_id": page_id,
                        "issue_type": issue,
                        "description": issue,
                        "suggestion": f"Corrigir {issue} na página demo",
                        "priority": "medium",
                        "status": "pending",
                        "ai_generated": True,
                    },
                )

        now = datetime.now(timezone.utc)
        self._rest(
            "POST",
            "scan_runs",
            json_data={
                "site_id": site_id,
                "status": "completed",
                "started_at": (now - timedelta(minutes=2)).isoformat(),
                "completed_at": now.isoformat(),
                "pages_scanned": crawl["pages_analyzed"],
                "tasks_created": crawl["total_issues"],
                "avg_score": crawl["average_score"],
                "issues_summary": crawl["issues_summary"],
            },
        )

        self._rest("DELETE", f"daily_snapshots?user_id=eq.{user_id}")
        today = datetime.now(BRT).date()
        for i in range(30):
            day = today - timedelta(days=29 - i)
            impressions = 400 + i * 18
            clicks = 20 + i * 2
            self._rest(
                "POST",
                "daily_snapshots",
                json_data={
                    "user_id": user_id,
                    "date": day.isoformat(),
                    "impressions": impressions,
                    "clicks": clicks,
                    "ctr": round(clicks / impressions, 4),
                    "position_avg": round(18 - i * 0.15, 2),
                    "pages_count": 12,
                },
            )

        self._rest("DELETE", f"user_search_terms?user_id=eq.{user_id}")
        terms = [
            "tênis running feminino",
            "camiseta algodão",
            "bolsa tote lona",
            "seo ecommerce",
            "tênis slip on",
        ]
        for term in terms:
            created = self._rest(
                "POST",
                "user_search_terms",
                json_data={"user_id": user_id, "term": term},
            )
            term_id = created[0]["id"] if isinstance(created, list) else created["id"]
            history = [{"date": (today - timedelta(days=j)).isoformat(), "value": 40 + j} for j in range(14)]
            self._rest(
                "POST",
                "term_snapshots",
                json_data={
                    "term_id": term_id,
                    "user_id": user_id,
                    "interest_over_time": {"history": history},
                    "related_queries": {
                        "top": [{"query": f"{term} barato", "value": 100}],
                        "rising": [{"query": f"{term} 2026", "value": 140}],
                    },
                    "date": today.isoformat(),
                },
            )

        expires = datetime.now(timezone.utc) + timedelta(days=30)
        existing_gsc = self._rest(
            "GET",
            "gsc_tokens",
            params={"user_id": f"eq.{user_id}", "select": "id", "limit": "1"},
        )
        gsc_payload = {
            "user_id": user_id,
            "access_token": DEMO_GSC_TOKEN,
            "refresh_token": DEMO_GSC_REFRESH,
            "expires_at": expires.isoformat(),
            "site_url": DEMO_GSC_SITE,
        }
        if existing_gsc:
            self._rest(
                "PATCH",
                f"gsc_tokens?user_id=eq.{user_id}",
                json_data=gsc_payload,
            )
        else:
            self._rest("POST", "gsc_tokens", json_data=gsc_payload)

    def seed(self) -> Dict[str, Any]:
        password = demo_password()
        created: Dict[str, str] = {}
        for account in DEMO_ACCOUNTS:
            user = self.upsert_user(account["email"], password)
            user_id = user["id"]
            created[account["role"]] = user_id
            if account["role"] == "trial":
                self.upsert_subscription(
                    user_id, plan_id=account["plan_id"], status="trialing", trial=True
                )
            else:
                self.upsert_subscription(
                    user_id, plan_id=account["plan_id"], status="active", trial=False
                )
        self.seed_store_and_content(created["full"])
        return {
            "password": password,
            "users": created,
            "admin_email": next(a["email"] for a in DEMO_ACCOUNTS if a["role"] == "admin"),
        }


def print_summary(result: Dict[str, Any]) -> None:
    print("")
    print("Sandbox 4SEO semeado.")
    print("  App:        http://localhost:8080/login")
    print("  Marketing:  http://localhost:3000")
    print("  API:        http://localhost:8000/docs")
    print("")
    print("  demo@demo.4seo.local   plano Scale (full)")
    print("  trial@demo.4seo.local  trial 7 dias")
    print("  admin@demo.4seo.local  admin + Scale")
    print(f"  senha: {result['password']}")
    print("")
    print("  Inclua admin@demo.4seo.local em ADMIN_EMAILS no backend/.env")
    print("  e ligue DEMO_MODE=true (ENVIRONMENT=development).")
    print("")


def main() -> int:
    try:
        seeder = DemoSeeder()
        result = seeder.seed()
    except SeedError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
