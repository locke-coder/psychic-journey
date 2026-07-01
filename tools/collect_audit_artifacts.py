"""Collect audit submission artifacts into audit_submit and a zip archive."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SUBMIT_DIR_NAME = "audit_submit"
ZIP_FILE_NAME = "audit_submit.zip"
LOG_DIR = Path("audit") / "logs"
PYTEST_RESULT_NAME = "pytest_result.txt"
GATE_RUNNER_ALL_NAME = "gate_runner_all.json"
FORBIDDEN_SCAN_NAME = "forbidden_pattern_scan.txt"

DIRECTORY_TARGETS = (
    "src",
    "tests",
    "config",
    "tools",
    "docs",
    "data/sample",
    "audit/logs",
)
FILE_TARGETS = (
    "app.py",
    "AGENTS.md",
    "README.md",
    "requirements.txt",
    "audit/pilot_checklist.md",
    "audit/d06a_kpi_scenario_unification.md",
    "audit/d06a_r1_input_sample_fixture_restore.md",
    "audit/d06b_deployment_readiness.md",
)
OUTPUT_GLOBS = (
    "outputs/latest",
)
OUTPUT_ARCHIVE_OLD_FORMAT_DIR = Path("outputs") / "archive_old_format"
OUTPUT_ARCHIVE_INVALID_DIR = Path("outputs") / "archive_invalid"
EXCLUDED_DIR_NAMES = {
    ".venv",
    ".venv_test",
    "__pycache__",
    ".pytest_cache",
    "runtime_storage",
    "operator_samples",
    "operator_data",
    "local_data",
    SUBMIT_DIR_NAME,
}
EXCLUDED_FILE_NAMES = {
    ".env",
}
EXCLUDED_FILE_PATTERNS = {
    "*.local.csv",
    "*.local.xlsx",
}
EXCLUDED_RELATIVE_PATHS = {
    ".streamlit/secrets.toml",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".key",
}
SENSITIVE_NAME_PATTERNS = (
    "*secret*",
    "*secrets*",
)
ALLOWED_SENSITIVE_EXAMPLE_NAMES = {
    "secrets.example.toml",
}
RUNTIME_DATA_DIR_NAMES = {
    "runtime_storage",
    "operator_samples",
    "operator_data",
    "local_data",
}
LOCAL_DATA_FILE_PATTERNS = (
    "*.local.csv",
    "*.local.xlsx",
)
FALLBACK_FORBIDDEN_PATTERNS = (
    ".weekday(",
    "dt.weekday",
    "weekday(",
    "next_monday",
    "next_thursday",
    "day_name ==",
    "day_name in",
    "date_range(",
    "bdate_range(",
    "period_range(",
    "input_path.write",
    "input_path.unlink",
    "input_path.rename",
    "input_path.replace",
    "to_csv(input_path",
    "to_excel(input_path",
    "shutil.move(",
    "os.replace(",
)


def audit_submit_dir(repo_root: Path | str | None = None) -> Path:
    """Return the audit submission directory path."""
    return _repo_root(repo_root) / SUBMIT_DIR_NAME


def audit_zip_path(repo_root: Path | str | None = None) -> Path:
    """Return the stable audit zip path."""
    return _repo_root(repo_root) / ZIP_FILE_NAME


def collect_audit_artifacts(
    repo_root: Path | str | None = None,
    *,
    include_archives: bool = False,
    exclude_outputs: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Collect required audit files and return a structured summary."""
    root = _repo_root(repo_root)
    submit_dir = audit_submit_dir(root)
    zip_path = audit_zip_path(root)

    if not dry_run:
        log_dir = root / LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        generated_logs = ensure_required_logs(root)
        forbidden_scan_path = write_forbidden_pattern_scan(root)
        generated_logs.append(_relative_display_path(forbidden_scan_path, root))
    else:
        generated_logs = []

    manifest = build_collection_manifest(
        root,
        include_archives=include_archives,
        exclude_outputs=exclude_outputs,
    )

    if not dry_run:
        reset_submit_dir(submit_dir, repo_root=root)
        copied_files = copy_manifest_files(root, submit_dir, manifest["files"])
        manifest_path = write_manifest_markdown(
            submit_dir / "manifest.md",
            manifest,
            include_archives=include_archives,
            exclude_outputs=exclude_outputs,
        )
        copied_files.append(_relative_display_path(manifest_path, submit_dir))
        created_zip = create_audit_zip(submit_dir, zip_path)
    else:
        copied_files = []
        created_zip = zip_path
        manifest_path = submit_dir / "manifest.md"

    return {
        "status": "DRY_RUN" if dry_run else "COLLECTED",
        "submit_dir": str(submit_dir),
        "zip_path": str(created_zip),
        "zip_name": created_zip.name,
        "manifest_path": str(manifest_path),
        "manifest_created": (submit_dir / "manifest.md").is_file(),
        "copied_files": copied_files,
        "planned_files": manifest["files"],
        "skipped_paths": manifest["skipped"],
        "excluded_sensitive_files": manifest["excluded_sensitive_files"],
        "excluded_runtime_data": manifest["excluded_runtime_data"],
        "excluded_operator_data": manifest["excluded_operator_data"],
        "generated_logs": generated_logs,
        "collection_targets": {
            "directories": list(DIRECTORY_TARGETS),
            "files": list(FILE_TARGETS),
            "outputs": [] if exclude_outputs else list(OUTPUT_GLOBS),
            "include_archives": include_archives,
            "exclude_outputs": exclude_outputs,
        },
        "excluded": {
            "directory_names": sorted(EXCLUDED_DIR_NAMES),
            "file_names": sorted(EXCLUDED_FILE_NAMES),
            "file_patterns": sorted(EXCLUDED_FILE_PATTERNS),
            "relative_paths": sorted(EXCLUDED_RELATIVE_PATHS),
            "suffixes": sorted(EXCLUDED_SUFFIXES),
            "sensitive_name_patterns": list(SENSITIVE_NAME_PATTERNS),
        },
    }


