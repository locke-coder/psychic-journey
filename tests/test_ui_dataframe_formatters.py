from __future__ import annotations

import pandas as pd
import pytest

from src.ui_dataframe_formatters import (
    REMAINING_OPERATION_DIRECTION_COLUMNS,
    display_column_label,
    format_daily_forecast_detail_df,
    format_display_df,
    format_remaining_operation_direction_df,
    localize_display_value,
)
from src.display_labels import get_status_label, get_strategy_label


AMOUNT_COLUMNS = {"monthly_target"}
RATE_COLUMNS = {"forecast_rate"}
TECHNICAL_CODE_COLUMNS = {"scenario_id"}
DISPLAY_COLUMN_LABELS = {
    "item": "항목",
    "value": "값",
    "scenario_id": "시나리오",
    "monthly_target": "월 전체 목표",
    "forecast_rate": "예상 달성률",
    "as_of_date": "기준일",
    "recommended": "추천 여부",
    "status": "계산 상태",
    "warnings": "확인 사항",
}
DISPLAY_VALUE_LABELS = {"OK": "정상", "Green": "낮음"}


def _validation_message(value: object) -> str:
    return "" if str(value) == "" else f"검증:{value}"


def _format_display(source: pd.DataFrame) -> pd.DataFrame:
    return format_display_df(
        source,
        amount_columns=AMOUNT_COLUMNS,
        rate_columns=RATE_COLUMNS,
        technical_code_columns=TECHNICAL_CODE_COLUMNS,
        display_column_labels=DISPLAY_COLUMN_LABELS,
        display_value_labels=DISPLAY_VALUE_LABELS,
        validation_message_formatter=_validation_message,
    )


def test_format_daily_forecast_detail_df_returns_formatted_copy() -> None:
    source = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-07-14"),
                "scenario_id": "F1-P1",
                "series_type": "ACTUAL",
                "day_type": "비마감일",
                "close_type": "일반",
                "daily_expected": None,
                "forecast_cum": 12.34,
                "target_cum": 20.0,
                "achievement_rate": 0.5,
                "target_achievement_rate": pd.NA,
            }
        ]
    )
    original = source.copy(deep=True)

    result = format_daily_forecast_detail_df(source)

    assert result is not source
    pd.testing.assert_frame_equal(source, original)
    assert list(result.columns) == [
        "날짜",
        "시나리오",
        "구분",
        "일자 구분",
        "마감 유형",
        "당일 추정",
        "누적 실적/예상",
        "누적 목표선",
        "월 목표 달성률",
        "계획선 달성률",
    ]
    assert result.iloc[0].to_dict() == {
        "날짜": "2026-07-14",
        "시나리오": "F1-P1",
        "구분": "ACTUAL",
        "일자 구분": "비마감일",
        "마감 유형": "일반",
        "당일 추정": "-",
        "누적 실적/예상": "12.3억 원",
        "누적 목표선": "20.0억 원",
        "월 목표 달성률": "50.0%",
        "계획선 달성률": "계산 불가",
    }


def test_format_daily_forecast_detail_df_preserves_missing_column_failure() -> None:
    with pytest.raises(KeyError, match="daily_expected"):
        format_daily_forecast_detail_df(pd.DataFrame({"date": ["2026-07-14"]}))


def test_format_remaining_operation_direction_df_selects_and_formats_copy() -> None:
    row = {
        "date": pd.Timestamp("2026-07-15"),
        "date_label": "07-15",
        "scenario_id": "F1-P1",
        "strategy_type": "P1",
        "operation_mode": "목표 보정 필요",
        "day_type": "마감일",
        "close_type": "월마감",
        "original_target": 10.04,
        "uplift": 1.26,
        "revised_target": 11.3,
        "expected_daily": 9.95,
        "expected_rate": 0.875,
        "direction": "상향",
        "direction_detail": "잔여 목표 보정",
        "extra": "표시 제외",
    }
    source = pd.DataFrame([row], columns=list(reversed(row)))
    original = source.copy(deep=True)

    result = format_remaining_operation_direction_df(source)

    assert result is not source
    pd.testing.assert_frame_equal(source, original)
    assert list(result.columns) == [
        "날짜",
        "날짜 라벨",
        "시나리오",
        "전략 구분",
        "운영 모드",
        "일자 구분",
        "마감 유형",
        "기존 일 목표",
        "업리프트",
        "관리 목표",
        "예상 일실적",
        "예상 달성률",
        "운영 방향",
        "방향 해석",
    ]
    assert result.iloc[0].to_dict() == {
        "날짜": "2026-07-15",
        "날짜 라벨": "07-15",
        "시나리오": "F1-P1",
        "전략 구분": "P1",
        "운영 모드": "목표 보정 필요",
        "일자 구분": "마감일",
        "마감 유형": "월마감",
        "기존 일 목표": "10.0억 원",
        "업리프트": "1.3억 원",
        "관리 목표": "11.3억 원",
        "예상 일실적": "9.9억 원",
        "예상 달성률": "87.5%",
        "운영 방향": "상향",
        "방향 해석": "잔여 목표 보정",
    }


