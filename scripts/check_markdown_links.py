#!/usr/bin/env python3
"""Validate repository-local Markdown links without making network requests."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
DEFAULT_IGNORES = (".git/", ".patches/", "data/", "replication/results", "validation/results")


def markdown_files(root: Path) -> list[Path]:
    files = [root / "README.md"] if (root / "README.md").is_file() else []
    files.extend(sorted((root / "docs").rglob("*.md")) if (root / "docs").is_dir() else [])
    return files


def strip_code_fences(text: str) -> str:
    output: list[str] = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if match:
            current = match.group(1)
            if not in_fence:
                in_fence = True
                marker = current
            elif current == marker:
                in_fence = False
                marker = ""
            output.append("")
        elif in_fence:
            output.append("")
        else:
            output.append(line)
    return "\n".join(output)


def github_anchor(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value.strip().lower())
    value = re.sub(r"[^\w\- ]", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def anchors(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    result: set[str] = set()
    for line in strip_code_fences(path.read_text(encoding="utf-8")).splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = github_anchor(match.group(1))
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.add(base if count == 0 else f"{base}-{count}")
    return result


def normalise_destination(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]
    # Remove an optional quoted Markdown title after the URL.
    match = re.match(r"^(\S+)(?:\s+[\"'].*[\"'])?$", value)
    return unquote(match.group(1) if match else value)


def resolve_target(source: Path, destination: str, root: Path) -> tuple[Path | None, str | None]:
    parsed = urlparse(destination)
    if parsed.scheme or destination.startswith("//"):
        return None, None
    if destination.startswith("#"):
        return source, destination[1:]

    path_part, _, anchor = destination.partition("#")
    path_part = path_part.split("?", 1)[0]
    if not path_part:
        return source, anchor or None
    if path_part.startswith("/"):
        target = root / path_part.lstrip("/")
    else:
        target = source.parent / path_part
    target = target.resolve()

    # Staged Wiki pages use extensionless sibling links.
    if source.parent == (root / "docs" / "wiki").resolve() and not target.exists() and not target.suffix:
        markdown_target = target.with_suffix(".md")
        if markdown_target.exists():
            target = markdown_target
    return target, anchor or None


def check_file(path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    text = strip_code_fences(path.read_text(encoding="utf-8"))
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in LINK_RE.finditer(line):
            destination = normalise_destination(match.group(1))
            if not destination or destination.startswith(("mailto:", "tel:", "javascript:")):
                continue
            target, anchor = resolve_target(path.resolve(), destination, root.resolve())
            if target is None:
                continue
            try:
                target.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{path.relative_to(root)}:{line_number}: link escapes repository: {destination}")
                continue
            if not target.exists():
                errors.append(f"{path.relative_to(root)}:{line_number}: missing target: {destination}")
                continue
            if anchor and target.is_file() and target.suffix.lower() == ".md":
                if github_anchor(anchor) not in anchors(target):
                    errors.append(f"{path.relative_to(root)}:{line_number}: missing anchor: {destination}")
    return errors


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for path in markdown_files(root):
        relative = path.relative_to(root).as_posix()
        if any(relative.startswith(prefix) for prefix in DEFAULT_IGNORES):
            continue
        errors.extend(check_file(path, root))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root")
    args = parser.parse_args(argv)
    errors = check_repository(args.root.resolve())
    if errors:
        print("Markdown link validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Markdown link validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
