#!/usr/bin/env python3
"""Run the public-market real-data replication workflow."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from fetch_hyperliquid_ohlcv import DEFAULT_END, DEFAULT_START

BASELINE_ASSETS = "BTC,ETH,SOL,AVAX,DOGE,ADA,XRP,DOT,FARTCOIN,XPL,CC,HEMI,S,BCH,ETC".split(",")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def quote_for(exchange: str) -> str:
    return "USDC" if exchange == "hyperliquid" else "USDT"


def baseline_symbols(exchange: str) -> str:
    quote = quote_for(exchange)
    return ",".join(f"{asset}/{quote}:{quote}" for asset in BASELINE_ASSETS)


def btc_symbol(exchange: str) -> str:
    quote = quote_for(exchange)
    return f"BTC/{quote}:{quote}"


def run(command: list[str], *, cwd: Path, dry_run: bool) -> None:
    print("+ " + " ".join(command), flush=True)
    if not dry_run:
        subprocess.run(command, cwd=cwd, check=True)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", choices=("baseline-15", "large"), default="baseline-15")
    p.add_argument("--exchange", default="binanceusdm")
    p.add_argument("--symbols", default=None)
    p.add_argument("--symbol-limit", type=int, default=None)
    p.add_argument("--fetch-symbol-limit", type=int, default=None)
    p.add_argument("--timeframe", default="1m")
    p.add_argument("--start", default=DEFAULT_START)
    p.add_argument("--end", default=DEFAULT_END)
    p.add_argument("--market-out", default=None)
    p.add_argument("--market-db", default=None)
    p.add_argument("--replication-input", default=None)
    p.add_argument("--symbols-out", default=None)
    p.add_argument("--replication-out", default=None)
    p.add_argument("--paper-comparison-out", default=None)
    p.add_argument("--skip-paper-comparison", action="store_true")
    p.add_argument("--config", default="replication/config.yaml")
    p.add_argument("--export-format", choices=("close", "ohlcv"), default="ohlcv")
    p.add_argument("--include-funding", action="store_true")
    p.add_argument("--limit", type=int, default=1000)
    p.add_argument("--funding-limit", type=int, default=1000)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--retry-sleep", type=float, default=1.0)
    p.add_argument("--skip-fetch", action="store_true")
    p.add_argument("--skip-replication", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--python", default=sys.executable)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = repo_root()
    limit = args.symbol_limit or (15 if args.profile == "baseline-15" else 76)
    if limit < 1:
        raise SystemExit("--symbol-limit must be at least 1")
    scope = "real_subset" if args.profile == "baseline-15" else f"large_{limit}"
    market_out = Path(args.market_out or root / "data" / f"{args.exchange}_ohlcv_{scope}")
    market_db = Path(args.market_db or market_out / "market_data.sqlite")
    replication_input = Path(args.replication_input or market_out / "replication_input_ohlcv.csv")
    symbols_out = Path(args.symbols_out or market_out / f"complete_symbols_{limit}.txt")
    replication_out = Path(args.replication_out or root / "replication" / f"results_real_{args.exchange}_{scope}")
    paper_comparison_out = Path(args.paper_comparison_out or replication_out / "paper_replication_gap_report.md")
    symbols = args.symbols or (baseline_symbols(args.exchange) if args.profile == "baseline-15" else None)

    fetch_cmd = None
    if not args.skip_fetch:
        fetch_cmd = [
            args.python, "scripts/fetch_hyperliquid_ohlcv.py", "--exchange", args.exchange,
            "--timeframe", args.timeframe, "--start", args.start, "--end", args.end,
            "--out", str(market_out), "--db", str(market_db), "--limit", str(args.limit),
            "--funding-limit", str(args.funding_limit), "--max-retries", str(args.max_retries),
            "--retry-sleep", str(args.retry_sleep),
        ]
        if symbols:
            fetch_cmd += ["--symbols", symbols]
        elif args.fetch_symbol_limit:
            fetch_cmd += ["--symbol-limit", str(args.fetch_symbol_limit)]

    export_cmd = [
        args.python, "scripts/export_replication_input.py", "--db", str(market_db),
        "--out", str(replication_input), "--exchange", args.exchange, "--timeframe", args.timeframe,
        "--format", args.export_format, "--complete-only", "--start", args.start, "--end", args.end,
        "--symbol-limit", str(limit), "--required-symbol", btc_symbol(args.exchange),
        "--symbols-out", str(symbols_out),
    ]
    if symbols:
        export_cmd += ["--symbols", symbols]
    if args.include_funding:
        export_cmd.append("--include-funding")

    replicate_cmd = None
    if not args.skip_replication:
        replicate_cmd = [args.python, "replication/replicate.py", "--config", args.config, "--input-csv", str(replication_input), "--out", str(replication_out)]
    paper_compare_cmd = None
    if not args.skip_replication and not args.skip_paper_comparison:
        paper_compare_cmd = [
            args.python, "scripts/compare_replication_to_paper.py",
            "--summary", str(replication_out / "summary.json"),
            "--trades", str(replication_out / "trades.csv"),
            "--ohlcv", str(replication_out / "ohlcv_used.csv"),
            "--out", str(paper_comparison_out),
        ]

    plan = {"profile": args.profile, "exchange": args.exchange, "paths": {"market_db": str(market_db), "replication_input": str(replication_input), "replication_out": str(replication_out), "paper_comparison_out": str(paper_comparison_out)}, "commands": {"fetch": fetch_cmd, "export": export_cmd, "replicate": replicate_cmd, "paper_compare": paper_compare_cmd}}
    print(json.dumps(plan, indent=2), flush=True)
    if fetch_cmd:
        run(fetch_cmd, cwd=root, dry_run=args.dry_run)
    run(export_cmd, cwd=root, dry_run=args.dry_run)
    if replicate_cmd:
        run(replicate_cmd, cwd=root, dry_run=args.dry_run)
    if paper_compare_cmd:
        run(paper_compare_cmd, cwd=root, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