def build_collection_manifest(
    repo_root: Path | str | None = None,
    *,
    include_archives: bool = False,
    exclude_outputs: bool = False,
) -> dict[str, list[str]]:
    """Return files planned for collection and skipped excluded paths."""
    root = _repo_root(repo_root)
    collected: dict[str, Path] = {}
    skipped: list[str] = []
    excluded_sensitive: list[str] = []

    for relative_dir in DIRECTORY_TARGETS:
        base = root / relative_dir
        if not base.is_dir():
            continue
        directory_files, excluded_paths, sensitive_paths = collect_directory_manifest(base, root)
        skipped.extend(excluded_paths)
        excluded_sensitive.extend(sensitive_paths)
        for file_path in directory_files:
            collected[_relative_display_path(file_path, root)] = file_path

    for relative_file in FILE_TARGETS:
        path = root / relative_file
        if path.is_file():
            if is_excluded_path(path, root):
                skipped.append(_relative_display_path(path, root))
                if is_sensitive_path(path, root):
                    excluded_sensitive.append(_relative_display_path(path, root))
            else:
                collected[_relative_display_path(path, root)] = path

    if not exclude_outputs:
        output_files, output_skipped, output_sensitive = collect_output_manifest(
            root,
            include_archives=include_archives,
        )
        skipped.extend(output_skipped)
        excluded_sensitive.extend(output_sensitive)
        for file_path in output_files:
            collected[_relative_display_path(file_path, root)] = file_path

    excluded_sensitive.extend(find_sensitive_files(root))
    excluded_runtime_data = find_excluded_runtime_data(root)
    skipped.extend(excluded_runtime_data)
    excluded_operator_data = [
        path
        for path in excluded_runtime_data
        if "operator_samples" in Path(path).parts
    ]

    return {
        "files": sorted(collected),
        "skipped": sorted(set(skipped)),
        "excluded_sensitive_files": sorted(set(excluded_sensitive)),
        "excluded_runtime_data": sorted(set(excluded_runtime_data)),
        "excluded_operator_data": sorted(set(excluded_operator_data)),
    }


