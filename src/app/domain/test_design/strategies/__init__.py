"""F022 strategy implementations.

See ``docs/01-product/F022_SPEC.md`` §5 for the per-strategy contract.

Each strategy is a stateless callable: ``generate(endpoint) -> list[TestIntent]``.
The engine wraps each call with truncation + WARNING per F022_SPEC §6.1.
"""
from __future__ import annotations

from .happy_path import HappyPathStrategy
from .required_field_missing import RequiredFieldMissingStrategy
from .enum_coverage import EnumCoverageStrategy
from .boundary_min_max import BoundaryMinMaxStrategy
from .format_invalid import FormatInvalidStrategy
from .auth_missing import AuthMissingStrategy


__all__ = [
    "HappyPathStrategy",
    "RequiredFieldMissingStrategy",
    "EnumCoverageStrategy",
    "BoundaryMinMaxStrategy",
    "FormatInvalidStrategy",
    "AuthMissingStrategy",
]