"""Build chart-ready dataframes for forecast history and Backtest views."""

from __future__ import annotations

from typing import Any

import pandas as pd


FORECAST_TREND_COLUMNS: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "forecast_model",
    "forecast_amount",
    "forecast_count",
)
MODEL_ERROR_COLUMNS: tuple[str, ...] = (
    "forecast_model",
    "sample_count",
    "mean_abs_error",
    "mean_error_rate",
    "median_error_rate",
    "bias",
)
TARGET_STATUS_DISTRIBUTION_COLUMNS: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "target_status",
    "scenario_count",
    "scenario_share",
)
GAP_SURPLUS_TREND_COLUMNS: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "forecast_model",
    "gap_to_target",
    "surplus_to_target",
)
STRATEGY_MIX_COLUMNS: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "strategy_id",
    "strategy_type",
    "scenario_count",
    "scenario_share",
)
VISUALIZATION_KEYS: tuple[str, ...] = (
    "forecast_trend",
    "model_error",
    "target_status_distribution",
    "gap_surplus_trend",
    "strategy_mix",
    "warnings",
)


def build_forecast_trend_df(forecast_history: pd.DataFrame | Any) -> pd.DataFrame:
    """Return forecast amount trend rows by month, as-of date, metric, and model."""
    history = _as_dataframe(forecast_history)
    required = ("target_month", "as_of_date", "metric", "forecast_model", "forecast_amount")
    if history.empty or not _has_columns(history, required):
        return pd.DataFrame(columns=FORECAST_TREND_COLUMNS)

    working = history.loc[:, list(required)].copy()
    working["forecast_amount"] = pd.to_numeric(
        working["forecast_amount"],
        errors="coerce",
    )
    trend = (
        working.dropna(subset=["forecast_amount"])
        .groupby(["target_month", "as_of_date", "metric", "forecast_model"], dropna=False)
        .agg(
            forecast_amount=("forecast_amount", "mean"),
            forecast_count=("forecast_amount", "size"),
        )
        .reset_index()
    )
    return _ordered(trend, FORECAST_TREND_COLUMNS, ["target_month", "as_of_date", "forecast_model"])


def build_model_error_df(backtest_df: pd.DataFrame | Any) -> pd.DataFrame:
    """Return model-level Backtest error summary for visualization."""
    backtest = _as_dataframe(backtest_df)
    required = ("forecast_model", "abs_error", "error_rate", "forecast_error")
    if backtest.empty or not _has_columns(backtest, required):
        return pd.DataFrame(columns=MODEL_ERROR_COLUMNS)

    working = backtest.loc[:, list(required)].copy()
    for column in ("abs_error", "error_rate", "forecast_error"):
        working[column] = pd.to_numeric(working[column], errors="coerce")

    summary = (
        working.groupby("forecast_model", dropna=False)
        .agg(
            sample_count=("error_rate", "size"),
            mean_abs_error=("abs_error", "mean"),
            mean_error_rate=("error_rate", "mean"),
            median_error_rate=("error_rate", "median"),
            bias=("forecast_error", "mean"),
        )
        .reset_index()
    )
    return _ordered(summary, MODEL_ERROR_COLUMNS, ["mean_error_rate", "forecast_model"])


def build_target_status_distribution_df(
    forecast_history: pd.DataFrame | Any,
) -> pd.DataFrame:
    """Return scenario-count shares by target status for stacked charts."""
    history = _as_dataframe(forecast_history)
    required = ("target_month", "as_of_date", "metric", "target_status")
    if history.empty or not _has_columns(history, required):
        return pd.DataFrame(columns=TARGET_STATUS_DISTRIBUTION_COLUMNS)

    grouped = (
        history.loc[:, list(required)]
        .groupby(list(required), dropna=False)
        .size()
        .rename("scenario_count")
        .reset_index()
    )
    total_keys = ["target_month", "as_of_date", "metric"]
    totals = grouped.groupby(total_keys, dropna=False)["scenario_count"].transform("sum")
    grouped["scenario_share"] = grouped["scenario_count"] / totals.mask(totals == 0)
    return _ordered(
        grouped,
        TARGET_STATUS_DISTRIBUTION_COLUMNS,
        ["target_month", "as_of_date", "target_status"],
    )


