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
TRIAL_COLUMNS = ("trial_ends_at", "trial_started_at")


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

        trial_select = ",".join(TRIAL_COLUMNS)
        trial_resp = client.get(
            f"{url}/rest/v1/subscriptions",
            headers=headers,
            params={"select": trial_select, "limit": "1"},
        )
        if trial_resp.status_code == 200:
            print(f"subscriptions.{','.join(TRIAL_COLUMNS)}: OK")
        else:
            ok = False
            print(
                f"subscriptions trial columns: MISSING ({trial_resp.status_code}) "
                f"{trial_resp.text[:200]}"
            )

    if not ok:
        print(
            "\nAplique supabase/billing.sql e "
            "supabase/migrations/20260812190000_subscription_trial.sql "
            "(veja supabase/BILLING_APPLY.md ou: python scripts/apply_billing_schema.py).",
            file=sys.stderr,
        )
        return 1

    print("\nSchema de billing + trial presente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
