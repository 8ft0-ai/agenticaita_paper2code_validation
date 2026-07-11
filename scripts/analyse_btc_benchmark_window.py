#!/usr/bin/env python3
"""Calculate distinct BTC benchmark-window return measures from OHLCV CSV data."""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class BenchmarkWindow:
    observations: int
    start_timestamp: str
    end_timestamp: str
    start_close: float
    end_close: float
    start_to_end_return_pct: float
    highest_price: float
    highest_timestamp: str
    lowest_price: float
    lowest_timestamp: str
    full_window_high_to_low_pct: float
    maximum_peak_to_trough_drawdown_pct: float
    maximum_drawdown_peak_timestamp: str
    maximum_drawdown_trough_timestamp: str
    trough_to_end_recovery_pct: float
    benchmark_notional_usd: float | None
    price_only_benchmark_pnl_usd: float | None


def read_rows(path: str | Path, asset: str = "BTC") -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row_asset = str(raw.get("asset") or "").upper()
            source_symbol = str(raw.get("source_symbol") or raw.get("symbol") or "").upper()
            if row_asset and row_asset != asset.upper() and not source_symbol.startswith(f"{asset.upper()}/"):
                continue
            close = float(raw["close"])
            high = float(raw.get("high") or close)
            low = float(raw.get("low") or close)
            rows.append(
                {
                    "timestamp": str(raw.get("timestamp") or raw.get("timestamp_ms") or len(rows)),
                    "close": close,
                    "high": high,
                    "low": low,
                }
            )
    rows.sort(key=lambda row: str(row["timestamp"]))
    if len(rows) < 2:
        raise ValueError("At least two valid BTC observations are required")
    return rows


def maximum_drawdown(rows: Iterable[dict[str, str | float]]) -> tuple[float, str, str]:
    peak = float("-inf")
    peak_timestamp = ""
    maximum = 0.0
    maximum_peak_timestamp = ""
    maximum_trough_timestamp = ""
    for row in rows:
        timestamp = str(row["timestamp"])
        high = float(row["high"])
        low = float(row["low"])
        if high > peak:
            peak = high
            peak_timestamp = timestamp
        drawdown = (low / peak - 1.0) * 100.0 if peak > 0 else 0.0
        if drawdown < maximum:
            maximum = drawdown
            maximum_peak_timestamp = peak_timestamp
            maximum_trough_timestamp = timestamp
    return maximum, maximum_peak_timestamp, maximum_trough_timestamp


def analyse(rows: list[dict[str, str | float]], notional_usd: float | None = None) -> BenchmarkWindow:
    first = rows[0]
    last = rows[-1]
    highest = max(rows, key=lambda row: float(row["high"]))
    lowest = min(rows, key=lambda row: float(row["low"]))
    maximum_dd, dd_peak, dd_trough = maximum_drawdown(rows)
    start_close = float(first["close"])
    end_close = float(last["close"])
    start_to_end = (end_close / start_close - 1.0) * 100.0
    highest_price = float(highest["high"])
    lowest_price = float(lowest["low"])
    full_high_to_low = (lowest_price / highest_price - 1.0) * 100.0
    recovery = (end_close / lowest_price - 1.0) * 100.0
    pnl = notional_usd * start_to_end / 100.0 if notional_usd is not None else None
    return BenchmarkWindow(
        observations=len(rows),
        start_timestamp=str(first["timestamp"]),
        end_timestamp=str(last["timestamp"]),
        start_close=start_close,
        end_close=end_close,
        start_to_end_return_pct=start_to_end,
        highest_price=highest_price,
        highest_timestamp=str(highest["timestamp"]),
        lowest_price=lowest_price,
        lowest_timestamp=str(lowest["timestamp"]),
        full_window_high_to_low_pct=full_high_to_low,
        maximum_peak_to_trough_drawdown_pct=maximum_dd,
        maximum_drawdown_peak_timestamp=dd_peak,
        maximum_drawdown_trough_timestamp=dd_trough,
        trough_to_end_recovery_pct=recovery,
        benchmark_notional_usd=notional_usd,
        price_only_benchmark_pnl_usd=pnl,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV containing timestamp, close and optional OHLC/asset columns")
    parser.add_argument("--asset", default="BTC")
    parser.add_argument("--notional-usd", type=float, default=None)
    parser.add_argument("--out", default=None, help="optional JSON output path")
    args = parser.parse_args(argv)
    result = asdict(analyse(read_rows(args.input, args.asset), args.notional_usd))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
