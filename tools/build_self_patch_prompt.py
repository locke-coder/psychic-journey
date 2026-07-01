"""Build Codex self-patch prompts from Gate Runner JSON results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "config" / "gate_audit_catalog.yaml"
DEFAULT_MAX_PATCH_ATTEMPTS = 2


def load_gate_result(result_path: Path | str) -> dict[str, Any]:
    """Read a Gate Runner JSON result file."""
    path = Path(result_path)
    with path.open(encoding="utf-8") as result_file:
        result = json.load(result_file)

    if not isinstance(result, dict):
        raise ValueError("Gate Runner result JSON must contain an object.")
    return result


def load_catalog(catalog_path: Path | str = CATALOG_PATH) -> dict[str, Any]:
    """Read the gate audit catalog."""
    path = Path(catalog_path)
    with path.open(encoding="utf-8") as catalog_file:
        catalog = yaml.safe_load(catalog_file)

    if not isinstance(catalog, dict) or not isinstance(catalog.get("gates"), list):
        raise ValueError("Gate catalog must contain a top-level 'gates' list.")
    return catalog


def build_prompt_from_files(
    *,
    gate_id: str,
    result_path: Path | str,
    patch_attempt: int,
    catalog_path: Path | str = CATALOG_PATH,
    output_dir: Path | str | None = None,
) -> tuple[str, Path]:
    """Build and save a self-patch or escalation prompt from local files."""
    result = load_gate_result(result_path)
    catalog = load_catalog(catalog_path)
    gate = find_gate_config(catalog, gate_id)
    max_patch_attempts = get_max_patch_attempts(catalog, gate)
    prompt = render_prompt(
        gate_id=gate_id,
        result=result,
        gate=gate,
        patch_attempt=patch_attempt,
        max_patch_attempts=max_patch_attempts,
    )
    output_path = save_prompt(
        prompt,
        gate_id=gate_id,
        output_dir=Path(output_dir) if output_dir is not None else REPO_ROOT / "outputs",
    )
    return prompt, output_path


def find_gate_config(catalog: dict[str, Any], gate_id: str) -> dict[str, Any]:
    """Return the configured catalog entry for a gate."""
    normalized_gate_id = normalize_gate_id(gate_id)
    for gate in catalog.get("gates", []):
        if isinstance(gate, dict) and normalize_gate_id(gate.get("gate_id")) == normalized_gate_id:
            return gate
    raise ValueError(f"Gate {normalized_gate_id} was not found in the gate catalog.")


def get_allowed_files(gate: dict[str, Any]) -> list[str]:
    """Read allowed files from catalog, falling back to required files."""
    allowed_files = _string_list(gate.get("allowed_files"))
    if allowed_files:
        return allowed_files
    return _string_list(gate.get("required_files"))


def get_max_patch_attempts(catalog: dict[str, Any], gate: dict[str, Any]) -> int:
    """Read the max patch attempts from gate or catalog defaults."""
    raw_value = gate.get("max_patch_attempts", catalog.get("max_patch_attempts"))
    if raw_value is None:
        return DEFAULT_MAX_PATCH_ATTEMPTS
    try:
        return max(0, int(raw_value))
    except (TypeError, ValueError):
        return DEFAULT_MAX_PATCH_ATTEMPTS


def render_prompt(
    *,
    gate_id: str,
    result: dict[str, Any],
    gate: dict[str, Any],
    patch_attempt: int,
    max_patch_attempts: int,
) -> str:
    """Render either a Self-Patch Prompt or a FAIL_ESCALATE prompt."""
    if patch_attempt < 1:
        raise ValueError("patch_attempt must be 1 or greater.")

    normalized_gate_id = normalize_gate_id(gate_id)
    analysis = analyze_result(normalized_gate_id, result)
    allowed_files = get_allowed_files(gate)
    gate_name = str(gate.get("gate_name") or "")
    phase = str(gate.get("phase") or "")
    is_escalation = patch_attempt > max_patch_attempts
    title = (
        f"FAIL_ESCALATE Prompt: {normalized_gate_id}"
        if is_escalation
        else f"Self-Patch Prompt: {normalized_gate_id}"
    )

    lines = [
        f"# {title}",
        "",
        "[MASTER PROMPT 적용]",
        "",
        "너는 이 저장소의 구현자이자 1차 감리자다.",
        "Gate Runner 결과 JSON을 근거로 실패 원인을 먼저 분류하고, 허용 범위 안에서만 대응한다.",
        "",
        "## Gate Context",
        f"- gate_id: {normalized_gate_id}",
        f"- gate_name: {gate_name or 'N/A'}",
        f"- phase: {phase or 'N/A'}",
        f"- result_status: {analysis['status']}",
        f"- tests_passed: {analysis['tests_passed']}",
        f"- patch_attempt: {patch_attempt}",
        f"- max_patch_attempts: {max_patch_attempts}",
        "",
        "## Failure Classification",
        _bullet_list(analysis["classifications"]),
        "",
        "## Failure Evidence",
        "### required_files_missing",
        _bullet_list(analysis["required_files_missing"]),
        "",
        "### missing_keywords",
        _bullet_list(analysis["missing_keywords"]),
        "",
        "### forbidden_patterns_found",
        _bullet_list(analysis["forbidden_patterns_found"]),
        "",
        "### test_only_forbidden_patterns",
        _bullet_list(analysis["test_only_patterns_found"]),
        "",
        "### errors",
        _bullet_list(analysis["errors"]),
        "",
        "### warnings",
        _bullet_list(analysis["warnings"]),
        "",
        "## allowed_files",
        _bullet_list(allowed_files),
        "",
        "## Mandatory Guardrails",
        "- 산식 변경 금지: 기존 F1/F2/F3 산식을 임의로 바꾸지 않는다.",
        "- 테스트 완화 금지: 테스트를 삭제하거나 기대값을 코드에 맞춰 완화하지 않는다.",
        "- allowed_files 외 수정 금지: 위 allowed_files에 없는 파일을 생성/수정/삭제하지 않는다.",
        "- 마감일은 is_close_day 컬럼으로만 판단한다.",
        "- 요일이나 날짜 패턴으로 마감일을 자동 추론하지 않는다.",
        "- day_name은 표시용으로만 사용한다.",
        "- 입력표에 없는 날짜를 임의로 생성하지 않는다.",
        "- 원본 입력 파일을 수정하지 않는다.",
        "- OVER_TARGET을 단순 NO_GAP으로만 처리하지 않는다.",
        "",
    ]

    if is_escalation:
        lines.extend(
            [
                "## Required Action",
                "FAIL_ESCALATE",
                (
                    f"- patch_attempt {patch_attempt} exceeds "
                    f"max_patch_attempts {max_patch_attempts}."
                ),
                "- 더 이상 자가수복을 진행하지 말고, 실패 원인과 필요한 사용자 결정을 보고한다.",
                "- 산식 변경, allowed_files 확대, 테스트 기대값 변경이 필요해 보이면 그 사유를 구체적으로 보고한다.",
                "",
                "## Completion Report Format",
                "- result:",
                "- files_changed:",
                "- tests_run:",
                "- gate_runner_results:",
                "- key_evidence:",
                "- remaining_risks:",
                "- next_recommended_step:",
            ]
        )
    else:
        lines.extend(
            [
                "## Required Action",
                f"- {normalized_gate_id} 실패를 allowed_files 안에서만 자가수복한다.",
                "- 실패 원인을 먼저 분류한 뒤 최소 수정으로 해결한다.",
                "- 산식 변경이 필요하면 즉시 FAIL_ESCALATE로 보고한다.",
                "- 테스트를 삭제하거나 기대값을 완화하지 않는다.",
                "",
                "## Required Verification",
                "- python -m pytest -q",
                f"- python tools/gate_runner.py {normalized_gate_id}",
                "",
                "## Completion Report Format",
                "- result:",
                "- files_changed:",
                "- tests_run:",
                "- gate_runner_results:",
                "- key_evidence:",
                "- remaining_risks:",
                "- next_recommended_step:",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def analyze_result(gate_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Classify the actionable parts of a Gate Runner result."""
    normalized_gate_id = normalize_gate_id(gate_id)
    result_gate = normalize_gate_id(result.get("gate") or result.get("gate_id"))
    warnings = _string_list(result.get("warnings"))
    errors = _string_list(result.get("errors"))
    reason = result.get("reason")
    if reason:
        errors.append(f"reason: {reason}")
    if result_gate and result_gate != normalized_gate_id:
        warnings.append(
            f"result gate {result_gate} differs from requested gate {normalized_gate_id}"
        )

    required_files_missing = _string_list(result.get("required_files_missing"))
    missing_keywords = _string_list(
        result.get("required_keywords_missing", result.get("missing_keywords"))
    )
    forbidden_patterns_found = _string_list(result.get("forbidden_patterns_found"))
    test_only_patterns_found = _string_list(result.get("test_only_patterns_found"))
    classifications = classify_failures(
        required_files_missing=required_files_missing,
        missing_keywords=missing_keywords,
        forbidden_patterns_found=forbidden_patterns_found,
        errors=errors,
        warnings=warnings,
    )

    return {
        "status": str(result.get("status") or "UNKNOWN"),
        "tests_passed": result.get("tests_passed", "UNKNOWN"),
        "required_files_missing": required_files_missing,
        "missing_keywords": missing_keywords,
        "forbidden_patterns_found": forbidden_patterns_found,
        "test_only_patterns_found": test_only_patterns_found,
        "errors": errors,
        "warnings": warnings,
        "classifications": classifications,
    }


