#!/usr/bin/env python3
"""Process one .patch-submission envelope from the patch-submissions branch."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MANIFEST_MARKER = "--- PATCH_SUBMISSION_MANIFEST_JSON ---"
DIFF_MARKER = "--- PATCH_SUBMISSION_UNIFIED_DIFF ---"
ZERO_SHA = "0" * 40


def run(cmd: list[str], *, cwd: Path, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=capture)


def append(path: Path, text: str = "") -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def fail(diag: Path, message: str) -> None:
    append(diag)
    append(diag, "### Failure")
    append(diag, "```text")
    append(diag, message)
    append(diag, "```")
    raise RuntimeError(message)


def detect_submission(repo: Path, before: str, after: str, diag: Path) -> tuple[str, Path]:
    if before == ZERO_SHA:
        result = run(["git", "ls-files", ".patches/inbox/*.patch-submission"], cwd=repo, capture=True)
    else:
        result = run([
            "git", "diff", "--name-only", "--diff-filter=AM", before, after, "--", ".patches/inbox/*.patch-submission"
        ], cwd=repo, capture=True)
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    append(diag, f"Submission envelopes found: {len(files)}")
    for file in files:
        append(diag, f"- `{file}`")
    if len(files) != 1:
        fail(diag, "Exactly one .patch-submission file is supported per push.")
    path = Path(files[0])
    if path.name == ".patch-submission" or not path.name.endswith(".patch-submission"):
        fail(diag, f"Invalid submission filename: {path}")
    return path.name.removesuffix(".patch-submission"), path


def parse_envelope(repo: Path, rel_path: Path, submission_id: str, work: Path, diag: Path) -> dict:
    text = (repo / rel_path).read_text(encoding="utf-8")
    if MANIFEST_MARKER not in text or DIFF_MARKER not in text:
        fail(diag, "Envelope must contain manifest and unified diff markers.")
    header, rest = text.split(MANIFEST_MARKER, 1)
    manifest_text, patch_text = rest.split(DIFF_MARKER, 1)
    if "PATCH_SUBMISSION_SCHEMA_VERSION: 2" not in header.strip():
        fail(diag, "Envelope header must include PATCH_SUBMISSION_SCHEMA_VERSION: 2.")
    patch_text = patch_text.lstrip("\r\n")
    if not patch_text.strip():
        fail(diag, "Unified diff section is empty.")
    try:
        data = json.loads(manifest_text.strip())
    except Exception as exc:  # noqa: BLE001
        fail(diag, f"Invalid manifest JSON: {exc}")
    required = ["schema_version", "issue_number", "base_ref", "implementation_branch", "commit_message", "pr_title"]
    missing = [key for key in required if str(data.get(key, "")).strip() == ""]
    if missing:
        fail(diag, "Missing required field(s): " + ", ".join(missing))
    if str(data["schema_version"]) != "2":
        fail(diag, "schema_version must be 2 for .patch-submission envelopes.")
    data["issue_number"] = int(data["issue_number"])
    if data["issue_number"] <= 0:
        fail(diag, "issue_number must be positive.")
    if str(data["base_ref"]).strip() != "main":
        fail(diag, "Only base_ref=main is supported.")
    branch = str(data["implementation_branch"]).strip()
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
        fail(diag, f"Invalid implementation_branch: {branch}")
    if branch in {"main", "master", "patch-submissions"} or branch.startswith(("/", ".", "refs/")) or branch.endswith("/") or ".." in branch or "//" in branch:
        fail(diag, f"Unsafe implementation_branch: {branch}")
    for field in ("commit_message", "pr_title"):
        value = str(data[field]).strip()
        if "\n" in value or "\r" in value:
            fail(diag, f"{field} must be a single line.")
        data[field] = value
    validation = data.get("validation", []) or []
    if not isinstance(validation, list) or not all(isinstance(item, str) for item in validation):
        fail(diag, "validation must be a list of strings.")
    data["validation"] = validation
    (work / "manifest.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (work / "patch.diff").write_text(patch_text, encoding="utf-8")
    append(diag, "")
    append(diag, "### Manifest")
    append(diag, f"- Submission id: `{submission_id}`")
    append(diag, f"- Issue: #{data['issue_number']}")
    append(diag, f"- Implementation branch: `{branch}`")
    append(diag, f"- Envelope: `{rel_path}`")
    return data


def validate_patch(repo: Path, data: dict, work: Path, diag: Path) -> None:
    patch = work / "patch.diff"
    changed = work / "changed-files.txt"
    run(["git", "fetch", "origin", "main"], cwd=repo)
    main_sha = run(["git", "rev-parse", "origin/main"], cwd=repo, capture=True).stdout.strip()
    append(diag, f"origin/main: `{main_sha}`")
    base_sha = str(data.get("base_sha", "")).strip()
    if base_sha and base_sha != main_sha:
        fail(diag, f"Base SHA mismatch: manifest={base_sha} current={main_sha}")
    run(["git", "checkout", "--detach", "origin/main"], cwd=repo)
    run(["git", "apply", "--check", str(patch)], cwd=repo)
    numstat = run(["git", "apply", "--numstat", str(patch)], cwd=repo, capture=True).stdout
    paths = [line.split("\t")[-1] for line in numstat.splitlines() if line.strip()]
    if not paths:
        fail(diag, "Patch affects no files.")
    changed.write_text("\n".join(paths) + "\n", encoding="utf-8")
    allow_workflow = bool(data.get("allow_workflow_changes", False))
    append(diag, "")
    append(diag, "### Changed files")
    for path in paths:
        append(diag, f"- `{path}`")
        if path.startswith((".patches/", "patches/", "output/", "benchmark_outputs/", "_site/", "data/")) or "/__pycache__/" in path or path.startswith("__pycache__/") or path in {".coverage", ".DS_Store"} or path.endswith((".pyc", ".pyo", ".sqlite", ".db")):
            fail(diag, f"Forbidden generated or broker path: {path}")
        if path.startswith(".git/") or "/.git/" in path or path.startswith("../") or "/../" in path:
            fail(diag, f"Suspicious path: {path}")
        if path.startswith(".github/workflows/") and not allow_workflow:
            fail(diag, f"Workflow change requires allow_workflow_changes=true: {path}")


def create_pr(repo: Path, data: dict, work: Path, diag: Path) -> tuple[str, str]:
    branch = data["implementation_branch"]
    patch = work / "patch.diff"
    changed = work / "changed-files.txt"
    run(["git", "fetch", "origin", "main"], cwd=repo)
    run(["git", "checkout", "-B", branch, "origin/main"], cwd=repo)
    run(["git", "apply", str(patch)], cwd=repo)
    run(["git", "add", "-A"], cwd=repo)
    run(["git", "commit", "-m", data["commit_message"]], cwd=repo)
    run(["git", "push", "--force-with-lease", "origin", branch], cwd=repo)
    body = work / "pr-body.md"
    body_parts = []
    if str(data.get("pr_body", "")).strip():
        body_parts.append(str(data["pr_body"]).strip())
    body_parts.append("---\n\n## Patch submissions broker audit")
    body_parts.append(f"- Source issue: #{data['issue_number']}")
    body_parts.append(f"- Submission id: `{os.environ['SUBMISSION_ID']}`")
    body_parts.append(f"- Workflow run: {os.environ.get('RUN_URL', '')}")
    body_parts.append(f"- Implementation branch: `{branch}`")
    body_parts.append("\nChanged files:")
    for path in changed.read_text(encoding="utf-8").splitlines():
        body_parts.append(f"- `{path}`")
    if data.get("validation"):
        body_parts.append("\nValidation reported by submitting agent:")
        for item in data["validation"]:
            body_parts.append(f"- {item}")
    body.write_text("\n".join(body_parts) + "\n", encoding="utf-8")
    pr_url = run(["gh", "pr", "create", "--base", "main", "--head", branch, "--title", data["pr_title"], "--body-file", str(body)], cwd=repo, capture=True).stdout.strip()
    pr_number = pr_url.rstrip("/").split("/")[-1]
    append(diag, f"PR: {pr_url}")
    return pr_number, pr_url


def archive(repo: Path, submission_id: str, rel_path: Path, work: Path, diag: Path, status: str, data: dict | None = None, pr_url: str = "") -> None:
    run(["git", "fetch", "origin", "patch-submissions"], cwd=repo, check=False)
    run(["git", "checkout", "patch-submissions"], cwd=repo, check=False)
    run(["git", "pull", "--ff-only", "origin", "patch-submissions"], cwd=repo, check=False)
    dest = repo / ".patches" / ("processed" if status == "processed" else "failed") / submission_id
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    source = repo / rel_path
    if source.exists():
        run(["git", "mv", str(rel_path), str(dest.relative_to(repo) / "submission.patch-submission")], cwd=repo, check=False)
    for src_name, dest_name in (("manifest.json", "manifest.json"), ("patch.diff", "patch.diff")):
        src = work / src_name
        if src.exists():
            shutil.copy2(src, dest / dest_name)
    if diag.exists():
        shutil.copy2(diag, dest / "diagnostics.md")
    result = {
        "status": status,
        "submission_id": submission_id,
        "issue_number": int(data.get("issue_number", 0)) if data else 0,
        "implementation_branch": data.get("implementation_branch", "") if data else "",
        "pull_request_url": pr_url,
        "workflow_run_url": os.environ.get("RUN_URL", ""),
    }
    (dest / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run(["git", "add", ".patches"], cwd=repo, check=False)
    run(["git", "commit", "-m", f"Archive patch submission: {submission_id} [{status}] [patch-broker:archive]"], cwd=repo, check=False)
    run(["git", "push", "origin", "HEAD:patch-submissions"], cwd=repo, check=False)


def comment(issue: int, body: str, repo: Path) -> None:
    run(["gh", "issue", "comment", str(issue), "--body", body], cwd=repo, check=False)


def main() -> int:
    repo = Path(os.environ.get("BROKER_REPO", ".")).resolve()
    work = Path(os.environ.get("RUNNER_TEMP", "/tmp")).resolve() / "patch-submission-envelope"
    work.mkdir(parents=True, exist_ok=True)
    diag = work / "diagnostics.md"
    append(diag, "## Patch submissions broker diagnostics")
    append(diag, f"- Repository: {os.environ.get('GITHUB_REPOSITORY', '')}")
    append(diag, f"- Workflow run: {os.environ.get('RUN_URL', '')}")
    data: dict | None = None
    submission_id = ""
    rel_path = Path("")
    try:
        submission_id, rel_path = detect_submission(repo, os.environ["BEFORE_SHA"], os.environ["AFTER_SHA"], diag)
        os.environ["SUBMISSION_ID"] = submission_id
        data = parse_envelope(repo, rel_path, submission_id, work, diag)
        validate_patch(repo, data, work, diag)
        pr_number, pr_url = create_pr(repo, data, work, diag)
        archive(repo, submission_id, rel_path, work, diag, "processed", data, pr_url)
        comment(data["issue_number"], f"Patch submissions broker created PR {pr_number}: {pr_url}", repo)
        return 0
    except Exception as exc:  # noqa: BLE001
        append(diag, f"Unhandled error: {exc}")
        if submission_id:
            archive(repo, submission_id, rel_path, work, diag, "failed", data)
        if data and data.get("issue_number"):
            body = "Patch submissions broker failed.\n\n" + diag.read_text(encoding="utf-8")[:12000]
            comment(int(data["issue_number"]), body, repo)
        return 1


if __name__ == "__main__":
    sys.exit(main())
