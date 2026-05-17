#!/usr/bin/env python3
"""Export downloaded candle data into replication-harness CSV input."""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


PROVENANCE_COLUMNS = ("exchange_id", "source_symbol", "timeframe")
CLOSE_COLUMNS = ("timestamp", "asset", *PROVENANCE_COLUMNS, "close")
OHLCV_COLUMNS = ("timestamp", "asset", *PROVENANCE_COLUMNS, "open", "high", "low", "close", "volume")
FUNDING_COLUMN = "funding_rate"


def base_asset_from_symbol(symbol: str) -> str:
    """Return the base asset used by the replication harness benchmark config."""
    return symbol.split("/", 1)[0].split(":", 1)[0]


def parse_symbols(value: str | None) -> list[str] | None:
    if value is None:
        return None
    symbols = [item.strip() for item in value.split(",") if item.strip()]
    return symbols or None


def parse_utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def timeframe_to_ms(timeframe: str) -> int:
    match = re.fullmatch(r"(\d+)([mhd])", timeframe)
    if not match:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    amount = int(match.group(1))
    unit = match.group(2)
    return amount * {"m": 60_000, "h": 3_600_000, "d": 86_400_000}[unit]


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)).fetchone()
    return row is not None


def complete_symbols_from_sqlite(
    conn: sqlite3.Connection,
    exchange_id: str,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    symbol_limit: int | None = None,
    required_symbol: str | None = None,
    symbols: list[str] | None = None,
) -> list[str]:
    timeframe_ms = timeframe_to_ms(timeframe)
    expected_count = ((end_ms - start_ms) // timeframe_ms) + 1
    query = [
        "SELECT symbol",
        "FROM candles",
        "WHERE exchange_id = ? AND timeframe = ? AND timestamp_ms BETWEEN ? AND ?",
    ]
    params: list[str | int] = [exchange_id, timeframe, start_ms, end_ms]
    if symbols:
        placeholders = ",".join("?" for _ in symbols)
        query.append(f"AND symbol IN ({placeholders})")
        params.extend(symbols)
    query.extend([
        "GROUP BY symbol",
        "HAVING COUNT(*) = ?",
        "AND COUNT(DISTINCT timestamp_ms) = ?",
        "AND MIN(timestamp_ms) = ?",
        "AND MAX(timestamp_ms) = ?",
    ])
    params.extend([expected_count, expected_count, start_ms, start_ms + (expected_count - 1) * timeframe_ms])
    complete = [row[0] for row in conn.execute(" ".join(query), params)]
    complete = sorted(complete, key=lambda symbol: (0 if symbol == required_symbol else 1, symbol))
    if symbol_limit is not None:
        complete = complete[:symbol_limit]
    return complete


def load_replication_rows(
    conn: sqlite3.Connection,
    exchange_id: str | None = None,
    timeframe: str = "1m",
    symbols: list[str] | None = None,
    full_ohlcv: bool = False,
    include_funding: bool = False,
) -> list[dict[str, str | float]]:
    has_funding_table = include_funding and table_exists(conn, "funding_rates")
    query = [
        "SELECT c.timestamp, c.exchange_id, c.symbol, c.timeframe, c.open, c.high, c.low, c.close, c.volume",
    ]
    if has_funding_table:
        query.append(", f.funding_rate")
    query.extend([
        "FROM candles c",
    ])
    if has_funding_table:
        query.append("LEFT JOIN funding_rates f ON f.exchange_id = c.exchange_id AND f.symbol = c.symbol AND f.timestamp_ms = c.timestamp_ms")
    query.extend([
        "WHERE c.timeframe = ?",
    ]
    )
    params: list[str] = [timeframe]
    if exchange_id:
        query.append("AND c.exchange_id = ?")
        params.append(exchange_id)
    if symbols:
        placeholders = ",".join("?" for _ in symbols)
        query.append(f"AND c.symbol IN ({placeholders})")
        params.extend(symbols)
    query.append("ORDER BY c.timestamp_ms, c.symbol")

    rows: list[dict[str, str | float]] = []
    for sqlite_row in conn.execute(" ".join(query), params):
        timestamp, row_exchange_id, symbol, row_timeframe, open_, high, low, close, volume, *funding_values = sqlite_row
        row: dict[str, str | float] = {
            "timestamp": str(timestamp),
            "asset": base_asset_from_symbol(str(symbol)),
            "exchange_id": str(row_exchange_id),
            "source_symbol": str(symbol),
            "timeframe": str(row_timeframe),
            "close": float(close),
        }
        if full_ohlcv:
            row.update({"open": float(open_), "high": float(high), "low": float(low), "volume": float(volume)})
        if include_funding:
            funding_rate = funding_values[0] if funding_values else None
            row[FUNDING_COLUMN] = "" if funding_rate is None else float(funding_rate)
        rows.append(row)
    return rows


def write_replication_input(rows: list[dict[str, str | float]], path: str | Path, full_ohlcv: bool = False, include_funding: bool = False) -> None:
    columns = OHLCV_COLUMNS if full_ohlcv else CLOSE_COLUMNS
    if include_funding:
        columns = (*columns, FUNDING_COLUMN)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({column: row[column] for column in columns} for row in rows)


def run_export(args: argparse.Namespace) -> dict[str, int | str]:
    full_ohlcv = args.format == "ohlcv"
    with sqlite3.connect(args.db) as conn:
        symbols = parse_symbols(args.symbols)
        if args.complete_only:
            if not args.exchange:
                raise ValueError("--complete-only requires --exchange")
            if not args.start or not args.end:
                raise ValueError("--complete-only requires --start and --end")
            symbols = complete_symbols_from_sqlite(
                conn,
                exchange_id=args.exchange,
                timeframe=args.timeframe,
                start_ms=parse_utc_ms(args.start),
                end_ms=parse_utc_ms(args.end),
                symbol_limit=args.symbol_limit,
                required_symbol=args.required_symbol,
                symbols=symbols,
            )
        rows = load_replication_rows(
            conn,
            exchange_id=args.exchange,
            timeframe=args.timeframe,
            symbols=symbols,
            full_ohlcv=full_ohlcv,
            include_funding=args.include_funding,
        )
    if args.symbols_out:
        symbols_path = Path(args.symbols_out)
        symbols_path.parent.mkdir(parents=True, exist_ok=True)
        symbols_path.write_text("\n".join(symbols or []) + ("\n" if symbols else ""), encoding="utf-8")
    write_replication_input(rows, args.out, full_ohlcv=full_ohlcv, include_funding=args.include_funding)
    return {"rows": len(rows), "symbols": len(symbols or []), "output": str(args.out), "format": args.format}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="SQLite database created by the market-data downloader")
    parser.add_argument("--out", required=True, help="output CSV path for the replication harness")
    parser.add_argument("--exchange", default=None, help="optional exchange_id filter, e.g. binanceusdm")
    parser.add_argument("--timeframe", default="1m", help="candle timeframe to export; defaults to 1m")
    parser.add_argument("--symbols", default=None, help="optional comma-separated exchange symbols to export")
    parser.add_argument("--format", choices=("close", "ohlcv"), default="close", help="output columns; defaults to close-only compatibility")
    parser.add_argument("--complete-only", action="store_true", help="export only symbols with complete candle coverage for --start/--end")
    parser.add_argument("--start", default=None, help="inclusive UTC start timestamp for --complete-only")
    parser.add_argument("--end", default=None, help="inclusive UTC end timestamp for --complete-only")
    parser.add_argument("--symbol-limit", type=int, default=None, help="maximum number of complete symbols to export")
    parser.add_argument("--required-symbol", default=None, help="complete symbol to prioritize before applying --symbol-limit")
    parser.add_argument("--symbols-out", default=None, help="optional path to write selected complete symbols")
    parser.add_argument("--include-funding", action="store_true", help="append funding_rate from funding_rates rows when present")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_export(args)
    print(f"wrote {result['rows']} rows across {result['symbols']} selected symbols to {result['output']} using {result['format']} format", flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
