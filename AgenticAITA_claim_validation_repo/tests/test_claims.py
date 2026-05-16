from __future__ import annotations

import json
import sqlite3
from argparse import Namespace
from math import isclose
from pathlib import Path

from metrics import (
    cbd_score,
    cbd_z_tilde,
    run_all_validations,
    validate_binomial,
    validate_pipeline_counts,
    validate_trading_metrics,
)
from real_data_validation import run_real_data_validation
from validate_claims import write_json, write_real_data_csv, write_real_data_markdown


def build_market_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE candles (
                exchange_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                retrieved_at TEXT NOT NULL,
                PRIMARY KEY (exchange_id, symbol, timeframe, timestamp_ms)
            );
            CREATE TABLE funding_rates (
                exchange_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                funding_rate REAL,
                retrieved_at TEXT NOT NULL,
                PRIMARY KEY (exchange_id, symbol, timestamp_ms)
            );
            CREATE TABLE fetch_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                data_kind TEXT NOT NULL DEFAULT 'ohlcv',
                method TEXT,
                timeframe TEXT NOT NULL,
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                status TEXT NOT NULL,
                candle_count INTEGER NOT NULL,
                error TEXT,
                csv_path TEXT,
                retrieved_at TEXT NOT NULL
            );
            """
        )
        btc_closes = [100, 101, 102, 103, 104, 105]
        eth_closes = [10, 10.01, 10.02, 10.03, 11.0, 11.01]
        for symbol, closes in [("BTC/USDC:USDC", btc_closes), ("ETH/USDC:USDC", eth_closes)]:
            for index, close in enumerate(closes):
                ts = index * 60_000
                conn.execute(
                    """
                    INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("hyperliquid", symbol, "1m", ts, f"1970-01-01T00:0{index}:00Z", close, close, close, close, 1.0, "now"),
                )
            conn.execute(
                """
                INSERT INTO fetch_metadata (
                    exchange_id, symbol, data_kind, method, timeframe, start_ms, end_ms,
                    status, candle_count, error, csv_path, retrieved_at
                ) VALUES (?, ?, 'ohlcv', 'fixture', '1m', 0, 300000, 'success', 6, NULL, ?, 'now')
                """,
                ("hyperliquid", symbol, f"{symbol}.csv"),
            )
        conn.execute(
            "INSERT INTO funding_rates VALUES ('hyperliquid', 'BTC/USDC:USDC', 0, '1970-01-01T00:00:00Z', 0.0001, 'now')"
        )


def test_pipeline_friction_passes() -> None:
    results = {r.claim_id: r for r in validate_pipeline_counts()}
    assert results["pipeline.agentic_friction"].status == "pass"
    assert isclose(results["pipeline.agentic_friction"].computed_value, 11.464968, abs_tol=1e-6)


def test_trading_core_metrics_pass() -> None:
    results = {r.claim_id: r for r in validate_trading_metrics()}
    for claim_id in [
        "trading.win_rate_pct",
        "trading.net_pnl",
        "trading.profit_factor",
        "trading.risk_reward",
        "trading.break_even_win_rate",
        "trading.alpha_percentage_points",
    ]:
        assert results[claim_id].status == "pass", claim_id


def test_binomial_exact_is_qualified_not_failed() -> None:
    results = {r.claim_id: r for r in validate_binomial()}
    assert results["stats.binomial_pvalue_normal_approx"].status == "pass"
    assert results["stats.binomial_pvalue_exact_one_sided"].status == "qualified"
    assert results["stats.binomial_significance"].status == "pass"


def test_cbd_properties() -> None:
    assert cbd_z_tilde(1.9) == 0.0
    assert 0.0 <= cbd_z_tilde(2.0) < 1.0
    assert 0.0 <= cbd_z_tilde(10.0) < 1.0
    assert cbd_score(3.0, 0.9) > cbd_score(3.0, 0.1)


def test_no_unexpected_failures() -> None:
    results = run_all_validations()
    assert not [r for r in results if r.status == "fail"]


def test_real_data_validation_adapter_uses_fixture_market_db(tmp_path: Path) -> None:
    db_path = tmp_path / "market_data.sqlite"
    build_market_db(db_path)
    rows = run_real_data_validation(
        Namespace(
            market_db=db_path,
            exchange="hyperliquid",
            timeframe="1m",
            symbols="BTC/USDC:USDC,ETH/USDC:USDC",
            btc_symbol="BTC/USDC:USDC",
            window=2,
            z_threshold=2.0,
            absolute_return_floor=0.05,
            cbd_alpha=0.5,
            cbd_kappa=0.5,
        )
    )
    by_id = {row["check_id"]: row for row in rows}

    assert by_id["real_data.coverage"]["status"] == "pass"
    assert by_id["real_data.funding_availability"]["status"] == "unsupported"
    assert by_id["real_data.azte_cbd_summary"]["section"] == "exploratory"
    assert by_id["real_data.azte_cbd_summary"]["details"]["total_triggers"] >= 1
    assert by_id["real_data.unsupported_original_claims"]["status"] == "unsupported"


def test_real_data_outputs_are_written(tmp_path: Path) -> None:
    rows = [
        {
            "section": "pass_fail",
            "check_id": "real_data.coverage",
            "status": "pass",
            "summary": "fixture coverage",
            "details": {"symbols": []},
        }
    ]
    write_json(tmp_path / "real_data_validation_results.json", rows)
    write_real_data_csv(tmp_path / "real_data_validation_results.csv", rows)
    write_real_data_markdown(tmp_path / "real_data_validation_report.md", rows)

    assert json.loads((tmp_path / "real_data_validation_results.json").read_text())[0]["check_id"] == "real_data.coverage"
    assert "real_data.coverage" in (tmp_path / "real_data_validation_results.csv").read_text()
    assert "Unsupported Original-Claim Caveats" in (tmp_path / "real_data_validation_report.md").read_text()
