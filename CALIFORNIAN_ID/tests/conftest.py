"""Pytest fixtures — force provider=mock in tests (HARD_RULES exception).

Per _work/HARD_RULES.md §1, mock is forbidden in prod runtime; the ONLY
allowed place is pytest. This fixture makes the exception explicit:
every test session sets CALIFORNIAN_ID_PROVIDER=mock so that
config.role_provider() short-circuits to mock without needing any real
LLM key.

Live-provider tests in tests/acceptance/ override this by requiring a
real key and pytest.skip'ing if it's absent.
"""
import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _force_mock_provider_for_tests():
    """Set CALIFORNIAN_ID_PROVIDER=mock for the whole session, unless the
    test explicitly sets a real provider (live acceptance tests do)."""
    prev = os.environ.get("CALIFORNIAN_ID_PROVIDER")
    if not prev:
        os.environ["CALIFORNIAN_ID_PROVIDER"] = "mock"
    yield
    if prev is None:
        os.environ.pop("CALIFORNIAN_ID_PROVIDER", None)
    else:
        os.environ["CALIFORNIAN_ID_PROVIDER"] = prev
