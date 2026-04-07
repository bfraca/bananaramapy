"""Shared fixtures for integration tests."""

from __future__ import annotations

import os

import pytest


def _has_key(env_var: str) -> bool:
    return bool(os.environ.get(env_var))


requires_gemini = pytest.mark.skipif(
    not _has_key("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set",
)
requires_openai = pytest.mark.skipif(
    not _has_key("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
requires_together = pytest.mark.skipif(
    not _has_key("TOGETHER_API_KEY"),
    reason="TOGETHER_API_KEY not set",
)
