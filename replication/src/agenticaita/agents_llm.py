"""LLM-backed AgenticAITA agents."""
from __future__ import annotations
import json, logging
from dataclasses import asdict
from typing import Any, Mapping
from .agents import AnalystConfig, RuleBasedAnalyst
from .azte import TriggerEvent
from .cbd import CBDResult
from .contracts import AnalystDecision, RiskDecision
from .llm import LLMError, LLMProvider
from .risk import DeterministicRiskManager, RiskConfig
LOG = logging.getLogger(__name__)
ANALYST_PROMPT = "You are the AgenticAITA Analyst. Analyze the market and produce a trading signal. Respond ONLY in JSON: {signal: long|short|wait, confidence: float[0,1], entry_price, stop_loss, take_profit, size_usd, reasoning: string}. Your reasoning MUST cite the composite score, volatility regime, and orderbook context explicitly."
RISK_PROMPT = "You are the AgenticAITA Risk Manager. Your goal is Proportional Portfolio Balancing. Calculate size_usd based on the Analyst's confidence. Respond ONLY in JSON: {approved: bool, size_usd: float, negotiation_summary: string}."

class LLMAnalyst:
    def __init__(self, provider: LLMProvider, config: AnalystConfig | None = None) -> None:
        self.provider, self.fallback, self.last_warning, self.last_prompt = provider, RuleBasedAnalyst(config), "", ""
    def decide(self, event: TriggerEvent, cbd: CBDResult, episodic_memory: list[str] | None = None) -> AnalystDecision:
        self.last_warning = ""; self.last_prompt = analyst_message(event, cbd, episodic_memory or [])
        try: return analyst_json(self.provider.complete(ANALYST_PROMPT, self.last_prompt), event, cbd)
        except (LLMError, KeyError, TypeError, ValueError) as exc:
            self.last_warning = f"LLMAnalyst fallback to deterministic proxy: {exc}"; LOG.warning(self.last_warning)
            return self.fallback.decide(event, cbd, episodic_memory)

class LLMRiskManager:
    def __init__(self, provider: LLMProvider, config: RiskConfig | None = None) -> None:
        self.provider, self.config, self.last_warning, self.last_prompt = provider, config or RiskConfig(), "", ""
        self.layer_a = DeterministicRiskManager(self.config)
    def evaluate(self, decision: AnalystDecision) -> RiskDecision:
        self.last_warning = ""; gate = self.layer_a.evaluate(decision)
        if not gate.approved: return gate
        self.last_prompt = json.dumps({"analyst_decision": decision.to_dict(), "layer_a": gate.to_dict()}, sort_keys=True)
        try: return risk_json(self.provider.complete(RISK_PROMPT, self.last_prompt), self.config)
        except (LLMError, KeyError, TypeError, ValueError) as exc:
            self.last_warning = f"LLMRiskManager fallback to deterministic approval: {exc}"; LOG.warning(self.last_warning)
            return gate

def analyst_message(event: TriggerEvent, cbd: CBDResult, memory: list[str]) -> str:
    regime = "high" if event.z_score >= 3 or event.abs_return >= 0.01 else "active" if event.z_score >= 2 or event.abs_return >= 0.003 else "low"
    return json.dumps({"trigger": asdict(event), "cbd": asdict(cbd), "composite_score": cbd.omega, "volatility_regime": regime, "orderbook_context": "not available; OHLCV trigger context is used as proxy", "episodic_memory_briefing": memory[-5:] or ["No prior reasoning on this asset is available."]}, sort_keys=True)

def analyst_json(p: Mapping[str, Any], e: TriggerEvent, c: CBDResult) -> AnalystDecision:
    signal = str(p["signal"]).lower(); reason = str(p.get("reasoning", "")).strip()
    if signal not in {"long", "short", "wait"} or not reason: raise ValueError("invalid analyst JSON contract")
    return AnalystDecision(e.asset, signal, f(p["confidence"], 0, 1), f(p.get("entry_price", e.price), 0, None), float(p.get("stop_loss", e.price)), float(p.get("take_profit", e.price)), f(p["size_usd"], 0, None), c.omega, e.z_score, reason)  # type: ignore[arg-type]

def risk_json(p: Mapping[str, Any], c: RiskConfig) -> RiskDecision:
    approved = p["approved"] if isinstance(p["approved"], bool) else str(p["approved"]).lower() == "true"; summary = str(p.get("negotiation_summary", "")).strip()
    if not summary: raise ValueError("invalid risk JSON contract")
    if not approved: return RiskDecision(False, 0.0, "llm_layer_b_rejected", summary)
    size = f(p["size_usd"], 0, c.max_position_size_usd)
    return RiskDecision(size > 0, size if size > 0 else 0.0, "" if size > 0 else "llm_layer_b_zero_size", summary)

def f(v: Any, lo: float | None, hi: float | None) -> float:
    x = float(v)
    if (lo is not None and x < lo) or (hi is not None and x > hi): raise ValueError("number outside bounds")
    return x