def collect_output_manifest(
    repo_root: Path,
    *,
    include_archives: bool = False,
) -> tuple[list[Path], list[str], list[str]]:
    """Return output files allowed in the audit package."""
    included_files: list[Path] = []
    skipped_paths: list[str] = []
    sensitive_paths: list[str] = []
    outputs_root = repo_root / "outputs"
    latest_root = outputs_root / "latest"

    if latest_root.is_dir():
        files, skipped, sensitive = collect_directory_manifest(latest_root, repo_root)
        included_files.extend(files)
        skipped_paths.extend(skipped)
        sensitive_paths.extend(sensitive)

    archive_root = repo_root / OUTPUT_ARCHIVE_OLD_FORMAT_DIR
    if archive_root.is_dir():
        if include_archives:
            files, skipped, sensitive = collect_directory_manifest(archive_root, repo_root)
            included_files.extend(files)
            skipped_paths.extend(skipped)
            sensitive_paths.extend(sensitive)
        else:
            skipped_paths.extend(
                _relative_display_path(path, repo_root)
                for path in sorted(archive_root.rglob("*"))
                if path.is_file()
            )

    invalid_root = repo_root / OUTPUT_ARCHIVE_INVALID_DIR
    if invalid_root.is_dir():
        skipped_paths.extend(
            _relative_display_path(path, repo_root)
            for path in sorted(invalid_root.rglob("*"))
            if path.is_file()
        )

    return included_files, skipped_paths, sensitive_paths


def collect_directory_manifest(base: Path, repo_root: Path) -> tuple[list[Path], list[str], list[str]]:
    """Return included files below base and excluded paths encountered."""
    included_files: list[Path] = []
    skipped_paths: list[str] = []
    sensitive_paths: list[str] = []

    for dirpath, dirnames, filenames in os.walk(base):
        current_dir = Path(dirpath)
        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            candidate = current_dir / dirname
            if is_excluded_path(candidate, repo_root):
                skipped_paths.append(_relative_display_path(candidate, repo_root))
                if is_sensitive_path(candidate, repo_root):
                    sensitive_paths.append(_relative_display_path(candidate, repo_root))
            else:
                kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            candidate = current_dir / filename
            if is_excluded_path(candidate, repo_root):
                skipped_paths.append(_relative_display_path(candidate, repo_root))
                if is_sensitive_path(candidate, repo_root):
                    sensitive_paths.append(_relative_display_path(candidate, repo_root))
                continue
            included_files.append(candidate)

    return included_files, skipped_paths, sensitive_paths


def is_excluded_path(path: Path | str, repo_root: Path | str | None = None) -> bool:
    """Return True when a path is excluded from audit submission artifacts."""
    root = _repo_root(repo_root)
    candidate = Path(path)
    relative_path = _relative_display_path(candidate, root)
    relative_parts = Path(relative_path).parts

    if any(part in EXCLUDED_DIR_NAMES for part in relative_parts):
        return True
    if relative_path == ZIP_FILE_NAME:
        return True
    if candidate.name in EXCLUDED_FILE_NAMES:
        return True
    if any(fnmatch.fnmatch(candidate.name.lower(), pattern) for pattern in EXCLUDED_FILE_PATTERNS):
        return True
    if candidate.suffix in EXCLUDED_SUFFIXES:
        return True
    if is_sensitive_path(candidate, root):
        return True
    return relative_path in EXCLUDED_RELATIVE_PATHS


