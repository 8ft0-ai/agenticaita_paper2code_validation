"""Deterministic stand-ins for the paper's LLM agents.

These agents are not claimed to reproduce the author's exact LLM behaviour.
They are a controlled surrogate that lets us test whether the published
architecture and gates are executable end-to-end.
"""
from __future__ import annotations

from dataclasses import dataclass

from .azte import TriggerEvent
from .cbd import CBDResult
from .contracts import AnalystDecision


@dataclass(frozen=True)
class AnalystConfig:
    base_position_size_usd: float = 188.0
    min_confidence_to_trade: float = 0.58
    stop_loss_fraction: float = 0.00627
    take_profit_fraction: float = 0.01894


class RuleBasedAnalyst:
    """A transparent proxy for an LLM analyst.

    Direction is based on the sign of the triggering return. Confidence combines
    anomaly strength and CBD score. This is intentionally simple and auditable.
    """

    def __init__(self, config: AnalystConfig | None = None) -> None:
        self.config = config or AnalystConfig()

    def decide(self, event: TriggerEvent, cbd: CBDResult) -> AnalystDecision:
        signal = "long" if event.signed_return > 0 else "short"
        confidence = max(0.0, min(1.0, 0.50 + 0.08 * min(event.z_score, 5.0) + 0.20 * cbd.omega))
        if confidence < self.config.min_confidence_to_trade:
            signal = "wait"
        entry = event.price
        if signal == "long":
            stop_loss = entry * (1.0 - self.config.stop_loss_fraction)
            take_profit = entry * (1.0 + self.config.take_profit_fraction)
        elif signal == "short":
            stop_loss = entry * (1.0 + self.config.stop_loss_fraction)
            take_profit = entry * (1.0 - self.config.take_profit_fraction)
        else:
            stop_loss = entry
            take_profit = entry
        reasoning = (
            f"Triggered by {event.reason}; z={event.z_score:.3f}; "
            f"abs_return={event.abs_return:.5f}; CBD omega={cbd.omega:.3f}; "
            f"rho_cb={cbd.correlation_break:.3f}; deterministic proxy decision."
        )
        return AnalystDecision(
            asset=event.asset,
            signal=signal,  # type: ignore[arg-type]
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            size_usd=self.config.base_position_size_usd,
            cbd_score=cbd.omega,
            z_score=event.z_score,
            reasoning=reasoning,
        )
