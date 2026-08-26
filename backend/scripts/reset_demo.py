#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apaga contas *@demo.4seo.local e reexecuta o seed."""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.demo.config import DEMO_EMAIL_DOMAIN  # noqa: E402
from seed_demo import DemoSeeder, SeedError, print_summary  # noqa: E402


def main() -> int:
    try:
        seeder = DemoSeeder()
        deleted = seeder.delete_demo_users()
        print(f"Removidas {deleted} conta(s) @{DEMO_EMAIL_DOMAIN}")
        result = seeder.seed()
    except SeedError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