def is_sensitive_path(path: Path | str, repo_root: Path | str | None = None) -> bool:
    """Return True for local secret/key files that must not be collected."""
    root = _repo_root(repo_root)
    candidate = Path(path)
    relative_path = _relative_display_path(candidate, root)
    name = candidate.name.lower()

    if name in ALLOWED_SENSITIVE_EXAMPLE_NAMES:
        return False
    if relative_path in EXCLUDED_RELATIVE_PATHS:
        return True
    if name in EXCLUDED_FILE_NAMES:
        return True
    if candidate.suffix.lower() == ".key":
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in SENSITIVE_NAME_PATTERNS)


def find_sensitive_files(repo_root: Path | str | None = None) -> list[str]:
    """Find sensitive file names without reading file contents."""
    root = _repo_root(repo_root)
    sensitive_files: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            candidate = current_dir / dirname
            relative_path = _relative_display_path(candidate, root)
            if dirname in EXCLUDED_DIR_NAMES or relative_path == "outputs/streamlit_deploy_source":
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            candidate = current_dir / filename
            if is_sensitive_path(candidate, root):
                sensitive_files.append(_relative_display_path(candidate, root))

    return sorted(set(sensitive_files))


def find_excluded_runtime_data(repo_root: Path | str | None = None) -> list[str]:
    """Return runtime/local data paths excluded from audit collection by name only."""
    root = _repo_root(repo_root)
    excluded_paths: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            candidate = current_dir / dirname
            relative_path = _relative_display_path(candidate, root)
            if dirname in RUNTIME_DATA_DIR_NAMES:
                excluded_paths.append(relative_path)
                nested_operator_dir = candidate / "operator_samples"
                if nested_operator_dir.is_dir():
                    excluded_paths.append(_relative_display_path(nested_operator_dir, root))
                continue
            if dirname in EXCLUDED_DIR_NAMES or relative_path == "outputs/streamlit_deploy_source":
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            lowered = filename.lower()
            if any(fnmatch.fnmatch(lowered, pattern) for pattern in LOCAL_DATA_FILE_PATTERNS):
                excluded_paths.append(_relative_display_path(current_dir / filename, root))

    return sorted(set(excluded_paths))


def ensure_required_logs(repo_root: Path | str | None = None) -> list[str]:
    """Create pytest and gate runner logs when they are missing."""
    root = _repo_root(repo_root)
    log_dir = root / LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    pytest_log = log_dir / PYTEST_RESULT_NAME
    if not pytest_log.is_file():
        write_pytest_result(root, pytest_log)
        generated.append(_relative_display_path(pytest_log, root))

    gate_log = log_dir / GATE_RUNNER_ALL_NAME
    if not gate_log.is_file():
        write_gate_runner_all_result(root, gate_log)
        generated.append(_relative_display_path(gate_log, root))

    return generated


def write_pytest_result(repo_root: Path, output_path: Path) -> Path:
    """Run pytest and write a durable text result file."""
    command = [sys.executable, "-m", "pytest", "-q"]
    completed = _run_command(command, repo_root)
    output = _combined_output(completed.stdout, completed.stderr)
    if not output:
        output = "pytest completed without output"
    text = "\n".join(
        [
            f"command: {_command_text(command)}",
            f"returncode: {completed.returncode}",
            "",
            output,
        ]
    )
    output_path.write_text(_with_trailing_newline(text), encoding="utf-8")
    return output_path


