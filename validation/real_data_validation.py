"""Real market-data validation adapter for AGENTICAITA reconstruction outputs."""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from compute_azte_cbd_metrics import (  # noqa: E402
    build_summary,
    compute_symbol_rows,
    find_btc_symbol,
    load_candles,
    load_symbols,
)
from fetch_hyperliquid_ohlcv import build_coverage_report  # noqa: E402


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return row is not None


def _stored_window(conn: sqlite3.Connection, exchange: str, timeframe: str) -> tuple[int, int]:
    if _table_exists(conn, "fetch_metadata"):
        row = conn.execute(
            """
            SELECT MIN(start_ms), MAX(end_ms)
            FROM fetch_metadata
            WHERE exchange_id = ? AND timeframe = ? AND data_kind = 'ohlcv'
            """,
            (exchange, timeframe),
        ).fetchone()
        if row and row[0] is not None and row[1] is not None:
            return int(row[0]), int(row[1])

    row = conn.execute(
        """
        SELECT MIN(timestamp_ms), MAX(timestamp_ms)
        FROM candles
        WHERE exchange_id = ? AND timeframe = ?
        """,
        (exchange, timeframe),
    ).fetchone()
    if not row or row[0] is None or row[1] is None:
        raise ValueError("no candles found for requested exchange/timeframe")
    return int(row[0]), int(row[1])


def _market_data_rows(conn: sqlite3.Connection, exchange: str, timeframe: str, symbols: list[str]) -> list[dict[str, Any]]:
    start_ms, end_ms = _stored_window(conn, exchange, timeframe)
    coverage = build_coverage_report(conn, exchange, symbols, timeframe, start_ms, end_ms)
    incomplete = len(coverage["incomplete_symbols"])
    funding_missing = len(symbols) - len(coverage["funding_available_symbols"])
    return [
        {
            "section": "pass_fail",
            "check_id": "real_data.coverage",
            "status": "pass" if incomplete == 0 else "fail",
            "summary": f"{len(symbols) - incomplete}/{len(symbols)} symbols have complete OHLCV coverage",
            "details": {
                "exchange": coverage["exchange"],
                "timeframe": coverage["timeframe"],
                "start": coverage["start"],
                "end": coverage["end"],
                "expected_count_per_symbol": coverage["expected_count_per_symbol"],
                "incomplete_symbols": coverage["incomplete_symbols"],
                "symbols": coverage["symbols"],
            },
        },
        {
            "section": "pass_fail",
            "check_id": "real_data.funding_availability",
            "status": "pass" if funding_missing == 0 else "unsupported",
            "summary": f"{len(coverage['funding_available_symbols'])}/{len(symbols)} symbols include funding-rate rows",
            "details": {
                "funding_available_symbols": coverage["funding_available_symbols"],
                "benchmark_modes": coverage["benchmark_modes"],
            },
        },
    ]


def _azte_cbd_rows(
    conn: sqlite3.Connection,
    exchange: str,
    timeframe: str,
    symbols: list[str],
    btc_symbol_arg: str | None,
    window: int,
    z_threshold: float,
    absolute_return_floor: float,
    cbd_alpha: float,
    cbd_kappa: float,
) -> list[dict[str, Any]]:
    stored_symbols = load_symbols(conn, exchange, timeframe, None)
    btc_symbol = find_btc_symbol(stored_symbols, btc_symbol_arg)
    btc_by_ts = None
    if btc_symbol is not None:
        btc_by_ts = {candle.timestamp_ms: candle for candle in load_candles(conn, exchange, btc_symbol, timeframe)}

    metric_rows: list[dict[str, Any]] = []
    for symbol in symbols:
        candles = load_candles(conn, exchange, symbol, timeframe)
        metric_rows.extend(
            compute_symbol_rows(
                symbol,
                candles,
                btc_by_ts,
                window,
                z_threshold,
                absolute_return_floor,
                cbd_alpha,
                cbd_kappa,
            )
        )

    summary = build_summary(metric_rows, symbols, btc_symbol)
    summary.update(
        {
            "exchange": exchange,
            "timeframe": timeframe,
            "window": window,
            "z_threshold": z_threshold,
            "absolute_return_floor": absolute_return_floor,
        }
    )
    by_symbol = {item["symbol"]: item for item in summary["symbols"]}
    rows = [
        {
            "section": "exploratory",
            "check_id": "real_data.azte_cbd_summary",
            "status": "exploratory",
            "summary": f"{summary['total_triggers']} AZTE trigger rows across {len(symbols)} symbols",
            "details": summary,
        }
    ]
    for symbol in symbols:
        item = by_symbol[symbol]
        rows.append(
            {
                "section": "exploratory",
                "check_id": f"real_data.azte_cbd.{symbol}",
                "status": "exploratory",
                "summary": (
                    f"{item['trigger_count']} triggers, {item['cbd_computed_rows']} CBD rows, "
                    f"{item['missing_btc_rows']} missing-BTC rows"
                ),
                "details": item,
            }
        )
    return rows


