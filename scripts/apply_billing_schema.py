# -*- coding: utf-8 -*-
"""Aplica supabase/billing.sql via Management API do Supabase.

Requer SUPABASE_ACCESS_TOKEN (Personal Access Token: https://supabase.com/dashboard/account/tokens)
com escopo database:write no projeto.

Uso:
  set SUPABASE_ACCESS_TOKEN=sbp_...
  python scripts/apply_billing_schema.py

Ou com project ref explícito:
  python scripts/apply_billing_schema.py --project-ref emnwonpdziqhtcfpuxxp
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REF = "emnwonpdziqhtcfpuxxp"
SQL_PATH = ROOT / "supabase" / "billing.sql"
API = "https://api.supabase.com/v1/projects/{ref}/database/query"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-ref", default=os.getenv("SUPABASE_PROJECT_REF", DEFAULT_REF))
    parser.add_argument("--sql-file", type=Path, default=SQL_PATH)
    args = parser.parse_args()

    token = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
    if not token:
        print(
            "ERRO: defina SUPABASE_ACCESS_TOKEN (Personal Access Token do Supabase Dashboard).\n"
            "Enquanto isso, aplique manualmente: supabase/BILLING_APPLY.md",
            file=sys.stderr,
        )
        return 2

    if not args.sql_file.is_file():
        print(f"ERRO: arquivo SQL não encontrado: {args.sql_file}", file=sys.stderr)
        return 2

    sql = args.sql_file.read_text(encoding="utf-8")
    url = API.format(ref=args.project_ref)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print(f"Aplicando {args.sql_file.name} em projeto {args.project_ref}…")
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, headers=headers, json={"query": sql})

    if resp.status_code not in (200, 201):
        print(f"FALHA HTTP {resp.status_code}: {resp.text[:800]}", file=sys.stderr)
        return 1

    print("OK — billing.sql aplicado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
