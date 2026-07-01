"""Compare local app files with the Streamlit deploy source."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEPLOY_SOURCE = REPO_ROOT / "outputs" / "streamlit_deploy_source"

REQUIRED_PATTERNS = [
    "app.py",
    "requirements.txt",
    "README.md",
    "src/**/*.py",
    "config/*.yaml",
    "data/sample/*.csv",
    ".streamlit/config.toml",
]
OPTIONAL_PATTERNS = [
    "config/gate_audit_catalog.yaml",
    "AGENTS.md",
    "docs/*.md",
    "tools/*.py",
]
OPTIONAL_TRACE_FILES = {"config/gate_audit_catalog.yaml"}
SENSITIVE_FILENAMES = {".env", "secrets.toml"}
SENSITIVE_SUFFIXES = {".key"}
EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "audit_submit",
    "outputs",
    "latest",
    "archive_old_format",
    "archive_invalid",
    "history",
}

RESULT_PASS = "PASS"
RESULT_CONDITIONAL = "CONDITIONAL_PASS"
RESULT_FAIL = "FAIL"
RESULT_BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class GitCommandResult:
    """Small subprocess result wrapper used for testable Git calls."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    unavailable: bool = False


GitRunner = Callable[[Sequence[str], Path, int], GitCommandResult]


def check_deploy_traceability(
    local_root: Path | str | None = None,
    deploy_source: Path | str | None = None,
    *,
    verify_remote: bool = True,
    git_runner: GitRunner | None = None,
) -> dict[str, Any]:
    """Return a structured L3/L4 deployment traceability report."""
    root = Path(local_root).resolve() if local_root is not None else REPO_ROOT
    deploy = (
        Path(deploy_source).resolve()
        if deploy_source is not None
        else DEFAULT_DEPLOY_SOURCE
    )
    runner = git_runner or run_git_command

    comparison = compare_core_files(root, deploy)
    git_status = inspect_deploy_git(deploy, verify_remote=verify_remote, git_runner=runner)
    l3_result, l4_result, recommendation = decide_release_results(comparison, git_status)

    return {
        "local_root": str(root),
        "deploy_source": str(deploy),
        "required_patterns": REQUIRED_PATTERNS,
        "optional_patterns": OPTIONAL_PATTERNS,
        "compared_files_count": comparison["compared_files_count"],
        "hash_match": comparison["hash_match"],
        "mismatched_files": comparison["mismatched_files"],
        "optional_mismatched_files": comparison["optional_mismatched_files"],
        "missing_required_files": comparison["missing_required_files"],
        "optional_missing_files": comparison["optional_missing_files"],
        "deploy_git_available": git_status["deploy_git_available"],
        "deploy_branch": git_status["deploy_branch"],
        "deploy_head": git_status["deploy_head"],
        "deploy_remote": git_status["deploy_remote"],
        "deploy_dirty": git_status["deploy_dirty"],
        "deploy_dirty_count": git_status["deploy_dirty_count"],
        "remote_head_verified": git_status["remote_head_verified"],
        "remote_head_error_type": git_status["remote_head_error_type"],
        "remote_head_error": git_status["remote_head_error"],
        "l3_result": l3_result,
        "l4_result": l4_result,
        "recommendation": recommendation,
    }


