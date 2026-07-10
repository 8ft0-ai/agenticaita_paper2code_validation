from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from llm_live_smoke import SMOKE_PRICES, build_smoke_input


def test_smoke_input_stays_tiny(tmp_path: Path) -> None:
    df = build_smoke_input(tmp_path / "input.csv")

    assert len(df) == len(SMOKE_PRICES)
    assert len(df) <= 5


def test_live_smoke_skips_cleanly_without_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    replication_root = Path(__file__).resolve().parents[1]
    out_dir = tmp_path / "skip"

    result = subprocess.run(
        [sys.executable, "llm_live_smoke.py", "--config", "config.yaml", "--out", str(out_dir), "--skip-without-key"],
        cwd=replication_root,
        check=True,
        capture_output=True,
        text=True,
    )

    status = json.loads((out_dir / "smoke_status.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert status["status"] == "skipped_missing_api_key"
    assert status["live_provider_available"] is False
    assert (out_dir / "llm_audit.jsonl").exists()


def test_live_smoke_without_key_runs_deterministic_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    replication_root = Path(__file__).resolve().parents[1]
    out_dir = tmp_path / "fallback"

    result = subprocess.run(
        [sys.executable, "llm_live_smoke.py", "--config", "config.yaml", "--out", str(out_dir)],
        cwd=replication_root,
        check=True,
        capture_output=True,
        text=True,
    )

    status = json.loads((out_dir / "smoke_status.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert status["status"] == "fallback_without_api_key"
    assert status["pipeline_rows"] >= 1
    assert status["agent_warning_rows"] >= 1
    assert (out_dir / "pipeline_log.csv").exists()
    assert (out_dir / "llm_audit.jsonl").exists()
