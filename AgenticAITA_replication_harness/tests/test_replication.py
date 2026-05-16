from __future__ import annotations

import sqlite3

import pytest

from src.agenticaita.azte import AdaptiveZScoreTriggerEngine
from src.agenticaita.cbd import CBDInputs, cbd_score, z_tilde
from src.agenticaita.contracts import AnalystDecision
from src.agenticaita.risk import DeterministicRiskManager, RiskConfig


def test_azte_abs_return_floor_triggers_after_warmup() -> None:
    azte = AdaptiveZScoreTriggerEngine(window=3, z_threshold=99.0, absolute_return_floor=0.003)
    prices = [100.0, 100.01, 100.02, 100.03, 100.50]
    event = None
    for i, price in enumerate(prices):
        _, event = azte.update(f"t{i}", "BTC", price)
    assert event is not None
    assert "abs_return_floor" in event.reason


def test_cbd_saturation_and_diversification_incentive() -> None:
    assert z_tilde(1.9) == 0.0
    assert 0.0 <= z_tilde(8.0) < 1.0
    high = cbd_score(CBDInputs(3.0, [1, 2, 3, 5], [10, 9, 7, 4])).omega
    low = cbd_score(CBDInputs(3.0, [1, 2, 3, 4], [10, 20, 30, 40])).omega
    assert high >= low


def test_risk_hard_gates_reject_wait_and_large_size() -> None:
    rm = DeterministicRiskManager(RiskConfig())
    wait = AnalystDecision("BTC", "wait", 0.9, 100, 99, 103, 100, 0.5, 2.1, "test")
    assert not rm.evaluate(wait).approved
    big = AnalystDecision("BTC", "long", 0.9, 100, 99, 103, 501, 0.5, 2.1, "test")
    assert not rm.evaluate(big).approved


def test_simulator_writes_audit_tables(tmp_path) -> None:
    pd = pytest.importorskip("pandas")

    from src.agenticaita.data import generate_synthetic_ohlcv
    from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig, write_sqlite

    df = generate_synthetic_ohlcv(["BTC", "XPL"], minutes=180, seed=7, macro_shock_minute=90, macro_shock_size=-0.04)
    sim = PipelineSimulator(SimulatorConfig(global_cooldown_seconds=0, per_asset_cooldown_seconds=0))
    pipeline_log, trades, vol_history = sim.run(df)
    assert not vol_history.empty
    assert set(["timestamp", "asset", "event"]).issubset(pipeline_log.columns) or pipeline_log.empty
    sqlite_path = tmp_path / "run.sqlite"
    write_sqlite(sqlite_path, pipeline_log, trades, vol_history)
    with sqlite3.connect(sqlite_path) as conn:
        tables = pd.read_sql_query("select name from sqlite_master where type='table'", conn)["name"].tolist()
    assert {"pipeline_log", "trades", "vol_history"}.issubset(set(tables))
