from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pytest

from src.agenticaita.contracts import AnalystDecision, RiskDecision
from src.agenticaita.metrics import summarise
from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig


class WaitAnalyst:
    last_warning = ""

    def decide(self, event, cbd, episodic_memory=None) -> AnalystDecision:
        return AnalystDecision(
            asset=event.asset,
            signal="wait",
            confidence=0.9,
            entry_price=event.price,
            stop_loss=event.price,
            take_profit=event.price,
            size_usd=0.0,
            cbd_score=cbd.omega,
            z_score=event.z_score,
            reasoning="wait for confirmation",
        )


@dataclass
class CountingRiskManager:
    calls: int = 0
    last_warning: str = ""

    def evaluate(self, decision: AnalystDecision) -> RiskDecision:
        self.calls += 1
        return RiskDecision(False, 0.0, "should_not_be_called", "unexpected")


def empty_trades() -> pd.DataFrame:
    return pd.DataFrame(columns=["net_pnl_usd"])


def test_analyst_wait_stops_before_risk_manager() -> None:
    risk = CountingRiskManager()
    simulator = PipelineSimulator(
        SimulatorConfig(
            rolling_window=2,
            z_threshold=99.0,
            absolute_return_floor=0.003,
            global_cooldown_seconds=0,
            per_asset_cooldown_seconds=0,
        ),
        analyst_agent=WaitAnalyst(),
        risk_manager=risk,
    )
    prices = pd.DataFrame(
        [
            {"timestamp": f"2026-04-06T00:0{index}:00Z", "asset": "BTC", "close": price}
            for index, price in enumerate([100.0, 100.01, 100.02, 101.0])
        ]
    )

    pipeline, trades, _ = simulator.run(prices)
    admitted = pipeline[pipeline["event"] == "trigger_admitted"]

    assert risk.calls == 0
    assert trades.empty
    assert len(admitted) == 1
    assert admitted.iloc[0]["analyst_signal"] == "wait"
    assert admitted.iloc[0]["risk_evaluated"] == False  # noqa: E712
    assert admitted.iloc[0]["risk_stage_status"] == "not_evaluated_analyst_wait"
    assert pd.isna(admitted.iloc[0]["risk_approved"])


def test_summary_counts_only_directional_risk_evaluations() -> None:
    pipeline = pd.DataFrame(
        [
            {"event": "trigger_admitted", "analyst_signal": "wait", "risk_evaluated": False, "risk_approved": None, "risk_rejection_reason": ""},
            {"event": "trigger_admitted", "analyst_signal": "long", "risk_evaluated": True, "risk_approved": True, "risk_rejection_reason": ""},
            {"event": "trigger_admitted", "analyst_signal": "short", "risk_evaluated": True, "risk_approved": False, "risk_rejection_reason": "confidence_below_gate"},
        ]
    )

    summary = summarise(pipeline, empty_trades())

    assert summary.total_invocations == 3
    assert summary.analyst_wait == 1
    assert summary.risk_approved == 1
    assert summary.risk_rejected == 1
    assert summary.risk_not_evaluated == 1
    assert summary.risk_rejection_reasons == {"confidence_below_gate": 1}
    assert summary.agentic_friction_pct == pytest.approx(200.0 / 3.0)
    assert summary.stage_accounting_valid is True


def test_legacy_logs_exclude_waits_from_risk_rejections() -> None:
    pipeline = pd.DataFrame(
        [
            {"event": "trigger_admitted", "analyst_signal": "wait", "risk_approved": False, "risk_rejection_reason": "signal_wait_or_invalid"},
            {"event": "trigger_admitted", "analyst_signal": "long", "risk_approved": True, "risk_rejection_reason": ""},
            {"event": "trigger_admitted", "analyst_signal": "short", "risk_approved": False, "risk_rejection_reason": "confidence_below_gate"},
        ]
    )

    summary = summarise(pipeline, empty_trades())

    assert summary.risk_approved == 1
    assert summary.risk_rejected == 1
    assert summary.risk_not_evaluated == 1
    assert summary.agentic_friction_pct == pytest.approx(200.0 / 3.0)
    assert summary.stage_accounting_valid is True


def test_empty_run_is_valid_and_has_no_friction() -> None:
    summary = summarise(pd.DataFrame(), empty_trades())

    assert summary.total_invocations == 0
    assert summary.risk_not_evaluated == 0
    assert summary.agentic_friction_pct is None
    assert summary.stage_accounting_valid is True
