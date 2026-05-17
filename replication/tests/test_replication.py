from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from src.agenticaita.azte import AdaptiveZScoreTriggerEngine
from src.agenticaita.cbd import CBDInputs, cbd_score, z_tilde
from src.agenticaita.contracts import AnalystDecision
from src.agenticaita.risk import DeterministicRiskManager, RiskConfig
from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig
from sweep import DEFAULT_GRID, PAPER_TARGETS, alignment_score, iter_grid


def test_alignment_score_exact_targets_is_zero() -> None:
    score, errors = alignment_score(dict(PAPER_TARGETS))

    assert score == 0.0
    assert all(value == 0.0 for value in errors.values())


def test_default_sweep_grid_has_representative_run_count() -> None:
    assert len(list(iter_grid(DEFAULT_GRID))) == 36


def test_sweep_cli_writes_ranked_outputs(tmp_path) -> None:
    pd = pytest.importorskip("pandas")

    replication_root = Path(__file__).resolve().parents[1]
    input_csv = tmp_path / "input.csv"
    out_dir = tmp_path / "sweep"
    timestamps = pd.date_range("2026-04-06", periods=50, freq="min", tz="UTC")
    rows = []
    for index, timestamp in enumerate(timestamps):
        close = 100.0 if index < 35 else 106.0 + index * 0.05
        rows.append({"timestamp": timestamp.isoformat(), "asset": "BTC", "close": close})
    pd.DataFrame(rows).to_csv(input_csv, index=False)

    subprocess.run(
        [sys.executable, "sweep.py", "--config", "config.yaml", "--input-csv", str(input_csv), "--out", str(out_dir), "--top-n", "2", "--max-runs", "2"],
        cwd=replication_root,
        check=True,
        capture_output=True,
        text=True,
    )

    results = pd.read_csv(out_dir / "calibration_sweep_results.csv")
    report = (out_dir / "calibration_sweep_top10.md").read_text(encoding="utf-8")

    assert len(results) == 2
    assert "alignment_score" in results.columns
    assert results["alignment_score"].is_monotonic_increasing
    assert "## Paper Targets" in report
    assert "## Top 2" in report


def test_replication_metadata_helpers_include_config_and_data_fields() -> None:
    pd = pytest.importorskip("pandas")

    from replicate import build_config_metadata, build_data_metadata

    cfg = {
        "experiment": {"name": "test", "mode": "dry_run", "seed": 7, "output_dir": "results"},
        "azte": {"polling_interval_seconds": 60, "rolling_window": 30, "z_threshold": 2.0, "absolute_return_floor": 0.003},
        "igp": {"global_cooldown_seconds": 3000, "per_asset_cooldown_seconds": 300},
        "risk": {"confidence_gate": 0.65, "max_stop_loss_fraction": 0.02, "max_position_size_usd": 500, "base_position_size_usd": 188},
        "cbd": {"alpha": 0.5, "kappa": 0.5, "benchmark_asset": "BTC"},
        "cost_scenarios": {"zero_cost": 0.0, "realistic": 0.001},
        "synthetic_data": {"assets": ["BTC"], "minutes": 10},
    }
    data = pd.DataFrame(
        [
            {
                "timestamp": "2026-04-06T00:00:00Z",
                "asset": "BTC",
                "exchange_id": "binanceusdm",
                "source_symbol": "BTC/USDT:USDT",
                "timeframe": "1m",
                "close": 100.0,
            },
            {
                "timestamp": "2026-04-06T00:01:00Z",
                "asset": "ETH",
                "exchange_id": "binanceusdm",
                "source_symbol": "ETH/USDT:USDT",
                "timeframe": "1m",
                "close": 10.0,
            },
        ]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)

    config_metadata = build_config_metadata(cfg)
    data_metadata = build_data_metadata(data, "input.csv")

    assert config_metadata["azte"]["rolling_window"] == 30
    assert config_metadata["igp"]["global_cooldown_seconds"] == 3000
    assert config_metadata["risk"]["confidence_gate"] == 0.65
    assert config_metadata["cbd"]["benchmark_asset"] == "BTC"
    assert config_metadata["cost_scenarios"]["realistic"] == 0.001
    assert data_metadata["data_source"] == "input.csv"
    assert data_metadata["candle_count"] == 2
    assert data_metadata["asset_count"] == 2
    assert data_metadata["assets"] == ["BTC", "ETH"]
    assert data_metadata["per_asset_candle_counts"] == {"BTC": 1, "ETH": 1}
    assert data_metadata["exchange_ids"] == ["binanceusdm"]
    assert data_metadata["source_symbols"] == ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    assert data_metadata["timeframes"] == ["1m"]


def test_replicate_outputs_run_metadata(tmp_path) -> None:
    pd = pytest.importorskip("pandas")

    replication_root = Path(__file__).resolve().parents[1]
    input_csv = tmp_path / "input.csv"
    out_dir = tmp_path / "results"
    timestamps = pd.date_range("2026-04-06", periods=45, freq="min", tz="UTC")
    rows = []
    for index, timestamp in enumerate(timestamps):
        close = 100.0 if index < 35 else 105.0 + (index - 35) * 0.1
        rows.append(
            {
                "timestamp": timestamp.isoformat(),
                "asset": "BTC",
                "exchange_id": "binanceusdm",
                "source_symbol": "BTC/USDT:USDT",
                "timeframe": "1m",
                "close": close,
            }
        )
    pd.DataFrame(rows).to_csv(input_csv, index=False)

    subprocess.run(
        [sys.executable, "replicate.py", "--config", "config.yaml", "--input-csv", str(input_csv), "--out", str(out_dir)],
        cwd=replication_root,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    markdown = (out_dir / "replication_report.md").read_text(encoding="utf-8")

    assert report["metadata"]["data"]["data_source"] == str(input_csv)
    assert report["metadata"]["data"]["candle_count"] == 45
    assert report["metadata"]["data"]["exchange_ids"] == ["binanceusdm"]
    assert report["metadata"]["config"]["azte"]["rolling_window"] == 30
    assert report["metadata"]["config"]["igp"]["global_cooldown_seconds"] == 3000
    assert report["metadata"]["config"]["risk"]["confidence_gate"] == 0.65
    assert report["metadata"]["execution"]["execution_model"] == "close_only_fixed_horizon"
    assert "git_commit_sha" in report["metadata"]
    assert "## Run Metadata" in markdown


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


def test_future_rows_returns_next_horizon_rows_only() -> None:
    pd = pytest.importorskip("pandas")
    sim = PipelineSimulator(SimulatorConfig(exit_horizon_minutes=2))
    df = pd.DataFrame([
        {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "close": 100.0},
        {"timestamp": "2026-04-06T00:01:00Z", "asset": "BTC", "close": 101.0},
        {"timestamp": "2026-04-06T00:02:00Z", "asset": "BTC", "close": 102.0},
        {"timestamp": "2026-04-06T00:03:00Z", "asset": "BTC", "close": 103.0},
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    sim._prices_by_asset = {"BTC": df}

    future = sim._future_rows("BTC", df.iloc[0]["timestamp"])

    assert future["close"].tolist() == [101.0, 102.0]


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
