import json
from pathlib import Path

from tools import build_self_patch_prompt


FORBIDDEN_PATTERN = "week" + "day("


def _write_catalog(tmp_path: Path, *, max_patch_attempts: int = 2) -> Path:
    catalog_path = tmp_path / "gate_audit_catalog.yaml"
    catalog = {
        "max_patch_attempts": max_patch_attempts,
        "gates": [
            {
                "gate_id": "G09",
                "gate_name": "Forecast Models Gate",
                "phase": "forecast_models",
                "allowed_files": [
                    "src/forecast_models.py",
                    "tests/test_forecast_models.py",
                ],
                "required_files": ["src/forecast_models.py"],
                "required_keywords": [
                    "target_status",
                    "surplus_to_target",
                    "OVER_TARGET",
                ],
                "forbidden_patterns": [FORBIDDEN_PATTERN],
            }
        ],
    }
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    return catalog_path


def _write_failed_g09_result(tmp_path: Path) -> Path:
    result_path = tmp_path / "gate_runner_G09.json"
    result = {
        "gate": "G09",
        "status": "FAIL",
        "tests_passed": False,
        "required_files_missing": [],
        "required_keywords_missing": ["target_status", "surplus_to_target"],
        "forbidden_patterns_found": [f"src/forecast_models.py:12: {FORBIDDEN_PATTERN}"],
        "test_only_patterns_found": [],
        "warnings": ["manual review warning"],
        "errors": ["pytest failed for targets tests/test_forecast_models.py"],
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result_path


def test_g09_failed_json_builds_self_patch_prompt(tmp_path: Path) -> None:
    catalog_path = _write_catalog(tmp_path)
    result_path = _write_failed_g09_result(tmp_path)
    output_dir = tmp_path / "outputs"

    prompt, output_path = build_self_patch_prompt.build_prompt_from_files(
        gate_id="G09",
        result_path=result_path,
        patch_attempt=1,
        catalog_path=catalog_path,
        output_dir=output_dir,
    )

    assert "# Self-Patch Prompt: G09" in prompt
    assert "MISSING_REQUIRED_KEYWORDS" in prompt
    assert "target_status" in prompt
    assert f"src/forecast_models.py:12: {FORBIDDEN_PATTERN}" in prompt
    assert output_path == output_dir / "self_patch_prompt_G09.md"
    assert output_path.read_text(encoding="utf-8") == prompt


def test_attempt_three_builds_fail_escalate_prompt(tmp_path: Path) -> None:
    catalog_path = _write_catalog(tmp_path, max_patch_attempts=2)
    result_path = _write_failed_g09_result(tmp_path)

    prompt, _output_path = build_self_patch_prompt.build_prompt_from_files(
        gate_id="G09",
        result_path=result_path,
        patch_attempt=3,
        catalog_path=catalog_path,
        output_dir=tmp_path / "outputs",
    )

    assert "# FAIL_ESCALATE Prompt: G09" in prompt
    assert "FAIL_ESCALATE" in prompt
    assert "patch_attempt 3 exceeds max_patch_attempts 2" in prompt


def test_prompt_includes_allowed_files_from_catalog(tmp_path: Path) -> None:
    catalog_path = _write_catalog(tmp_path)
    result_path = _write_failed_g09_result(tmp_path)

    prompt, _output_path = build_self_patch_prompt.build_prompt_from_files(
        gate_id="G09",
        result_path=result_path,
        patch_attempt=1,
        catalog_path=catalog_path,
        output_dir=tmp_path / "outputs",
    )

    assert "## allowed_files" in prompt
    assert "- src/forecast_models.py" in prompt
    assert "- tests/test_forecast_models.py" in prompt


def test_prompt_includes_required_forbidden_guardrails(tmp_path: Path) -> None:
    catalog_path = _write_catalog(tmp_path)
    result_path = _write_failed_g09_result(tmp_path)

    prompt, _output_path = build_self_patch_prompt.build_prompt_from_files(
        gate_id="G09",
        result_path=result_path,
        patch_attempt=1,
        catalog_path=catalog_path,
        output_dir=tmp_path / "outputs",
    )

    assert "산식 변경 금지" in prompt
    assert "테스트 완화 금지" in prompt
    assert "allowed_files 외 수정 금지" in prompt