def build_gap_surplus_trend_df(forecast_history: pd.DataFrame | Any) -> pd.DataFrame:
    """Return average gap and surplus trend rows by model."""
    history = _as_dataframe(forecast_history)
    required = (
        "target_month",
        "as_of_date",
        "metric",
        "forecast_model",
        "gap_to_target",
        "surplus_to_target",
    )
    if history.empty or not _has_columns(history, required):
        return pd.DataFrame(columns=GAP_SURPLUS_TREND_COLUMNS)

    working = history.loc[:, list(required)].copy()
    for column in ("gap_to_target", "surplus_to_target"):
        working[column] = pd.to_numeric(working[column], errors="coerce")

    trend = (
        working.groupby(["target_month", "as_of_date", "metric", "forecast_model"], dropna=False)
        .agg(
            gap_to_target=("gap_to_target", "mean"),
            surplus_to_target=("surplus_to_target", "mean"),
        )
        .reset_index()
    )
    return _ordered(trend, GAP_SURPLUS_TREND_COLUMNS, ["target_month", "as_of_date", "forecast_model"])


def build_strategy_mix_df(forecast_history: pd.DataFrame | Any) -> pd.DataFrame:
    """Return strategy mix rows for scenario composition visuals."""
    history = _as_dataframe(forecast_history)
    required = ("target_month", "as_of_date", "metric", "strategy_id", "strategy_type")
    if history.empty or not _has_columns(history, required):
        return pd.DataFrame(columns=STRATEGY_MIX_COLUMNS)

    grouped = (
        history.loc[:, list(required)]
        .groupby(list(required), dropna=False)
        .size()
        .rename("scenario_count")
        .reset_index()
    )
    total_keys = ["target_month", "as_of_date", "metric"]
    totals = grouped.groupby(total_keys, dropna=False)["scenario_count"].transform("sum")
    grouped["scenario_share"] = grouped["scenario_count"] / totals.mask(totals == 0)
    return _ordered(grouped, STRATEGY_MIX_COLUMNS, ["target_month", "as_of_date", "strategy_id"])


def build_visualization(
    forecast_history: pd.DataFrame | Any | None = None,
    backtest_df: pd.DataFrame | Any | None = None,
) -> dict[str, pd.DataFrame | list[str]]:
    """Return all visualization-ready tables for the history and Backtest tab."""
    warnings: list[str] = []
    history = pd.DataFrame() if forecast_history is None else _as_dataframe(forecast_history)
    backtest = pd.DataFrame() if backtest_df is None else _as_dataframe(backtest_df)

    if history.empty:
        warnings.append("forecast_history is empty; forecast history visuals are empty.")
    if backtest.empty:
        warnings.append("backtest_df is empty; model error visuals are empty.")

    return {
        "forecast_trend": build_forecast_trend_df(history),
        "model_error": build_model_error_df(backtest),
        "target_status_distribution": build_target_status_distribution_df(history),
        "gap_surplus_trend": build_gap_surplus_trend_df(history),
        "strategy_mix": build_strategy_mix_df(history),
        "warnings": warnings,
    }


def _as_dataframe(value: pd.DataFrame | Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    raise ValueError("visualization input must be a DataFrame.")


def _has_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> bool:
    return set(columns).issubset(df.columns)


def _ordered(df: pd.DataFrame, columns: tuple[str, ...], sort_by: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = pd.NA
    if result.empty:
        return pd.DataFrame(columns=columns)
    available_sort = [column for column in sort_by if column in result.columns]
    if available_sort:
        result = result.sort_values(available_sort, kind="mergesort")
    return result.loc[:, list(columns)].reset_index(drop=True)
