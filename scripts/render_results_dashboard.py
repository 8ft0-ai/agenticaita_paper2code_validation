#!/usr/bin/env python3
"""Render a static local HTML dashboard from results_index.jsonl."""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

SCENARIO_LABELS = {
    "static_validation": "Static validation",
    "real_data_validation": "Real-data validation",
    "market_data_coverage": "Market-data coverage",
    "replication": "Replication",
    "quality_check": "Quality checks",
    "unknown": "Unknown",
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


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


def scenario_label(scenario: Any) -> str:
    key = str(scenario or "unknown")
    return SCENARIO_LABELS.get(key, key.replace("_", " ").title())


def status_class(status: Any) -> str:
    key = str(status or "unknown").lower()
    return key if key in {"pass", "warning", "fail", "unknown"} else "unknown"


def warning_row(source: Path, message: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "run_id": source.name,
        "scenario": "unknown",
        "status": "warning",
        "quality_status": "unknown",
        "data": {},
        "metrics": {},
        "warnings": [message],
        "artefacts": {},
    }


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


def bar(value: float, maximum: float, label: str) -> str:
    width = 0.0 if maximum <= 0 else max(0.0, min(100.0, value / maximum * 100.0))
    return f'<div class="bar"><span style="width:{width:.1f}%"></span><b>{esc(label)}</b></div>'


def status_cards(rows: list[dict[str, Any]]) -> str:
    counts = Counter(status_class(row.get("status")) for row in rows)
    return "\n".join(
        f'<section class="card {key}"><small>{label}</small><strong>{counts.get(key, 0)}</strong></section>'
        for key, label in [("pass", "Pass"), ("warning", "Warning"), ("fail", "Fail"), ("unknown", "Unknown")]
    )


def status_summary(rows: list[dict[str, Any]]) -> str:
    counts = Counter(status_class(row.get("status")) for row in rows)
    maximum = max(counts.values(), default=1)
    return "<h2>Status summary</h2>" + "\n".join(bar(counts.get(key, 0), maximum, f"{key}: {counts.get(key, 0)}") for key in ("pass", "warning", "fail", "unknown"))


def symbol_summary(rows: list[dict[str, Any]]) -> str:
    values: list[tuple[dict[str, Any], Any, Any]] = []
    for row in rows:
        total = metric(row, "symbol_count", "asset_count", "symbols_requested")
        complete = metric(row, "complete_symbols", "symbols_complete")
        if total is not None or complete is not None:
            values.append((row, complete, total))
    if not values:
        return "<h2>Symbol coverage</h2><p>No symbol coverage metrics were present.</p>"
    maximum = max(float(total or complete or 0) for _, complete, total in values) or 1.0
    lines = ["<h2>Symbol coverage</h2>"]
    for row, complete, total in values:
        lines.append(bar(float(complete or total or 0), maximum, f"{row.get('run_id')}: {complete if complete is not None else '?'} / {total if total is not None else '?'}"))
    return "\n".join(lines)


def trade_summary(rows: list[dict[str, Any]]) -> str:
    trade_rows = [row for row in rows if metric(row, "trade_count") is not None or metric(row, "net_pnl_usd", "total_pnl_usd") is not None]
    if not trade_rows:
        return "<h2>Trade and PnL summary</h2><p>No trade or PnL metrics were present.</p>"
    lines = ["<h2>Trade and PnL summary</h2>", "<table><tr><th>Run</th><th>Scenario</th><th>Trades</th><th>Net PnL</th></tr>"]
    for row in trade_rows:
        lines.append(
            f"<tr><td>{esc(row.get('run_id'))}</td><td>{esc(scenario_label(row.get('scenario')))}</td>"
            f"<td>{esc(metric(row, 'trade_count'))}</td><td>{esc(metric(row, 'net_pnl_usd', 'total_pnl_usd'))}</td></tr>"
        )
    lines.append("</table>")
    return "\n".join(lines)


def href(path: Any) -> str:
    return quote(str(path), safe="/:._-#?=&%")


def artefacts(row: dict[str, Any]) -> str:
    links = []
    for key, path in sorted(get_dict(row, "artefacts").items()):
        links.append(f'<a href="{esc(href(path))}">{esc(key)}</a>')
    return ", ".join(links)


def window_text(row: dict[str, Any]) -> str:
    data = get_dict(row, "data")
    start = data.get("start_timestamp") or data.get("start") or data.get("window_start")
    end = data.get("end_timestamp") or data.get("end") or data.get("window_end")
    return f"{start or ''} -> {end or ''}" if start or end else ""


def symbols_text(row: dict[str, Any]) -> str:
    total = metric(row, "symbol_count", "asset_count", "symbols_requested")
    complete = metric(row, "complete_symbols", "symbols_complete")
    if total is not None and complete is not None:
        return f"{complete}/{total}"
    return "" if total is None else str(total)


def run_table(rows: list[dict[str, Any]]) -> str:
    lines = ["<table><tr><th>Run</th><th>Status</th><th>Quality</th><th>Commit</th><th>Window</th><th>Symbols</th><th>Trades</th><th>Net PnL</th><th>Warnings</th><th>Artefacts</th></tr>"]
    for row in rows:
        status = status_class(row.get("status"))
        quality = status_class(row.get("quality_status"))
        commit = str(row.get("commit_sha") or "")[:8]
        warnings = "; ".join(str(item) for item in get_list(row, "warnings"))
        lines.append(
            f"<tr><td>{esc(row.get('run_id'))}</td><td><span class=\"pill {status}\">{esc(row.get('status') or 'unknown')}</span></td>"
            f"<td><span class=\"pill {quality}\">{esc(row.get('quality_status') or 'unknown')}</span></td><td>{esc(commit)}</td>"
            f"<td>{esc(window_text(row))}</td><td>{esc(symbols_text(row))}</td><td>{esc(metric(row, 'trade_count'))}</td>"
            f"<td>{esc(metric(row, 'net_pnl_usd', 'total_pnl_usd'))}</td><td>{esc(warnings)}</td><td>{artefacts(row)}</td></tr>"
        )
    lines.append("</table>")
    return "\n".join(lines)


def grouped_tables(rows: list[dict[str, Any]]) -> str:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("scenario") or "unknown")].append(row)
    order = ["static_validation", "real_data_validation", "market_data_coverage", "replication", "quality_check", "unknown"]
    lines: list[str] = []
    for scenario in order + sorted(set(groups) - set(order)):
        if scenario in groups:
            lines.append(f"<h2>{esc(scenario_label(scenario))}</h2>")
            lines.append(run_table(groups[scenario]))
    return "\n".join(lines)


