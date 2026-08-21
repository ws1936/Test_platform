"""F022 Test Design Engine.

Public surface per F022_SPEC §10.2:

* ``TestDesignEngine`` — strategy orchestration
* ``TestIntent`` — declarative case intent (consumed by F023)
* ``StrategyError`` / ``StrategyCapError`` / ``StrategyDisabledError``
"""
from __future__ import annotations

from app.domain.test_design.engine import TestDesignEngine
from app.domain.test_design.exceptions import (
    StrategyCapError,
    StrategyDisabledError,
    StrategyError,
)
from app.domain.test_design.schema import TestIntent


__all__ = [
    "StrategyCapError",
    "StrategyDisabledError",
    "StrategyError",
    "TestDesignEngine",
    "TestIntent",
]