"""F022 strategy exceptions.

Per F022_SPEC §6.2, F022 raises Python exceptions only.  HTTP-level
business codes belong to F023 / ADR-009 and are *not* defined here.
"""
from __future__ import annotations


class StrategyError(Exception):
    """F022 基线策略异常。"""


class StrategyCapError(StrategyError):
    """``strategy_*_max_per_op > generator_max_intents_per_operation``.

    Raised at engine construction (startup-time validation per
    F022_SPEC §6.1 / F022_PRECHECK §2.4).  Halts startup rather than
    silently truncating.
    """


class StrategyDisabledError(StrategyError):
    """F023 calls ``design()`` requesting a strategy that is not enabled.

    Defensive only — current F022 callers only iterate ``enabled``
    strategies so this should not occur in production.
    """


__all__ = [
    "StrategyError",
    "StrategyCapError",
    "StrategyDisabledError",
]