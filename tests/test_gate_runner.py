import json
from pathlib import Path

import pytest

from tools import gate_runner


EXPECTED_JSON_KEYS = {
    "gate",
    "status",
    "tests_passed",
    "required_files_missing",
    "required_keywords_missing",
    "forbidden_patterns_found",
    "test_only_patterns_found",
    "warnings",
    "errors",
}

AUDITED_GATE_IDS = ("G09", "G10", "G12", "G13", "G15", "G18")
LIST_RESULT_KEYS = {
    "required_files_missing",
    "required_keywords_missing",
    "forbidden_patterns_found",
    "test_only_patterns_found",
    "warnings",
    "errors",
}


def _write_catalog(
    tmp_path: Path,
    *,
    gate_id: str = "G99",
    required_files: list[str] | None = None,
    pytest_targets: list[str] | None = None,
    keyword_scan_files: list[str] | None = None,
    required_keywords: list[str] | None = None,
    required_gates: list[str] | None = None,
    forbidden_patterns: list[str] | None = None,
    forbidden_context_patterns: list[dict] | None = None,
    required_test_patterns: list[dict] | None = None,
    static_warnings: list[str] | None = None,
    extra_gates: list[dict] | None = None,
) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    catalog_path = config_dir / "gate_audit_catalog.yaml"
    catalog = {
        "gates": [
            {
                "gate_id": gate_id,
                "gate_name": "Temporary Test Gate",
                "phase": "test",
                "required_files": required_files or [],
                "pytest_targets": pytest_targets or [],
                "keyword_scan_files": keyword_scan_files or [],
                "required_keywords": required_keywords or [],
                "required_gates": required_gates or [],
                "required_test_patterns": required_test_patterns or [],
                "forbidden_patterns": forbidden_patterns or [],
                "forbidden_context_patterns": forbidden_context_patterns or [],
                "warning_keywords": [],
                "static_warnings": static_warnings or [],
                "pass_conditions": [],
            }
        ] + (extra_gates or [])
    }
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    return catalog_path


def _assert_result_shape(result: dict, gate_id: str) -> None:
    assert EXPECTED_JSON_KEYS == set(result)
    assert result["gate"] == gate_id
    assert result["status"] in gate_runner.VALID_STATUSES
    assert isinstance(result["tests_passed"], bool)
    for key in LIST_RESULT_KEYS:
        assert isinstance(result[key], list)
    assert json.loads(json.dumps(result, ensure_ascii=False))["gate"] == gate_id


def test_gate_runner_importable() -> None:
    assert callable(gate_runner.run_gate)


def test_unknown_gate_returns_structured_blocked_result() -> None:
    result = gate_runner.run_gate("UNKNOWN", execute_pytest=False)

    _assert_result_shape(result, "UNKNOWN")
    assert result["status"] in {"BLOCKED", "FAIL"}


def test_all_gate_runs_without_nested_pytest() -> None:
    result = gate_runner.run_gate("ALL", execute_pytest=False)

    _assert_result_shape(result, "ALL")
    assert result["status"] in {"PASS", "FAIL", "BLOCKED"}


def test_g13_declares_report_builder_overachievement_audit_requirements() -> None:
    catalog = gate_runner.load_catalog()
    gates = {gate["gate_id"]: gate for gate in catalog["gates"]}
    g13 = gates["G13"]

    assert {
        "목표 초과 예상",
        "target_status",
        "target_variance",
        "surplus_to_target",
        "OVER_TARGET",
        "O1_TARGET_HOLD_BUFFER",
        "O2_STRETCH_TARGET_CAPTURE",
        "O3_QUALITY_GUARD_RELIEF",
        "O1",
        "O2",
        "O3",
        "취소",
        "철회",
        "미결제",
    } <= set(g13["required_keywords"])

    pattern_labels = {
        requirement["label"]
        for requirement in g13.get("required_test_patterns", [])
    }
    assert {
        "OVER_TARGET report test exists",
        "OVER_TARGET fixture uses target status",
        "목표 초과 예상 phrase assertion",
        "OVER_TARGET report is not reduced to NO_GAP",
        "O1 report wording assertion",
        "O2 report wording assertion",
        "O3 report wording assertion",
        "cancellation and payment risk wording assertions",
    } <= pattern_labels


