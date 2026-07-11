from __future__ import annotations

import pandas as pd
import pytest

from src.agenticaita.agents_llm import LLMAnalyst, LLMRiskManager, analyst_json, risk_json
from src.agenticaita.azte import TriggerEvent
from src.agenticaita.cbd import CBDResult
from src.agenticaita.contracts import AnalystDecision
from src.agenticaita.metrics import summarise
from src.agenticaita.risk import RiskConfig
from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_message: str):
        self.calls.append((system_prompt, user_message))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def event() -> TriggerEvent:
    return TriggerEvent("2026-04-06T00:31:00Z", "BTC", 100.0, 0.004, 0.004, 0.001, 0.001, 3.0, "z_score")


def cbd() -> CBDResult:
    return CBDResult(0.39, 0.2, 0.8, 0.6)


def valid_long() -> dict:
    return {
        "signal": "long",
        "confidence": 0.8,
        "entry_price": 100.0,
        "stop_loss": 99.0,
        "take_profit": 102.0,
        "size_usd": 100.0,
        "reasoning": "Composite score 0.60, active volatility regime, orderbook context unavailable.",
    }


def test_wait_contract_accepts_null_action_fields_without_fallback() -> None:
    payload = {
        "signal": "wait",
        "confidence": 0.7,
        "entry_price": None,
        "stop_loss": None,
        "take_profit": None,
        "size_usd": None,
        "reasoning": "Composite score 0.60, active volatility regime, orderbook context unavailable.",
    }
    provider = FakeProvider([payload])
    analyst = LLMAnalyst(provider)

    decision = analyst.decide(event(), cbd())

    assert decision.signal == "wait"
    assert decision.size_usd == 0.0
    assert decision.entry_price == event().price
    assert analyst.last_provenance == "llm_valid"
    assert analyst.last_repair_attempted is False
    assert len(provider.calls) == 1


def test_directional_null_triggers_one_repair_then_valid_decision() -> None:
    invalid = {**valid_long(), "entry_price": None}
    provider = FakeProvider([invalid, valid_long()])
    analyst = LLMAnalyst(provider)

    decision = analyst.decide(event(), cbd())

    assert decision.signal == "long"
    assert analyst.last_provenance == "llm_repaired"
    assert analyst.last_repair_attempted is True
    assert "entry_price is required" in analyst.last_contract_error
    assert len(provider.calls) == 2


def test_failed_repair_falls_back_once_and_records_provenance() -> None:
    invalid = {**valid_long(), "stop_loss": None}
    provider = FakeProvider([invalid, invalid])
    analyst = LLMAnalyst(provider)

    decision = analyst.decide(event(), cbd())

    assert decision.signal in {"long", "short", "wait"}
    assert analyst.last_provenance == "deterministic_fallback"
    assert analyst.last_repair_attempted is True
    assert "repair failed" in analyst.last_warning
    assert len(provider.calls) == 2


def test_directional_levels_and_null_text_are_rejected() -> None:
    with pytest.raises(ValueError, match="long levels"):
        analyst_json({**valid_long(), "stop_loss": 101.0}, event(), cbd())
    with pytest.raises(ValueError, match="reasoning must be a non-empty string"):
        analyst_json({**valid_long(), "reasoning": None}, event(), cbd())
    with pytest.raises(ValueError, match="size_usd must be greater than"):
        analyst_json({**valid_long(), "size_usd": 0}, event(), cbd())


def test_risk_contract_repairs_invalid_approval_once() -> None:
    provider = FakeProvider(
        [
            {"approved": True, "size_usd": None, "negotiation_summary": "invalid"},
            {"approved": True, "size_usd": 80, "negotiation_summary": "repaired"},
        ]
    )
    manager = LLMRiskManager(provider, RiskConfig(confidence_gate=0.6))
    decision = AnalystDecision("BTC", "long", 0.8, 100, 99, 102, 100, 0.6, 3, "ok")

    result = manager.evaluate(decision)

    assert result.approved and result.size_usd == 80
    assert manager.last_provenance == "llm_repaired"
    assert manager.last_repair_attempted is True
    assert len(provider.calls) == 2


def test_pipeline_and_summary_separate_valid_repaired_and_gate_outcomes() -> None:
    provider = FakeProvider(
        [
            {**valid_long(), "entry_price": None},
            valid_long(),
            {"approved": True, "size_usd": 80, "negotiation_summary": "approved"},
        ]
    )
    simulator = PipelineSimulator(
        SimulatorConfig(
            rolling_window=2,
            z_threshold=99,
            absolute_return_floor=0.003,
            global_cooldown_seconds=0,
            per_asset_cooldown_seconds=0,
            benchmark_asset="BTC",
            exit_horizon_minutes=1,
        ),
        analyst_agent=LLMAnalyst(provider),
        risk_manager=LLMRiskManager(provider, RiskConfig(confidence_gate=0.6)),
    )
    prices = pd.DataFrame(
        [
            {"timestamp": f"2026-04-06T00:0{index}:00Z", "asset": "BTC", "close": close}
            for index, close in enumerate([100.0, 100.01, 100.02, 101.0, 101.1])
        ]
    )

    pipeline, trades, _ = simulator.run(prices)
    admitted = pipeline[pipeline["event"] == "trigger_admitted"]
    summary = summarise(pipeline, trades)

    assert len(admitted) == 1
    assert admitted.iloc[0]["analyst_provenance"] == "llm_repaired"
    assert admitted.iloc[0]["analyst_repair_attempted"] == True  # noqa: E712
    assert admitted.iloc[0]["risk_provenance"] == "llm_valid"
    assert summary.analyst_provenance_counts == {"llm_repaired": 1}
    assert summary.analyst_repair_attempted == 1
    assert summary.approvals_by_analyst_provenance == {"llm_repaired": 1}
    assert summary.approvals_by_risk_provenance == {"llm_valid": 1}


def test_rejected_risk_response_does_not_require_size() -> None:
    result = risk_json({"approved": False, "negotiation_summary": "reject"}, RiskConfig())
    assert not result.approved and result.size_usd == 0.0
