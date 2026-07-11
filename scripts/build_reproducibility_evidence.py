#!/usr/bin/env python3
"""Build or verify a compact, non-secret evidence bundle for a replication run."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import sys
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "1"
SECRET_KEY_RE = re.compile(r"(api[_-]?key|token|secret|password|credential)", re.IGNORECASE)
DEFAULT_ARTEFACTS = (
    "summary.json",
    "trades.csv",
    "pipeline_log.csv",
    "replication_report.md",
    "paper_replication_gap_report.md",
    "ohlcv_used.csv",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if SECRET_KEY_RE.search(str(key)) else redact(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        if value.startswith(("/tmp/", "/var/folders/", "C:\\Users\\", "/Users/", "/home/")):
            return Path(value).name
        return value
    return value


def relative_path(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.name


def file_record(path: Path, base: Path, *, required: bool = False) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": relative_path(path, base),
        "required": required,
        "status": "present" if path.is_file() else "missing",
    }
    if path.is_file():
        record.update({"size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return record


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def read_lines(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def base_asset(symbol: str) -> str:
    return symbol.split("/", 1)[0].split(":", 1)[0]


def llm_audit_summary(path: Path | None) -> dict[str, Any]:
    summary = {"status": "missing", "audit_rows": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "reported_cost_usd": 0.0}
    if path is None or not path.is_file():
        return summary
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        summary["audit_rows"] += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = row.get("usage", {}) if isinstance(row, dict) else {}
        if not isinstance(usage, dict):
            usage = {}
        for source, target in (
            ("prompt_tokens", "prompt_tokens"),
            ("completion_tokens", "completion_tokens"),
            ("total_tokens", "total_tokens"),
        ):
            try:
                summary[target] += int(usage.get(source, 0) or 0)
            except (TypeError, ValueError):
                pass
        try:
            summary["reported_cost_usd"] += float(row.get("cost", row.get("reported_cost_usd", 0.0)) or 0.0)
        except (AttributeError, TypeError, ValueError):
            pass
    summary["status"] = "available"
    summary["reported_cost_usd"] = round(float(summary["reported_cost_usd"]), 10)
    return summary


def pipeline_diagnostics(path: Path | None) -> dict[str, Any]:
    result = {"status": "missing", "rows": 0, "warning_rows": 0, "fallback_rows": 0, "risk_rejection_reasons": {}}
    if path is None or not path.is_file():
        return result
    reasons: dict[str, int] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            result["rows"] += 1
            warning = str(row.get("agent_warnings") or "").strip()
            if warning:
                result["warning_rows"] += 1
            if "fallback" in warning.lower():
                result["fallback_rows"] += 1
            reason = str(row.get("risk_rejection_reason") or "").strip()
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
    result["status"] = "available"
    result["risk_rejection_reasons"] = dict(sorted(reasons.items()))
    return result


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    base = Path(args.base_dir).resolve()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = base / run_dir
    summary_path = run_dir / "summary.json"
    summary = read_json(summary_path)
    metadata = summary.get("metadata", {}) if isinstance(summary.get("metadata"), dict) else {}
    config = redact(metadata.get("config", {}) if isinstance(metadata.get("config"), dict) else {})
    data_metadata = redact(metadata.get("data", {}) if isinstance(metadata.get("data"), dict) else {})

    selected_symbols_path = Path(args.selected_symbols) if args.selected_symbols else None
    if selected_symbols_path and not selected_symbols_path.is_absolute():
        selected_symbols_path = base / selected_symbols_path
    selected_symbols = read_lines(selected_symbols_path)

    input_path = Path(args.input) if args.input else None
    if input_path and not input_path.is_absolute():
        input_path = base / input_path

    requested_files: list[tuple[str, Path, bool]] = []
    for name in DEFAULT_ARTEFACTS:
        requested_files.append((name.replace(".", "_"), run_dir / name, name in {"summary.json", "replication_report.md"}))
    for report in args.report or []:
        path = Path(report)
        if not path.is_absolute():
            path = base / path
        requested_files.append((f"promoted_report_{len(requested_files)}", path, True))

    artefacts = {key: file_record(path, base, required=required) for key, path, required in requested_files}
    audit_path = run_dir / "llm_audit.jsonl"
    pipeline_path = run_dir / "pipeline_log.csv"

    bundle: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "scenario": args.scenario,
        "commit_sha": args.commit_sha,
        "command": args.command,
        "generated_at": args.generated_at,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.system().lower(),
        },
        "run": {
            "directory": relative_path(run_dir, base),
            "summary_status": "available" if summary else "missing",
        },
        "configuration": {
            "effective": config,
            "sha256": canonical_sha256(config),
        },
        "data": {
            "metadata": data_metadata,
            "selected_source_symbols": selected_symbols,
            "selected_source_symbol_count": len(selected_symbols),
            "distinct_base_asset_count": len({base_asset(symbol) for symbol in selected_symbols}),
            "selected_symbols_sha256": canonical_sha256(selected_symbols),
            "input": file_record(input_path, base) if input_path else {"status": "not_supplied"},
        },
        "llm": {
            "provider": args.provider,
            "model": args.model,
            "audit": llm_audit_summary(audit_path),
            "pipeline_diagnostics": pipeline_diagnostics(pipeline_path),
        },
        "artefacts": artefacts,
        "local_only_artefacts": sorted(set(args.local_only_artifact or [])),
        "limitations": sorted(set(args.limitation or [])),
    }
    bundle["bundle_content_sha256"] = canonical_sha256({key: value for key, value in bundle.items() if key != "bundle_content_sha256"})
    return bundle


def verify_bundle(bundle: dict[str, Any], base_dir: Path) -> list[str]:
    errors: list[str] = []
    for key, record in bundle.get("artefacts", {}).items():
        if not isinstance(record, dict) or record.get("status") != "present":
            continue
        path = base_dir / str(record.get("path", ""))
        if not path.is_file():
            errors.append(f"{key}: missing file {record.get('path')}")
            continue
        actual = sha256_file(path)
        if actual != record.get("sha256"):
            errors.append(f"{key}: hash mismatch for {record.get('path')}")
    expected_bundle_hash = bundle.get("bundle_content_sha256")
    actual_bundle_hash = canonical_sha256({key: value for key, value in bundle.items() if key != "bundle_content_sha256"})
    if expected_bundle_hash != actual_bundle_hash:
        errors.append("bundle content hash mismatch")
    return errors


def markdown(bundle: dict[str, Any]) -> str:
    lines = [
        f"# Reproducibility Evidence: {bundle.get('scenario') or 'run'}",
        "",
        f"- Commit: `{bundle.get('commit_sha') or 'unavailable'}`",
        f"- Run directory: `{bundle['run']['directory']}`",
        f"- Configuration digest: `{bundle['configuration']['sha256']}`",
        f"- Selected source symbols: `{bundle['data']['selected_source_symbol_count']}`",
        f"- Distinct base assets: `{bundle['data']['distinct_base_asset_count']}`",
        f"- Bundle digest: `{bundle['bundle_content_sha256']}`",
        "",
        "## Artefacts",
        "",
        "| Artefact | Status | Size | SHA-256 |",
        "| --- | --- | ---: | --- |",
    ]
    for key, record in sorted(bundle["artefacts"].items()):
        lines.append(f"| `{key}` | {record.get('status')} | {record.get('size_bytes', '-')} | `{record.get('sha256', '-')}` |")
    if bundle.get("limitations"):
        lines.extend(["", "## Limitations", ""])
        lines.extend(f"- {item}" for item in bundle["limitations"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir")
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--scenario", default="replication")
    parser.add_argument("--commit-sha", default=None)
    parser.add_argument("--command", default=None)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument("--selected-symbols", default=None)
    parser.add_argument("--input", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--report", action="append", default=[])
    parser.add_argument("--local-only-artifact", action="append", default=[])
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-md", default=None)
    parser.add_argument("--verify", default=None, help="verify an existing evidence JSON instead of building")
    args = parser.parse_args(argv)

    base = Path(args.base_dir).resolve()
    if args.verify:
        path = Path(args.verify)
        if not path.is_absolute():
            path = base / path
        bundle = read_json(path)
        errors = verify_bundle(bundle, base)
        if errors:
            for error in errors:
                print(f"FAIL: {error}", file=sys.stderr)
            return 1
        print("PASS: evidence bundle hashes verified")
        return 0

    if not args.run_dir or not args.out_json:
        parser.error("--run-dir and --out-json are required when building")
    bundle = build_bundle(args)
    output = Path(args.out_json)
    if not output.is_absolute():
        output = base / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_md:
        md = Path(args.out_md)
        if not md.is_absolute():
            md = base / md
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(markdown(bundle), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
