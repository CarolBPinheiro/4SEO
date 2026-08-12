# -*- coding: utf-8 -*-
"""Inventário não-secreto do backend/.env para go-live (imprime SET/EMPTY)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")

KEYS = [
    ("SUPABASE_URL", True),
    ("SUPABASE_SERVICE_KEY", True),
    ("SUPABASE_ANON_KEY", True),
    ("OPENAI_API_KEY", True),
    ("FRONTEND_URL", True),
    ("BACKEND_URL", True),
    ("NUVEMSHOP_APP_ID", False),
    ("NUVEMSHOP_CLIENT_SECRET", False),
    ("SHOPIFY_API_KEY", False),
    ("SHOPIFY_API_SECRET", False),
    ("LOJAINTEGRADA_APP_KEY", False),
    ("ASAAS_API_KEY", True),
    ("ASAAS_BASE_URL", True),
    ("ASAAS_WEBHOOK_TOKEN", True),
    ("APP_PUBLIC_URL", True),
]


def main() -> int:
    print("=== Inventário backend/.env (sem valores) ===")
    missing_required = []
    for key, required in KEYS:
        val = (os.getenv(key) or "").strip()
        state = "SET" if val else "EMPTY"
        extra = ""
        if key == "ASAAS_BASE_URL" and val:
            extra = f" ({val})"
        if key.endswith("URL") and val:
            extra = f" ({val})"
        print(f"{key}: {state}{extra}")
        if required and not val:
            missing_required.append(key)

    print("")
    if missing_required:
        print("Faltando obrigatórios:", ", ".join(missing_required))
        return 1

    base = (os.getenv("ASAAS_BASE_URL") or "").lower()
    if "sandbox" not in base and "api.asaas.com" in base:
        print("AVISO: ASAAS_BASE_URL está em PRODUÇÃO — go-live pede Sandbox primeiro.")
    elif "sandbox" in base:
        print("OK: Asaas em Sandbox.")

    li = (os.getenv("LOJAINTEGRADA_APP_KEY") or "").strip()
    if not li:
        print("INFO: LOJAINTEGRADA_APP_KEY vazia — LI fora do go-live até chegar a chave.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