def compare_core_files(local_root: Path | str, deploy_source: Path | str) -> dict[str, Any]:
    """Hash local and deploy files without reading excluded sensitive paths."""
    local = Path(local_root)
    deploy = Path(deploy_source)
    if not local.is_dir() or not deploy.is_dir():
        missing = []
        if not local.is_dir():
            missing.append("local_root")
        if not deploy.is_dir():
            missing.append("deploy_source")
        return {
            "compared_files_count": 0,
            "hash_match": False,
            "mismatched_files": [],
            "optional_mismatched_files": [],
            "missing_required_files": missing,
            "optional_missing_files": [],
        }

    local_required_all = collect_files(local, REQUIRED_PATTERNS)
    deploy_required_all = collect_files(deploy, REQUIRED_PATTERNS)
    local_required = {
        path: value
        for path, value in local_required_all.items()
        if path not in OPTIONAL_TRACE_FILES
    }
    deploy_required = {
        path: value
        for path, value in deploy_required_all.items()
        if path not in OPTIONAL_TRACE_FILES
    }
    local_optional = collect_files(local, OPTIONAL_PATTERNS)
    deploy_optional = collect_files(deploy, OPTIONAL_PATTERNS)
    local_optional.update(
        {
            path: value
            for path, value in local_required_all.items()
            if path in OPTIONAL_TRACE_FILES
        }
    )
    deploy_optional.update(
        {
            path: value
            for path, value in deploy_required_all.items()
            if path in OPTIONAL_TRACE_FILES
        }
    )

    required_paths = sorted(set(local_required) | set(deploy_required))
    optional_common_paths = sorted(set(local_optional) & set(deploy_optional))
    optional_missing_paths = sorted(set(local_optional) ^ set(deploy_optional))

    mismatched_files: list[str] = []
    optional_mismatched_files: list[str] = []
    missing_required_files: list[str] = []
    compared_count = 0
    for relative_path in required_paths:
        local_path = local_required.get(relative_path) or local_optional.get(relative_path)
        deploy_path = deploy_required.get(relative_path) or deploy_optional.get(relative_path)
        if local_path is None or deploy_path is None:
            missing_required_files.append(relative_path)
            continue

        compared_count += 1
        if sha256_file(local_path) != sha256_file(deploy_path):
            mismatched_files.append(relative_path)

    for relative_path in optional_common_paths:
        local_path = local_optional[relative_path]
        deploy_path = deploy_optional[relative_path]
        compared_count += 1
        if sha256_file(local_path) != sha256_file(deploy_path):
            optional_mismatched_files.append(relative_path)

    hash_match = not mismatched_files and not missing_required_files
    return {
        "compared_files_count": compared_count,
        "hash_match": hash_match,
        "mismatched_files": mismatched_files,
        "optional_mismatched_files": optional_mismatched_files,
        "missing_required_files": missing_required_files,
        "optional_missing_files": optional_missing_paths,
    }


def collect_files(root: Path | str, patterns: Sequence[str]) -> dict[str, Path]:
    """Collect candidate files by relative path with sensitive exclusions."""
    base = Path(root)
    files: dict[str, Path] = {}
    for pattern in patterns:
        matches = base.glob(pattern)
        for path in matches:
            if not path.is_file() or should_exclude(path, base):
                continue
            relative_path = path.resolve().relative_to(base.resolve()).as_posix()
            files[relative_path] = path
    return dict(sorted(files.items()))


def should_exclude(path: Path, root: Path) -> bool:
    """Return True for caches, generated outputs, and sensitive file paths."""
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    parts = set(relative.parts)
    if parts & EXCLUDED_PARTS:
        return True
    lowered_name = path.name.lower()
    if lowered_name in SENSITIVE_FILENAMES:
        return True
    if path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    return False


