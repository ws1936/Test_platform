"""F022 TestDesignEngine — orchestrates the 6 strategies.

Per F022_SPEC §6.  Constructor takes a ``Settings``-like object (we
type as a Protocol so the engine doesn't import ``app.config`` —
keeps F022 self-contained for testing and future reuse).

Public surface:

* ``TestDesignEngine(settings)`` — construct + run startup cap check.
* ``engine.design(endpoint)`` — per-operation entry; returns
  ``list[TestIntent]`` after truncation.
* ``engine.design_batch(endpoints)`` — bulk entry; returns dict keyed
  by ``"<METHOD> <path>"``.

Truncation rules (F022_SPEC §6.1 / F022_PRECHECK §2.2):

* Each strategy's output is truncated to its own ``max_per_op`` (with
  WARNING); engine also re-applies the cap defensively.
* Total intents > ``max_intents_per_op`` triggers a hard truncation
  by strategy priority (happy_path first).
"""
from __future__ import annotations
import logging
from typing import Any, Optional, Protocol

from app.domain.openapi_importer.schema_model import EndpointSchema
from app.domain.test_design.exceptions import StrategyCapError
from app.domain.test_design.schema import TestIntent
from app.domain.test_design.strategies.auth_missing import AuthMissingStrategy
from app.domain.test_design.strategies.boundary_min_max import BoundaryMinMaxStrategy
from app.domain.test_design.strategies.enum_coverage import EnumCoverageStrategy
from app.domain.test_design.strategies.format_invalid import FormatInvalidStrategy
from app.domain.test_design.strategies.happy_path import HappyPathStrategy
from app.domain.test_design.strategies.required_field_missing import (
    RequiredFieldMissingStrategy,
)


logger = logging.getLogger(__name__)


# Strategy execution priority: first in list runs first; in hard-cap
# truncation, earlier-produced intents are kept, later ones dropped.
# Matches F022_SPEC §2 Q9.
_STRATEGY_ORDER: tuple[str, ...] = (
    "happy_path",
    "required_field_missing",
    "enum_coverage",
    "boundary_min_max",
    "format_invalid",
    "auth_missing",
)


class _StrategySettings(Protocol):
    """Subset of ``Settings`` that the engine reads.

    Defined as a Protocol so F022 doesn't pull in ``app.config`` —
    keeps tests lightweight and lets F022 be reused with custom
    settings objects.
    """

    strategy_happy_path: bool
    strategy_required_field_missing: bool
    strategy_enum_coverage: bool
    strategy_boundary_min_max: bool
    strategy_format_invalid: bool
    strategy_auth_missing: bool

    generator_max_intents_per_operation: int

    strategy_required_field_missing_max_per_op: int
    strategy_enum_coverage_max_per_op: int
    strategy_boundary_min_max_max_per_op: int
    strategy_format_invalid_max_per_op: int
    strategy_auth_missing_max_per_op: int


class TestDesignEngine:
    """F022 策略编排引擎。"""

    def __init__(self, settings: _StrategySettings) -> None:
        self._enabled: dict[str, bool] = {
            "happy_path": True,  # always on per F022_SPEC §5.2.1 / Q4
            "required_field_missing": settings.strategy_required_field_missing,
            "enum_coverage": settings.strategy_enum_coverage,
            "boundary_min_max": settings.strategy_boundary_min_max,
            "format_invalid": settings.strategy_format_invalid,
            "auth_missing": settings.strategy_auth_missing,
        }
        self._max_per_op_total: int = settings.generator_max_intents_per_operation
        self._strategies = {
            "happy_path": HappyPathStrategy(),
            "required_field_missing": RequiredFieldMissingStrategy(
                max_per_op=settings.strategy_required_field_missing_max_per_op
            ),
            "enum_coverage": EnumCoverageStrategy(
                max_per_op=settings.strategy_enum_coverage_max_per_op
            ),
            "boundary_min_max": BoundaryMinMaxStrategy(
                max_per_op=settings.strategy_boundary_min_max_max_per_op
            ),
            "format_invalid": FormatInvalidStrategy(
                max_per_op=settings.strategy_format_invalid_max_per_op
            ),
            "auth_missing": AuthMissingStrategy(
                max_per_op=settings.strategy_auth_missing_max_per_op
            ),
        }
        self._validate_caps()

    # ---- 启动校验 -----------------------------------------------------
    def _validate_caps(self) -> None:
        for name, strat in self._strategies.items():
            if strat.max_per_op > self._max_per_op_total:
                raise StrategyCapError(
                    f"strategy '{name}' max_per_op={strat.max_per_op} "
                    f"exceeds generator_max_intents_per_operation="
                    f"{self._max_per_op_total}"
                )
        if not (1 <= self._max_per_op_total <= 100):
            raise StrategyCapError(
                f"generator_max_intents_per_operation must be in [1, 100], "
                f"got {self._max_per_op_total}"
            )

    # ---- 对外接口 -----------------------------------------------------
    def design(self, endpoint: EndpointSchema) -> list[TestIntent]:
        """Per-operation 设计入口（F023 主调用）。"""
        intents: list[TestIntent] = []
        for name in _STRATEGY_ORDER:
            if not self._enabled.get(name, False):
                continue
            strat = self._strategies[name]
            produced = strat.generate(endpoint)
            if name != "happy_path":
                # happy_path always 1 (Q8) and not subject to per-strategy cap
                if len(produced) > strat.max_per_op:
                    logger.warning(
                        "F022 strategy truncated: strategy=%s produced=%d "
                        "cap=%d operation=%s %s",
                        name,
                        len(produced),
                        strat.max_per_op,
                        endpoint.method,
                        endpoint.path,
                    )
                    produced = produced[: strat.max_per_op]
            intents.extend(produced)
        # 硬截（按策略优先级取前 N）
        if len(intents) > self._max_per_op_total:
            logger.warning(
                "F022 hard cap hit: produced=%d cap=%d operation=%s %s",
                len(intents),
                self._max_per_op_total,
                endpoint.method,
                endpoint.path,
            )
            intents = intents[: self._max_per_op_total]
        return intents

    def design_batch(
        self, endpoints: list[EndpointSchema]
    ) -> dict[str, list[TestIntent]]:
        """批量入口（按 ``"<METHOD> <path>"`` 作 key 返回）。"""
        return {f"{ep.method} {ep.path}": self.design(ep) for ep in endpoints}


__all__ = ["TestDesignEngine"]