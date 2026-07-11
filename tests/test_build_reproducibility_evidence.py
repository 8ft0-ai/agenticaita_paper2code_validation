from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.build_reproducibility_evidence import build_bundle, redact, verify_bundle


def args_for(root: Path, run_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        base_dir=str(root),
        run_dir=str(run_dir),
        scenario="deterministic_76_asset",
        commit_sha="abc123",
        command="python replication/replicate.py",
        generated_at="2026-07-11T00:00:00Z",
        selected_symbols=str(root / "symbols.txt"),
        input=str(root / "input.csv"),
        provider=None,
        model=None,
        report=[str(root / "docs" / "report.md")],
        local_only_artifact=["market_data.sqlite", "raw OHLCV"],
        limitation=["Original author artefacts unavailable"],
    )


def prepare(root: Path) -> Path:
    run_dir = root / "run"
    run_dir.mkdir()
    (root / "docs").mkdir()
    (root / "symbols.txt").write_text("BTC/USDT:USDT\nETH/USDT:USDT\n", encoding="utf-8")
    (root / "input.csv").write_text("timestamp,asset,close\nt1,BTC,100\nt2,BTC,101\n", encoding="utf-8")
    (root / "docs" / "report.md").write_text("# Report\n", encoding="utf-8")
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "config": {
                        "llm": {"api_key": "secret", "api_key_env": "OPENROUTER_API_KEY", "model": "test"},
                        "output_dir": "/tmp/private/run",
                    },
                    "data": {"asset_count": 2, "candle_count": 2},
                },
                "summary": {"trades_executed": 1},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "replication_report.md").write_text("# Replication\n", encoding="utf-8")
    (run_dir / "pipeline_log.csv").write_text(
        "event,agent_warnings,risk_rejection_reason\ntrigger_admitted,LLM fallback,confidence_below_gate\n",
        encoding="utf-8",
    )
    return run_dir


def test_bundle_is_stable_and_redacts_secrets_and_private_paths(tmp_path: Path) -> None:
    run_dir = prepare(tmp_path)
    args = args_for(tmp_path, run_dir)

    first = build_bundle(args)
    second = build_bundle(args)

    assert first == second
    assert first["configuration"]["effective"]["llm"]["api_key"] == "[REDACTED]"
    assert first["configuration"]["effective"]["llm"]["api_key_env"] == "[REDACTED]"
    assert first["configuration"]["effective"]["output_dir"] == "run"
    assert "/tmp/private" not in json.dumps(first)
    assert first["data"]["selected_source_symbol_count"] == 2
    assert first["data"]["distinct_base_asset_count"] == 2
    assert first["llm"]["pipeline_diagnostics"]["fallback_rows"] == 1


def test_missing_optional_artefacts_are_recorded_not_fabricated(tmp_path: Path) -> None:
    run_dir = prepare(tmp_path)
    bundle = build_bundle(args_for(tmp_path, run_dir))

    assert bundle["artefacts"]["trades_csv"]["status"] == "missing"
    assert "sha256" not in bundle["artefacts"]["trades_csv"]
    assert bundle["llm"]["audit"]["status"] == "missing"


def test_verification_detects_changed_artefact(tmp_path: Path) -> None:
    run_dir = prepare(tmp_path)
    bundle = build_bundle(args_for(tmp_path, run_dir))

    assert verify_bundle(bundle, tmp_path) == []
    (run_dir / "summary.json").write_text("{}\n", encoding="utf-8")
    errors = verify_bundle(bundle, tmp_path)

    assert any("hash mismatch" in error for error in errors)


def test_recursive_redaction_preserves_non_secret_values() -> None:
    value = redact({"token": "abc", "nested": [{"password": "p", "model": "qwen"}]})
    assert value == {"nested": [{"model": "qwen", "password": "[REDACTED]"}], "token": "[REDACTED]"}
