# -*- coding: utf-8 -*-
"""Verifica se as tabelas de billing existem no Supabase (via REST + service_role)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")

TABLES = ("billing_checkouts", "subscriptions", "billing_webhook_events")


def main() -> int:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY") or ""
    if not url or not key:
        print("ERRO: SUPABASE_URL / SUPABASE_SERVICE_KEY ausentes em backend/.env", file=sys.stderr)
        return 2

    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    ok = True
    with httpx.Client(timeout=30.0) as client:
        for table in TABLES:
            resp = client.get(
                f"{url}/rest/v1/{table}",
                headers=headers,
                params={"select": "id", "limit": "1"},
            )
            status = "OK" if resp.status_code == 200 else f"MISSING ({resp.status_code})"
            print(f"{table}: {status}")
            if resp.status_code != 200:
                ok = False

    if not ok:
        print(
            "\nAplique supabase/billing.sql (veja supabase/BILLING_APPLY.md "
            "ou: python scripts/apply_billing_schema.py).",
            file=sys.stderr,
        )
        return 1

    print("\nSchema de billing presente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
