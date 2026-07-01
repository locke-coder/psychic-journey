"""Audit Gate Runner for the monthly closing forecast project."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "config" / "gate_audit_catalog.yaml"
VALID_STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
RESULT_KEYS = (
    "gate",
    "status",
    "tests_passed",
    "required_files_missing",
    "required_keywords_missing",
    "forbidden_patterns_found",
    "test_only_patterns_found",
    "warnings",
    "errors",
)


def load_catalog(catalog_path: Path | None = None) -> dict[str, Any]:
    """Load and validate the gate audit catalog."""
    path = catalog_path or CATALOG_PATH
    with path.open(encoding="utf-8") as catalog_file:
        catalog = yaml.safe_load(catalog_file)

    if not isinstance(catalog, dict) or not isinstance(catalog.get("gates"), list):
        raise ValueError("Gate catalog must contain a top-level 'gates' list.")
    return catalog


def run_gate(
    gate_id: str,
    *,
    repo_root: Path | None = None,
    catalog_path: Path | None = None,
    execute_pytest: bool = True,
) -> dict[str, Any]:
    """Run one configured gate and return the JSON-serializable result."""
    normalized_gate_id = str(gate_id).upper()
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    result = _empty_result(normalized_gate_id)

    active_catalog_path = catalog_path or root / "config" / "gate_audit_catalog.yaml"
    try:
        catalog = load_catalog(active_catalog_path)
    except Exception as exc:  # noqa: BLE001 - audit tool must report structured errors.
        result["status"] = "BLOCKED"
        result["tests_passed"] = False
        result["errors"].append(f"Could not load gate catalog: {exc}")
        return result

    gates = _gate_by_id(catalog)
    gate = gates.get(normalized_gate_id)
    if gate is None:
        result["status"] = "BLOCKED"
        result["tests_passed"] = False
        known_gates = ", ".join(sorted(gates))
        result["errors"].append(
            f"Unknown gate: {normalized_gate_id}. Known gates: {known_gates}."
        )
        return result

    required_files = _string_list(gate.get("required_files"))
    pytest_targets = _string_list(gate.get("pytest_targets"))
    command_targets = _command_targets(gate.get("command_targets"))
    required_keywords = _string_list(gate.get("required_keywords"))
    forbidden_patterns = _string_list(gate.get("forbidden_patterns"))
    required_gates = _string_list(gate.get("required_gates"))
    keyword_scan_files = _string_list(gate.get("keyword_scan_files")) or required_files

    missing_files = find_missing_required_files(root, required_files)
    result["required_files_missing"] = missing_files

    keyword_files = [
        root / relative_path
        for relative_path in keyword_scan_files
        if (root / relative_path).is_file()
    ]
    result["required_keywords_missing"] = find_missing_required_keywords(
        keyword_files,
        required_keywords,
    )
    result["warnings"].extend(_string_list(gate.get("static_warnings")))
    result["errors"].extend(
        find_missing_required_test_patterns(root, gate.get("required_test_patterns"))
    )

    scan_groups = collect_forbidden_scan_files(root)
    forbidden_scan = detect_forbidden_patterns(
        scan_groups["source_files"],
        forbidden_patterns,
        root,
        test_file_paths=scan_groups["test_files"],
    )
    result["forbidden_patterns_found"] = forbidden_scan["forbidden_patterns_found"]
    result["test_only_patterns_found"] = forbidden_scan["test_only_patterns_found"]
    result["warnings"].extend(forbidden_scan["warnings"])
    result["forbidden_patterns_found"] = _dedupe(
        [
            *result["forbidden_patterns_found"],
            *detect_forbidden_context_patterns(
                scan_groups["source_files"],
                gate.get("forbidden_context_patterns"),
                root,
            ),
        ]
    )
    result["errors"].extend(
        run_required_gates(
            normalized_gate_id,
            required_gates,
            repo_root=root,
            catalog_path=active_catalog_path,
            execute_pytest=execute_pytest,
        )
    )

    if missing_files:
        result["status"] = "BLOCKED"
        result["tests_passed"] = False
        result["warnings"].append("pytest skipped because required files are missing.")
        return _ordered_result(result)

    if execute_pytest:
        tests_passed, pytest_errors = run_pytest(pytest_targets, root)
        commands_passed, command_errors = run_command_targets(command_targets, root)
        result["tests_passed"] = tests_passed and commands_passed
        result["errors"].extend(pytest_errors)
        result["errors"].extend(command_errors)
    else:
        result["tests_passed"] = True
        result["warnings"].append("pytest execution skipped by caller.")
        if command_targets:
            result["warnings"].append("command execution skipped by caller.")

    if (
        not result["tests_passed"]
        or result["required_keywords_missing"]
        or result["forbidden_patterns_found"]
        or result["errors"]
    ):
        result["status"] = "FAIL"
    else:
        result["status"] = "PASS"

    return _ordered_result(result)


def find_missing_required_files(repo_root: Path, required_files: Sequence[str]) -> list[str]:
    """Return required catalog paths that do not exist as files."""
    return [
        relative_path
        for relative_path in required_files
        if not (repo_root / relative_path).is_file()
    ]


def find_missing_required_keywords(
    file_paths: Iterable[Path],
    required_keywords: Sequence[str],
) -> list[str]:
    """Return required keywords absent from the combined target file text."""
    combined_text = "\n".join(_read_text(path) for path in file_paths if path.is_file())
    return [keyword for keyword in required_keywords if keyword and keyword not in combined_text]


def find_missing_required_test_patterns(
    repo_root: Path,
    required_test_patterns: object,
) -> list[str]:
    """Return configured test-pattern checks absent from their target files."""
    missing: list[str] = []
    for requirement in _test_pattern_requirements(required_test_patterns):
        relative_path = requirement["file"]
        path = repo_root / relative_path
        label = requirement["label"]
        patterns = requirement["any_of"]

        if not path.is_file():
            missing.append(
                f"required test pattern file missing: {relative_path} [{label}]"
            )
            continue

        text = _read_text(path)
        if not any(pattern in text for pattern in patterns):
            expected = " OR ".join(patterns)
            missing.append(
                "required test pattern missing: "
                f"{relative_path} [{label}] expected one of: {expected}"
            )
    return missing


def detect_forbidden_patterns(
    file_paths: Iterable[Path | str],
    forbidden_patterns: Sequence[str],
    repo_root: Path | str,
    *,
    test_file_paths: Iterable[Path | str] | None = None,
) -> dict[str, list[str]]:
    """Find forbidden patterns, failing source files and warning on tests."""
    root = Path(repo_root)
    source_hits: list[str] = []
    test_hits: list[str] = []
    warnings: list[str] = []

    source_files, test_files = _split_forbidden_scan_inputs(
        file_paths,
        root,
        test_file_paths=test_file_paths,
    )

    source_hits = _find_forbidden_pattern_hits(source_files, forbidden_patterns, root)
    test_hits = _find_forbidden_pattern_hits(test_files, forbidden_patterns, root)
    warnings = [
        f"test-only forbidden-pattern warning: {hit}"
        for hit in test_hits
    ]

    return {
        "forbidden_patterns_found": _dedupe(source_hits),
        "test_only_patterns_found": _dedupe(test_hits),
        "failures": _dedupe(source_hits),
        "warnings": _dedupe(warnings),
    }


def detect_forbidden_context_patterns(
    file_paths: Iterable[Path | str],
    forbidden_context_patterns: object,
    repo_root: Path | str,
) -> list[str]:
    """Find forbidden phrases near a required anchor in source files."""
    root = Path(repo_root)
    hits: list[str] = []
    requirements = _context_pattern_requirements(forbidden_context_patterns)
    if not requirements:
        return hits

    for raw_path in file_paths:
        path = _normalize_repo_path(raw_path, root)
        if not path.is_file():
            continue

        relative_path = _relative_display_path(path, root)
        lines = _read_text(path).splitlines()
        for line_index, line in enumerate(lines):
            for requirement in requirements:
                anchor = requirement["anchor"]
                if anchor not in line:
                    continue

                window = requirement["window"]
                start = max(0, line_index - window)
                end = min(len(lines), line_index + window + 1)
                context = "\n".join(lines[start:end])
                for pattern in requirement["forbidden_any"]:
                    if pattern and pattern in context:
                        hits.append(
                            f"{relative_path}:{line_index + 1}: "
                            f"{requirement['label']}: {anchor} near {pattern}"
                        )
    return _dedupe(hits)


def collect_forbidden_scan_files(repo_root: Path | str) -> dict[str, list[Path]]:
    """Return the source and test Python files covered by forbidden scans."""
    root = Path(repo_root)
    source_files: list[Path] = []
    src_dir = root / "src"
    if src_dir.is_dir():
        source_files.extend(src_dir.rglob("*.py"))

    app_path = root / "app.py"
    if app_path.is_file():
        source_files.append(app_path)

    test_files: list[Path] = []
    tests_dir = root / "tests"
    if tests_dir.is_dir():
        test_files.extend(tests_dir.rglob("*.py"))

    return {
        "source_files": _sorted_unique_paths(source_files, root),
        "test_files": _sorted_unique_paths(test_files, root),
    }


def run_pytest(pytest_targets: Sequence[str], repo_root: Path) -> tuple[bool, list[str]]:
    """Run configured pytest targets and capture failures as JSON errors."""
    if not pytest_targets:
        return True, []

    command = [sys.executable, "-m", "pytest", "-q", *pytest_targets]
    completed = subprocess.run(  # noqa: S603 - targets are catalog-controlled paths.
        command,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode == 0:
        return True, []

    output = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part.strip()
    )
    return (
        False,
        [
            (
                "pytest failed for targets "
                f"{', '.join(pytest_targets)} with exit code {completed.returncode}: "
                f"{_trim_output(output)}"
            )
        ],
    )


def run_command_targets(
    command_targets: Sequence[Sequence[str]],
    repo_root: Path,
) -> tuple[bool, list[str]]:
    """Run configured audit commands and capture failures as JSON errors."""
    errors: list[str] = []
    for raw_command in command_targets:
        command = [
            sys.executable if token == "{python}" else token
            for token in raw_command
        ]
        if not command:
            continue
        try:
            completed = subprocess.run(  # noqa: S603 - catalog-controlled command.
                command,
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            output = "\n".join(
                part.strip()
                for part in (exc.stdout or "", exc.stderr or "")
                if part and str(part).strip()
            )
            errors.append(
                "command timed out for target "
                f"{' '.join(raw_command)}: {_trim_output(output)}"
            )
            continue

        if completed.returncode != 0:
            output = "\n".join(
                part.strip()
                for part in (completed.stdout, completed.stderr)
                if part.strip()
            )
            errors.append(
                "command failed for target "
                f"{' '.join(raw_command)} with exit code {completed.returncode}: "
                f"{_trim_output(output)}"
            )
    return not errors, errors


def run_required_gates(
    current_gate_id: str,
    required_gate_ids: Sequence[str],
    *,
    repo_root: Path,
    catalog_path: Path,
    execute_pytest: bool,
) -> list[str]:
    """Run dependent gates and return failure summaries for non-PASS results."""
    failures: list[str] = []
    for gate_id in required_gate_ids:
        normalized_gate_id = str(gate_id).upper()
        if not normalized_gate_id:
            continue
        if normalized_gate_id == current_gate_id:
            failures.append(f"required gate {normalized_gate_id} cannot depend on itself.")
            continue

        result = run_gate(
            normalized_gate_id,
            repo_root=repo_root,
            catalog_path=catalog_path,
            execute_pytest=execute_pytest,
        )
        if result["status"] != "PASS":
            failures.append(
                "required gate "
                f"{normalized_gate_id} did not pass: {result['status']}; "
                f"{_summarize_gate_result(result)}"
            )
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        result = _empty_result("")
        result["status"] = "BLOCKED"
        result["tests_passed"] = False
        result["errors"].append("Usage: python tools/gate_runner.py <GATE_ID|ALL>")
        print(json.dumps(_ordered_result(result), ensure_ascii=False, indent=2))
        return 1

    result = run_gate(args[0])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


def _empty_result(gate_id: str) -> dict[str, Any]:
    return {
        "gate": gate_id,
        "status": "NOT_RUN",
        "tests_passed": False,
        "required_files_missing": [],
        "required_keywords_missing": [],
        "forbidden_patterns_found": [],
        "test_only_patterns_found": [],
        "warnings": [],
        "errors": [],
    }


def _gate_by_id(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gates: dict[str, dict[str, Any]] = {}
    for gate in catalog.get("gates", []):
        if isinstance(gate, dict) and "gate_id" in gate:
            gates[str(gate["gate_id"]).upper()] = gate
    return gates


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _command_targets(value: object) -> list[list[str]]:
    if not isinstance(value, list):
        return []

    commands: list[list[str]] = []
    for item in value:
        if isinstance(item, list):
            command = [str(token) for token in item if str(token)]
        else:
            command = shlex.split(str(item))
        if command:
            commands.append(command)
    return commands


def _test_pattern_requirements(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    requirements: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue

        relative_path = str(item.get("file", ""))
        patterns = _string_list(item.get("any_of"))
        if not relative_path or not patterns:
            continue

        label = str(item.get("label") or f"required_test_patterns[{index}]")
        requirements.append(
            {
                "file": relative_path,
                "label": label,
                "any_of": patterns,
            }
        )
    return requirements


def _context_pattern_requirements(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    requirements: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue

        anchor = str(item.get("anchor", ""))
        patterns = _string_list(item.get("forbidden_any"))
        if not anchor or not patterns:
            continue

        raw_window = item.get("window", 0)
        try:
            window = max(0, int(raw_window))
        except (TypeError, ValueError):
            window = 0

        label = str(item.get("label") or f"forbidden_context_patterns[{index}]")
        requirements.append(
            {
                "anchor": anchor,
                "forbidden_any": patterns,
                "label": label,
                "window": window,
            }
        )
    return requirements


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _relative_display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_fail_forbidden_path(relative_path: str) -> bool:
    return relative_path == "app.py" or relative_path.startswith("src/")


def _is_test_forbidden_path(relative_path: str) -> bool:
    return relative_path.startswith("tests/")


def _split_forbidden_scan_inputs(
    file_paths: Iterable[Path | str],
    repo_root: Path,
    *,
    test_file_paths: Iterable[Path | str] | None,
) -> tuple[list[Path], list[Path]]:
    if test_file_paths is not None:
        return (
            _sorted_unique_paths(
                (_normalize_repo_path(path, repo_root) for path in file_paths),
                repo_root,
            ),
            _sorted_unique_paths(
                (_normalize_repo_path(path, repo_root) for path in test_file_paths),
                repo_root,
            ),
        )

    source_files: list[Path] = []
    test_files: list[Path] = []
    for raw_path in file_paths:
        path = _normalize_repo_path(raw_path, repo_root)
        relative_path = _relative_display_path(path, repo_root)
        if _is_fail_forbidden_path(relative_path):
            source_files.append(path)
        elif _is_test_forbidden_path(relative_path):
            test_files.append(path)

    return (
        _sorted_unique_paths(source_files, repo_root),
        _sorted_unique_paths(test_files, repo_root),
    )


def _find_forbidden_pattern_hits(
    file_paths: Iterable[Path],
    forbidden_patterns: Sequence[str],
    repo_root: Path,
) -> list[str]:
    hits: list[str] = []
    for path in file_paths:
        if not path.is_file():
            continue

        relative_path = _relative_display_path(path, repo_root)
        for line_number, line in enumerate(_read_text(path).splitlines(), start=1):
            for pattern in forbidden_patterns:
                if pattern and pattern in line:
                    hits.append(f"{relative_path}:{line_number}: {pattern}")
    return _dedupe(hits)


def _sorted_unique_paths(paths: Iterable[Path], repo_root: Path) -> list[Path]:
    unique_paths: dict[str, Path] = {}
    for path in paths:
        unique_paths[str(path.resolve())] = path
    return sorted(
        unique_paths.values(),
        key=lambda path: _relative_display_path(path, repo_root),
    )


def _normalize_repo_path(path: Path | str, repo_root: Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _trim_output(output: str, limit: int = 4000) -> str:
    if len(output) <= limit:
        return output
    return output[:limit] + "... [truncated]"


def _summarize_gate_result(result: dict[str, Any]) -> str:
    parts: list[str] = []
    if not result.get("tests_passed"):
        parts.append("tests_passed=False")

    for key in (
        "required_files_missing",
        "required_keywords_missing",
        "forbidden_patterns_found",
        "errors",
    ):
        values = result.get(key) or []
        if values:
            parts.append(f"{key}={values[:3]}")

    if not parts:
        return "no detailed failure fields were reported"
    return _trim_output("; ".join(parts), limit=1200)


def _ordered_result(result: dict[str, Any]) -> dict[str, Any]:
    ordered = {key: result.get(key) for key in RESULT_KEYS}
    assert ordered["status"] in VALID_STATUSES
    return ordered


if __name__ == "__main__":
    raise SystemExit(main())
