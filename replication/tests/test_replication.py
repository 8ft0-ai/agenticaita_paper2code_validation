from __future__ import annotations

import sqlite3

import pytest

from src.agenticaita.azte import AdaptiveZScoreTriggerEngine
from src.agenticaita.cbd import CBDInputs, cbd_score, z_tilde
from src.agenticaita.contracts import AnalystDecision
from src.agenticaita.risk import DeterministicRiskManager, RiskConfig
from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig


def test_load_ohlcv_csv_accepts_close_only(tmp_path) -> None:
    pd = pytest.importorskip("pandas")

    from src.agenticaita.data import load_ohlcv_csv

    path = tmp_path / "close_only.csv"
    pd.DataFrame(
        [
            {"timestamp": "2026-04-06T00:01:00Z", "asset": "ETH", "close": "2000.5"},
            {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "close": "70000.1"},
        ]
    ).to_csv(path, index=False)

    df = load_ohlcv_csv(path)

    assert df.columns.tolist() == ["timestamp", "asset", "close"]
    assert df["asset"].tolist() == ["BTC", "ETH"]
    assert df["close"].tolist() == [70000.1, 2000.5]
    assert str(df["timestamp"].dt.tz) == "UTC"


def test_load_ohlcv_csv_preserves_and_casts_full_ohlcv(tmp_path) -> None:
    pd = pytest.importorskip("pandas")

    from src.agenticaita.data import load_ohlcv_csv

    path = tmp_path / "full_ohlcv.csv"
    pd.DataFrame(
        [
            {
                "timestamp": "2026-04-06T00:00:00Z",
                "asset": "BTC",
                "open": "70000.0",
                "high": "70100.0",
                "low": "69950.0",
                "close": "70025.0",
                "volume": "123.4",
                "source_symbol": "BTC/USDT:USDT",
            }
        ]
    ).to_csv(path, index=False)

    df = load_ohlcv_csv(path)

    assert {"open", "high", "low", "close", "volume", "source_symbol"}.issubset(df.columns)
    for column in ["open", "high", "low", "close", "volume"]:
        assert pd.api.types.is_float_dtype(df[column])
    assert df.loc[0, "source_symbol"] == "BTC/USDT:USDT"


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


def test_risk_rejects_invalid_directional_exit_levels() -> None:
    rm = DeterministicRiskManager(RiskConfig())
    bad_long = AnalystDecision("BTC", "long", 0.9, 100, 101, 103, 100, 0.5, 2.1, "test")
    bad_short = AnalystDecision("BTC", "short", 0.9, 100, 99, 101, 100, 0.5, 2.1, "test")

    assert rm.evaluate(bad_long).rejection_reason == "invalid_long_exit_levels"
    assert rm.evaluate(bad_short).rejection_reason == "invalid_short_exit_levels"


def make_simulator_with_prices(rows: list[dict]) -> PipelineSimulator:
    pd = pytest.importorskip("pandas")
    sim = PipelineSimulator(SimulatorConfig(exit_horizon_minutes=3))
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    sim._prices_by_asset = {"BTC": df.sort_values("timestamp").reset_index(drop=True)}
    return sim


def make_decision(signal: str = "long") -> AnalystDecision:
    if signal == "long":
        return AnalystDecision("BTC", "long", 0.9, 100.0, 99.0, 102.0, 100.0, 0.5, 2.1, "test")
    return AnalystDecision("BTC", "short", 0.9, 100.0, 101.0, 98.0, 100.0, 0.5, 2.1, "test")


def test_ohlcv_long_stop_loss_hit() -> None:
    sim = make_simulator_with_prices([
        {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "open": 100, "high": 100, "low": 100, "close": 100},
        {"timestamp": "2026-04-06T00:01:00Z", "asset": "BTC", "open": 100, "high": 101, "low": 98.5, "close": 100},
    ])

    record = sim._execute(sim._prices_by_asset["BTC"].iloc[0]["timestamp"], make_decision("long"), 100.0)

    assert record.exit_price == 99.0
    assert record.reason == "stop_loss_intrabar"
    assert record.execution_model == "ohlcv_intrabar_stop_take_profit"
    assert record.net_pnl_usd < 0


def test_ohlcv_long_take_profit_hit() -> None:
    sim = make_simulator_with_prices([
        {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "open": 100, "high": 100, "low": 100, "close": 100},
        {"timestamp": "2026-04-06T00:01:00Z", "asset": "BTC", "open": 100, "high": 102.5, "low": 99.5, "close": 101},
    ])

    record = sim._execute(sim._prices_by_asset["BTC"].iloc[0]["timestamp"], make_decision("long"), 100.0)

    assert record.exit_price == 102.0
    assert record.reason == "take_profit_intrabar"
    assert record.net_pnl_usd > 0


