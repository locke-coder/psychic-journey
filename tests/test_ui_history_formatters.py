from __future__ import annotations

import pandas as pd
import pytest

from src.ui_history_formatters import (
    format_historical_forecast_comparison_df,
    format_historical_monthly_summary_df,
    format_historical_stage_df,
)


def test_format_historical_forecast_comparison_df_preserves_contract() -> None:
    row = {
        "comparison_group": "현재",
        "basis": "선택 시나리오",
        "forecast_amount": 12.34,
        "forecast_rate": 0.5,
        "diff_vs_target": -1.25,
        "diff_vs_historical_median": None,
        "extra": "제외",
    }
    source = pd.DataFrame([row], columns=list(reversed(row)))
    original = source.copy(deep=True)

    result = format_historical_forecast_comparison_df(source)

    assert result is not source
    pd.testing.assert_frame_equal(source, original)
    assert result.iloc[0].to_dict() == {
        "구분": "현재",
        "비교 기준": "선택 시나리오",
        "월말 예상 실적": "12.3억 원",
        "월 목표 대비": "50.0%",
        "목표 대비": "-1.2억 원",
        "과거 중앙값 대비": "계산 불가",
    }


def test_format_historical_stage_df_preserves_contract() -> None:
    row = {
        "month": "2026-05",
        "matched_business_day_no": 10,
        "as_of_target_cum": 100.0,
        "as_of_actual_cum": 95.55,
        "as_of_achievement_rate": 0.9555,
        "monthly_target": 200.0,
        "final_actual_cum": 210.0,
        "final_achievement_rate": 1.05,
        "remaining_actual_growth": 114.45,
        "extra": "제외",
    }
    source = pd.DataFrame([row], columns=list(reversed(row)))
    original = source.copy(deep=True)

    result = format_historical_stage_df(source)

    assert result is not source
    pd.testing.assert_frame_equal(source, original)
    assert result.iloc[0].to_dict() == {
        "월": "2026-05",
        "비교 영업일차": 10,
        "당시 누적 목표": "100.0억 원",
        "당시 누적 실적": "95.5억 원",
        "당시 누적 달성률": "95.5%",
        "월 목표": "200.0억 원",
        "최종 누적 실적": "210.0억 원",
        "최종 달성률": "105.0%",
        "비교일 이후 증가 실적": "114.5억 원",
    }


def test_format_historical_monthly_summary_df_preserves_contract() -> None:
    row = {
        "month": "2026-05",
        "row_count": 20,
        "completed_actual_days": 18,
        "final_business_day_no": 20,
        "monthly_target": 200.0,
        "final_actual_cum": 210.0,
        "final_achievement_rate": 1.05,
        "close_day_count": 4,
        "extra": "제외",
    }
    source = pd.DataFrame([row], columns=list(reversed(row)))
    original = source.copy(deep=True)

    result = format_historical_monthly_summary_df(source)

    assert result is not source
    pd.testing.assert_frame_equal(source, original)
    assert result.iloc[0].to_dict() == {
        "월": "2026-05",
        "행 수": 20,
        "실적 입력일 수": 18,
        "최종 영업일차": 20,
        "월 목표": "200.0억 원",
        "최종 누적 실적": "210.0억 원",
        "최종 달성률": "105.0%",
        "마감일 수": 4,
    }


@pytest.mark.parametrize(
    ("formatter", "source_column", "display_column"),
    [
        (format_historical_forecast_comparison_df, "basis", "비교 기준"),
        (format_historical_stage_df, "month", "월"),
        (format_historical_monthly_summary_df, "row_count", "행 수"),
    ],
)
def test_history_formatters_omit_missing_optional_and_extra_columns(
    formatter,
    source_column: str,
    display_column: str,
) -> None:
    source = pd.DataFrame([{source_column: "값", "extra": "제외"}])

    result = formatter(source)

    assert list(result.columns) == [display_column]
    assert result.iloc[0, 0] == "값"


@pytest.mark.parametrize(
    "formatter",
    [
        format_historical_forecast_comparison_df,
        format_historical_stage_df,
        format_historical_monthly_summary_df,
    ],
)
def test_history_formatters_return_new_empty_frame(formatter) -> None:
    source = pd.DataFrame(columns=["extra"])
    original = source.copy(deep=True)

    result = formatter(source)

    assert result is not source
    assert result.empty
    assert list(result.columns) == []
    pd.testing.assert_frame_equal(source, original)
