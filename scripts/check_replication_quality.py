#!/usr/bin/env python3
"""Validate replication inputs and generated outputs before interpretation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REQUIRED_OHLCV_COLUMNS = ("timestamp", "asset", "close")
REQUIRED_PIPELINE_LOG_COLUMNS = ("timestamp", "asset", "event")
REQUIRED_TRADES_COLUMNS = ("timestamp", "asset", "signal", "net_pnl_usd")


class QualityCheckError(ValueError):
    """Raised when replication artefacts are unsafe to interpret."""


def missing_columns(frame: pd.DataFrame, required: tuple[str, ...]) -> list[str]:
    return sorted(set(required) - set(frame.columns))


def read_csv(path: Path, *, required: bool = True) -> pd.DataFrame | None:
    if not path.exists():
        if required:
            raise QualityCheckError(f"{path.name} is missing: {path}")
        return None
    return pd.read_csv(path)


def check_input_csv(path: Path) -> dict[str, object]:
    frame = read_csv(path)
    assert frame is not None
    errors: list[str] = []
    missing = missing_columns(frame, REQUIRED_OHLCV_COLUMNS)

    if frame.empty:
        errors.append("OHLCV input is empty")
    if missing:
        errors.append(f"OHLCV input missing required columns: {missing}")

    duplicate_count = 0
    if not missing and not frame.empty:
        duplicate_count = int(frame.duplicated(subset=["timestamp", "asset"]).sum())
        if duplicate_count:
            errors.append(f"OHLCV input contains {duplicate_count} duplicate (timestamp, asset) rows")

    if errors:
        raise QualityCheckError("; ".join(errors))

    return {
        "status": "pass",
        "path": str(path),
        "rows": int(len(frame)),
        "columns_checked": list(REQUIRED_OHLCV_COLUMNS),
        "duplicate_timestamp_asset_rows": duplicate_count,
    }


def check_pipeline_log(path: Path, *, real_data: bool) -> dict[str, object]:
    frame = read_csv(path)
    assert frame is not None
    missing = missing_columns(frame, REQUIRED_PIPELINE_LOG_COLUMNS)
    errors: list[str] = []

    if real_data and frame.empty:
        errors.append("pipeline_log.csv is empty for real-data run")
    if not frame.empty and missing:
        errors.append(f"pipeline_log.csv missing required columns: {missing}")

    if errors:
        raise QualityCheckError("; ".join(errors))

    return {"status": "pass", "path": str(path), "rows": int(len(frame)), "columns_checked": list(REQUIRED_PIPELINE_LOG_COLUMNS)}


def check_trades(path: Path) -> tuple[dict[str, object], list[str]]:
    frame = read_csv(path, required=False)
    warnings: list[str] = []
    if frame is None:
        warnings.append(f"trades.csv is missing: {path}")
        return {"status": "warning", "path": str(path), "rows": 0}, warnings

    if frame.empty:
        warnings.append("trades.csv is empty; no executed trades were produced")
        return {"status": "warning", "path": str(path), "rows": 0, "columns_checked": list(REQUIRED_TRADES_COLUMNS)}, warnings

    missing = missing_columns(frame, REQUIRED_TRADES_COLUMNS)
    if missing:
        raise QualityCheckError(f"trades.csv missing required columns: {missing}")
    return {"status": "pass", "path": str(path), "rows": int(len(frame)), "columns_checked": list(REQUIRED_TRADES_COLUMNS)}, warnings


def check_report(path: Path) -> dict[str, object]:
    if not path.exists() or path.stat().st_size == 0:
        raise QualityCheckError(f"replication_report.md is missing or empty: {path}")
    return {"status": "pass", "path": str(path), "bytes": path.stat().st_size}


def check_results_dir(path: Path, *, real_data: bool) -> tuple[dict[str, object], list[str]]:
    if not path.exists() or not path.is_dir():
        raise QualityCheckError(f"results directory is missing: {path}")

    trades, warnings = check_trades(path / "trades.csv")
    result = {
        "status": "pass",
        "path": str(path),
        "pipeline_log": check_pipeline_log(path / "pipeline_log.csv", real_data=real_data),
        "trades": trades,
        "report_generation": check_report(path / "replication_report.md"),
    }
    return result, warnings


def run_checks(input_csv: Path, results_dir: Path | None, *, real_data: bool) -> tuple[dict[str, object], list[str]]:
    warnings: list[str] = []
    result: dict[str, object] = {
        "status": "pass",
        "real_data": real_data,
        "input": check_input_csv(input_csv),
    }
    if results_dir is not None:
        outputs, output_warnings = check_results_dir(results_dir, real_data=real_data)
        result["outputs"] = outputs
        warnings.extend(output_warnings)
    result["warnings"] = warnings
    return result, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", required=True, help="replication input CSV to validate")
    parser.add_argument("--results-dir", default=None, help="optional replication results directory to validate")
    parser.add_argument("--real-data", action="store_true", help="require non-empty pipeline_log.csv when checking outputs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result, warnings = run_checks(
            Path(args.input_csv),
            Path(args.results_dir) if args.results_dir else None,
            real_data=args.real_data,
        )
    except QualityCheckError as exc:
        print(f"replication quality check failed: {exc}", file=sys.stderr)
        return 2

    for warning in warnings:
        print(f"quality warning: {warning}", file=sys.stderr)
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