def inspect_deploy_git(
    deploy_source: Path | str,
    *,
    verify_remote: bool,
    git_runner: GitRunner,
) -> dict[str, Any]:
    """Inspect deploy Git metadata without mutating the repository."""
    deploy = Path(deploy_source)
    base = {
        "deploy_git_available": False,
        "deploy_branch": None,
        "deploy_head": None,
        "deploy_remote": None,
        "deploy_dirty": None,
        "deploy_dirty_count": None,
        "remote_head_verified": False,
        "remote_head_error_type": None,
        "remote_head_error": None,
    }
    if not deploy.is_dir():
        base["remote_head_error_type"] = "DEPLOY_SOURCE_MISSING"
        return base

    inside = git_runner(["rev-parse", "--is-inside-work-tree"], deploy, 10)
    if inside.unavailable:
        base["remote_head_error_type"] = "GIT_UNAVAILABLE"
        return base
    if inside.returncode != 0 or inside.stdout.strip().lower() != "true":
        base["remote_head_error_type"] = "NOT_A_GIT_REPOSITORY"
        return base

    base["deploy_git_available"] = True
    branch = git_runner(["branch", "--show-current"], deploy, 10)
    if branch.returncode == 0:
        base["deploy_branch"] = _none_if_empty(branch.stdout.strip())

    head = git_runner(["rev-parse", "HEAD"], deploy, 10)
    if head.returncode == 0:
        base["deploy_head"] = _none_if_empty(head.stdout.strip())

    remote = git_runner(["remote", "get-url", "origin"], deploy, 10)
    if remote.returncode == 0:
        base["deploy_remote"] = sanitize_text(_none_if_empty(remote.stdout.strip()))

    status = git_runner(["status", "--short", "--untracked-files=all"], deploy, 10)
    if status.returncode == 0:
        status_lines = [line for line in status.stdout.splitlines() if line.strip()]
        base["deploy_dirty"] = bool(status_lines)
        base["deploy_dirty_count"] = len(status_lines)

    if verify_remote:
        remote_check = verify_remote_head(
            deploy,
            branch=str(base["deploy_branch"] or ""),
            remote_name="origin",
            git_runner=git_runner,
        )
        base.update(remote_check)
    return base


def verify_remote_head(
    deploy_source: Path,
    *,
    branch: str,
    remote_name: str,
    git_runner: GitRunner,
) -> dict[str, Any]:
    """Try to verify remote HEAD and classify network/TLS failures safely."""
    if not branch:
        return {
            "remote_head_verified": False,
            "remote_head_error_type": "NO_DEPLOY_BRANCH",
            "remote_head_error": "Deploy branch could not be determined.",
        }

    result = git_runner(["ls-remote", "--heads", remote_name, branch], deploy_source, 20)
    if result.returncode == 0 and result.stdout.strip():
        return {
            "remote_head_verified": True,
            "remote_head_error_type": None,
            "remote_head_error": None,
        }

    error_text = sanitize_text("\n".join([result.stdout, result.stderr]).strip())
    return {
        "remote_head_verified": False,
        "remote_head_error_type": classify_remote_error(result, error_text),
        "remote_head_error": _trim(error_text),
    }


def decide_release_results(
    comparison: dict[str, Any],
    git_status: dict[str, Any],
) -> tuple[str, str, list[str]]:
    """Apply L3 and L4 interpretation rules."""
    recommendations: list[str] = []
    if not comparison["hash_match"]:
        recommendations.append("Resolve local/deploy core file hash mismatch before pilot use.")
        return RESULT_FAIL, RESULT_FAIL, recommendations

    if not git_status["deploy_git_available"]:
        recommendations.append("Deploy source Git metadata is unavailable; confirm deployment provenance.")
        return RESULT_CONDITIONAL, RESULT_FAIL, recommendations

    dirty = bool(git_status["deploy_dirty"])
    remote_verified = bool(git_status["remote_head_verified"])
    if dirty:
        recommendations.append("Deploy source has uncommitted or untracked changes; L3 may proceed only as a known warning.")
    if not remote_verified:
        recommendations.append("Remote HEAD was not verified; record the blocker before L4 release.")

    l3_result = RESULT_CONDITIONAL if dirty or not remote_verified else RESULT_PASS
    l4_result = RESULT_PASS if not dirty and remote_verified else RESULT_FAIL
    if l4_result != RESULT_PASS:
        recommendations.append("L4 release requires clean deploy source and verified remote HEAD.")
    return l3_result, l4_result, recommendations


