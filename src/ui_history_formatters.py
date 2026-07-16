"""Display-only DataFrame formatters for historical and backtest tables."""

from __future__ import annotations

import pandas as pd

from src.ui_formatters import format_amount, format_rate


HISTORICAL_FORECAST_COMPARISON_COLUMNS = (
    "comparison_group",
    "basis",
    "forecast_amount",
    "forecast_rate",
    "diff_vs_target",
    "diff_vs_historical_median",
)
HISTORICAL_STAGE_COLUMNS = (
    "month",
    "matched_business_day_no",
    "as_of_target_cum",
    "as_of_actual_cum",
    "as_of_achievement_rate",
    "monthly_target",
    "final_actual_cum",
    "final_achievement_rate",
    "remaining_actual_growth",
)
HISTORICAL_MONTHLY_SUMMARY_COLUMNS = (
    "month",
    "row_count",
    "completed_actual_days",
    "final_business_day_no",
    "monthly_target",
    "final_actual_cum",
    "final_achievement_rate",
    "close_day_count",
)


def format_historical_forecast_comparison_df(
    comparison_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return the historical forecast comparison in its display-only shape."""
    result = comparison_df.copy()
    result = result.loc[
        :,
        [column for column in HISTORICAL_FORECAST_COMPARISON_COLUMNS if column in result.columns],
    ]
    for column in ("forecast_amount", "diff_vs_target", "diff_vs_historical_median"):
        if column in result.columns:
            result[column] = result[column].map(format_amount)
    if "forecast_rate" in result.columns:
        result["forecast_rate"] = result["forecast_rate"].map(format_rate)
    return result.rename(
        columns={
            "comparison_group": "구분",
            "basis": "비교 기준",
            "forecast_amount": "월말 예상 실적",
            "forecast_rate": "월 목표 대비",
            "diff_vs_target": "목표 대비",
            "diff_vs_historical_median": "과거 중앙값 대비",
        }
    )


def format_historical_stage_df(stage_df: pd.DataFrame) -> pd.DataFrame:
    """Return the same-business-day historical stage table for display."""
    result = stage_df.copy()
    result = result.loc[:, [column for column in HISTORICAL_STAGE_COLUMNS if column in result.columns]]
    for column in (
        "as_of_target_cum",
        "as_of_actual_cum",
        "monthly_target",
        "final_actual_cum",
        "remaining_actual_growth",
    ):
        if column in result.columns:
            result[column] = result[column].map(format_amount)
    for column in ("as_of_achievement_rate", "final_achievement_rate"):
        if column in result.columns:
            result[column] = result[column].map(format_rate)
    return result.rename(
        columns={
            "month": "월",
            "matched_business_day_no": "비교 영업일차",
            "as_of_target_cum": "당시 누적 목표",
            "as_of_actual_cum": "당시 누적 실적",
            "as_of_achievement_rate": "당시 누적 달성률",
            "monthly_target": "월 목표",
            "final_actual_cum": "최종 누적 실적",
            "final_achievement_rate": "최종 달성률",
            "remaining_actual_growth": "비교일 이후 증가 실적",
        }
    )


def format_historical_monthly_summary_df(monthly_summary: pd.DataFrame) -> pd.DataFrame:
    """Return the completed historical month summary for display."""
    result = monthly_summary.copy()
    result = result.loc[
        :,
        [column for column in HISTORICAL_MONTHLY_SUMMARY_COLUMNS if column in result.columns],
    ]
    for column in ("monthly_target", "final_actual_cum"):
        if column in result.columns:
            result[column] = result[column].map(format_amount)
    if "final_achievement_rate" in result.columns:
        result["final_achievement_rate"] = result["final_achievement_rate"].map(format_rate)
    return result.rename(
        columns={
            "month": "월",
            "row_count": "행 수",
            "completed_actual_days": "실적 입력일 수",
            "final_business_day_no": "최종 영업일차",
            "monthly_target": "월 목표",
            "final_actual_cum": "최종 누적 실적",
            "final_achievement_rate": "최종 달성률",
            "close_day_count": "마감일 수",
        }
    )