def classify_failures(
    *,
    required_files_missing: Sequence[str],
    missing_keywords: Sequence[str],
    forbidden_patterns_found: Sequence[str],
    errors: Sequence[str],
    warnings: Sequence[str],
) -> list[str]:
    """Map raw Gate Runner fields into coarse self-patch categories."""
    classifications: list[str] = []
    if required_files_missing:
        classifications.append("BLOCKED_REQUIRED_FILES_MISSING")
    if missing_keywords:
        classifications.append("MISSING_REQUIRED_KEYWORDS")
    if forbidden_patterns_found:
        classifications.append("FORBIDDEN_PATTERN_VIOLATION")
    if any("pytest failed" in error.lower() for error in errors):
        classifications.append("PYTEST_FAILURE")
    if errors and "PYTEST_FAILURE" not in classifications:
        classifications.append("GATE_EXECUTION_OR_ASSERTION_ERROR")
    if warnings:
        classifications.append("NON_BLOCKING_WARNINGS_PRESENT")
    if not classifications:
        classifications.append("NO_FAILURE_DETAILS_IN_JSON")
    return classifications


def save_prompt(prompt: str, *, gate_id: str, output_dir: Path) -> Path:
    """Save the prompt under outputs/self_patch_prompt_{gate}.md."""
    normalized_gate_id = normalize_gate_id(gate_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"self_patch_prompt_{normalized_gate_id}.md"
    output_path.write_text(prompt, encoding="utf-8")
    return output_path


def normalize_gate_id(value: object) -> str:
    """Normalize gate identifiers for CLI and catalog matching."""
    return str(value or "").strip().upper()


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_trim_text(str(item)) for item in value]
    return [_trim_text(str(value))]