def write_gate_runner_all_result(repo_root: Path, output_path: Path) -> Path:
    """Run tools/gate_runner.py ALL and write JSON output."""
    command = [sys.executable, str(repo_root / "tools" / "gate_runner.py"), "ALL"]
    completed = _run_command(command, repo_root)
    result = _parse_gate_runner_output(completed)
    result.setdefault("gate", "ALL")
    result["returncode"] = completed.returncode
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_forbidden_pattern_scan(repo_root: Path | str | None = None) -> Path:
    """Write a source/test forbidden pattern scan report."""
    root = _repo_root(repo_root)
    output_path = root / LOG_DIR / FORBIDDEN_SCAN_NAME
    output_path.parent.mkdir(parents=True, exist_ok=True)

    patterns = load_forbidden_patterns(root)
    source_files, test_files = forbidden_scan_files(root)
    source_hits = find_pattern_hits(source_files, patterns, root)
    test_hits = find_pattern_hits(test_files, patterns, root)

    lines = [
        "Forbidden Pattern Scan",
        f"patterns_checked: {len(patterns)}",
        f"source_files_checked: {len(source_files)}",
        f"test_files_checked: {len(test_files)}",
        "",
        "source_hits:",
    ]
    lines.extend(f"- {hit}" for hit in source_hits)
    if not source_hits:
        lines.append("- PASS: no source hits")
    lines.append("")
    lines.append("test_hits:")
    lines.extend(f"- {hit}" for hit in test_hits)
    if not test_hits:
        lines.append("- PASS: no test hits")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def load_forbidden_patterns(repo_root: Path | str | None = None) -> list[str]:
    """Load forbidden patterns from the gate catalog, falling back to defaults."""
    root = _repo_root(repo_root)
    catalog_path = root / "config" / "gate_audit_catalog.yaml"
    if catalog_path.is_file():
        try:
            from tools import gate_runner

            catalog = gate_runner.load_catalog(catalog_path)
            patterns: list[str] = []
            for gate in catalog.get("gates", []):
                if not isinstance(gate, dict):
                    continue
                for pattern in gate.get("forbidden_patterns", []) or []:
                    patterns.append(str(pattern))
            return _dedupe([pattern for pattern in patterns if pattern])
        except Exception:
            pass
    return list(FALLBACK_FORBIDDEN_PATTERNS)


def forbidden_scan_files(repo_root: Path | str | None = None) -> tuple[list[Path], list[Path]]:
    """Return source and test files used for forbidden pattern reporting."""
    root = _repo_root(repo_root)
    source_files: list[Path] = []
    src_dir = root / "src"
    if src_dir.is_dir():
        source_files.extend(path for path in src_dir.rglob("*.py") if path.is_file())
    app_path = root / "app.py"
    if app_path.is_file():
        source_files.append(app_path)

    test_files: list[Path] = []
    tests_dir = root / "tests"
    if tests_dir.is_dir():
        test_files.extend(path for path in tests_dir.rglob("*.py") if path.is_file())

    return (
        sorted(path for path in source_files if not is_excluded_path(path, root)),
        sorted(path for path in test_files if not is_excluded_path(path, root)),
    )


def find_pattern_hits(
    file_paths: Iterable[Path],
    patterns: Sequence[str],
    repo_root: Path | str | None = None,
) -> list[str]:
    """Return pattern hits in relative path, line number format."""
    root = _repo_root(repo_root)
    hits: list[str] = []
    for path in file_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        relative_path = _relative_display_path(path, root)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in patterns:
                if pattern and pattern in line:
                    hits.append(f"{relative_path}:{line_number}: {pattern}")
    return _dedupe(hits)


def copy_manifest_files(
    repo_root: Path | str,
    submit_dir: Path | str,
    relative_files: Sequence[str],
) -> list[str]:
    """Copy manifest files into the submit directory."""
    root = Path(repo_root)
    destination_root = Path(submit_dir)
    copied: list[str] = []
    for relative_file in relative_files:
        source = root / relative_file
        destination = destination_root / relative_file
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(relative_file)
    return copied


