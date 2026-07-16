"""Copy-based DataFrame formatters for Streamlit display tables."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping

import pandas as pd

from src.display_labels import get_metric_label, get_status_label, get_strategy_label
from src.ui_formatters import (
    _is_missing,
    format_amount,
    format_date,
    format_optional_amount,
    format_rate,
)


REMAINING_OPERATION_DIRECTION_COLUMNS = (
    "date",
    "date_label",
    "scenario_id",
    "strategy_type",
    "operation_mode",
    "day_type",
    "close_type",
    "original_target",
    "uplift",
    "revised_target",
    "expected_daily",
    "expected_rate",
    "direction",
    "direction_detail",
)


def format_remaining_operation_direction_df(source: pd.DataFrame) -> pd.DataFrame:
    """Return the remaining-operation table in its display-only shape."""
    result = source.copy()
    result = result.loc[:, list(REMAINING_OPERATION_DIRECTION_COLUMNS)]
    result["date"] = result["date"].map(format_date)
    for column in ("original_target", "uplift", "revised_target", "expected_daily"):
        result[column] = result[column].map(format_amount)
    result["expected_rate"] = result["expected_rate"].map(format_rate)
    return result.rename(
        columns={
            "date": "날짜",
            "date_label": "날짜 라벨",
            "scenario_id": "시나리오",
            "strategy_type": "전략 구분",
            "operation_mode": "운영 모드",
            "day_type": "일자 구분",
            "close_type": "마감 유형",
            "original_target": "기존 일 목표",
            "uplift": "업리프트",
            "revised_target": "관리 목표",
            "expected_daily": "예상 일실적",
            "expected_rate": "예상 달성률",
            "direction": "운영 방향",
            "direction_detail": "방향 해석",
        }
    )


def format_daily_forecast_detail_df(detail: pd.DataFrame) -> pd.DataFrame:
    """Return a formatted copy of the selected scenario's daily detail."""
    result = detail.copy()
    result["date"] = result["date"].map(format_date)
    result["daily_expected"] = result["daily_expected"].map(format_optional_amount)
    result["forecast_cum"] = result["forecast_cum"].map(format_amount)
    result["target_cum"] = result["target_cum"].map(format_amount)
    result["achievement_rate"] = result["achievement_rate"].map(format_rate)
    result["target_achievement_rate"] = result["target_achievement_rate"].map(format_rate)
    return result.rename(
        columns={
            "date": "날짜",
            "scenario_id": "시나리오",
            "series_type": "구분",
            "day_type": "일자 구분",
            "close_type": "마감 유형",
            "daily_expected": "당일 추정",
            "forecast_cum": "누적 실적/예상",
            "target_cum": "누적 목표선",
            "achievement_rate": "월 목표 달성률",
            "target_achievement_rate": "계획선 달성률",
        }
    )


def format_display_df(
    df: pd.DataFrame,
    *,
    amount_columns: Collection[str],
    rate_columns: Collection[str],
    technical_code_columns: Collection[str],
    display_column_labels: Mapping[str, str],
    display_value_labels: Mapping[str, object],
    validation_message_formatter: Callable[[object], str],
) -> pd.DataFrame:
    """Format a generic app table while preserving its current empty-frame behavior."""
    if df.empty:
        return df

    result = df.copy()
    if {"item", "value"}.issubset(result.columns):
        original_items = result["item"].astype(str)
        result["value"] = [
            _format_named_value(
                item,
                value,
                amount_columns=amount_columns,
                rate_columns=rate_columns,
            )
            for item, value in zip(result["item"], result["value"])
        ]
        result["value"] = result["value"].map(
            lambda value: localize_display_value(
                value,
                display_value_labels=display_value_labels,
                validation_message_formatter=validation_message_formatter,
            )
        )
        result["item"] = original_items.map(
            lambda column: display_column_label(
                column,
                display_column_labels=display_column_labels,
            )
        )
        return result

    for column in result.columns:
        if column in technical_code_columns:
            result[column] = result[column].map(
                lambda value: "" if _is_missing(value) else str(value)
            )
        elif column in amount_columns:
            result[column] = result[column].map(format_amount)
        elif column in rate_columns:
            result[column] = result[column].map(format_rate)
        elif "date" in str(column).lower():
            result[column] = result[column].map(format_date)
        else:
            result[column] = result[column].map(
                lambda value: localize_display_value(
                    value,
                    display_value_labels=display_value_labels,
                    validation_message_formatter=validation_message_formatter,
                )
            )
    return result.rename(
        columns={
            column: display_column_label(
                column,
                display_column_labels=display_column_labels,
            )
            for column in result.columns
        }
    )


def display_column_label(
    column: object,
    *,
    display_column_labels: Mapping[str, str],
) -> str:
    text = str(column)
    return display_column_labels.get(text, get_metric_label(text))


def localize_display_value(
    value: object,
    *,
    display_value_labels: Mapping[str, object],
    validation_message_formatter: Callable[[object], str],
) -> object:
    if _is_missing(value):
        return value
    if isinstance(value, bool):
        return "예" if value else "아니오"
    if isinstance(value, (list, tuple, set)):
        localized = [validation_message_formatter(item) for item in value]
        return ", ".join(str(item) for item in localized if str(item))
    text = str(value)
    if text in {"UNDER_TARGET", "ON_TARGET", "OVER_TARGET", "UNKNOWN_TARGET_STATUS"}:
        return get_status_label(text)
    strategy_label = get_strategy_label(text)
    if strategy_label != text:
        return strategy_label
    return display_value_labels.get(text, value)


def _format_named_value(
    name: object,
    value: object,
    *,
    amount_columns: Collection[str],
    rate_columns: Collection[str],
) -> object:
    column_name = str(name)
    if column_name in amount_columns:
        return format_amount(value)
    if column_name in rate_columns:
        return format_rate(value)
    if "date" in column_name.lower():
        return format_date(value)
    return value
