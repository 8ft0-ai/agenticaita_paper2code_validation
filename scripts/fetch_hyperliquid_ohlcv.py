#!/usr/bin/env python3
"""Download historical Hyperliquid perpetual 1-minute OHLCV candles."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_START = "2026-04-06T00:00:00Z"
DEFAULT_END = "2026-04-11T23:59:59Z"
DEFAULT_OUT = "data/hyperliquid_ohlcv"
DEFAULT_DB_NAME = "market_data.sqlite"


def parse_utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def iso_utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def timeframe_to_ms(timeframe: str) -> int:
    match = re.fullmatch(r"(\d+)([mhd])", timeframe)
    if not match:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    amount = int(match.group(1))
    unit = match.group(2)
    multiplier = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}[unit]
    return amount * multiplier


def safe_symbol_filename(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol).strip("_") or "symbol"


def resolve_active_swap_symbols(markets: dict[str, dict[str, Any]]) -> list[str]:
    symbols: list[str] = []
    for symbol, market in markets.items():
        active = market.get("active")
        is_swap = market.get("swap") is True or market.get("type") in {"swap", "perpetual"}
        if is_swap and active is not False:
            symbols.append(str(market.get("symbol") or symbol))
    return sorted(set(symbols))


def select_symbols(all_symbols: Iterable[str], requested: str | None, symbol_limit: int | None) -> list[str]:
    symbols = list(all_symbols)
    if requested:
        requested_symbols = [item.strip() for item in requested.split(",") if item.strip()]
        known = set(symbols)
        missing = [symbol for symbol in requested_symbols if symbol not in known]
        if missing:
            raise ValueError(f"Requested symbols not found in active swap markets: {missing}")
        symbols = requested_symbols
    if symbol_limit is not None:
        if symbol_limit < 1:
            raise ValueError("--symbol-limit must be at least 1")
        symbols = symbols[:symbol_limit]
    return symbols


def fetch_symbol_candles(
    exchange: Any,
    symbol: str,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    limit: int,
    max_retries: int,
    retry_sleep: float,
) -> tuple[list[list[Any]], str | None]:
    timeframe_ms = timeframe_to_ms(timeframe)
    since = start_ms
    candles: list[list[Any]] = []
    seen: set[int] = set()

    while since <= end_ms:
        batch = None
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
                break
            except Exception as exc:  # pragma: no cover - exact ccxt exceptions vary by version.
                last_error = exc
                if attempt == max_retries:
                    return candles, f"fetch failed at {iso_utc(since)}: {exc}"
                time.sleep(retry_sleep * (attempt + 1))

        if batch is None:
            return candles, f"fetch failed at {iso_utc(since)}: {last_error}"
        if not batch:
            break

        advanced_to = since
        for candle in batch:
            if len(candle) < 6:
                continue
            ts = int(candle[0])
            advanced_to = max(advanced_to, ts)
            if start_ms <= ts <= end_ms and ts not in seen:
                seen.add(ts)
                candles.append(candle[:6])

        next_since = advanced_to + timeframe_ms
        if next_since <= since:
            return candles, f"pagination stalled at {iso_utc(since)}"
        since = next_since

        rate_limit_ms = getattr(exchange, "rateLimit", None)
        if rate_limit_ms:
            time.sleep(float(rate_limit_ms) / 1000.0)

    candles.sort(key=lambda item: int(item[0]))
    return candles, None


def normalise_funding_rate(row: dict[str, Any]) -> tuple[int, float] | None:
    timestamp = row.get("timestamp")
    rate = row.get("fundingRate")
    if rate is None:
        rate = row.get("funding_rate")
    if timestamp is None or rate is None:
        return None
    return int(timestamp), float(rate)


def fetch_symbol_funding_rates(
    exchange: Any,
    symbol: str,
    start_ms: int,
    end_ms: int,
    limit: int,
    max_retries: int,
    retry_sleep: float,
) -> tuple[list[tuple[int, float]], str | None, str]:
    method_name = "fetch_funding_rate_history"
    method = getattr(exchange, method_name, None)
    if method is None:
        return [], f"{method_name} is not available on exchange", method_name

    since = start_ms
    funding_rates: list[tuple[int, float]] = []
    seen: set[int] = set()
    while since <= end_ms:
        batch = None
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                batch = method(symbol, since=since, limit=limit)
                break
            except Exception as exc:  # pragma: no cover - exact ccxt exceptions vary by version.
                last_error = exc
                if attempt == max_retries:
                    return funding_rates, f"{method_name} failed at {iso_utc(since)}: {exc}", method_name
                time.sleep(retry_sleep * (attempt + 1))

        if batch is None:
            return funding_rates, f"{method_name} failed at {iso_utc(since)}: {last_error}", method_name
        if not batch:
            break

        advanced_to = since
        for item in batch:
            parsed = normalise_funding_rate(item)
            if parsed is None:
                continue
            ts, funding_rate = parsed
            advanced_to = max(advanced_to, ts)
            if start_ms <= ts <= end_ms and ts not in seen:
                seen.add(ts)
                funding_rates.append((ts, funding_rate))

        next_since = advanced_to + 1
        if next_since <= since:
            return funding_rates, f"{method_name} pagination stalled at {iso_utc(since)}", method_name
        since = next_since

        rate_limit_ms = getattr(exchange, "rateLimit", None)
        if rate_limit_ms:
            time.sleep(float(rate_limit_ms) / 1000.0)

    funding_rates.sort(key=lambda item: item[0])
    if not funding_rates:
        return funding_rates, f"{method_name} returned no funding history for requested window", method_name
    return funding_rates, None, method_name


def write_candles_csv(path: Path, symbol: str, candles: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp_ms", "timestamp", "symbol", "open", "high", "low", "close", "volume"])
        for ts, open_, high, low, close, volume in candles:
            writer.writerow([int(ts), iso_utc(int(ts)), symbol, open_, high, low, close, volume])


def init_storage(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS symbols (
            exchange_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            market_type TEXT,
            active INTEGER,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            PRIMARY KEY (exchange_id, symbol)
        );

        CREATE TABLE IF NOT EXISTS candles (
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
            PRIMARY KEY (exchange_id, symbol, timeframe, timestamp_ms),
            FOREIGN KEY (exchange_id, symbol) REFERENCES symbols(exchange_id, symbol)
        );

        CREATE TABLE IF NOT EXISTS funding_rates (
            exchange_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timestamp_ms INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            funding_rate REAL,
            retrieved_at TEXT NOT NULL,
            PRIMARY KEY (exchange_id, symbol, timestamp_ms),
            FOREIGN KEY (exchange_id, symbol) REFERENCES symbols(exchange_id, symbol)
        );

        CREATE TABLE IF NOT EXISTS fetch_metadata (
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
            retrieved_at TEXT NOT NULL,
            FOREIGN KEY (exchange_id, symbol) REFERENCES symbols(exchange_id, symbol)
        );
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(fetch_metadata)")}
    if "data_kind" not in columns:
        conn.execute("ALTER TABLE fetch_metadata ADD COLUMN data_kind TEXT NOT NULL DEFAULT 'ohlcv'")
    if "method" not in columns:
        conn.execute("ALTER TABLE fetch_metadata ADD COLUMN method TEXT")
    return conn


def store_symbol_catalog(conn: sqlite3.Connection, exchange_id: str, markets: dict[str, dict[str, Any]]) -> None:
    now = iso_utc(int(time.time() * 1000))
    for market_key, market in markets.items():
        symbol = str(market.get("symbol") or market_key)
        market_type = market.get("type")
        if market_type is None:
            market_type = "swap" if market.get("swap") is True else "spot" if market.get("spot") is True else None
        active = market.get("active")
        conn.execute(
            """
            INSERT INTO symbols (exchange_id, symbol, market_type, active, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(exchange_id, symbol) DO UPDATE SET
                market_type = excluded.market_type,
                active = excluded.active,
                last_seen_at = excluded.last_seen_at
            """,
            (exchange_id, symbol, market_type, None if active is None else int(bool(active)), now, now),
        )


def store_candles(
    conn: sqlite3.Connection,
    exchange_id: str,
    symbol: str,
    timeframe: str,
    candles: list[list[Any]],
) -> None:
    retrieved_at = iso_utc(int(time.time() * 1000))
    rows = [
        (
            exchange_id,
            symbol,
            timeframe,
            int(ts),
            iso_utc(int(ts)),
            float(open_),
            float(high),
            float(low),
            float(close),
            float(volume),
            retrieved_at,
        )
        for ts, open_, high, low, close, volume in candles
    ]
    conn.executemany(
        """
        INSERT INTO candles (
            exchange_id, symbol, timeframe, timestamp_ms, timestamp,
            open, high, low, close, volume, retrieved_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(exchange_id, symbol, timeframe, timestamp_ms) DO UPDATE SET
            timestamp = excluded.timestamp,
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume,
            retrieved_at = excluded.retrieved_at
        """,
        rows,
    )


def store_funding_rates(
    conn: sqlite3.Connection,
    exchange_id: str,
    symbol: str,
    funding_rates: list[tuple[int, float]],
) -> None:
    retrieved_at = iso_utc(int(time.time() * 1000))
    rows = [
        (exchange_id, symbol, ts, iso_utc(ts), funding_rate, retrieved_at)
        for ts, funding_rate in funding_rates
    ]
    conn.executemany(
        """
        INSERT INTO funding_rates (
            exchange_id, symbol, timestamp_ms, timestamp, funding_rate, retrieved_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(exchange_id, symbol, timestamp_ms) DO UPDATE SET
            timestamp = excluded.timestamp,
            funding_rate = excluded.funding_rate,
            retrieved_at = excluded.retrieved_at
        """,
        rows,
    )


def store_fetch_metadata(
    conn: sqlite3.Connection,
    exchange_id: str,
    symbol: str,
    data_kind: str,
    method: str | None,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    status: str,
    candle_count: int,
    error: str | None,
    csv_path: Path,
) -> None:
    conn.execute(
        """
        INSERT INTO fetch_metadata (
            exchange_id, symbol, data_kind, method, timeframe, start_ms, end_ms,
            status, candle_count, error, csv_path, retrieved_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            exchange_id,
            symbol,
            data_kind,
            method,
            timeframe,
            start_ms,
            end_ms,
            status,
            candle_count,
            error,
            str(csv_path),
            iso_utc(int(time.time() * 1000)),
        ),
    )


def expected_timestamps(start_ms: int, end_ms: int, timeframe_ms: int) -> list[int]:
    return list(range(start_ms, end_ms + 1, timeframe_ms))


def build_coverage_report(
    conn: sqlite3.Connection,
    exchange_id: str,
    symbols: list[str],
    timeframe: str,
    start_ms: int,
    end_ms: int,
) -> dict[str, Any]:
    expected = expected_timestamps(start_ms, end_ms, timeframe_to_ms(timeframe))
    expected_set = set(expected)
    symbol_reports: list[dict[str, Any]] = []
    unavailable_symbols: list[str] = []

    latest_status = {
        row[0]: row[1]
        for row in conn.execute(
            """
            SELECT symbol, status
            FROM fetch_metadata
            WHERE exchange_id = ? AND timeframe = ? AND start_ms = ? AND end_ms = ? AND data_kind = 'ohlcv'
            ORDER BY id
            """,
            (exchange_id, timeframe, start_ms, end_ms),
        )
    }
    latest_funding = {
        row[0]: {"status": row[1], "method": row[2], "error": row[3]}
        for row in conn.execute(
            """
            SELECT symbol, status, method, error
            FROM fetch_metadata
            WHERE exchange_id = ? AND start_ms = ? AND end_ms = ? AND data_kind = 'funding'
            ORDER BY id
            """,
            (exchange_id, start_ms, end_ms),
        )
    }

    for symbol in symbols:
        rows = conn.execute(
            """
            SELECT timestamp_ms, COUNT(*)
            FROM candles
            WHERE exchange_id = ? AND symbol = ? AND timeframe = ? AND timestamp_ms BETWEEN ? AND ?
            GROUP BY timestamp_ms
            ORDER BY timestamp_ms
            """,
            (exchange_id, symbol, timeframe, start_ms, end_ms),
        ).fetchall()
        present = {int(timestamp_ms) for timestamp_ms, _count in rows}
        duplicate_count = sum(int(count) - 1 for _timestamp_ms, count in rows if int(count) > 1)
        missing = sorted(expected_set - present)
        status = latest_status.get(symbol, "not_requested")
        funding_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM funding_rates
            WHERE exchange_id = ? AND symbol = ? AND timestamp_ms BETWEEN ? AND ?
            """,
            (exchange_id, symbol, start_ms, end_ms),
        ).fetchone()[0]
        funding = latest_funding.get(symbol, {"status": "not_requested", "method": None, "error": None})
        if status != "success" or not rows:
            unavailable_symbols.append(symbol)
        symbol_reports.append(
            {
                "symbol": symbol,
                "status": status,
                "candle_count": len(present),
                "expected_count": len(expected),
                "missing_count": len(missing),
                "missing_intervals": [iso_utc(ts) for ts in missing[:50]],
                "duplicate_timestamps": duplicate_count,
                "complete": status == "success" and len(missing) == 0 and duplicate_count == 0,
                "funding_status": funding["status"],
                "funding_method": funding["method"],
                "funding_count": funding_count,
                "funding_error": funding["error"],
            }
        )

    incomplete_symbols = [item["symbol"] for item in symbol_reports if not item["complete"]]
    funding_available_symbols = [item["symbol"] for item in symbol_reports if item["funding_count"] > 0]
    return {
        "exchange": exchange_id,
        "timeframe": timeframe,
        "start": iso_utc(start_ms),
        "end": iso_utc(end_ms),
        "expected_count_per_symbol": len(expected),
        "symbols": symbol_reports,
        "incomplete_symbols": incomplete_symbols,
        "unavailable_symbols": unavailable_symbols,
        "funding_available_symbols": funding_available_symbols,
        "benchmark_modes": {
            "price_only": "available when OHLCV candles are complete",
            "funding_adjusted": "available only for symbols with stored funding_rates rows; otherwise report as unsupported/incomplete",
        },
    }


def write_coverage_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")

    lines = [
        "# Market Data Coverage Report",
        "",
        f"Exchange: `{report['exchange']}`",
        f"Timeframe: `{report['timeframe']}`",
        f"Window: `{report['start']}` to `{report['end']}`",
        f"Expected candles per symbol: `{report['expected_count_per_symbol']}`",
        "Benchmark modes: price-only benchmarks use OHLCV candles; funding-adjusted benchmarks require stored funding-rate rows and are qualified per symbol below.",
        "",
        "| Symbol | Status | Candles | Expected | Missing | Duplicates | Complete | Funding status | Funding rows |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    for item in report["symbols"]:
        lines.append(
            "| {symbol} | {status} | {candle_count} | {expected_count} | {missing_count} | "
            "{duplicate_timestamps} | {complete} | {funding_status} | {funding_count} |".format(**item)
        )
    lines.extend(["", "## Funding Availability", ""])
    for item in report["symbols"]:
        if item["funding_error"]:
            lines.append(f"- `{item['symbol']}`: `{item['funding_status']}` via `{item['funding_method']}` - {item['funding_error']}")
        else:
            lines.append(f"- `{item['symbol']}`: `{item['funding_status']}` with `{item['funding_count']}` rows")
    lines.extend(["", "## Incomplete Symbols", ""])
    lines.extend(f"- `{symbol}`" for symbol in report["incomplete_symbols"])
    if not report["incomplete_symbols"]:
        lines.append("- None")
    lines.extend(["", "## Missing Interval Samples", ""])
    for item in report["symbols"]:
        if item["missing_intervals"]:
            sample = ", ".join(f"`{timestamp}`" for timestamp in item["missing_intervals"])
            lines.append(f"- `{item['symbol']}`: {sample}")
    if not any(item["missing_intervals"] for item in report["symbols"]):
        lines.append("- None")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_download(exchange: Any, args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out)
    db_path = Path(args.db) if args.db else out_dir / DEFAULT_DB_NAME
    start_ms = parse_utc_ms(args.start)
    end_ms = parse_utc_ms(args.end)
    if end_ms < start_ms:
        raise ValueError("--end must be greater than or equal to --start")

    markets = exchange.load_markets()
    all_symbols = resolve_active_swap_symbols(markets)
    symbols = select_symbols(all_symbols, args.symbols, args.symbol_limit)
    conn = init_storage(db_path)
    store_symbol_catalog(conn, args.exchange, markets)
    manifest: dict[str, Any] = {
        "exchange": args.exchange,
        "timeframe": args.timeframe,
        "start": iso_utc(start_ms),
        "end": iso_utc(end_ms),
        "sqlite_path": str(db_path),
        "active_swap_symbol_count": len(all_symbols),
        "requested_symbols": symbols,
        "successes": [],
        "failures": [],
    }

    for index, symbol in enumerate(symbols, start=1):
        print(f"[{index}/{len(symbols)}] fetching {symbol}", flush=True)
        candles, error = fetch_symbol_candles(
            exchange,
            symbol,
            args.timeframe,
            start_ms,
            end_ms,
            args.limit,
            args.max_retries,
            args.retry_sleep,
        )
        csv_path = out_dir / f"{safe_symbol_filename(symbol)}.csv"
        write_candles_csv(csv_path, symbol, candles)
        store_candles(conn, args.exchange, symbol, args.timeframe, candles)
        record = {"symbol": symbol, "candles": len(candles), "path": str(csv_path)}
        if error:
            store_fetch_metadata(
                conn, args.exchange, symbol, "ohlcv", "fetch_ohlcv", args.timeframe, start_ms, end_ms, "failed", len(candles), error, csv_path
            )
            record["error"] = error
            manifest["failures"].append(record)
        else:
            store_fetch_metadata(
                conn, args.exchange, symbol, "ohlcv", "fetch_ohlcv", args.timeframe, start_ms, end_ms, "success", len(candles), None, csv_path
            )
            manifest["successes"].append(record)

        funding_rates, funding_error, funding_method = fetch_symbol_funding_rates(
            exchange,
            symbol,
            start_ms,
            end_ms,
            args.funding_limit,
            args.max_retries,
            args.retry_sleep,
        )
        store_funding_rates(conn, args.exchange, symbol, funding_rates)
        funding_status = "success" if funding_error is None else "unsupported"
        store_fetch_metadata(
            conn,
            args.exchange,
            symbol,
            "funding",
            funding_method,
            "funding",
            start_ms,
            end_ms,
            funding_status,
            len(funding_rates),
            funding_error,
            csv_path,
        )
        record["funding_rates"] = len(funding_rates)
        if funding_error:
            record["funding_error"] = funding_error
        conn.commit()

    out_dir.mkdir(parents=True, exist_ok=True)
    coverage = build_coverage_report(conn, args.exchange, symbols, args.timeframe, start_ms, end_ms)
    coverage_json_path = out_dir / "coverage_report.json"
    coverage_markdown_path = out_dir / "coverage_report.md"
    write_coverage_reports(coverage, coverage_json_path, coverage_markdown_path)
    conn.close()
    manifest_path = out_dir / "manifest.json"
    manifest["manifest_path"] = str(manifest_path)
    manifest["coverage_report_path"] = str(coverage_markdown_path)
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exchange", default="hyperliquid", help="ccxt exchange id; defaults to hyperliquid")
    parser.add_argument("--timeframe", default="1m", help="OHLCV timeframe; defaults to 1m")
    parser.add_argument("--start", default=DEFAULT_START, help="inclusive UTC start timestamp")
    parser.add_argument("--end", default=DEFAULT_END, help="inclusive UTC end timestamp")
    parser.add_argument("--out", default=DEFAULT_OUT, help="output directory for CSV files and manifest")
    parser.add_argument("--db", default=None, help="SQLite database path; defaults to <out>/market_data.sqlite")
    parser.add_argument("--symbols", default=None, help="comma-separated active swap symbols for a smoke subset")
    parser.add_argument("--symbol-limit", type=int, default=None, help="first N active swap symbols for smoke testing")
    parser.add_argument("--limit", type=int, default=1000, help="per-request candle limit")
    parser.add_argument("--funding-limit", type=int, default=1000, help="per-request funding history limit")
    parser.add_argument("--max-retries", type=int, default=3, help="retries per paginated request")
    parser.add_argument("--retry-sleep", type=float, default=2.0, help="base seconds between retries")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        import ccxt  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised by users without dependencies.
        raise SystemExit("ccxt is required; install dependencies with `pip install -r requirements.txt`") from exc

    exchange_cls = getattr(ccxt, args.exchange)
    exchange = exchange_cls({"enableRateLimit": True})
    manifest = run_download(exchange, args)
    print(
        f"wrote {len(manifest['successes'])} successful symbols and "
        f"{len(manifest['failures'])} failures to {manifest['manifest_path']} "
        f"with coverage at {manifest['coverage_report_path']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