def test_g15_declares_streamlit_app_audit_requirements() -> None:
    catalog = gate_runner.load_catalog()
    gates = {gate["gate_id"]: gate for gate in catalog["gates"]}
    g15 = gates["G15"]

    assert g15["required_files"] == ["app.py", "tests/test_app_smoke.py"]
    assert g15["pytest_targets"] == ["tests/test_app_smoke.py"]
    assert {
        "target_status",
        "target_variance",
        "surplus_to_target",
        "OVER_TARGET",
        "O1_TARGET_HOLD_BUFFER",
        "O2_STRETCH_TARGET_CAPTURE",
        "O3_QUALITY_GUARD_RELIEF",
        "목표 초과 예상",
    } <= set(g15["required_keywords"])
    assert {
        "app.py",
        "tests/test_app_smoke.py",
        "src/report_builder.py",
        "tests/test_report_builder.py",
    } <= set(g15.get("keyword_scan_files", []))
    assert any("화면 캡처" in warning for warning in g15["static_warnings"])

    pattern_labels = {
        requirement["label"]
        for requirement in g15.get("required_test_patterns", [])
    }
    assert {
        "app import smoke test exists",
        "target_status KPI display code exists",
        "surplus_to_target KPI display code exists",
        "target_variance KPI display code exists",
        "O1/O2/O3 explanation display code exists",
        "O1/O2/O3 explanation test exists",
        "validation error calculation guard exists",
        "validation error stops scenario calculation test exists",
        "report builder output is rendered by Streamlit",
        "목표 초과 예상 report phrase source exists",
    } <= pattern_labels


def test_g18_declares_final_audit_requirements() -> None:
    catalog = gate_runner.load_catalog()
    gates = {gate["gate_id"]: gate for gate in catalog["gates"]}
    g18 = gates["G18"]

    assert g18["pytest_targets"] == ["tests"]
    assert g18["required_gates"] == ["G09", "G10", "G12", "G13", "G15"]
    assert {
        "target_status",
        "surplus_to_target",
        "target_variance",
        "O1_TARGET_HOLD_BUFFER",
        "O2_STRETCH_TARGET_CAPTURE",
        "O3_QUALITY_GUARD_RELIEF",
        "OVERACHIEVEMENT",
        "목표 초과 예상",
    } <= set(g18["required_keywords"])
    assert {
        "date_range(",
        "bdate_range(",
        "period_range(",
        "input_path.write",
        "input_path.unlink",
        "to_csv(input_path",
        "to_excel(input_path",
    } <= set(g18["forbidden_patterns"])

    pattern_labels = {
        requirement["label"]
        for requirement in g18.get("required_test_patterns", [])
    }
    assert {
        "target_variance assertion exists",
        "UNDER_TARGET branch is covered",
        "ON_TARGET branch exists",
        "OVER_TARGET branch is covered",
        "OVER_TARGET is not reduced to NO_GAP",
        "목표 초과 예상 phrase assertion",
        "target_status KPI display code exists",
        "surplus_to_target KPI display code exists",
    } <= pattern_labels


def test_forbidden_pattern_detection_ignores_files_outside_scan_groups(tmp_path: Path) -> None:
    temp_file = tmp_path / "scratch_audit_note.py"
    temp_file.write_text("candidate = next_monday\n", encoding="utf-8")

    result = gate_runner.detect_forbidden_patterns(
        [temp_file],
        ["next_monday"],
        tmp_path,
    )

    assert result["forbidden_patterns_found"] == []
    assert result["test_only_patterns_found"] == []
    assert result["warnings"] == []


