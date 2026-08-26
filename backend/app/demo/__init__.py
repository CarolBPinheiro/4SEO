"""Sandbox de demonstração local (DEMO_MODE)."""

from app.demo.config import (
    DemoModeError,
    assert_demo_safe,
    demo_info_payload,
    is_demo_mode,
    is_demo_token,
)

__all__ = [
    "DemoModeError",
    "assert_demo_safe",
    "demo_info_payload",
    "is_demo_mode",
    "is_demo_token",
]
