from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "docs" / "guides" / "bootstrap_paper_project.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_paper_project", SCRIPT)
assert SPEC and SPEC.loader
bootstrap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bootstrap
SPEC.loader.exec_module(bootstrap)


def args(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "--project-dir",
        str(tmp_path / "project"),
        "--title",
        "Example Paper",
        "--arxiv-id",
        "2501.01234",
        "--paper-version",
        "v2",
        *extra,
    ]


def test_identifier_and_version_validation() -> None:
    assert bootstrap.validate_arxiv_id("2501.01234") == "2501.01234"
    assert bootstrap.validate_arxiv_id("hep-th/9901001") == "hep-th/9901001"
    assert bootstrap.validate_paper_version("V3") == "v3"
    with pytest.raises(Exception):
        bootstrap.validate_arxiv_id("not-an-id")
    with pytest.raises(Exception):
        bootstrap.validate_paper_version("latest")


def test_scaffold_uses_canonical_templates_and_renders_metadata(tmp_path: Path) -> None:
    assert bootstrap.main(args(tmp_path, "--with-issue-specs", "--with-ci")) == 0
    root = tmp_path / "project"
    ledger = (root / "docs/claims/claim_ledger.csv").read_text(encoding="utf-8")
    assert "paper_version" in ledger
    assert "v2" in ledger
    assert (root / "PROJECT_PROFILE.md").is_file()
    assert (root / "docs/decisions/gate_log.md").is_file()
    assert (root / "docs/review/final_independent_review.md").is_file()
    assert (root / "docs/issues/07-independent-review.md").is_file()
    workflow = (root / ".github/workflows/validation-smoke.yml").read_text(encoding="utf-8")
    assert "find tests -type f -name 'test_*.py'" in workflow
    manifest = json.loads((root / ".paper-validation-scaffold.json").read_text(encoding="utf-8"))
    assert manifest["scaffold_version"] == bootstrap.SCAFFOLD_VERSION
    assert "docs/claims/claim_ledger.csv" in manifest["generated_files"]


def test_non_empty_directory_requires_explicit_mode(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "owned.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit, match="non-empty"):
        bootstrap.main(args(tmp_path))


def test_update_missing_preserves_existing_files(tmp_path: Path) -> None:
    assert bootstrap.main(args(tmp_path)) == 0
    root = tmp_path / "project"
    readme = root / "README.md"
    readme.write_text("user-owned\n", encoding="utf-8")
    (root / "PROJECT_PROFILE.md").unlink()
    assert bootstrap.main(args(tmp_path, "--update-missing")) == 0
    assert readme.read_text(encoding="utf-8") == "user-owned\n"
    assert (root / "PROJECT_PROFILE.md").is_file()


def test_force_replaces_generated_paths(tmp_path: Path) -> None:
    assert bootstrap.main(args(tmp_path)) == 0
    readme = tmp_path / "project/README.md"
    readme.write_text("changed", encoding="utf-8")
    assert bootstrap.main(args(tmp_path, "--force")) == 0
    assert readme.read_text(encoding="utf-8").startswith("# Example Paper")


def test_dry_run_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert bootstrap.main(args(tmp_path, "--dry-run")) == 0
    assert not (tmp_path / "project").exists()
    output = capsys.readouterr().out
    assert "Planned files:" in output
    assert "docs/claims/claim_ledger.csv" in output


def test_missing_required_template_fails_clearly(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    with pytest.raises(SystemExit, match="Missing required templates"):
        bootstrap.main(args(tmp_path, "--template-dir", str(template_dir)))


def test_paper_version_is_required(tmp_path: Path) -> None:
    argv = [
        "--project-dir",
        str(tmp_path / "project"),
        "--title",
        "Example Paper",
        "--arxiv-id",
        "2501.01234",
    ]
    with pytest.raises(SystemExit):
        bootstrap.parse_args(argv)
