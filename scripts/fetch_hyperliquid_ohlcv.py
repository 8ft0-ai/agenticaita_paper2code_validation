#!/usr/bin/env python3
"""Download historical Hyperliquid perpetual 1-minute OHLCV candles."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_START = "2026-04-06T00:00:00Z"
DEFAULT_END = "2026-04-11T23:59:59Z"
DEFAULT_OUT = "data/hyperliquid_ohlcv"


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


def write_candles_csv(path: Path, symbol: str, candles: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp_ms", "timestamp", "symbol", "open", "high", "low", "close", "volume"])
        for ts, open_, high, low, close, volume in candles:
            writer.writerow([int(ts), iso_utc(int(ts)), symbol, open_, high, low, close, volume])


def run_download(exchange: Any, args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out)
    start_ms = parse_utc_ms(args.start)
    end_ms = parse_utc_ms(args.end)
    if end_ms < start_ms:
        raise ValueError("--end must be greater than or equal to --start")

    markets = exchange.load_markets()
    all_symbols = resolve_active_swap_symbols(markets)
    symbols = select_symbols(all_symbols, args.symbols, args.symbol_limit)
    manifest: dict[str, Any] = {
        "exchange": args.exchange,
        "timeframe": args.timeframe,
        "start": iso_utc(start_ms),
        "end": iso_utc(end_ms),
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
        record = {"symbol": symbol, "candles": len(candles), "path": str(csv_path)}
        if error:
            record["error"] = error
            manifest["failures"].append(record)
        else:
            manifest["successes"].append(record)

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest["manifest_path"] = str(manifest_path)
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
    parser.add_argument("--symbols", default=None, help="comma-separated active swap symbols for a smoke subset")
    parser.add_argument("--symbol-limit", type=int, default=None, help="first N active swap symbols for smoke testing")
    parser.add_argument("--limit", type=int, default=1000, help="per-request candle limit")
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
        f"{len(manifest['failures'])} failures to {manifest['manifest_path']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
