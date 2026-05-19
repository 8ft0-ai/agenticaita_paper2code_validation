#!/usr/bin/env python3
"""Write a GitHub Actions job summary from results_index.jsonl."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


def read_index(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append(warning_row(path, f"invalid JSONL line {line_number}: {exc}"))
            continue
        rows.append(row if isinstance(row, dict) else warning_row(path, f"line {line_number} is not a JSON object"))
    return rows


def warning_row(path: Path, message: str) -> dict[str, Any]:
    return {"run_id": path.name, "scenario": "unknown", "status": "warning", "quality_status": "unknown", "warnings": [message], "data": {}, "metrics": {}, "artefacts": {}}


def safe(value: Any) -> str:
    return "" if value is None else str(value).replace("|", "\\|").replace("\n", " ")


def get_dict(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    return value if isinstance(value, dict) else {}


def get_list(row: dict[str, Any], key: str) -> list[Any]:
    value = row.get(key)
    return value if isinstance(value, list) else []


def metric(row: dict[str, Any], *names: str) -> Any:
    metrics = get_dict(row, "metrics")
    data = get_dict(row, "data")
    for name in names:
        if metrics.get(name) is not None:
            return metrics[name]
        if data.get(name) is not None:
            return data[name]
    return None


def normal_status(value: Any) -> str:
    status = str(value or "unknown").lower()
    return status if status in {"pass", "warning", "fail", "unknown"} else "unknown"


def symbol_text(row: dict[str, Any]) -> str:
    total = metric(row, "symbol_count", "asset_count", "symbols_requested")
    complete = metric(row, "complete_symbols", "symbols_complete")
    if total is not None and complete is not None:
        return f"{complete}/{total}"
    return "" if total is None else str(total)


def window_text(row: dict[str, Any]) -> str:
    data = get_dict(row, "data")
    start = data.get("start_timestamp") or data.get("start") or data.get("window_start")
    end = data.get("end_timestamp") or data.get("end") or data.get("window_end")
    return f"{start or ''} -> {end or ''}" if start or end else ""


def artefact_names(row: dict[str, Any]) -> str:
    return ", ".join(sorted(get_dict(row, "artefacts")))


def render_summary(rows: list[dict[str, Any]], *, index_path: str | None = None, summary_file: str | None = None, dashboard: str | None = None) -> str:
    counts = Counter(normal_status(row.get("status")) for row in rows)
    lines = ["# Run results summary", "", "## Status counts", "", "| Status | Count |", "| --- | ---: |"]
    for status in ("pass", "warning", "fail", "unknown"):
        lines.append(f"| {status} | {counts.get(status, 0)} |")
    lines.extend(["", "## Runs", "", "| Run ID | Scenario | Status | Quality | Commit | Window | Symbols | Trades | Net PnL | Warnings | Artefacts |", "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |"])
    for row in rows:
        warnings = "; ".join(str(item) for item in get_list(row, "warnings"))
        commit = str(row.get("commit_sha") or "")[:8]
        lines.append("| {run_id} | {scenario} | {status} | {quality} | {commit} | {window} | {symbols} | {trades} | {pnl} | {warnings} | {artefacts} |".format(run_id=safe(row.get("run_id")), scenario=safe(row.get("scenario")), status=safe(row.get("status")), quality=safe(row.get("quality_status")), commit=safe(commit), window=safe(window_text(row)), symbols=safe(symbol_text(row)), trades=safe(metric(row, "trade_count")), pnl=safe(metric(row, "net_pnl_usd", "total_pnl_usd")), warnings=safe(warnings), artefacts=safe(artefact_names(row))))
    lines.extend(["", "## Generated artefacts", ""])
    for path, label in ((index_path, "results_index.jsonl"), (summary_file, "results_index.md"), (dashboard, "results_dashboard.html")):
        if path:
            lines.append(f"- [{label}]({path})")
    if not any((index_path, summary_file, dashboard)):
        lines.append("- No index or dashboard paths were supplied.")
    return "\n".join(lines) + "\n"


def write_output(markdown: str, out: str | None) -> None:
    if out:
        Path(out).write_text(markdown, encoding="utf-8")
        return
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write(markdown)
        return
    print(markdown, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, help="results_index.jsonl path")
    parser.add_argument("--summary-file", default=None, help="optional results_index.md path to link")
    parser.add_argument("--dashboard", default=None, help="optional results_dashboard.html path to link")
    parser.add_argument("--out", default=None, help="write summary to this file instead of GITHUB_STEP_SUMMARY/stdout")
    args = parser.parse_args(argv)
    markdown = render_summary(read_index(Path(args.index)), index_path=args.index, summary_file=args.summary_file, dashboard=args.dashboard)
    write_output(markdown, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
