from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_markdown_links", ROOT / "scripts" / "check_markdown_links.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_relative_link_and_anchor_pass(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "[Guide](docs/guide.md#details)\n")
    write(tmp_path / "docs" / "guide.md", "# Guide\n\n## Details\n")
    assert MODULE.check_repository(tmp_path) == []


def test_missing_target_and_anchor_fail(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "[Missing](docs/missing.md)\n[Bad anchor](docs/guide.md#absent)\n")
    write(tmp_path / "docs" / "guide.md", "# Guide\n")
    errors = MODULE.check_repository(tmp_path)
    assert any("missing target" in error for error in errors)
    assert any("missing anchor" in error for error in errors)


def test_wiki_extensionless_links_resolve_to_sibling_markdown(tmp_path: Path) -> None:
    write(tmp_path / "docs" / "wiki" / "Home.md", "[Runbook](Runbook)\n")
    write(tmp_path / "docs" / "wiki" / "Runbook.md", "# Runbook\n")
    assert MODULE.check_repository(tmp_path) == []


def test_external_links_and_fenced_examples_are_ignored(tmp_path: Path) -> None:
    write(
        tmp_path / "README.md",
        "[External](https://example.com/docs)\n\n```markdown\n[Example](missing.md)\n```\n",
    )
    assert MODULE.check_repository(tmp_path) == []


def test_link_cannot_escape_repository(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "[Outside](../outside.md)\n")
    errors = MODULE.check_repository(tmp_path)
    assert len(errors) == 1
    assert "escapes repository" in errors[0]


def test_generated_paths_are_not_scanned(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Home\n")
    write(tmp_path / "replication" / "results_local" / "report.md", "[Broken](missing.md)\n")
    assert MODULE.check_repository(tmp_path) == []
