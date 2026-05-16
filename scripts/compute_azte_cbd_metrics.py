#!/usr/bin/env python3
"""Compute AZTE trigger and CBD metrics from stored historical candles."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import statistics
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DB = "data/hyperliquid_ohlcv/market_data.sqlite"
DEFAULT_OUT = "data/hyperliquid_ohlcv/azte_cbd_metrics"


@dataclass(frozen=True)
class Candle:
    timestamp_ms: int
    timestamp: str
    close: float


def safe_symbol_filename(symbol: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "_.-" else "_" for char in symbol).strip("_")
    return cleaned or "symbol"


def load_symbols(conn: sqlite3.Connection, exchange_id: str, timeframe: str, requested: str | None) -> list[str]:
    if requested:
        return [item.strip() for item in requested.split(",") if item.strip()]
    rows = conn.execute(
        """
        SELECT DISTINCT symbol
        FROM candles
        WHERE exchange_id = ? AND timeframe = ?
        ORDER BY symbol
        """,
        (exchange_id, timeframe),
    ).fetchall()
    return [str(row[0]) for row in rows]


def load_candles(conn: sqlite3.Connection, exchange_id: str, symbol: str, timeframe: str) -> list[Candle]:
    rows = conn.execute(
        """
        SELECT timestamp_ms, timestamp, close
        FROM candles
        WHERE exchange_id = ? AND symbol = ? AND timeframe = ?
        ORDER BY timestamp_ms
        """,
        (exchange_id, symbol, timeframe),
    ).fetchall()
    return [Candle(int(ts), str(timestamp), float(close)) for ts, timestamp, close in rows]


def find_btc_symbol(symbols: Iterable[str], requested: str | None) -> str | None:
    if requested:
        return requested
    for symbol in symbols:
        base = symbol.split("/", 1)[0].upper()
        if base == "BTC":
            return symbol
    return None


def pearson(x_values: list[float], y_values: list[float]) -> float | None:
    if len(x_values) != len(y_values) or len(x_values) < 3:
        return None
    if not all(math.isfinite(value) for value in x_values + y_values):
        return None
    try:
        x_std = statistics.stdev(x_values)
        y_std = statistics.stdev(y_values)
    except statistics.StatisticsError:
        return None
    if x_std == 0.0 or y_std == 0.0:
        return None
    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(y_values)
    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values)) / (len(x_values) - 1)
    rho = covariance / (x_std * y_std)
    return max(-1.0, min(1.0, rho)) if math.isfinite(rho) else None


def z_tilde(z_score: float, threshold: float, kappa: float) -> float:
    magnitude = abs(float(z_score))
    if magnitude < threshold:
        return 0.0
    return 1.0 - math.exp(-float(kappa) * (magnitude - threshold))


def compute_symbol_rows(
    symbol: str,
    candles: list[Candle],
    btc_by_ts: dict[int, Candle] | None,
    window: int,
    z_threshold: float,
    absolute_return_floor: float,
    cbd_alpha: float,
    cbd_kappa: float,
) -> list[dict[str, Any]]:
    if window < 2:
        raise ValueError("window must be at least 2")
    if not 0.0 <= cbd_alpha <= 1.0:
        raise ValueError("cbd-alpha must be in [0, 1]")

    rows: list[dict[str, Any]] = []
    abs_history: deque[float] = deque(maxlen=window)
    asset_close_history: deque[float] = deque(maxlen=window)
    btc_close_history: deque[float] = deque(maxlen=window)
    previous_close: float | None = None

    for candle in candles:
        btc_candle = btc_by_ts.get(candle.timestamp_ms) if btc_by_ts is not None else None
        if btc_candle is not None:
            asset_close_history.append(candle.close)
            btc_close_history.append(btc_candle.close)

        if previous_close is None:
            previous_close = candle.close
            continue

        signed_return = (candle.close - previous_close) / previous_close
        abs_return = abs(signed_return)
        previous_close = candle.close

        warmup = len(abs_history) < window
        rolling_mean = None
        rolling_std = None
        z_score = None
        triggered = False
        trigger_reason = "warmup" if warmup else "none"
        if not warmup:
            history = list(abs_history)
            rolling_mean = statistics.mean(history)
            rolling_std = statistics.stdev(history)
            if rolling_std > 0.0:
                z_score = (abs_return - rolling_mean) / rolling_std
            else:
                z_score = math.inf if abs_return > rolling_mean else 0.0
            z_trigger = z_score >= z_threshold
            floor_trigger = abs_return >= absolute_return_floor
            triggered = bool(z_trigger or floor_trigger)
            if z_trigger and floor_trigger:
                trigger_reason = "z_score_and_abs_return_floor"
            elif z_trigger:
                trigger_reason = "z_score"
            elif floor_trigger:
                trigger_reason = "abs_return_floor"

        correlation_to_btc = None
        rho_cb = None
        anomaly_score = None
        omega = None
        cbd_status = "missing_btc_data"
        if btc_by_ts is None:
            cbd_status = "btc_symbol_unavailable"
        elif btc_candle is None:
            cbd_status = "missing_btc_timestamp"
        elif len(asset_close_history) < window or len(btc_close_history) < window:
            cbd_status = "warmup"
        elif z_score is None:
            cbd_status = "azte_warmup"
        else:
            correlation_to_btc = pearson(list(asset_close_history), list(btc_close_history))
            if correlation_to_btc is None:
                cbd_status = "degenerate_correlation"
            else:
                rho_cb = 1.0 - abs(correlation_to_btc)
                anomaly_score = z_tilde(z_score, z_threshold, cbd_kappa)
                omega = cbd_alpha * anomaly_score + (1.0 - cbd_alpha) * rho_cb
                cbd_status = "computed"

        rows.append(
            {
                "timestamp_ms": candle.timestamp_ms,
                "timestamp": candle.timestamp,
                "symbol": symbol,
                "close": candle.close,
                "signed_return": signed_return,
                "abs_return": abs_return,
                "rolling_window": window,
                "warmup": warmup,
                "rolling_mean_abs_return": rolling_mean,
                "rolling_std_abs_return": rolling_std,
                "z_score": z_score,
                "triggered": triggered,
                "trigger_reason": trigger_reason,
                "btc_available": btc_candle is not None,
                "correlation_to_btc": correlation_to_btc,
                "rho_cb": rho_cb,
                "z_tilde": anomaly_score,
                "omega": omega,
                "cbd_status": cbd_status,
            }
        )
        abs_history.append(abs_return)
    return rows


def format_cell(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.12g}"
    if value is None:
        return ""
    return value


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "timestamp_ms",
        "timestamp",
        "symbol",
        "close",
        "signed_return",
        "abs_return",
        "rolling_window",
        "warmup",
        "rolling_mean_abs_return",
        "rolling_std_abs_return",
        "z_score",
        "triggered",
        "trigger_reason",
        "btc_available",
        "correlation_to_btc",
        "rho_cb",
        "z_tilde",
        "omega",
        "cbd_status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_cell(row[key]) for key in fieldnames})


def build_summary(all_rows: list[dict[str, Any]], symbols: list[str], btc_symbol: str | None) -> dict[str, Any]:
    by_symbol: list[dict[str, Any]] = []
    for symbol in symbols:
        rows = [row for row in all_rows if row["symbol"] == symbol]
        triggered_rows = [row for row in rows if row["triggered"]]
        computed_cbd = [row for row in rows if row["cbd_status"] == "computed"]
        by_symbol.append(
            {
                "symbol": symbol,
                "rows": len(rows),
                "warmup_rows": sum(1 for row in rows if row["warmup"]),
                "trigger_count": len(triggered_rows),
                "first_trigger_timestamp": triggered_rows[0]["timestamp"] if triggered_rows else None,
                "cbd_computed_rows": len(computed_cbd),
                "missing_btc_rows": sum(1 for row in rows if row["cbd_status"].startswith("missing_btc")),
            }
        )
    return {
        "btc_symbol": btc_symbol,
        "symbols": by_symbol,
        "total_rows": len(all_rows),
        "total_triggers": sum(item["trigger_count"] for item in by_symbol),
    }


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_metrics(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db)
    out_dir = Path(args.out)
    with sqlite3.connect(db_path) as conn:
        symbols = load_symbols(conn, args.exchange, args.timeframe, args.symbols)
        stored_symbols = load_symbols(conn, args.exchange, args.timeframe, None)
        if not symbols:
            raise ValueError("no candle symbols found for requested exchange/timeframe")
        btc_symbol = find_btc_symbol(stored_symbols, args.btc_symbol)
        btc_by_ts = None
        if btc_symbol is not None:
            btc_candles = load_candles(conn, args.exchange, btc_symbol, args.timeframe)
            btc_by_ts = {candle.timestamp_ms: candle for candle in btc_candles}

        all_rows: list[dict[str, Any]] = []
        for symbol in symbols:
            candles = load_candles(conn, args.exchange, symbol, args.timeframe)
            rows = compute_symbol_rows(
                symbol,
                candles,
                btc_by_ts,
                args.window,
                args.z_threshold,
                args.absolute_return_floor,
                args.cbd_alpha,
                args.cbd_kappa,
            )
            all_rows.extend(rows)
            if args.per_symbol:
                write_rows(out_dir / f"{safe_symbol_filename(symbol)}_azte_cbd_metrics.csv", rows)

    events = [row for row in all_rows if row["triggered"]]
    write_rows(out_dir / "azte_cbd_metrics.csv", all_rows)
    write_rows(out_dir / "azte_cbd_events.csv", events)
    summary = build_summary(all_rows, symbols, btc_symbol)
    summary.update(
        {
            "exchange": args.exchange,
            "timeframe": args.timeframe,
            "window": args.window,
            "z_threshold": args.z_threshold,
            "absolute_return_floor": args.absolute_return_floor,
            "metrics_csv": str(out_dir / "azte_cbd_metrics.csv"),
            "events_csv": str(out_dir / "azte_cbd_events.csv"),
        }
    )
    write_summary(out_dir / "azte_cbd_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database created by fetch_hyperliquid_ohlcv.py")
    parser.add_argument("--out", default=DEFAULT_OUT, help="output directory for metrics CSV/JSON files")
    parser.add_argument("--exchange", default="hyperliquid", help="exchange_id stored in the candles table")
    parser.add_argument("--timeframe", default="1m", help="timeframe stored in the candles table")
    parser.add_argument("--symbols", default=None, help="comma-separated symbols to compute; defaults to all stored symbols")
    parser.add_argument("--btc-symbol", default=None, help="BTC symbol to use for CBD; defaults to the first stored BTC market")
    parser.add_argument("--window", type=int, default=30, help="rolling AZTE/CBD window size")
    parser.add_argument("--z-threshold", type=float, default=2.0, help="AZTE z-score threshold")
    parser.add_argument("--absolute-return-floor", type=float, default=0.003, help="AZTE absolute-return floor")
    parser.add_argument("--cbd-alpha", type=float, default=0.5, help="CBD blend weight for z_tilde")
    parser.add_argument("--cbd-kappa", type=float, default=0.5, help="CBD saturation parameter")
    parser.add_argument("--per-symbol", action="store_true", help="also write one metrics CSV per symbol")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_metrics(args)
    print(
        f"wrote {summary['total_rows']} metric rows and {summary['total_triggers']} trigger events "
        f"to {summary['metrics_csv']} and {summary['events_csv']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
