from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

import app
from src.operational_closeout import (
    BLOCKED,
    MANUAL,
    PASS,
    REFRESH,
    build_operational_closeout_summary,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "operational_closeout.py"


def _fresh_logs() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"검증 항목": label, "상태": "24시간 이내"}
            for label in ("pytest", "Gate Runner", "금지 패턴", "outputs mtime")
        ]
    )


def _base_kwargs() -> dict[str, object]:
    return {
        "validation_result": {"errors": [], "warnings": ["검토 주의"]},
        "selected_row": {
            "scenario_id": "F1_O1",
            "target_status": "OVER_TARGET",
            "forecast_after_provision": 123.4,
        },
        "report_text": "현재 예상과 운영 판단을 공유하기 위한 테스트 보고문입니다.",
        "expected_report_name": "daily_report_sales_20260715.xlsx",
        "latest_excel_status": {
            "exists": True,
            "file_name": "daily_report_sales_20260715.xlsx",
            "modified_at": "2026-07-15 10:00:00",
            "size_bytes": 1234,
        },
        "audit_logs": _fresh_logs(),
    }


def test_all_machine_checks_end_with_manual_security_confirmation() -> None:
    result = build_operational_closeout_summary(**_base_kwargs())
    items = result["items"].set_index("단계")

    assert result["overall_code"] == MANUAL
    assert result["overall_label"] == "수동 확인 후 공유 가능"
    assert result["pass_count"] == 5
    assert result["blocked_count"] == 0
    assert result["refresh_count"] == 0
    assert items.loc["공유 보안", "code"] == MANUAL
    assert result["final_forecast_modified"] is False
    assert result["outputs_modified"] is False


def test_validation_error_blocks_closeout_before_refresh_items() -> None:
    kwargs = _base_kwargs()
    kwargs["validation_result"] = {"errors": ["누적 실적 누락"], "warnings": []}
    kwargs["latest_excel_status"] = {"exists": False}

    result = build_operational_closeout_summary(**kwargs)

    assert result["overall_code"] == BLOCKED
    assert result["blocked_count"] == 1
    assert result["refresh_count"] == 1
    assert "입력 · 데이터" in result["next_action"]


def test_mismatched_excel_is_refresh_not_false_ready() -> None:
    kwargs = _base_kwargs()
    kwargs["latest_excel_status"] = {
        "exists": True,
        "file_name": "daily_report_sales_20260714.xlsx",
        "modified_at": "2026-07-14 10:00:00",
    }

    result = build_operational_closeout_summary(**kwargs)
    excel_row = result["items"].loc[
        result["items"]["단계"] == "Excel 공유본"
    ].iloc[0]

    assert result["overall_code"] == REFRESH
    assert excel_row["code"] == REFRESH
    assert "실제 daily_report_sales_20260714.xlsx" in excel_row["근거"]
    assert "현재 생성 예정 daily_report_sales_20260715.xlsx" in excel_row["근거"]


def test_stale_or_missing_audit_log_requires_refresh() -> None:
    kwargs = _base_kwargs()
    kwargs["audit_logs"] = pd.DataFrame(
        [
            {"검증 항목": "pytest", "상태": "24시간 이내"},
            {"검증 항목": "Gate Runner", "상태": "갱신 필요"},
            {"검증 항목": "금지 패턴", "상태": "확인 필요"},
        ]
    )

    result = build_operational_closeout_summary(**kwargs)
    audit_row = result["items"].loc[
        result["items"]["단계"] == "저장 검증 로그"
    ].iloc[0]

    assert result["overall_code"] == REFRESH
    assert audit_row["code"] == REFRESH
    assert "Gate Runner" in audit_row["근거"]
    assert "금지 패턴" in audit_row["근거"]


def test_missing_selection_and_report_are_both_blockers() -> None:
    kwargs = _base_kwargs()
    kwargs["selected_row"] = {}
    kwargs["report_text"] = "입력 후 계산됩니다."

    result = build_operational_closeout_summary(**kwargs)

    assert result["overall_code"] == BLOCKED
    assert result["blocked_count"] == 2
    assert set(
        result["items"].loc[result["items"]["code"] == BLOCKED, "단계"]
    ) == {"예측·전략 확정", "보고문"}


def test_closeout_builder_does_not_mutate_input_frames_or_mappings() -> None:
    kwargs = _base_kwargs()
    logs = kwargs["audit_logs"]
    assert isinstance(logs, pd.DataFrame)
    logs_before = logs.copy(deep=True)
    validation_before = dict(kwargs["validation_result"])
    selection_before = dict(kwargs["selected_row"])

    build_operational_closeout_summary(**kwargs)

    assert_frame_equal(logs, logs_before)
    assert kwargs["validation_result"] == validation_before
    assert kwargs["selected_row"] == selection_before


def test_report_and_audit_pages_share_one_closeout_renderer() -> None:
    report_source = inspect.getsource(app._render_report_detail_page)
    audit_source = inspect.getsource(app._render_audit_detail_page)
    renderer_source = inspect.getsource(app._render_operational_closeout_summary)

    assert "_build_operational_closeout_from_context(" in report_source
    assert "_render_operational_closeout_summary(closeout, detailed=False)" in report_source
    assert "_build_operational_closeout_from_context(" in audit_source
    assert "_render_operational_closeout_summary(closeout, detailed=True)" in audit_source
    assert "운영 마감 상태" in renderer_source
    assert "Excel·감사 로그·예측값을 생성하거나 수정하지 않습니다." in renderer_source


def test_closeout_module_has_no_forecast_or_output_write_dependencies() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "forecast_models" not in source
    assert "scenario_runner" not in source
    assert "excel_exporter" not in source
    assert "open(" not in source
    assert "write_" not in source
    assert "to_csv(" not in source
    assert "to_excel(" not in source
    assert f'"{PASS}"' in source
