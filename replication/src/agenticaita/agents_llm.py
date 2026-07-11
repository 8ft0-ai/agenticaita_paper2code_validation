"""LLM-backed AgenticAITA agents."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Mapping, cast

from .agents import AnalystConfig, RuleBasedAnalyst
from .azte import TriggerEvent
from .cbd import CBDResult
from .contracts import AnalystDecision, RiskDecision, Signal
from .llm import LLMError, LLMProvider
from .risk import DeterministicRiskManager, RiskConfig

LOG = logging.getLogger(__name__)

ANALYST_PROMPT = """\
You are the AgenticAITA Analyst. Analyse the supplied market context and produce a trading signal.
Respond ONLY with one JSON object.
For long or short, use this schema:
{signal: long|short, confidence: float[0,1], entry_price: positive float,
 stop_loss: positive float, take_profit: positive float, size_usd: positive float,
 reasoning: non-empty string}.
For wait, use this smaller schema:
{signal: wait, confidence: float[0,1], reasoning: non-empty string}.
Do not emit null for a required field. Long levels must satisfy stop_loss < entry_price < take_profit.
Short levels must satisfy take_profit < entry_price < stop_loss.
Your reasoning MUST cite the composite score, volatility regime, and orderbook context explicitly.
"""

ANALYST_REPAIR_PROMPT = """\
Repair one invalid AgenticAITA Analyst response. Respond ONLY with a valid JSON object.
Preserve the intended signal when it can be made valid without inventing market facts.
For wait, return only signal, confidence and reasoning. For long or short, return all actionable fields.
Do not return null values. This is the only repair attempt.
"""

RISK_PROMPT = """\
You are the AgenticAITA Risk Manager. Your goal is Proportional Portfolio Balancing.
Respond ONLY with one JSON object.
For approval: {approved: true, size_usd: positive float, negotiation_summary: non-empty string}.
For rejection: {approved: false, negotiation_summary: non-empty string}.
Do not emit null for a required field.
"""

RISK_REPAIR_PROMPT = """\
Repair one invalid AgenticAITA Risk Manager response. Respond ONLY with a valid JSON object.
For approval include a positive size_usd. For rejection omit size_usd. Do not return null values.
This is the only repair attempt.
"""


@dataclass(frozen=True)
class VolatilityRegimeConfig:
    high_z_score: float = 3.0
    active_z_score: float = 2.0
    high_abs_return: float = 0.01
    active_abs_return: float = 0.003

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "VolatilityRegimeConfig":
        raw = data or {}
        return cls(
            float(raw.get("high_z_score", cls.high_z_score)),
            float(raw.get("active_z_score", cls.active_z_score)),
            float(raw.get("high_abs_return", cls.high_abs_return)),
            float(raw.get("active_abs_return", cls.active_abs_return)),
        )


class LLMAnalyst:
    def __init__(
        self,
        provider: LLMProvider,
        config: AnalystConfig | None = None,
        *,
        system_prompt: str | None = None,
        volatility_regime_config: VolatilityRegimeConfig | Mapping[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self.fallback = RuleBasedAnalyst(config)
        self.system_prompt = system_prompt or ANALYST_PROMPT
        self.volatility_regime_config = (
            volatility_regime_config
            if isinstance(volatility_regime_config, VolatilityRegimeConfig)
            else VolatilityRegimeConfig.from_mapping(volatility_regime_config)
        )
        self.last_warning = ""
        self.last_prompt = ""
        self.last_provenance = "not_run"
        self.last_contract_error = ""
        self.last_repair_attempted = False

    def _reset(self) -> None:
        self.last_warning = ""
        self.last_provenance = "not_run"
        self.last_contract_error = ""
        self.last_repair_attempted = False

    def _fallback_decision(
        self,
        event: TriggerEvent,
        cbd: CBDResult,
        episodic_memory: list[str] | None,
        error: Exception,
    ) -> AnalystDecision:
        self.last_provenance = "deterministic_fallback"
        self.last_warning = f"LLMAnalyst fallback to deterministic proxy: {error}"
        LOG.warning(self.last_warning)
        return self.fallback.decide(event, cbd, episodic_memory)

    def decide(self, event: TriggerEvent, cbd: CBDResult, episodic_memory: list[str] | None = None) -> AnalystDecision:
        self._reset()
        memory = episodic_memory or []
        self.last_prompt = analyst_message(event, cbd, memory, self.volatility_regime_config)
        try:
            payload = self.provider.complete(self.system_prompt, self.last_prompt)
        except LLMError as exc:
            self.last_contract_error = str(exc)
            return self._fallback_decision(event, cbd, episodic_memory, exc)

        try:
            decision = analyst_json(payload, event, cbd)
            self.last_provenance = "llm_valid"
            return decision
        except (TypeError, ValueError) as exc:
            self.last_contract_error = str(exc)
            self.last_repair_attempted = True
            repair_message = json.dumps(
                {
                    "validation_error": str(exc),
                    "invalid_response": dict(payload),
                    "market_context": json.loads(self.last_prompt),
                },
                sort_keys=True,
            )
            try:
                repaired = self.provider.complete(ANALYST_REPAIR_PROMPT, repair_message)
                decision = analyst_json(repaired, event, cbd)
                self.last_provenance = "llm_repaired"
                self.last_warning = f"LLMAnalyst repaired invalid response: {exc}"
                LOG.warning(self.last_warning)
                return decision
            except (LLMError, TypeError, ValueError) as repair_exc:
                combined = ValueError(f"initial contract error: {exc}; repair failed: {repair_exc}")
                return self._fallback_decision(event, cbd, episodic_memory, combined)


class LLMRiskManager:
    def __init__(self, provider: LLMProvider, config: RiskConfig | None = None, *, system_prompt: str | None = None) -> None:
        self.provider = provider
        self.config = config or RiskConfig()
        self.system_prompt = system_prompt or RISK_PROMPT
        self.last_warning = ""
        self.last_prompt = ""
        self.last_provenance = "not_run"
        self.last_contract_error = ""
        self.last_repair_attempted = False
        self.layer_a = DeterministicRiskManager(self.config)

    def _reset(self) -> None:
        self.last_warning = ""
        self.last_provenance = "not_run"
        self.last_contract_error = ""
        self.last_repair_attempted = False

    def evaluate(self, decision: AnalystDecision) -> RiskDecision:
        self._reset()
        gate = self.layer_a.evaluate(decision)
        if not gate.approved:
            self.last_provenance = "deterministic_hard_gate"
            return gate

        self.last_prompt = json.dumps(
            {"analyst_decision": decision.to_dict(), "layer_a": gate.to_dict()},
            sort_keys=True,
        )
        try:
            payload = self.provider.complete(self.system_prompt, self.last_prompt)
        except LLMError as exc:
            self.last_contract_error = str(exc)
            self.last_provenance = "deterministic_fallback"
            self.last_warning = f"LLMRiskManager fallback to deterministic approval: {exc}"
            LOG.warning(self.last_warning)
            return gate

        try:
            result = risk_json(payload, self.config)
            self.last_provenance = "llm_valid"
            return result
        except (TypeError, ValueError) as exc:
            self.last_contract_error = str(exc)
            self.last_repair_attempted = True
            repair_message = json.dumps(
                {
                    "validation_error": str(exc),
                    "invalid_response": dict(payload),
                    "risk_context": json.loads(self.last_prompt),
                },
                sort_keys=True,
            )
            try:
                repaired = self.provider.complete(RISK_REPAIR_PROMPT, repair_message)
                result = risk_json(repaired, self.config)
                self.last_provenance = "llm_repaired"
                self.last_warning = f"LLMRiskManager repaired invalid response: {exc}"
                LOG.warning(self.last_warning)
                return result
            except (LLMError, TypeError, ValueError) as repair_exc:
                self.last_provenance = "deterministic_fallback"
                self.last_warning = (
                    "LLMRiskManager fallback to deterministic approval: "
                    f"initial contract error: {exc}; repair failed: {repair_exc}"
                )
                LOG.warning(self.last_warning)
                return gate


def volatility_regime(event: TriggerEvent, config: VolatilityRegimeConfig | Mapping[str, Any] | None = None) -> str:
    thresholds = config if isinstance(config, VolatilityRegimeConfig) else VolatilityRegimeConfig.from_mapping(config)
    if event.z_score >= thresholds.high_z_score or event.abs_return >= thresholds.high_abs_return:
        return "high"
    if event.z_score >= thresholds.active_z_score or event.abs_return >= thresholds.active_abs_return:
        return "active"
    return "low"


def analyst_message(
    event: TriggerEvent,
    cbd: CBDResult,
    memory: list[str],
    regime_config: VolatilityRegimeConfig | Mapping[str, Any] | None = None,
) -> str:
    return json.dumps(
        {
            "trigger": asdict(event),
            "cbd": asdict(cbd),
            "composite_score": cbd.omega,
            "volatility_regime": volatility_regime(event, regime_config),
            "orderbook_context": "not available; OHLCV trigger context is used as proxy",
            "funding_context": "not supplied to the Analyst in this replication path",
            "market_snapshot": {
                "asset": event.asset,
                "timestamp": event.timestamp,
                "price": event.price,
                "signed_return": event.signed_return,
                "absolute_return": event.abs_return,
            },
            "episodic_memory_briefing": memory[-5:] or ["No prior reasoning on this asset is available."],
            "context_limitations": [
                "historical L2 order-book snapshots unavailable",
                "paper's exact prompt and full 20-bar context unavailable",
            ],
        },
        sort_keys=True,
    )


def analyst_json(payload: Mapping[str, Any], event: TriggerEvent, cbd: CBDResult) -> AnalystDecision:
    signal = parse_signal(payload)
    confidence = float_field(payload, "confidence", minimum=0.0, maximum=1.0)
    reasoning = text_field(payload, "reasoning")
    if signal == "wait":
        return AnalystDecision(
            asset=event.asset,
            signal=signal,
            confidence=confidence,
            entry_price=event.price,
            stop_loss=event.price,
            take_profit=event.price,
            size_usd=0.0,
            cbd_score=cbd.omega,
            z_score=event.z_score,
            reasoning=reasoning,
        )

    entry_price = float_field(payload, "entry_price", minimum=0.0, exclusive_minimum=True)
    stop_loss = float_field(payload, "stop_loss", minimum=0.0, exclusive_minimum=True)
    take_profit = float_field(payload, "take_profit", minimum=0.0, exclusive_minimum=True)
    size_usd = float_field(payload, "size_usd", minimum=0.0, exclusive_minimum=True)
    if signal == "long" and not (stop_loss < entry_price < take_profit):
        raise ValueError("long levels must satisfy stop_loss < entry_price < take_profit")
    if signal == "short" and not (take_profit < entry_price < stop_loss):
        raise ValueError("short levels must satisfy take_profit < entry_price < stop_loss")
    return AnalystDecision(
        asset=event.asset,
        signal=signal,
        confidence=confidence,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        size_usd=size_usd,
        cbd_score=cbd.omega,
        z_score=event.z_score,
        reasoning=reasoning,
    )


def risk_json(payload: Mapping[str, Any], config: RiskConfig) -> RiskDecision:
    approved = bool_field(payload, "approved")
    summary = text_field(payload, "negotiation_summary")
    if not approved:
        return RiskDecision(False, 0.0, "llm_layer_b_rejected", summary)

    size = float_field(payload, "size_usd", minimum=0.0, maximum=config.max_position_size_usd, exclusive_minimum=True)
    return RiskDecision(True, size, "", summary)


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
    raw = required_field(payload, field)
    if raw is None:
        raise ValueError(f"{field} must be a non-empty string")
    value = str(raw).strip()
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
