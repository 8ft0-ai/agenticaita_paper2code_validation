"""Deterministic risk gates from the AGENTICAITA paper."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import AnalystDecision, RiskDecision


@dataclass(frozen=True)
class RiskConfig:
    confidence_gate: float = 0.60
    max_stop_loss_fraction: float = 0.02
    max_position_size_usd: float = 500.0


class DeterministicRiskManager:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def evaluate(self, decision: AnalystDecision) -> RiskDecision:
        if decision.signal not in {"long", "short"}:
            return RiskDecision(False, 0.0, "signal_wait_or_invalid", "Rejected before LLM validation: signal is not directional.")
        if decision.confidence < self.config.confidence_gate:
            return RiskDecision(False, 0.0, "confidence_below_gate", "Rejected before LLM validation: confidence gate failed.")
        if decision.entry_price <= 0:
            return RiskDecision(False, 0.0, "invalid_entry_price", "Rejected before LLM validation: invalid entry price.")
        if decision.signal == "long" and not (decision.stop_loss < decision.entry_price < decision.take_profit):
            return RiskDecision(False, 0.0, "invalid_long_exit_levels", "Rejected before LLM validation: long exit levels are not directional.")
        if decision.signal == "short" and not (decision.take_profit < decision.entry_price < decision.stop_loss):
            return RiskDecision(False, 0.0, "invalid_short_exit_levels", "Rejected before LLM validation: short exit levels are not directional.")
        stop_distance = abs(decision.entry_price - decision.stop_loss) / decision.entry_price
        if stop_distance > self.config.max_stop_loss_fraction:
            return RiskDecision(False, 0.0, "stop_loss_too_wide", "Rejected before LLM validation: stop-loss exceeds 2% hard gate.")
        if decision.size_usd > self.config.max_position_size_usd:
            return RiskDecision(False, 0.0, "position_too_large", "Rejected before LLM validation: size exceeds maximum position.")
        return RiskDecision(True, min(decision.size_usd, self.config.max_position_size_usd), "", "Approved by deterministic hard gates.")
