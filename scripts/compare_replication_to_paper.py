#!/usr/bin/env python3
"""Compare a functional replication summary against AGENTICAITA paper aggregates."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PAPER_BASELINE: dict[str, Any] = {
    "total_invocations": 157,
    "analyst_long": 142,
    "analyst_short": 2,
    "analyst_wait": 13,
    "risk_approved": 139,
    "risk_rejected": 5,
    "trades_executed": 139,
    "unique_traded_assets": 76,
    "wins": 72,
    "losses": 67,
    "gross_profit_usd": 79.67,
    "gross_loss_usd_abs": 94.74,
    "net_pnl_usd": -15.07,
    "total_notional_usd": 26079.0,
    "win_rate_pct": 51.80,
    "profit_factor": 0.841,
    "agentic_friction_pct": 11.5,
    "btc_benchmark_pnl_usd": -3912.0,
    "reported_alpha_usd": 3896.0,
}


METRIC_LABELS = {
    "total_invocations": "Total invocations",
    "analyst_long": "Analyst long signals",
    "analyst_short": "Analyst short signals",
    "analyst_wait": "Analyst wait signals",
    "risk_approved": "Risk Manager approvals",
    "risk_rejected": "Risk Manager rejections",
    "trades_executed": "Executed dry-run trades",
    "unique_traded_assets": "Unique traded assets",
    "wins": "Winning trades",
    "losses": "Losing trades",
    "gross_profit_usd": "Gross profit USD",
    "gross_loss_usd_abs": "Gross loss USD",
    "net_pnl_usd": "Net PnL USD",
    "total_notional_usd": "Total notional USD",
    "win_rate_pct": "Win rate percent",
    "profit_factor": "Profit factor",
    "agentic_friction_pct": "Agentic friction percent",
    "btc_benchmark_pnl_usd": "BTC price-only benchmark PnL USD",
    "reported_alpha_usd": "BTC benchmark alpha USD",
}


APPROX_TOLERANCES = {
    "win_rate_pct": 5.0,
    "profit_factor": 0.25,
    "agentic_friction_pct": 5.0,
}


def load_summary(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_trade_metrics(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    trade_path = Path(path)
    if not trade_path.exists():
        return {}
    with trade_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {"unique_traded_assets": 0, "total_notional_usd": 0.0}
    assets = {row.get("asset", "") for row in rows if row.get("asset")}
    total_notional = sum(float(row.get("size_usd") or 0.0) for row in rows)
    return {"unique_traded_assets": len(assets), "total_notional_usd": total_notional}


def _is_btc_row(row: dict[str, str]) -> bool:
    asset = str(row.get("asset") or "").strip().upper()
    source_symbol = str(row.get("source_symbol") or row.get("symbol") or "").strip().upper()
    return asset == "BTC" or asset.startswith("BTC/") or source_symbol.startswith("BTC/")


def _timestamp_sort_key(value: str, row_number: int) -> tuple[int, float | str, int]:
    raw = value.strip()
    try:
        return 0, float(raw), row_number
    except ValueError:
        return 1, raw, row_number


def read_btc_benchmark_metrics(
    path: str | Path | None,
    *,
    total_notional_usd: float | None,
    replication_net_pnl_usd: float | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "status": "unavailable",
        "reason": "OHLCV artefact was not supplied.",
        "btc_benchmark_pnl_usd": None,
        "reported_alpha_usd": None,
    }
    if path is None:
        return metrics

    ohlcv_path = Path(path)
    metrics["ohlcv_path"] = str(ohlcv_path)
    if not ohlcv_path.exists():
        metrics["reason"] = f"OHLCV artefact does not exist: {ohlcv_path}"
        return metrics
    if total_notional_usd is None or total_notional_usd <= 0:
        metrics["reason"] = "Replication total notional is unavailable or zero."
        return metrics
    if replication_net_pnl_usd is None:
        metrics["reason"] = "Replication net PnL is unavailable."
        return metrics

    btc_prices: list[tuple[tuple[int, float | str, int], float]] = []
    with ohlcv_path.open(newline="", encoding="utf-8") as handle:
        for row_number, row in enumerate(csv.DictReader(handle)):
            if not _is_btc_row(row):
                continue
            try:
                close = float(row.get("close") or "")
            except ValueError:
                continue
            if close <= 0:
                continue
            timestamp = str(row.get("timestamp") or row.get("timestamp_ms") or row_number)
            btc_prices.append((_timestamp_sort_key(timestamp, row_number), close))

    if len(btc_prices) < 2:
        metrics["reason"] = "Fewer than two valid BTC close observations were found in the OHLCV artefact."
        return metrics

    btc_prices.sort(key=lambda item: item[0])
    start_close = btc_prices[0][1]
    end_close = btc_prices[-1][1]
    price_return = (end_close / start_close) - 1.0
    benchmark_pnl = float(total_notional_usd) * price_return
    alpha = float(replication_net_pnl_usd) - benchmark_pnl

    metrics.update(
        {
            "status": "available",
            "reason": "Computed from the first and last BTC close in the supplied OHLCV artefact.",
            "btc_start_close": start_close,
            "btc_end_close": end_close,
            "btc_price_return_pct": round(price_return * 100.0, 8),
            "total_notional_usd": float(total_notional_usd),
            "replication_net_pnl_usd": float(replication_net_pnl_usd),
            "btc_benchmark_pnl_usd": round(benchmark_pnl, 2),
            "reported_alpha_usd": round(alpha, 2),
        }
    )
    return metrics


def replication_values(
    report: dict[str, Any],
    trade_metrics: dict[str, Any] | None = None,
    benchmark_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trade_metrics = trade_metrics or {}
    benchmark_metrics = benchmark_metrics or {}
    summary = report.get("summary", {})
    values = {metric: summary.get(metric) for metric in PAPER_BASELINE}
    values.update(
        {
            key: trade_metrics.get(key)
            for key in ("unique_traded_assets", "total_notional_usd")
            if key in trade_metrics
        }
    )
    values["btc_benchmark_pnl_usd"] = benchmark_metrics.get("btc_benchmark_pnl_usd")
    values["reported_alpha_usd"] = benchmark_metrics.get("reported_alpha_usd")
    return values


def classify(metric: str, paper_value: Any, replicated_value: Any) -> str:
    if replicated_value is None or replicated_value == "":
        return "unavailable"
    if paper_value == replicated_value:
        return "exact"
    if isinstance(paper_value, (int, float)) and isinstance(replicated_value, (int, float)):
        if metric in APPROX_TOLERANCES and abs(float(replicated_value) - float(paper_value)) <= APPROX_TOLERANCES[metric]:
            return "approximate"
        return "divergent"
    return "divergent"


def build_rows(
    report: dict[str, Any],
    trade_metrics: dict[str, Any] | None = None,
    benchmark_metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    replicated = replication_values(report, trade_metrics, benchmark_metrics)
    rows = []
    for metric, paper_value in PAPER_BASELINE.items():
        replication_value = replicated.get(metric)
        delta = ""
        if isinstance(paper_value, (int, float)) and isinstance(replication_value, (int, float)):
            delta = replication_value - paper_value
        rows.append(
            {
                "metric": metric,
                "label": METRIC_LABELS[metric],
                "paper": paper_value,
                "replication": "" if replication_value is None else replication_value,
                "delta": delta,
                "classification": classify(metric, paper_value, replication_value),
            }
        )
    return rows


def markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = ["| Metric | Paper | Replication | Delta | Classification |", "| --- | ---: | ---: | ---: | --- |"]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['paper']} | {row['replication']} | {row['delta']} | {row['classification']} |"
        )
    return "\n".join(lines)


def run_context(report: dict[str, Any]) -> dict[str, Any]:
    metadata = report.get("metadata", {})
    data = metadata.get("data", {})
    execution = metadata.get("execution", report.get("execution", {}))
    config = metadata.get("config", {})
    return {
        "data_source": report.get("data_source"),
        "asset_count": data.get("asset_count"),
        "candle_count": data.get("candle_count"),
        "start_timestamp": data.get("start_timestamp"),
        "end_timestamp": data.get("end_timestamp"),
        "execution_model": execution.get("execution_model"),
        "agents": config.get("agents"),
        "azte": config.get("azte"),
        "cbd": config.get("cbd"),
        "risk": config.get("risk"),
    }


def benchmark_markdown(benchmark_metrics: dict[str, Any] | None) -> list[str]:
    benchmark_metrics = benchmark_metrics or {
        "status": "unavailable",
        "reason": "BTC benchmark calculation was not requested.",
    }
    lines = [
        "## BTC Price-Only Benchmark",
        "",
        f"Status: `{benchmark_metrics.get('status', 'unavailable')}`",
        "",
        str(benchmark_metrics.get("reason", "No availability reason was recorded.")),
    ]
    if benchmark_metrics.get("status") == "available":
        lines.extend(
            [
                "",
                f"- BTC start close: `{benchmark_metrics['btc_start_close']}`",
                f"- BTC end close: `{benchmark_metrics['btc_end_close']}`",
                f"- BTC price return: `{benchmark_metrics['btc_price_return_pct']:.6f}%`",
                f"- Replication total notional: `${benchmark_metrics['total_notional_usd']:.2f}`",
                f"- BTC benchmark PnL: `${benchmark_metrics['btc_benchmark_pnl_usd']:.2f}`",
                f"- Replication alpha versus BTC: `${benchmark_metrics['reported_alpha_usd']:.2f}`",
            ]
        )
    lines.extend(
        [
            "",
            "This is price-only benchmark arithmetic. It does not reproduce the paper's funding-adjusted perpetual-futures benchmark because funding cash flows and the original sizing history are unavailable.",
        ]
    )
    return lines


def write_markdown(
    rows: list[dict[str, Any]],
    report: dict[str, Any],
    summary_path: str,
    trades_path: str | None,
    out_path: str | Path,
    benchmark_metrics: dict[str, Any] | None = None,
) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    lines = [
        "# AGENTICAITA Paper Replication Gap Report",
        "",
        f"Replication summary: `{summary_path}`",
        f"Trades CSV: `{trades_path or 'not supplied'}`",
        "",
        "This report compares a functional replication run against the AGENTICAITA paper's reported aggregate values. It measures structural and outcome similarity; it does not prove the original live dry-run because the authors' original artefacts are unavailable.",
        "",
        "## Classification Summary",
        "",
        "| Classification | Count |",
        "| --- | ---: |",
    ]
    for key in ("exact", "approximate", "divergent", "unavailable"):
        lines.append(f"| {key} | {counts.get(key, 0)} |")
    lines.extend(
        [
            "",
            "## Run Context",
            "",
            "```json",
            json.dumps(run_context(report), indent=2),
            "```",
            "",
        ]
    )
    lines.extend(benchmark_markdown(benchmark_metrics))
    lines.extend(
        [
            "",
            "## Paper Baseline Comparison",
            "",
            markdown_table(rows),
            "",
            "## Interpretation Rules",
            "",
            "- `exact`: replication value equals the paper aggregate exactly.",
            "- `approximate`: replication value is within a deliberately broad structural-comparison tolerance for rate-like metrics.",
            "- `divergent`: replication value is available but differs outside the comparison tolerance.",
            "- `unavailable`: the replication artefacts do not contain enough information to compute the comparison.",
            "",
            "## Non-Recoverable Original Artefacts",
            "",
            "Public APIs and reconstructed OHLCV/funding data cannot recover the paper's original L2 order book snapshots, original LLM prompts and completions, original Risk Manager approvals, author-side SQLite dry-run logs, or configuration history. Venue substitutions and proxy public data should therefore be treated as functional replication inputs, not evidence of exact historical equivalence.",
        ]
    )
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, help="replication summary.json")
    parser.add_argument("--trades", default=None, help="optional replication trades.csv for unique traded assets and notional")
    parser.add_argument(
        "--ohlcv",
        default=None,
        help="optional OHLCV CSV for the BTC price-only benchmark; defaults to ohlcv_used.csv beside summary.json",
    )
    parser.add_argument("--out", required=True, help="output Markdown gap report path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = load_summary(args.summary)
    trade_metrics = read_trade_metrics(args.trades)
    summary = report.get("summary", {})
    ohlcv_path = Path(args.ohlcv) if args.ohlcv else Path(args.summary).with_name("ohlcv_used.csv")
    benchmark_metrics = read_btc_benchmark_metrics(
        ohlcv_path,
        total_notional_usd=trade_metrics.get("total_notional_usd"),
        replication_net_pnl_usd=summary.get("net_pnl_usd"),
    )
    rows = build_rows(report, trade_metrics, benchmark_metrics)
    write_markdown(rows, report, args.summary, args.trades, args.out, benchmark_metrics)
    print(f"wrote paper replication gap report to {args.out}")


if __name__ == "__main__":
    main()