def write_manifest_markdown(
    output_path: Path,
    manifest: dict[str, list[str]],
    *,
    include_archives: bool,
    exclude_outputs: bool,
) -> Path:
    """Write a package manifest with included and excluded path lists."""
    lines = [
        "# Audit Submit Manifest",
        "",
        "## Options",
        f"- include_archives: {include_archives}",
        f"- exclude_outputs: {exclude_outputs}",
        "",
        "## Included Files",
    ]
    lines.extend(f"- {path}" for path in manifest.get("files", []))
    if not manifest.get("files"):
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Excluded Files",
        ]
    )
    lines.extend(f"- {path}" for path in manifest.get("skipped", []))
    if not manifest.get("skipped"):
        lines.append("- none")

    lines.extend(
        [
            "",
            "## excluded_sensitive_files",
        ]
    )
    lines.extend(f"- {path}" for path in manifest.get("excluded_sensitive_files", []))
    if not manifest.get("excluded_sensitive_files"):
        lines.append("- none")

    lines.extend(
        [
            "",
            "## excluded_runtime_data",
        ]
    )
    lines.extend(f"- {path}" for path in manifest.get("excluded_runtime_data", []))
    if not manifest.get("excluded_runtime_data"):
        lines.append("- none")

    lines.extend(
        [
            "",
            "## excluded_operator_data",
        ]
    )
    lines.extend(f"- {path}" for path in manifest.get("excluded_operator_data", []))
    if not manifest.get("excluded_operator_data"):
        lines.append("- none")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def reset_submit_dir(submit_dir: Path | str, *, repo_root: Path | str | None = None) -> Path:
    """Create an empty audit_submit directory after checking its boundary."""
    root = _repo_root(repo_root)
    path = Path(submit_dir)
    resolved = path.resolve()
    if resolved.parent != root.resolve() or resolved.name != SUBMIT_DIR_NAME:
        raise ValueError(f"Refusing to reset unexpected submit directory: {path}")

    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_audit_zip(
    submit_dir: Path | str,
    zip_path: Path | str,
) -> Path:
    """Create audit_submit.zip from the submit directory."""
    source_dir = Path(submit_dir)
    output_path = Path(zip_path)
    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir).as_posix())
    return output_path


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Collect files required for external audit submission.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned files without copying, running checks, or writing a zip.",
    )
    parser.add_argument(
        "--include-archives",
        action="store_true",
        help="Include outputs/archive_old_format in addition to outputs/latest.",
    )
    parser.add_argument(
        "--exclude-outputs",
        action="store_true",
        help="Do not include any outputs in the audit submission package.",
    )
    args = parser.parse_args(argv)

    result = collect_audit_artifacts(
        dry_run=args.dry_run,
        include_archives=args.include_archives,
        exclude_outputs=args.exclude_outputs,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _parse_gate_runner_output(
    completed: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "gate": "ALL",
            "status": "FAIL",
            "tests_passed": False,
            "required_files_missing": [],
            "required_keywords_missing": [],
            "forbidden_patterns_found": [],
            "warnings": [],
            "errors": ["gate_runner returned non-JSON output."],
            "stdout": _trim_output(stdout),
            "stderr": _trim_output(stderr),
        }

    if not isinstance(parsed, dict):
        return {
            "gate": "ALL",
            "status": "FAIL",
            "tests_passed": False,
            "required_files_missing": [],
            "required_keywords_missing": [],
            "forbidden_patterns_found": [],
            "warnings": [],
            "errors": ["gate_runner returned JSON that is not an object."],
            "stdout": _trim_output(stdout),
            "stderr": _trim_output(stderr),
        }

    result = dict(parsed)
    if stderr.strip():
        errors = result.setdefault("errors", [])
        if isinstance(errors, list):
            errors.append(f"stderr: {_trim_output(stderr)}")
    return result


def _run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # noqa: S603 - commands are fixed audit commands.
            list(command),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:  # noqa: BLE001 - artifact generation must continue.
        return subprocess.CompletedProcess(
            list(command),
            1,
            stdout="",
            stderr=f"{type(exc).__name__}: {exc}",
        )


def _repo_root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else REPO_ROOT


def _relative_display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _combined_output(stdout: str | None, stderr: str | None) -> str:
    return "\n".join(part.strip() for part in (stdout, stderr) if part and part.strip())


def _with_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _command_text(command: Sequence[str]) -> str:
    return " ".join(str(part) for part in command)


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


if __name__ == "__main__":
    raise SystemExit(main())