def test_format_remaining_operation_direction_df_requires_contract_columns() -> None:
    missing_column = REMAINING_OPERATION_DIRECTION_COLUMNS[-1]
    source = pd.DataFrame(
        [{column: None for column in REMAINING_OPERATION_DIRECTION_COLUMNS if column != missing_column}]
    )

    with pytest.raises(KeyError, match=missing_column):
        format_remaining_operation_direction_df(source)


def test_format_display_df_preserves_empty_frame_identity() -> None:
    source = pd.DataFrame(columns=["scenario_id", "monthly_target"])

    result = _format_display(source)

    assert result is source


def test_format_display_df_formats_all_generic_column_branches_without_mutation() -> None:
    source = pd.DataFrame(
        [
            {
                "scenario_id": pd.NA,
                "monthly_target": 12.34,
                "forecast_rate": 0.5,
                "as_of_date": pd.Timestamp("2026-07-14"),
                "recommended": True,
                "status": "OK",
                "warnings": ["alpha", "beta"],
                "unknown": 7,
            }
        ]
    )
    original = source.copy(deep=True)

    result = _format_display(source)

    assert result is not source
    pd.testing.assert_frame_equal(source, original)
    assert result.iloc[0].to_dict() == {
        "시나리오": "",
        "월 전체 목표": "12.3억 원",
        "예상 달성률": "50.0%",
        "기준일": "2026-07-14",
        "추천 여부": "예",
        "계산 상태": "정상",
        "확인 사항": "검증:alpha, 검증:beta",
        "unknown": 7,
    }


def test_format_display_df_formats_item_value_tables_without_mutation() -> None:
    source = pd.DataFrame(
        {
            "item": ["monthly_target", "forecast_rate", "as_of_date", "status", "warnings"],
            "value": [12.34, 0.5, pd.Timestamp("2026-07-14"), "OK", ["alpha", ""]],
        }
    )
    original = source.copy(deep=True)

    result = _format_display(source)

    assert result is not source
    pd.testing.assert_frame_equal(source, original)
    assert result["item"].tolist() == [
        "월 전체 목표",
        "예상 달성률",
        "기준일",
        "계산 상태",
        "확인 사항",
    ]
    assert result["value"].tolist() == [
        "12.3억 원",
        "50.0%",
        "2026-07-14",
        "정상",
        "검증:alpha",
    ]


def test_localize_display_value_preserves_all_existing_branches() -> None:
    kwargs = {
        "display_value_labels": DISPLAY_VALUE_LABELS,
        "validation_message_formatter": _validation_message,
    }
    marker = object()

    assert localize_display_value(None, **kwargs) is None
    assert localize_display_value(pd.NA, **kwargs) is pd.NA
    assert localize_display_value(True, **kwargs) == "예"
    assert localize_display_value(False, **kwargs) == "아니오"
    assert localize_display_value(["alpha", "beta"], **kwargs) == "검증:alpha, 검증:beta"
    assert localize_display_value("UNDER_TARGET", **kwargs) == get_status_label("UNDER_TARGET")
    assert localize_display_value("P1", **kwargs) == get_strategy_label("P1")
    assert localize_display_value("Green", **kwargs) == "낮음"
    assert localize_display_value(marker, **kwargs) is marker


def test_display_column_label_uses_explicit_mapping_then_metric_fallback() -> None:
    assert (
        display_column_label(
            "monthly_target",
            display_column_labels=DISPLAY_COLUMN_LABELS,
        )
        == "월 전체 목표"
    )
    assert (
        display_column_label(
            "target_status",
            display_column_labels=DISPLAY_COLUMN_LABELS,
        )
        == "목표 상태"
    )
