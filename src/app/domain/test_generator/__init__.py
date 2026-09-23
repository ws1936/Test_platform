"""F023 Test Generator — TestIntent → TestCaseCreateRequest.

See ``docs/01-product/F023_SPEC.md`` §3 for the full contract.
Pure functions, no DB / HTTP coupling. ADR-009 locks the design.
"""

from __future__ import annotations

from app.domain.test_generator.generator import TestGenerator

__all__ = ["TestGenerator"]
