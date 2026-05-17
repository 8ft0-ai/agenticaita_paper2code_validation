#!/usr/bin/env python3
"""Export downloaded candle data into replication-harness CSV input."""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path


CLOSE_COLUMNS = ("timestamp", "asset", "close")
OHLCV_COLUMNS = ("timestamp", "asset", "open", "high", "low", "close", "volume")


def base_asset_from_symbol(symbol: str) -> str:
    """Return the base asset used by the replication harness benchmark config."""
    return symbol.split("/", 1)[0].split(":", 1)[0]


def parse_symbols(value: str | None) -> list[str] | None:
    if value is None:
        return None
    symbols = [item.strip() for item in value.split(",") if item.strip()]
    return symbols or None


def load_replication_rows(
    conn: sqlite3.Connection,
    exchange_id: str | None = None,
    timeframe: str = "1m",
    symbols: list[str] | None = None,
    full_ohlcv: bool = False,
) -> list[dict[str, str | float]]:
    query = [
        "SELECT timestamp, symbol, open, high, low, close, volume",
        "FROM candles",
        "WHERE timeframe = ?",
    ]
    params: list[str] = [timeframe]
    if exchange_id:
        query.append("AND exchange_id = ?")
        params.append(exchange_id)
    if symbols:
        placeholders = ",".join("?" for _ in symbols)
        query.append(f"AND symbol IN ({placeholders})")
        params.extend(symbols)
    query.append("ORDER BY timestamp_ms, symbol")

    rows: list[dict[str, str | float]] = []
    for timestamp, symbol, open_, high, low, close, volume in conn.execute(" ".join(query), params):
        row: dict[str, str | float] = {
            "timestamp": str(timestamp),
            "asset": base_asset_from_symbol(str(symbol)),
            "close": float(close),
        }
        if full_ohlcv:
            row.update({"open": float(open_), "high": float(high), "low": float(low), "volume": float(volume)})
        rows.append(row)
    return rows


def write_replication_input(rows: list[dict[str, str | float]], path: str | Path, full_ohlcv: bool = False) -> None:
    columns = OHLCV_COLUMNS if full_ohlcv else CLOSE_COLUMNS
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({column: row[column] for column in columns} for row in rows)


def run_export(args: argparse.Namespace) -> dict[str, int | str]:
    full_ohlcv = args.format == "ohlcv"
    with sqlite3.connect(args.db) as conn:
        rows = load_replication_rows(
            conn,
            exchange_id=args.exchange,
            timeframe=args.timeframe,
            symbols=parse_symbols(args.symbols),
            full_ohlcv=full_ohlcv,
        )
    write_replication_input(rows, args.out, full_ohlcv=full_ohlcv)
    return {"rows": len(rows), "output": str(args.out), "format": args.format}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="SQLite database created by the market-data downloader")
    parser.add_argument("--out", required=True, help="output CSV path for the replication harness")
    parser.add_argument("--exchange", default=None, help="optional exchange_id filter, e.g. binanceusdm")
    parser.add_argument("--timeframe", default="1m", help="candle timeframe to export; defaults to 1m")
    parser.add_argument("--symbols", default=None, help="optional comma-separated exchange symbols to export")
    parser.add_argument("--format", choices=("close", "ohlcv"), default="close", help="output columns; defaults to close-only compatibility")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_export(args)
    print(f"wrote {result['rows']} rows to {result['output']} using {result['format']} format", flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
