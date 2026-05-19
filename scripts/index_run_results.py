#!/usr/bin/env python3
"""Index local validation, market-data, quality-check, and replication run results."""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any

from build_run_manifest import build_manifest


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def escape_md(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


def warning_manifest(run_dir: Path, base: Path, message: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "run_id": run_dir.name or rel(run_dir, base),
        "scenario": "unknown",
        "commit_sha": None,
        "command": None,
        "started_at": None,
        "completed_at": None,
        "status": "warning",
        "quality_status": "unknown",
        "data": {},
        "metrics": {},
        "warnings": [message],
        "artefacts": {},
        "missing_artefacts": [],
    }


def load_or_build_manifest(run_dir: Path, base: Path) -> dict[str, Any]:
    manifest_path = run_dir / "run_manifest.json"
    try:
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            if not isinstance(manifest, dict):
                raise ValueError("run_manifest.json must contain an object")
            return manifest
        namespace = argparse.Namespace(
            run_dir=str(run_dir),
            scenario="auto",
            out=None,
            run_id=None,
            commit_sha=None,
            command=None,
            started_at=None,
            completed_at=None,
            quality_json=None,
            base_dir=str(base),
        )
        return build_manifest(namespace)
    except Exception as exc:  # pragma: no cover - exercised through subprocess tests
        return warning_manifest(run_dir, base, f"could not parse run directory: {exc}")


def discover_run_dirs(patterns: list[str], base: Path) -> list[Path]:
    seen: set[Path] = set()
    run_dirs: list[Path] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if not matches:
            missing = (base / pattern).resolve()
            if missing not in seen:
                seen.add(missing)
                run_dirs.append(missing)
            continue
        for match in matches:
            path = Path(match)
            if path.name == "run_manifest.json" or path.suffix == ".json":
                path = path.parent
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                run_dirs.append(path)
    return run_dirs


def compact_row(manifest: dict[str, Any]) -> dict[str, Any]:
    data = manifest.get("data", {}) if isinstance(manifest.get("data"), dict) else {}
    metrics = manifest.get("metrics", {}) if isinstance(manifest.get("metrics"), dict) else {}
    artefacts = manifest.get("artefacts", {}) if isinstance(manifest.get("artefacts"), dict) else {}
    warnings = manifest.get("warnings", []) if isinstance(manifest.get("warnings"), list) else []
    return {
        "run_id": manifest.get("run_id"),
        "scenario": manifest.get("scenario"),
        "status": manifest.get("status"),
        "quality_status": manifest.get("quality_status"),
        "commit_sha": manifest.get("commit_sha"),
        "window_start": data.get("start_timestamp") or data.get("start") or data.get("window_start"),
        "window_end": data.get("end_timestamp") or data.get("end") or data.get("window_end"),
        "symbol_count": metrics.get("symbol_count") or data.get("asset_count") or data.get("symbols_requested"),
        "complete_symbols": metrics.get("complete_symbols") or data.get("symbols_complete"),
        "trade_count": metrics.get("trade_count"),
        "net_pnl_usd": metrics.get("net_pnl_usd") or metrics.get("total_pnl_usd"),
        "warnings": warnings,
        "artefacts": artefacts,
    }


def format_symbols(row: dict[str, Any]) -> str:
    complete, total = row.get("complete_symbols"), row.get("symbol_count")
    if complete is not None and total is not None:
        return f"{complete}/{total}"
    if total is not None:
        return str(total)
    return ""


def format_artefacts(artefacts: dict[str, str]) -> str:
    links = [f"[{escape_md(key)}]({escape_md(path)})" for key, path in sorted(artefacts.items())[:4]]
    extra = len(artefacts) - len(links)
    if extra > 0:
        links.append(f"+{extra} more")
    return ", ".join(links)


def write_markdown(path: Path, manifests: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Run Results Index",
        "",
        "This generated local index summarises validation, market-data, quality-check, and replication runs without committing raw generated artefacts.",
        "",
        "| Run ID | Scenario | Status | Quality | Commit | Window | Symbols | Trades | Net PnL | Warnings | Artefacts |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for manifest in manifests:
        row = compact_row(manifest)
        window = ""
        if row.get("window_start") or row.get("window_end"):
            window = f"{row.get('window_start') or ''} -> {row.get('window_end') or ''}"
        warnings = "; ".join(str(w) for w in row.get("warnings", []))
        lines.append(
            "| {run_id} | {scenario} | {status} | {quality} | {commit} | {window} | {symbols} | {trades} | {pnl} | {warnings} | {artefacts} |".format(
                run_id=escape_md(row.get("run_id")),
                scenario=escape_md(row.get("scenario")),
                status=escape_md(row.get("status")),
                quality=escape_md(row.get("quality_status")),
                commit=escape_md(row.get("commit_sha")),
                window=escape_md(window),
                symbols=escape_md(format_symbols(row)),
                trades=escape_md(row.get("trade_count")),
                pnl=escape_md(row.get("net_pnl_usd")),
                warnings=escape_md(warnings),
                artefacts=format_artefacts(row.get("artefacts", {})),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", required=True, help="run directories or glob patterns to index")
    parser.add_argument("--out-jsonl", default="results_index.jsonl")
    parser.add_argument("--out-md", default="results_index.md")
    parser.add_argument("--base-dir", default=".")
    args = parser.parse_args(argv)

    base = Path(args.base_dir)
    run_dirs = discover_run_dirs(args.runs, base)
    manifests = [load_or_build_manifest(path, base) for path in run_dirs]
    write_jsonl(Path(args.out_jsonl), manifests)
    write_markdown(Path(args.out_md), manifests)
    print(f"indexed {len(manifests)} run(s)")
    print(f"JSONL: {args.out_jsonl}")
    print(f"Markdown: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