def test_forbidden_pattern_detection_separates_source_failures_and_warnings(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    source_file = source_dir / "bad_close_day_logic.py"
    source_file.write_text("result = current_date.weekday()\n", encoding="utf-8")
    test_file = tests_dir / "test_forbidden_pattern_catalog.py"
    test_file.write_text('assert "weekday(" in forbidden_patterns\n', encoding="utf-8")

    result = gate_runner.detect_forbidden_patterns(
        [source_file, test_file],
        ["weekday("],
        tmp_path,
    )

    assert result["forbidden_patterns_found"] == [
        "src/bad_close_day_logic.py:1: weekday("
    ]
    assert result["failures"] == ["src/bad_close_day_logic.py:1: weekday("]
    assert result["test_only_patterns_found"] == [
        "tests/test_forbidden_pattern_catalog.py:1: weekday("
    ]
    assert result["warnings"] == [
        "test-only forbidden-pattern warning: "
        "tests/test_forbidden_pattern_catalog.py:1: weekday("
    ]


def test_run_gate_fails_when_any_src_file_contains_weekday_call(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source_file = source_dir / "bad_close_day_logic.py"
    source_file.write_text("close_key = input_date.weekday()\n", encoding="utf-8")
    catalog_path = _write_catalog(
        tmp_path,
        forbidden_patterns=[".weekday("],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "FAIL"
    assert result["forbidden_patterns_found"] == [
        "src/bad_close_day_logic.py:1: .weekday("
    ]
    assert result["test_only_patterns_found"] == []


def test_run_gate_warns_when_tests_verify_forbidden_pattern_strings(
    tmp_path: Path,
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_forbidden_pattern_scan.py"
    test_file.write_text('assert ".weekday(" not in source\n', encoding="utf-8")
    catalog_path = _write_catalog(
        tmp_path,
        forbidden_patterns=[".weekday("],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "PASS"
    assert result["forbidden_patterns_found"] == []
    assert result["test_only_patterns_found"] == [
        "tests/test_forbidden_pattern_scan.py:1: .weekday("
    ]
    assert (
        "test-only forbidden-pattern warning: "
        "tests/test_forbidden_pattern_scan.py:1: .weekday("
    ) in result["warnings"]


def test_run_gate_allows_day_name_column_strings(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source_file = source_dir / "display_columns.py"
    source_file.write_text(
        'columns = ["date", "day_name", "is_close_day"]\n',
        encoding="utf-8",
    )
    catalog_path = _write_catalog(
        tmp_path,
        forbidden_patterns=["day_name ==", "day_name in"],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "PASS"
    assert result["forbidden_patterns_found"] == []
    assert result["test_only_patterns_found"] == []


def test_run_gate_fails_when_src_file_contains_day_name_equality(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source_file = source_dir / "close_day_logic.py"
    source_file.write_text('if day_name == "월요일":\n    close_day = True\n', encoding="utf-8")
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["src/close_day_logic.py"],
        forbidden_patterns=["day_name =="],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "FAIL"
    assert result["forbidden_patterns_found"] == [
        "src/close_day_logic.py:1: day_name =="
    ]


def test_run_gate_keeps_test_forbidden_pattern_declarations_non_blocking(
    tmp_path: Path,
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_forbidden_catalog.py"
    test_file.write_text('assert "day_name ==" in forbidden_patterns\n', encoding="utf-8")
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["tests/test_forbidden_catalog.py"],
        forbidden_patterns=["day_name =="],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "PASS"
    assert result["forbidden_patterns_found"] == []
    assert result["test_only_patterns_found"] == [
        "tests/test_forbidden_catalog.py:1: day_name =="
    ]
    assert (
        "test-only forbidden-pattern warning: "
        "tests/test_forbidden_catalog.py:1: day_name =="
    ) in result["warnings"]


def test_run_gate_fails_when_required_keyword_is_missing(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source_file = source_dir / "forecast_summary.py"
    source_file.write_text("surplus_to_target = 0\n", encoding="utf-8")
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["src/forecast_summary.py"],
        required_keywords=["target_status", "surplus_to_target"],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "FAIL"
    assert result["required_keywords_missing"] == ["target_status"]


def test_run_gate_uses_keyword_scan_files_for_required_keywords(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text("from reports import render_report\n", encoding="utf-8")
    report_file = tmp_path / "report_source.py"
    report_file.write_text("status = '목표 초과 예상'\n", encoding="utf-8")
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["app.py"],
        keyword_scan_files=["app.py", "report_source.py"],
        required_keywords=["목표 초과 예상"],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "PASS"
    assert result["required_keywords_missing"] == []


def test_run_gate_includes_static_warnings_without_failing(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text("target_status = 'OVER_TARGET'\n", encoding="utf-8")
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["app.py"],
        required_keywords=["target_status"],
        static_warnings=["manual screenshot capture required"],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "PASS"
    assert "manual screenshot capture required" in result["warnings"]


def test_run_gate_fails_when_required_gate_does_not_pass(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source_file = source_dir / "forecast_summary.py"
    source_file.write_text("surplus_to_target = 0\n", encoding="utf-8")
    catalog_path = _write_catalog(
        tmp_path,
        required_gates=["G01"],
        extra_gates=[
            {
                "gate_id": "G01",
                "gate_name": "Dependency Gate",
                "phase": "dependency",
                "required_files": ["src/forecast_summary.py"],
                "pytest_targets": [],
                "keyword_scan_files": [],
                "required_keywords": ["target_status"],
                "required_test_patterns": [],
                "forbidden_patterns": [],
                "forbidden_context_patterns": [],
                "warning_keywords": [],
                "static_warnings": [],
                "pass_conditions": [],
            }
        ],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "FAIL"
    assert any(
        "required gate G01 did not pass: FAIL" in error
        for error in result["errors"]
    )


def test_run_gate_fails_when_required_test_pattern_is_missing(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_forecast_models.py"
    test_file.write_text(
        'assert result["target_status"] == OVER_TARGET\n',
        encoding="utf-8",
    )
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["tests/test_forecast_models.py"],
        required_test_patterns=[
            {
                "file": "tests/test_forecast_models.py",
                "label": "surplus_to_target positive assertion",
                "any_of": [
                    'surplus_to_target"] > 0',
                    "surplus_to_target'] > 0",
                ],
            }
        ],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "FAIL"
    assert (
        "required test pattern missing: tests/test_forecast_models.py "
        "[surplus_to_target positive assertion]"
    ) in result["errors"][0]


def test_run_gate_passes_when_required_test_pattern_matches_any_option(
    tmp_path: Path,
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_forecast_models.py"
    test_file.write_text(
        'assert result["surplus_to_target"] > 0\n',
        encoding="utf-8",
    )
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["tests/test_forecast_models.py"],
        required_test_patterns=[
            {
                "file": "tests/test_forecast_models.py",
                "label": "surplus_to_target positive assertion",
                "any_of": [
                    'surplus_to_target"] > 0',
                    "surplus_to_target'] > 0",
                ],
            }
        ],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_run_gate_fails_when_forbidden_context_pattern_is_near_anchor(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source_file = source_dir / "status_labels.py"
    source_file.write_text(
        'labels = {"CAPACITY_LIMITED": "목표 달성 가능"}\n',
        encoding="utf-8",
    )
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["src/status_labels.py"],
        forbidden_context_patterns=[
            {
                "label": "CAPACITY_LIMITED must not be shown as achievable",
                "anchor": "CAPACITY_LIMITED",
                "forbidden_any": ["목표 달성 가능"],
                "window": 0,
            }
        ],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "FAIL"
    assert result["forbidden_patterns_found"] == [
        "src/status_labels.py:1: "
        "CAPACITY_LIMITED must not be shown as achievable: "
        "CAPACITY_LIMITED near 목표 달성 가능"
    ]


def test_run_gate_allows_capacity_limited_uncertain_context(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source_file = source_dir / "status_labels.py"
    source_file.write_text(
        'labels = {"CAPACITY_LIMITED": "목표 달성이 불확실"}\n',
        encoding="utf-8",
    )
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["src/status_labels.py"],
        forbidden_context_patterns=[
            {
                "label": "CAPACITY_LIMITED must not be shown as achievable",
                "anchor": "CAPACITY_LIMITED",
                "forbidden_any": ["목표 달성 가능"],
                "window": 0,
            }
        ],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "PASS"
    assert result["forbidden_patterns_found"] == []


def test_run_gate_blocks_when_required_file_is_missing(tmp_path: Path) -> None:
    catalog_path = _write_catalog(
        tmp_path,
        required_files=["src/missing_forecast.py"],
        required_keywords=["target_status"],
    )

    result = gate_runner.run_gate(
        "G99",
        repo_root=tmp_path,
        catalog_path=catalog_path,
        execute_pytest=False,
    )

    _assert_result_shape(result, "G99")
    assert result["status"] == "BLOCKED"
    assert result["tests_passed"] is False
    assert result["required_files_missing"] == ["src/missing_forecast.py"]


@pytest.mark.parametrize("gate_id", AUDITED_GATE_IDS)
def test_audited_gate_json_structure_is_serializable(gate_id: str) -> None:
    result = gate_runner.run_gate(gate_id, execute_pytest=False)

    _assert_result_shape(result, gate_id)