def run_real_data_validation(args: Any) -> list[dict[str, Any]]:
    db_path = Path(args.market_db)
    with sqlite3.connect(db_path) as conn:
        symbols = load_symbols(conn, args.exchange, args.timeframe, args.symbols)
        if not symbols:
            raise ValueError("no candle symbols found for requested exchange/timeframe")
        rows = _market_data_rows(conn, args.exchange, args.timeframe, symbols)
        rows.extend(
            _azte_cbd_rows(
                conn,
                args.exchange,
                args.timeframe,
                symbols,
                args.btc_symbol,
                args.window,
                args.z_threshold,
                args.absolute_return_floor,
                args.cbd_alpha,
                args.cbd_kappa,
            )
        )

    rows.append(
        {
            "section": "caveat",
            "check_id": "real_data.unsupported_original_claims",
            "status": "unsupported",
            "summary": "Downloaded candles can reconstruct coverage and exploratory AZTE/CBD metrics, not the paper's original live run.",
            "details": {
                "unsupported": [
                    "Original L2 order book snapshots are not recoverable from OHLCV downloads.",
                    "Original LLM decisions, prompts, negotiations, and risk-manager approvals are not recoverable without logs.",
                    "The paper's original SQLite records and dry-run trade provenance remain unsupported unless provided as artefacts.",
                ]
            },
        }
    )
    return rows


def write_real_data_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# AGENTICAITA real-data validation report",
        "",
        "This report validates a downloaded market-data SQLite store separately from paper-reported aggregate arithmetic.",
        "Pass/fail rows are limited to data availability checks; AZTE/CBD rows are exploratory reconstruction metrics.",
        "",
        "## Summary",
        "",
    ]
    for status in ["pass", "fail", "unsupported", "exploratory"]:
        lines.append(f"- **{status}**: {counts.get(status, 0)}")
    lines.extend(["", "## Results", "", "| Section | Check ID | Status | Summary |", "|---|---|---:|---|"])
    for row in rows:
        lines.append(
            "| {section} | {check_id} | {status} | {summary} |".format(
                section=str(row["section"]).replace("|", "\\|"),
                check_id=str(row["check_id"]).replace("|", "\\|"),
                status=str(row["status"]).replace("|", "\\|"),
                summary=str(row["summary"]).replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "## Unsupported Original-Claim Caveats",
            "",
            "- Public OHLCV/funding APIs cannot recover the paper's original L2 order book snapshots.",
            "- Public market data cannot recover original LLM calls, agent decisions, or negotiation logs.",
            "- The original SQLite dry-run trade records remain unsupported unless the artefact is supplied.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def serialise_real_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "section": str(row["section"]),
        "check_id": str(row["check_id"]),
        "status": str(row["status"]),
        "summary": str(row["summary"]),
        "details": json.dumps(row["details"], ensure_ascii=False, sort_keys=True),
    }
