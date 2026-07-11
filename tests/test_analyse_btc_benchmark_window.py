from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.analyse_btc_benchmark_window import analyse, maximum_drawdown, read_rows


def fixture_rows() -> list[dict[str, str | float]]:
    return [
        {"timestamp": "2026-04-06T00:00:00Z", "close": 100.0, "high": 101.0, "low": 99.0},
        {"timestamp": "2026-04-07T00:00:00Z", "close": 110.0, "high": 112.0, "low": 100.0},
        {"timestamp": "2026-04-08T00:00:00Z", "close": 90.0, "high": 105.0, "low": 84.0},
        {"timestamp": "2026-04-11T23:59:00Z", "close": 106.0, "high": 108.0, "low": 89.0},
    ]


def test_distinguishes_start_end_return_from_peak_to_trough_drawdown() -> None:
    result = analyse(fixture_rows(), notional_usd=1_000.0)

    assert result.start_to_end_return_pct == pytest.approx(6.0)
    assert result.maximum_peak_to_trough_drawdown_pct == pytest.approx(-25.0)
    assert result.full_window_high_to_low_pct == pytest.approx(-25.0)
    assert result.trough_to_end_recovery_pct == pytest.approx(26.19047619)
    assert result.price_only_benchmark_pnl_usd == pytest.approx(60.0)
    assert result.maximum_drawdown_peak_timestamp == "2026-04-07T00:00:00Z"
    assert result.maximum_drawdown_trough_timestamp == "2026-04-08T00:00:00Z"


def test_maximum_drawdown_respects_time_order() -> None:
    drawdown, peak, trough = maximum_drawdown(
        [
            {"timestamp": "t1", "high": 80.0, "low": 70.0},
            {"timestamp": "t2", "high": 100.0, "low": 95.0},
            {"timestamp": "t3", "high": 98.0, "low": 90.0},
        ]
    )

    assert drawdown == pytest.approx(-12.5)
    assert peak == "t1"
    assert trough == "t1"


def test_csv_reader_filters_to_btc_and_cli_writes_json(tmp_path: Path) -> None:
    input_path = tmp_path / "ohlcv.csv"
    output_path = tmp_path / "result.json"
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "asset", "source_symbol", "open", "high", "low", "close"])
        writer.writeheader()
        writer.writerows(
            [
                {"timestamp": "2026-04-06T00:00:00Z", "asset": "ETH", "source_symbol": "ETH/USDT:USDT", "open": 10, "high": 11, "low": 9, "close": 10},
                {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "source_symbol": "BTC/USDT:USDT", "open": 100, "high": 101, "low": 99, "close": 100},
                {"timestamp": "2026-04-11T23:59:00Z", "asset": "BTC", "source_symbol": "BTC/USDT:USDT", "open": 105, "high": 107, "low": 104, "close": 106},
            ]
        )

    rows = read_rows(input_path)
    assert len(rows) == 2

    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "scripts/analyse_btc_benchmark_window.py", "--input", str(input_path), "--notional-usd", "1000", "--out", str(output_path)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["start_to_end_return_pct"] == pytest.approx(6.0)
    assert result["price_only_benchmark_pnl_usd"] == pytest.approx(60.0)


def test_requires_two_observations(tmp_path: Path) -> None:
    path = tmp_path / "one.csv"
    path.write_text("timestamp,asset,close\n2026-04-06T00:00:00Z,BTC,100\n", encoding="utf-8")
    with pytest.raises(ValueError, match="At least two"):
        read_rows(path)
