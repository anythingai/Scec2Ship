"""Demo mode utilities for judge-proof demonstrations."""

from .failure_injector import (
    inject_failure,
    generate_fix_patch,
    apply_fix_patch,
    get_demo_status,
    reset_demo_state,
    get_overlay_messages,
    is_demo_enabled,
    is_failure_injection_enabled,
)

__all__ = [
    "inject_failure",
    "generate_fix_patch",
    "apply_fix_patch",
    "get_demo_status",
    "reset_demo_state",
    "get_overlay_messages",
    "is_demo_enabled",
    "is_failure_injection_enabled",
]
