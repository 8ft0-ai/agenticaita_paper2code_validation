"""LLM-backed AgenticAITA agents."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, Mapping, cast

from .agents import AnalystConfig, RuleBasedAnalyst
from .azte import TriggerEvent
from .cbd import CBDResult
from .contracts import AnalystDecision, RiskDecision, Signal
from .llm import LLMError, LLMProvider
from .risk import DeterministicRiskManager, RiskConfig

LOG = logging.getLogger(__name__)

ANALYST_PROMPT = """\
You are the AgenticAITA Analyst. Analyze the market and produce a trading signal.
Respond ONLY in JSON with this schema:
{signal: long|short|wait, confidence: float[0,1], entry_price, stop_loss,
take_profit, size_usd, reasoning: string}.
Your reasoning MUST cite the composite score, volatility regime, and orderbook
context explicitly.
"""

RISK_PROMPT = """\
You are the AgenticAITA Risk Manager. Your goal is Proportional Portfolio
Balancing. Calculate size_usd based on the Analyst's confidence.
Respond ONLY in JSON with this schema:
{approved: bool, size_usd: float, negotiation_summary: string}.
"""


class LLMAnalyst:
    def __init__(self, provider: LLMProvider, config: AnalystConfig | None = None) -> None:
        self.provider = provider
        self.fallback = RuleBasedAnalyst(config)
        self.last_warning = ""
        self.last_prompt = ""

    def decide(self, event: TriggerEvent, cbd: CBDResult, episodic_memory: list[str] | None = None) -> AnalystDecision:
        self.last_warning = ""
        self.last_prompt = analyst_message(event, cbd, episodic_memory or [])
        try:
            return analyst_json(self.provider.complete(ANALYST_PROMPT, self.last_prompt), event, cbd)
        except (LLMError, TypeError, ValueError) as exc:
            self.last_warning = f"LLMAnalyst fallback to deterministic proxy: {exc}"
            LOG.warning(self.last_warning)
            return self.fallback.decide(event, cbd, episodic_memory)


class LLMRiskManager:
    def __init__(self, provider: LLMProvider, config: RiskConfig | None = None) -> None:
        self.provider = provider
        self.config = config or RiskConfig()
        self.last_warning = ""
        self.last_prompt = ""
        self.layer_a = DeterministicRiskManager(self.config)

    def evaluate(self, decision: AnalystDecision) -> RiskDecision:
        self.last_warning = ""
        gate = self.layer_a.evaluate(decision)
        if not gate.approved:
            return gate

        self.last_prompt = json.dumps(
            {"analyst_decision": decision.to_dict(), "layer_a": gate.to_dict()},
            sort_keys=True,
        )
        try:
            return risk_json(self.provider.complete(RISK_PROMPT, self.last_prompt), self.config)
        except (LLMError, TypeError, ValueError) as exc:
            self.last_warning = f"LLMRiskManager fallback to deterministic approval: {exc}"
            LOG.warning(self.last_warning)
            return gate


def volatility_regime(event: TriggerEvent) -> str:
    if event.z_score >= 3 or event.abs_return >= 0.01:
        return "high"
    if event.z_score >= 2 or event.abs_return >= 0.003:
        return "active"
    return "low"


def analyst_message(event: TriggerEvent, cbd: CBDResult, memory: list[str]) -> str:
    return json.dumps(
        {
            "trigger": asdict(event),
            "cbd": asdict(cbd),
            "composite_score": cbd.omega,
            "volatility_regime": volatility_regime(event),
            "orderbook_context": "not available; OHLCV trigger context is used as proxy",
            "episodic_memory_briefing": memory[-5:] or ["No prior reasoning on this asset is available."],
        },
        sort_keys=True,
    )


def analyst_json(payload: Mapping[str, Any], event: TriggerEvent, cbd: CBDResult) -> AnalystDecision:
    signal = parse_signal(payload)
    reasoning = text_field(payload, "reasoning")
    return AnalystDecision(
        asset=event.asset,
        signal=signal,
        confidence=float_field(payload, "confidence", minimum=0.0, maximum=1.0),
        entry_price=float_field(payload, "entry_price", default=event.price, minimum=0.0, exclusive_minimum=True),
        stop_loss=float_field(payload, "stop_loss", default=event.price, minimum=0.0, exclusive_minimum=True),
        take_profit=float_field(payload, "take_profit", default=event.price, minimum=0.0, exclusive_minimum=True),
        size_usd=float_field(payload, "size_usd", minimum=0.0),
        cbd_score=cbd.omega,
        z_score=event.z_score,
        reasoning=reasoning,
    )


def risk_json(payload: Mapping[str, Any], config: RiskConfig) -> RiskDecision:
    approved = bool_field(payload, "approved")
    summary = text_field(payload, "negotiation_summary")
    if not approved:
        return RiskDecision(False, 0.0, "llm_layer_b_rejected", summary)

    size = float_field(payload, "size_usd", minimum=0.0, maximum=config.max_position_size_usd)
    return RiskDecision(
        approved=size > 0,
        size_usd=size if size > 0 else 0.0,
        rejection_reason="" if size > 0 else "llm_layer_b_zero_size",
        negotiation_summary=summary,
    )


def parse_signal(payload: Mapping[str, Any]) -> Signal:
    value = str(required_field(payload, "signal")).lower()
    if value not in {"long", "short", "wait"}:
        raise ValueError(f"signal must be one of long, short, wait; got {value!r}")
    return cast(Signal, value)


def bool_field(payload: Mapping[str, Any], field: str) -> bool:
    value = required_field(payload, field)
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError(f"{field} must be boolean, got {value!r}")


def text_field(payload: Mapping[str, Any], field: str) -> str:
    value = str(required_field(payload, field)).strip()
    if not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def float_field(
    payload: Mapping[str, Any],
    field: str,
    *,
    default: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_minimum: bool = False,
) -> float:
    raw = payload.get(field, default)
    if raw is None:
        raise ValueError(f"{field} is required")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric, got {raw!r}") from exc
    if minimum is not None:
        too_low = value <= minimum if exclusive_minimum else value < minimum
        if too_low:
            qualifier = "greater than" if exclusive_minimum else "at least"
            raise ValueError(f"{field} must be {qualifier} {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} must be at most {maximum}, got {value}")
    return value


def required_field(payload: Mapping[str, Any], field: str) -> Any:
    if field not in payload:
        raise ValueError(f"{field} is required")
    return payload[field]
