"""Backtest forecast history against confirmed month-end actuals."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd


JOIN_KEYS: tuple[str, ...] = ("target_month", "metric")
FORECAST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "target_month",
    "metric",
    "forecast_model",
    "strategy_id",
    "forecast_amount",
)
FINAL_ACTUAL_REQUIRED_COLUMNS: tuple[str, ...] = (
    "target_month",
    "metric",
    "final_actual",
)
BACKTEST_CALC_COLUMNS: tuple[str, ...] = (
    "forecast_error",
    "abs_error",
    "error_rate",
    "signed_error_rate",
    "over_forecast_flag",
    "under_forecast_flag",
)
MODEL_SUMMARY_COLUMNS: tuple[str, ...] = (
    "forecast_model",
    "sample_count",
    "mean_abs_error",
    "mean_error_rate",
    "median_error_rate",
    "bias",
    "best_model_by_error_rate",
)
STRATEGY_SUMMARY_COLUMNS: tuple[str, ...] = (
    "strategy_id",
    "strategy_type",
    "sample_count",
    "mean_abs_error",
    "mean_error_rate",
    "median_error_rate",
    "bias",
)


def build_backtest_dataset(
    forecast_history: pd.DataFrame,
    final_actuals: pd.DataFrame,
) -> pd.DataFrame:
    """Join forecast history to final actuals and calculate row-level errors."""
    forecast = _as_dataframe(forecast_history, "forecast_history")
    actuals = _as_dataframe(final_actuals, "final_actuals")

    if forecast.empty or actuals.empty:
        return _empty_backtest_frame(forecast, actuals)

    _validate_required_columns(
        forecast.columns,
        FORECAST_REQUIRED_COLUMNS,
        "forecast_history",
    )
    _validate_required_columns(
        actuals.columns,
        FINAL_ACTUAL_REQUIRED_COLUMNS,
        "final_actuals",
    )

    forecast_for_join = _normalize_join_keys(forecast)
    actuals_for_join = _normalize_join_keys(actuals)
    actual_columns = _dedupe_columns([*JOIN_KEYS, *actuals_for_join.columns])
    backtest = forecast_for_join.merge(
        actuals_for_join.loc[:, actual_columns],
        on=list(JOIN_KEYS),
        how="inner",
        validate="many_to_one",
    )
    if backtest.empty:
        return _empty_backtest_frame(forecast, actuals)

    backtest["forecast_amount"] = pd.to_numeric(
        backtest["forecast_amount"],
        errors="coerce",
    )
    backtest["final_actual"] = pd.to_numeric(
        backtest["final_actual"],
        errors="coerce",
    )
    backtest["forecast_error"] = (
        backtest["forecast_amount"] - backtest["final_actual"]
    )
    backtest["abs_error"] = backtest["forecast_error"].abs()

    safe_final_actual = backtest["final_actual"].mask(backtest["final_actual"] == 0)
    backtest["error_rate"] = backtest["abs_error"] / safe_final_actual
    backtest["signed_error_rate"] = backtest["forecast_error"] / safe_final_actual
    backtest["over_forecast_flag"] = (backtest["forecast_error"] > 0).astype(object)
    backtest["under_forecast_flag"] = (backtest["forecast_error"] < 0).astype(object)

    return backtest.reset_index(drop=True)


def summarize_by_forecast_model(backtest_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize backtest errors by forecast model."""
    backtest = _as_dataframe(backtest_df, "backtest_df")
    if backtest.empty:
        return pd.DataFrame(columns=MODEL_SUMMARY_COLUMNS)

    summary = _summarize_by(backtest, ("forecast_model",))
    summary["best_model_by_error_rate"] = pd.Series(
        [False] * len(summary),
        dtype=object,
    )

    best_model = get_best_model(summary)
    if best_model is not None:
        summary.loc[
            summary["forecast_model"].astype(str) == str(best_model),
            "best_model_by_error_rate",
        ] = True

    return summary.loc[:, MODEL_SUMMARY_COLUMNS].reset_index(drop=True)


