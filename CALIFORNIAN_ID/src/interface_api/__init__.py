"""Vertical-slice HTTP interface for Tinkuy Workspace.

TEST-QUALITY: not registered in production provider selection;
mounts on a separate port (default 8791) and stores state in a
separate SQLite file. Does not modify Socrates runtime.
"""
from .server import Handler, get_store, reset_store_for_tests, serve

__all__ = ["Handler", "get_store", "reset_store_for_tests", "serve"]