def test_ohlcv_short_stop_loss_hit() -> None:
    sim = make_simulator_with_prices([
        {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "open": 100, "high": 100, "low": 100, "close": 100},
        {"timestamp": "2026-04-06T00:01:00Z", "asset": "BTC", "open": 100, "high": 101.5, "low": 99, "close": 100},
    ])

    record = sim._execute(sim._prices_by_asset["BTC"].iloc[0]["timestamp"], make_decision("short"), 100.0)

    assert record.exit_price == 101.0
    assert record.reason == "stop_loss_intrabar"
    assert record.net_pnl_usd < 0


def test_ohlcv_short_take_profit_hit() -> None:
    sim = make_simulator_with_prices([
        {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "open": 100, "high": 100, "low": 100, "close": 100},
        {"timestamp": "2026-04-06T00:01:00Z", "asset": "BTC", "open": 100, "high": 100.5, "low": 97.5, "close": 99},
    ])

    record = sim._execute(sim._prices_by_asset["BTC"].iloc[0]["timestamp"], make_decision("short"), 100.0)

    assert record.exit_price == 98.0
    assert record.reason == "take_profit_intrabar"
    assert record.net_pnl_usd > 0


def test_ohlcv_same_bar_tie_uses_stop_loss() -> None:
    sim = make_simulator_with_prices([
        {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "open": 100, "high": 100, "low": 100, "close": 100},
        {"timestamp": "2026-04-06T00:01:00Z", "asset": "BTC", "open": 100, "high": 103, "low": 98, "close": 101},
    ])

    record = sim._execute(sim._prices_by_asset["BTC"].iloc[0]["timestamp"], make_decision("long"), 100.0)

    assert record.exit_price == 99.0
    assert record.reason == "stop_loss_intrabar_tie_breaker"


def test_ohlcv_no_hit_exits_at_horizon_close() -> None:
    sim = make_simulator_with_prices([
        {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "open": 100, "high": 100, "low": 100, "close": 100},
        {"timestamp": "2026-04-06T00:01:00Z", "asset": "BTC", "open": 100, "high": 101, "low": 99.5, "close": 100.5},
        {"timestamp": "2026-04-06T00:02:00Z", "asset": "BTC", "open": 100.5, "high": 101.5, "low": 99.5, "close": 101.0},
    ])

    record = sim._execute(sim._prices_by_asset["BTC"].iloc[0]["timestamp"], make_decision("long"), 100.0)

    assert record.exit_price == 101.0
    assert record.reason == "fixed_horizon_ohlcv_timeout"


def test_close_only_execution_fallback_remains_deterministic() -> None:
    pd = pytest.importorskip("pandas")
    sim = PipelineSimulator(SimulatorConfig(exit_horizon_minutes=2))
    df = pd.DataFrame([
        {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "close": 100.0},
        {"timestamp": "2026-04-06T00:01:00Z", "asset": "BTC", "close": 101.0},
        {"timestamp": "2026-04-06T00:02:00Z", "asset": "BTC", "close": 102.0},
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    sim._prices_by_asset = {"BTC": df}

    record = sim._execute(df.iloc[0]["timestamp"], make_decision("long"), 100.0)

    assert record.exit_price == 102.0
    assert record.reason == "fixed_horizon_close_only_fallback"
    assert record.execution_model == "close_only_fixed_horizon"


def test_simulator_writes_audit_tables(tmp_path) -> None:
    pd = pytest.importorskip("pandas")

    from src.agenticaita.data import generate_synthetic_ohlcv
    from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig, write_sqlite

    df = generate_synthetic_ohlcv(["BTC", "XPL"], minutes=180, seed=7, macro_shock_minute=90, macro_shock_size=-0.04)
    sim = PipelineSimulator(SimulatorConfig(global_cooldown_seconds=0, per_asset_cooldown_seconds=0))
    pipeline_log, trades, vol_history = sim.run(df)
    assert not vol_history.empty
    assert set(["timestamp", "asset", "event"]).issubset(pipeline_log.columns) or pipeline_log.empty
    if not trades.empty:
        assert {"exit_timestamp", "stop_loss", "take_profit", "execution_model"}.issubset(trades.columns)
    sqlite_path = tmp_path / "run.sqlite"
    write_sqlite(sqlite_path, pipeline_log, trades, vol_history)
    with sqlite3.connect(sqlite_path) as conn:
        tables = pd.read_sql_query("select name from sqlite_master where type='table'", conn)["name"].tolist()
    assert {"pipeline_log", "trades", "vol_history"}.issubset(set(tables))
