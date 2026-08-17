# -*- coding: utf-8 -*-
"""Aplica schema de billing (+ trial) via Management API do Supabase.

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
DEFAULT_SQL_FILES = (
    ROOT / "supabase" / "billing.sql",
    ROOT / "supabase" / "migrations" / "20260812190000_subscription_trial.sql",
)
API = "https://api.supabase.com/v1/projects/{ref}/database/query"


def _apply_sql(
    *, client: httpx.Client, url: str, headers: dict[str, str], sql_file: Path
) -> int:
    if not sql_file.is_file():
        print(f"ERRO: arquivo SQL não encontrado: {sql_file}", file=sys.stderr)
        return 2

    sql = sql_file.read_text(encoding="utf-8")
    print(f"Aplicando {sql_file.name}…")
    resp = client.post(url, headers=headers, json={"query": sql})
    if resp.status_code not in (200, 201):
        print(f"FALHA HTTP {resp.status_code}: {resp.text[:800]}", file=sys.stderr)
        return 1
    print(f"OK — {sql_file.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-ref", default=os.getenv("SUPABASE_PROJECT_REF", DEFAULT_REF)
    )
    parser.add_argument(
        "--sql-file",
        type=Path,
        action="append",
        dest="sql_files",
        help="Arquivo SQL (pode repetir). Default: billing.sql + migration de trial.",
    )
    args = parser.parse_args()

    token = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
    if not token:
        print(
            "ERRO: defina SUPABASE_ACCESS_TOKEN (Personal Access Token do Supabase Dashboard).\n"
            "Enquanto isso, aplique manualmente: supabase/BILLING_APPLY.md",
            file=sys.stderr,
        )
        return 2

    sql_files = tuple(args.sql_files) if args.sql_files else DEFAULT_SQL_FILES
    url = API.format(ref=args.project_ref)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print(f"Projeto {args.project_ref}")
    with httpx.Client(timeout=120.0) as client:
        for sql_file in sql_files:
            code = _apply_sql(
                client=client, url=url, headers=headers, sql_file=sql_file
            )
            if code != 0:
                return code

    print("Schema de billing + trial aplicado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
