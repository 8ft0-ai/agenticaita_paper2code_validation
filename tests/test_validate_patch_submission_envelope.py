from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_patch_submission_envelope import ValidationError, parse_envelope_text


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_patch_submission_envelope.py"


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout


def init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "test@example.com")
    run_git(repo, "config", "user.name", "Test User")
    (repo / "example.txt").write_text("before\n", encoding="utf-8")
    run_git(repo, "add", "example.txt")
    run_git(repo, "commit", "-m", "base")
    return repo, run_git(repo, "rev-parse", "HEAD").strip()


def write_envelope(path: Path, *, base_sha: str, patch_text: str) -> None:
    manifest = {
        "schema_version": 2,
        "issue_number": 112,
        "base_ref": "main",
        "base_sha": base_sha,
        "implementation_branch": "feature/112-validator",
        "commit_message": "Add validator",
        "pr_title": "Add validator",
        "validation": [],
    }
    path.write_text(
        "PATCH_SUBMISSION_SCHEMA_VERSION: 2\n"
        "--- PATCH_SUBMISSION_MANIFEST_JSON ---\n"
        f"{json.dumps(manifest, indent=2)}\n"
        "--- PATCH_SUBMISSION_UNIFIED_DIFF ---\n"
        f"{patch_text}",
        encoding="utf-8",
    )


def test_parse_envelope_requires_final_patch_newline() -> None:
    text = (
        "PATCH_SUBMISSION_SCHEMA_VERSION: 2\n"
        "--- PATCH_SUBMISSION_MANIFEST_JSON ---\n"
        '{"schema_version":2,"issue_number":112,"base_ref":"main","implementation_branch":"feature/112-validator","commit_message":"Add validator","pr_title":"Add validator"}\n'
        "--- PATCH_SUBMISSION_UNIFIED_DIFF ---\n"
        "diff --git a/example.txt b/example.txt"
    )

    with pytest.raises(ValidationError, match="must end with a newline"):
        parse_envelope_text(text)


def test_validator_accepts_patch_extracted_from_envelope(tmp_path: Path) -> None:
    repo, base_sha = init_repo(tmp_path)
    (repo / "example.txt").write_text("after\n", encoding="utf-8")
    patch_text = run_git(repo, "diff", "--binary")
    assert patch_text.endswith("\n")
    run_git(repo, "checkout", "--", "example.txt")
    envelope = repo / "submission.patch-submission"
    write_envelope(envelope, base_sha=base_sha, patch_text=patch_text)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(envelope), "--repo-root", str(repo), "--base-ref", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "PASS: envelope patch applies cleanly" in result.stdout
    assert "example.txt" in result.stdout


def test_validator_surfaces_git_apply_error(tmp_path: Path) -> None:
    repo, base_sha = init_repo(tmp_path)
    bad_patch = """diff --git a/example.txt b/example.txt
index 4afc7d4..9652283 100644
--- a/example.txt
+++ b/example.txt
@@ -1 +1 @@
-not-present
+after
"""
    envelope = repo / "bad.patch-submission"
    write_envelope(envelope, base_sha=base_sha, patch_text=bad_patch)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(envelope), "--repo-root", str(repo), "--base-ref", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "git apply --check" in result.stderr
    assert "stderr:" in result.stderr