def run_git_command(args: Sequence[str], cwd: Path, timeout: int) -> GitCommandResult:
    """Run a read-only Git command and capture output."""
    git_executable = resolve_git_executable()
    if git_executable is None:
        return GitCommandResult(127, "", "git executable not found", unavailable=True)
    try:
        completed = subprocess.run(  # noqa: S603 - args are fixed by this tool.
            [git_executable, *args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return GitCommandResult(
            124,
            sanitize_text(exc.stdout or ""),
            sanitize_text(exc.stderr or ""),
            timed_out=True,
        )
    return GitCommandResult(
        completed.returncode,
        sanitize_text(completed.stdout),
        sanitize_text(completed.stderr),
    )


def resolve_git_executable() -> str | None:
    """Find Git from PATH or the bundled portable Git next to the workspace."""
    from_path = shutil.which("git")
    if from_path:
        return from_path
    portable_git = REPO_ROOT.parent / ".portablegit" / "cmd" / "git.exe"
    if portable_git.is_file():
        return str(portable_git)
    return None


def sha256_file(path: Path) -> str:
    """Return a file hash without logging contents."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_text(value: str | None) -> str | None:
    """Remove credentials from URLs that Git may print."""
    if value is None:
        return None
    text = re.sub(r"://[^/@\s]+@+", "://***@", str(value))
    text = re.sub(r"://([^:/@\s]+):[^/@\s]+@", r"://\1:***@", text)
    return text


def classify_remote_error(result: GitCommandResult, error_text: str | None) -> str:
    """Map Git remote failures to stable audit categories."""
    lowered = (error_text or "").lower()
    if result.unavailable:
        return "GIT_UNAVAILABLE"
    if result.timed_out:
        return "TIMEOUT"
    if "ssl" in lowered or "tls" in lowered or "certificate" in lowered:
        return "BLOCKED_REMOTE_HEAD_TLS"
    if "could not resolve" in lowered or "failed to connect" in lowered:
        return "BLOCKED_REMOTE_HEAD_NETWORK"
    if "authentication" in lowered or "permission denied" in lowered:
        return "BLOCKED_REMOTE_HEAD_AUTH"
    return "BLOCKED_REMOTE_HEAD"


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Check deploy traceability for L3/L4.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--l3", action="store_true", help="Use L3 pilot exit semantics.")
    mode.add_argument("--l4", action="store_true", help="Use L4 release exit semantics.")
    args = parser.parse_args(argv)

    result = check_deploy_traceability()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text_result(result))

    selected_result = result["l4_result"] if args.l4 else result["l3_result"]
    if args.l4:
        return 0 if selected_result == RESULT_PASS else 1
    return 0 if selected_result in {RESULT_PASS, RESULT_CONDITIONAL} else 1


def format_text_result(result: dict[str, Any]) -> str:
    """Return a compact non-sensitive traceability report."""
    lines = [
        f"deploy_traceability_l3: {result['l3_result']}",
        f"deploy_traceability_l4: {result['l4_result']}",
        f"hash_match: {result['hash_match']}",
        f"compared_files_count: {result['compared_files_count']}",
        f"mismatched_files: {len(result['mismatched_files'])}",
        f"optional_mismatched_files: {len(result['optional_mismatched_files'])}",
        f"missing_required_files: {len(result['missing_required_files'])}",
        f"deploy_git_available: {result['deploy_git_available']}",
        f"deploy_branch: {result['deploy_branch'] or 'unknown'}",
        f"deploy_head: {result['deploy_head'] or 'unknown'}",
        f"deploy_dirty: {result['deploy_dirty']}",
        f"remote_head_verified: {result['remote_head_verified']}",
        f"remote_head_error_type: {result['remote_head_error_type'] or 'none'}",
    ]
    if result["mismatched_files"]:
        lines.append("mismatched_files:")
        lines.extend(f"  - {path}" for path in result["mismatched_files"])
    if result["optional_mismatched_files"]:
        lines.append("optional_mismatched_files:")
        lines.extend(f"  - {path}" for path in result["optional_mismatched_files"])
    if result["missing_required_files"]:
        lines.append("missing_required_files:")
        lines.extend(f"  - {path}" for path in result["missing_required_files"])
    if result["optional_missing_files"]:
        lines.append("optional_missing_files:")
        lines.extend(f"  - {path}" for path in result["optional_missing_files"])
    if result["recommendation"]:
        lines.append("recommendation:")
        lines.extend(f"  - {item}" for item in result["recommendation"])
    return "\n".join(lines)


def _none_if_empty(value: str) -> str | None:
    return value or None


def _trim(value: str | None, limit: int = 500) -> str | None:
    if not value:
        return None
    compact = " ".join(str(value).split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