def render(rows: list[dict[str, Any]], source: Path) -> str:
    css = """
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:2rem;background:#f6f8fa;color:#1f2328}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));gap:1rem}.card,.panel{background:white;border:1px solid #d0d7de;border-radius:.75rem;padding:1rem;margin:1rem 0}.card small{display:block;color:#57606a}.card strong{font-size:2rem}.pass{border-color:#1a7f37}.warning{border-color:#bf8700}.fail{border-color:#cf222e}.unknown{border-color:#57606a}
table{border-collapse:collapse;width:100%;font-size:.92rem}th,td{border-bottom:1px solid #d8dee4;padding:.55rem;text-align:left;vertical-align:top}th{background:#f6f8fa}.pill{border-radius:999px;padding:.15rem .5rem;font-weight:600}.pill.pass{background:#dafbe1}.pill.warning{background:#fff8c5}.pill.fail{background:#ffebe9}.pill.unknown{background:#eaeef2}.bar{position:relative;background:#eaeef2;border-radius:.4rem;min-height:1.8rem;margin:.5rem 0;overflow:hidden}.bar span{position:absolute;inset:0 auto 0 0;background:#0969da}.bar b{position:relative;display:inline-block;padding:.35rem .5rem}
"""
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Run Results Dashboard</title><style>{css}</style></head>
<body>
<header><h1>Run Results Dashboard</h1><p>Generated from <code>{esc(source)}</code>. This is a local generated artefact.</p></header>
<div class="grid">{status_cards(rows)}</div>
<section class="panel">{status_summary(rows)}</section>
<section class="panel">{symbol_summary(rows)}</section>
<section class="panel">{trade_summary(rows)}</section>
<section class="panel"><h2>Runs by scenario</h2>{grouped_tables(rows)}</section>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, help="results_index.jsonl path")
    parser.add_argument("--out", default="results_dashboard.html", help="HTML dashboard output path")
    args = parser.parse_args(argv)
    index_path = Path(args.index)
    rows = read_index(index_path)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(rows, index_path), encoding="utf-8")
    print(f"rendered {len(rows)} run(s) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