def _bullet_list(values: Sequence[str]) -> str:
    if not values:
        return "- none"
    return "\n".join(f"- {value}" for value in values)


def _trim_text(value: str, limit: int = 2000) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "... [truncated]"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Codex self-patch prompt from a Gate Runner JSON result.",
    )
    parser.add_argument("--gate", required=True, help="Gate id, for example G09.")
    parser.add_argument(
        "--result",
        required=True,
        type=Path,
        help="Path to the Gate Runner result JSON file.",
    )
    parser.add_argument(
        "--attempt",
        required=True,
        type=int,
        help="Current self-patch attempt number.",
    )
    parser.add_argument(
        "--catalog",
        default=CATALOG_PATH,
        type=Path,
        help="Path to config/gate_audit_catalog.yaml.",
    )
    parser.add_argument(
        "--output-dir",
        default=REPO_ROOT / "outputs",
        type=Path,
        help="Directory where self_patch_prompt_{gate}.md will be saved.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        prompt, _output_path = build_prompt_from_files(
            gate_id=args.gate,
            result_path=args.result,
            patch_attempt=args.attempt,
            catalog_path=args.catalog,
            output_dir=args.output_dir,
        )
    except Exception as exc:  # noqa: BLE001 - CLI must return a readable failure.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(prompt, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
