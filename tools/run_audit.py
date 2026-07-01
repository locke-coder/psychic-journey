"""Run audit gates and persist their logs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = REPO_ROOT / "audit" / "logs"
SUPPORTED_GATES = ("ALL", "G09", "G10", "G12", "G13", "G15", "G18")
RESULT_LIST_KEYS = (
    "required_files_missing",
    "required_keywords_missing",
    "forbidden_patterns_found",
    "warnings",
    "errors",
)


def normalize_gate(gate: str) -> str:
    """Normalize and validate a supported audit gate id."""
    normalized = str(gate).upper()
    if normalized not in SUPPORTED_GATES:
        supported = ", ".join(SUPPORTED_GATES)
        raise ValueError(f"Unsupported gate: {gate}. Supported gates: {supported}.")
    return normalized


def ensure_log_dir(
    log_dir: Path | str | None = None,
    *,
    repo_root: Path | str | None = None,
) -> Path:
    """Create the audit log directory if needed and return it."""
    path = _resolve_log_dir(log_dir, repo_root=repo_root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def gate_log_path(
    gate: str,
    log_dir: Path | str | None = None,
    *,
    repo_root: Path | str | None = None,
) -> Path:
    """Return the JSON log path for a gate runner invocation."""
    normalized = normalize_gate(gate)
    return ensure_log_dir(log_dir, repo_root=repo_root) / f"gate_runner_{normalized}.json"


def pytest_log_path(
    log_dir: Path | str | None = None,
    *,
    repo_root: Path | str | None = None,
) -> Path:
    """Return the pytest text log path."""
    return ensure_log_dir(log_dir, repo_root=repo_root) / "pytest_result.txt"


def run_gate_runner(
    gate: str,
    *,
    repo_root: Path | str | None = None,
    log_dir: Path | str | None = None,
    runner_path: Path | str | None = None,
) -> dict[str, Any]:
    """Execute tools/gate_runner.py and always write a structured JSON log."""
    normalized = normalize_gate(gate)
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    runner = Path(runner_path) if runner_path is not None else root / "tools" / "gate_runner.py"
    output_path = gate_log_path(normalized, log_dir, repo_root=root)
    command = [sys.executable, str(runner), normalized]

    try:
        completed = subprocess.run(  # noqa: S603 - command is built from fixed paths.
            command,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        result = _parse_gate_runner_output(normalized, completed)
    except Exception as exc:  # noqa: BLE001 - audit logs must survive runner errors.
        result = _failure_result(
            normalized,
            f"gate_runner execution failed: {type(exc).__name__}: {exc}",
        )

    write_json_log(result, output_path)
    return result


def run_pytest_capture(
    *,
    repo_root: Path | str | None = None,
    log_dir: Path | str | None = None,
    pytest_args: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Run pytest and persist stdout/stderr to audit/logs/pytest_result.txt."""
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    output_path = pytest_log_path(log_dir, repo_root=root)
    command = [sys.executable, "-m", "pytest", "-q", *(pytest_args or ())]

    try:
        completed = subprocess.run(  # noqa: S603 - pytest args are caller-controlled.
            command,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = _combined_output(completed.stdout, completed.stderr)
        if not output:
            output = f"pytest completed with exit code {completed.returncode}"
        output_path.write_text(_with_trailing_newline(output), encoding="utf-8")
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "log_path": str(output_path),
        }
    except Exception as exc:  # noqa: BLE001 - audit logs must survive pytest errors.
        message = f"pytest execution failed: {type(exc).__name__}: {exc}"
        output_path.write_text(message + "\n", encoding="utf-8")
        return {
            "status": "FAIL",
            "returncode": None,
            "log_path": str(output_path),
            "errors": [message],
        }


def run_audit(
    gate: str,
    *,
    capture_pytest: bool = False,
    repo_root: Path | str | None = None,
    log_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Run an audit gate and return a compact execution summary."""
    normalized = normalize_gate(gate)
    pytest_result = (
        run_pytest_capture(repo_root=repo_root, log_dir=log_dir)
        if capture_pytest
        else None
    )
    gate_result = run_gate_runner(normalized, repo_root=repo_root, log_dir=log_dir)
    gate_path = gate_log_path(normalized, log_dir, repo_root=repo_root)

    summary: dict[str, Any] = {
        "gate": normalized,
        "status": gate_result.get("status", "FAIL"),
        "gate_log": str(gate_path),
        "pytest_log": pytest_result["log_path"] if pytest_result else None,
    }
    if pytest_result is not None:
        summary["pytest_status"] = pytest_result["status"]
        summary["pytest_returncode"] = pytest_result["returncode"]
    return summary


def write_json_log(result: dict[str, Any], path: Path | str) -> Path:
    """Write a JSON result with stable formatting."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run audit gates and save logs.")
    parser.add_argument("gate", help="One of: ALL, G09, G10, G12, G13, G15, G18")
    parser.add_argument(
        "--pytest",
        action="store_true",
        dest="capture_pytest",
        help="Also run python -m pytest -q and save audit/logs/pytest_result.txt.",
    )
    args = parser.parse_args(argv)

    try:
        summary = run_audit(args.gate, capture_pytest=args.capture_pytest)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary.get("status") != "PASS":
        return 1
    if summary.get("pytest_status") not in (None, "PASS"):
        return 1
    return 0


def _parse_gate_runner_output(gate: str, completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return _failure_result(
            gate,
            f"gate_runner returned non-JSON output with exit code {completed.returncode}.",
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    if not isinstance(parsed, dict):
        return _failure_result(
            gate,
            "gate_runner returned JSON that is not an object.",
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    result = dict(parsed)
    result.setdefault("gate", gate)
    result.setdefault("status", "PASS" if completed.returncode == 0 else "FAIL")
    for key in RESULT_LIST_KEYS:
        if not isinstance(result.get(key), list):
            result[key] = [] if key != "errors" else [str(result.get(key))]
    if completed.returncode != 0 and stderr.strip():
        result["errors"].append(f"stderr: {_trim_output(stderr)}")
    return result


def _resolve_log_dir(
    log_dir: Path | str | None,
    *,
    repo_root: Path | str | None = None,
) -> Path:
    if log_dir is not None:
        return Path(log_dir)
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    return root / "audit" / "logs"


def _failure_result(
    gate: str,
    message: str,
    *,
    returncode: int | None = None,
    stdout: str = "",
    stderr: str = "",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "gate": gate,
        "status": "FAIL",
        "tests_passed": False,
        "required_files_missing": [],
        "required_keywords_missing": [],
        "forbidden_patterns_found": [],
        "warnings": [],
        "errors": [message],
    }
    if returncode is not None:
        result["returncode"] = returncode
    if stdout:
        result["stdout"] = _trim_output(stdout)
    if stderr:
        result["stderr"] = _trim_output(stderr)
    return result


def _combined_output(stdout: str | None, stderr: str | None) -> str:
    return "\n".join(part.strip() for part in (stdout, stderr) if part and part.strip())


def _with_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _trim_output(output: str, limit: int = 4000) -> str:
    if len(output) <= limit:
        return output
    return output[:limit] + "... [truncated]"


if __name__ == "__main__":
    raise SystemExit(main())
