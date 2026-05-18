from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else ["timestamp", "asset", "close"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_quality(*args: str) -> subprocess.CompletedProcess[str]:
    root = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, "scripts/check_replication_quality.py", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )


def test_quality_cli_rejects_missing_required_input_columns(tmp_path: Path) -> None:
    input_csv = tmp_path / "bad.csv"
    write_csv(input_csv, [{"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC"}], fieldnames=["timestamp", "asset"])

    result = run_quality("--input-csv", str(input_csv))

    assert result.returncode == 2
    assert "replication quality check failed" in result.stderr
    assert "missing required columns" in result.stderr


def test_quality_cli_rejects_duplicate_timestamp_asset_rows(tmp_path: Path) -> None:
    input_csv = tmp_path / "duplicate.csv"
    write_csv(
        input_csv,
        [
            {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "close": 100.0},
            {"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "close": 101.0},
        ],
    )

    result = run_quality("--input-csv", str(input_csv))

    assert result.returncode == 2
    assert "duplicate (timestamp, asset)" in result.stderr


def test_quality_cli_rejects_empty_pipeline_log_for_real_data(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    results_dir = tmp_path / "results"
    write_csv(input_csv, [{"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "close": 100.0}])
    write_csv(results_dir / "pipeline_log.csv", [], fieldnames=["timestamp", "asset", "event"])
    write_csv(results_dir / "trades.csv", [], fieldnames=["timestamp", "asset", "signal", "net_pnl_usd"])
    (results_dir / "replication_report.md").write_text("# report\n", encoding="utf-8")

    result = run_quality("--input-csv", str(input_csv), "--results-dir", str(results_dir), "--real-data")

    assert result.returncode == 2
    assert "pipeline_log.csv is empty for real-data run" in result.stderr


def test_quality_cli_warns_on_empty_trades_and_accepts_outputs(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    results_dir = tmp_path / "results"
    write_csv(input_csv, [{"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "close": 100.0}])
    write_csv(results_dir / "pipeline_log.csv", [{"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "event": "trigger"}])
    write_csv(results_dir / "trades.csv", [], fieldnames=["timestamp", "asset", "signal", "net_pnl_usd"])
    (results_dir / "replication_report.md").write_text("# report\n", encoding="utf-8")

    result = run_quality("--input-csv", str(input_csv), "--results-dir", str(results_dir), "--real-data")

    assert result.returncode == 0
    assert "quality warning" in result.stderr
    assert "trades.csv is empty" in result.stderr
    assert '"status": "pass"' in result.stdout


def test_quality_cli_rejects_missing_report(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    results_dir = tmp_path / "results"
    write_csv(input_csv, [{"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "close": 100.0}])
    write_csv(results_dir / "pipeline_log.csv", [{"timestamp": "2026-04-06T00:00:00Z", "asset": "BTC", "event": "trigger"}])

    result = run_quality("--input-csv", str(input_csv), "--results-dir", str(results_dir), "--real-data")

    assert result.returncode == 2
    assert "replication_report.md is missing or empty" in result.stderr