def summarize_by_strategy(backtest_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize backtest errors by strategy."""
    backtest = _as_dataframe(backtest_df, "backtest_df")
    if backtest.empty:
        return pd.DataFrame(columns=STRATEGY_SUMMARY_COLUMNS)

    if "strategy_type" not in backtest.columns:
        backtest = backtest.copy()
        backtest["strategy_type"] = ""

    summary = _summarize_by(backtest, ("strategy_id", "strategy_type"))
    return summary.loc[:, STRATEGY_SUMMARY_COLUMNS].reset_index(drop=True)


def get_best_model(summary_df: pd.DataFrame) -> str | None:
    """Return the model with the lowest finite mean error rate."""
    summary = _as_dataframe(summary_df, "summary_df")
    if summary.empty:
        return None

    _validate_required_columns(
        summary.columns,
        ("forecast_model", "mean_error_rate"),
        "summary_df",
    )
    ranked = summary.copy()
    ranked["mean_error_rate"] = pd.to_numeric(
        ranked["mean_error_rate"],
        errors="coerce",
    )
    sort_columns = ["mean_error_rate", "forecast_model"]
    sort_ascending = [True, True]
    if "mean_abs_error" in ranked.columns:
        ranked["mean_abs_error"] = pd.to_numeric(
            ranked["mean_abs_error"],
            errors="coerce",
        )
        sort_columns.insert(1, "mean_abs_error")
        sort_ascending.insert(1, True)

    ranked = ranked.loc[ranked["mean_error_rate"].notna()]
    if ranked.empty:
        return None

    ranked = ranked.sort_values(
        sort_columns,
        ascending=sort_ascending,
        kind="mergesort",
    )
    return str(ranked.iloc[0]["forecast_model"])


def _summarize_by(
    backtest_df: pd.DataFrame,
    group_columns: tuple[str, ...],
) -> pd.DataFrame:
    required_columns = (
        *group_columns,
        "forecast_error",
        "abs_error",
        "error_rate",
    )
    _validate_required_columns(backtest_df.columns, required_columns, "backtest_df")

    working = backtest_df.copy()
    for column in ("forecast_error", "abs_error", "error_rate"):
        working[column] = pd.to_numeric(working[column], errors="coerce")

    summary = (
        working.groupby(list(group_columns), dropna=False)
        .agg(
            sample_count=("forecast_error", "size"),
            mean_abs_error=("abs_error", "mean"),
            mean_error_rate=("error_rate", "mean"),
            median_error_rate=("error_rate", "median"),
            bias=("forecast_error", "mean"),
        )
        .reset_index()
    )
    return summary


def _empty_backtest_frame(
    forecast_history: pd.DataFrame,
    final_actuals: pd.DataFrame,
) -> pd.DataFrame:
    columns = _dedupe_columns(
        [
            *forecast_history.columns,
            *(column for column in final_actuals.columns if column not in JOIN_KEYS),
            *BACKTEST_CALC_COLUMNS,
        ]
    )
    if not columns:
        columns = _dedupe_columns(
            [
                *FORECAST_REQUIRED_COLUMNS,
                "final_actual",
                *BACKTEST_CALC_COLUMNS,
            ]
        )
    return pd.DataFrame(columns=columns)


def _normalize_join_keys(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for key in JOIN_KEYS:
        normalized[key] = normalized[key].astype(str).str.strip()
    return normalized


def _validate_required_columns(
    columns: Iterable[str],
    required_columns: Iterable[str],
    dataset_name: str,
) -> None:
    present_columns = set(columns)
    missing_columns = [
        column for column in required_columns if column not in present_columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required {dataset_name} columns: {missing}")


def _dedupe_columns(columns: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(columns))


def _as_dataframe(value: Any, dataset_name: str) -> pd.DataFrame:
    if not isinstance(value, pd.DataFrame):
        raise ValueError(f"{dataset_name} must be a DataFrame.")
    return value.copy()
