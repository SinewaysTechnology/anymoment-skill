"""Example request bodies match the live OpenAPI schemas."""

from __future__ import annotations

import validate_examples


def test_live_openapi_accepts_skill_examples():
    assert validate_examples.main() == 0
