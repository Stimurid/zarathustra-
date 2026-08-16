"""Thin re-export shim over ``californian_id.models`` — one import surface.

Reasons for a shim rather than importing californian_id directly at every
call site:

    * a single grep for ``socrates_runtime.models`` shows every model
      touchpoint;
    * a future test could swap the shim to a test-only build_client;
    * the shim keeps the provider abstraction reused, not duplicated —
      no per-provider Socrates classes, no parallel factory.
"""
from __future__ import annotations

from californian_id.models import Message, ModelClient, ModelResult, build_client

__all__ = ["Message", "ModelClient", "ModelResult", "build_client"]
