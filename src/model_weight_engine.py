"""Calculate auxiliary model weights from Backtest error summaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


MODEL_WEIGHT_COLUMNS: tuple[str, ...] = (
    "forecast_model",
    "sample_count",
    "error_rate",
    "model_weight",
    "weight_status",
)
WEIGHTED_FORECAST_COLUMNS: tuple[str, ...] = (
    "forecast_model",
    "forecast_amount",
    "model_weight",
    "weighted_forecast_amount",
)


def calculate_model_weights(
    model_summary_df: pd.DataFrame | Any,
    min_samples: int = 3,
) -> pd.DataFrame:
    """Return ModelWeights where lower error_rate receives higher model_weight."""
    summary = _as_dataframe(model_summary_df, "model_summary_df")
    if summary.empty or "forecast_model" not in summary.columns:
        return pd.DataFrame(columns=MODEL_WEIGHT_COLUMNS)

    working = summary.copy()
    if "sample_count" not in working.columns:
        working["sample_count"] = 0
    working["sample_count"] = pd.to_numeric(working["sample_count"], errors="coerce").fillna(0)
    working["error_rate"] = _select_error_rate(working)
    working = working.loc[working["forecast_model"].notna()].copy()
    if working.empty:
        return pd.DataFrame(columns=MODEL_WEIGHT_COLUMNS)

    eligible = working.loc[
        (working["sample_count"] >= min_samples) & working["error_rate"].notna()
    ].copy()
    if eligible.empty:
        return _equal_fallback_weights(working, "fallback_equal_weight")

    result = working.copy()
    result["model_weight"] = 0.0
    result["weight_status"] = "insufficient_samples"

    zero_error = eligible.loc[eligible["error_rate"] == 0]
    if not zero_error.empty:
        assigned_weight = 1.0 / len(zero_error)
        result.loc[zero_error.index, "model_weight"] = assigned_weight
        result.loc[zero_error.index, "weight_status"] = "zero_error_weighted"
    else:
        positive = eligible.loc[eligible["error_rate"] > 0].copy()
        if positive.empty:
            return _equal_fallback_weights(working, "fallback_equal_weight")
        inverse_error = 1.0 / positive["error_rate"]
        result.loc[positive.index, "model_weight"] = inverse_error / inverse_error.sum()
        result.loc[positive.index, "weight_status"] = "error_weighted"

    return _finalize_weights(result)


def apply_model_weights(
    forecast_results_df: pd.DataFrame | Any,
    weights: pd.DataFrame | Mapping[str, float] | Any,
) -> pd.DataFrame:
    """Annotate forecast rows with model_weight and weighted contribution."""
    forecasts = _as_dataframe(forecast_results_df, "forecast_results_df")
    if forecasts.empty:
        return pd.DataFrame(columns=[*forecasts.columns, "model_weight", "weighted_forecast_amount"])
    if "forecast_model" not in forecasts.columns or "forecast_amount" not in forecasts.columns:
        raise ValueError("forecast_results_df requires forecast_model and forecast_amount.")

    weight_df = _normalize_weights(weights)
    result = forecasts.copy()
    result["forecast_amount"] = pd.to_numeric(result["forecast_amount"], errors="coerce")
    if weight_df.empty:
        equal_weight = 1.0 / result["forecast_model"].nunique()
        result["model_weight"] = equal_weight
    else:
        result = result.merge(
            weight_df.loc[:, ["forecast_model", "model_weight"]],
            on="forecast_model",
            how="left",
        )
        missing_weight = result["model_weight"].isna()
        if missing_weight.any():
            remaining_weight = max(0.0, 1.0 - result.loc[~missing_weight, "model_weight"].sum())
            missing_models = result.loc[missing_weight, "forecast_model"].nunique()
            fill_weight = remaining_weight / missing_models if missing_models else 0.0
            result.loc[missing_weight, "model_weight"] = fill_weight

    result["weighted_forecast_amount"] = result["forecast_amount"] * result["model_weight"]
    return result.reset_index(drop=True)


def calculate_weighted_forecast(
    forecast_results_df: pd.DataFrame | Any,
    weights: pd.DataFrame | Mapping[str, float] | Any,
) -> dict[str, object]:
    """Return a weighted forecast as an auxiliary metric, not a model replacement."""
    forecasts = _as_dataframe(forecast_results_df, "forecast_results_df")
    if forecasts.empty:
        return {
            "weighted_forecast": float("nan"),
            "model_contributions": pd.DataFrame(columns=WEIGHTED_FORECAST_COLUMNS),
            "warnings": ["forecast_results_df is empty."],
        }
    if "forecast_model" not in forecasts.columns or "forecast_amount" not in forecasts.columns:
        raise ValueError("forecast_results_df requires forecast_model and forecast_amount.")

    model_forecasts = (
        forecasts.loc[:, ["forecast_model", "forecast_amount"]]
        .assign(forecast_amount=lambda df: pd.to_numeric(df["forecast_amount"], errors="coerce"))
        .dropna(subset=["forecast_amount"])
        .groupby("forecast_model", dropna=False, as_index=False)["forecast_amount"]
        .mean()
    )
    weighted = apply_model_weights(model_forecasts, weights)
    weighted_forecast = float(weighted["weighted_forecast_amount"].sum())
    return {
        "weighted_forecast": weighted_forecast,
        "model_contributions": weighted.loc[:, list(WEIGHTED_FORECAST_COLUMNS)],
        "warnings": [],
    }


def _select_error_rate(df: pd.DataFrame) -> pd.Series:
    for column in ("mean_error_rate", "error_rate", "median_error_rate"):
        if column in df.columns:
            return pd.to_numeric(df[column], errors="coerce")
    return pd.Series([pd.NA] * len(df), index=df.index, dtype="Float64")


def _equal_fallback_weights(df: pd.DataFrame, status: str) -> pd.DataFrame:
    result = df.copy()
    result["model_weight"] = 1.0 / len(result) if len(result) else 0.0
    result["weight_status"] = status
    return _finalize_weights(result)


def _finalize_weights(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    total_weight = pd.to_numeric(result["model_weight"], errors="coerce").fillna(0).sum()
    if total_weight > 0:
        result["model_weight"] = result["model_weight"] / total_weight
    for column in MODEL_WEIGHT_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    return result.loc[:, list(MODEL_WEIGHT_COLUMNS)].reset_index(drop=True)


def _normalize_weights(weights: pd.DataFrame | Mapping[str, float] | Any) -> pd.DataFrame:
    if isinstance(weights, pd.DataFrame):
        if weights.empty:
            return pd.DataFrame(columns=["forecast_model", "model_weight"])
        if "forecast_model" not in weights.columns or "model_weight" not in weights.columns:
            raise ValueError("weights DataFrame requires forecast_model and model_weight.")
        result = weights.loc[:, ["forecast_model", "model_weight"]].copy()
    elif isinstance(weights, Mapping):
        result = pd.DataFrame(
            {
                "forecast_model": list(weights.keys()),
                "model_weight": list(weights.values()),
            }
        )
    elif weights is None:
        return pd.DataFrame(columns=["forecast_model", "model_weight"])
    else:
        raise ValueError("weights must be a DataFrame, mapping, or None.")

    result["model_weight"] = pd.to_numeric(result["model_weight"], errors="coerce").fillna(0.0)
    total_weight = result["model_weight"].sum()
    if total_weight > 0:
        result["model_weight"] = result["model_weight"] / total_weight
    return result.reset_index(drop=True)


def _as_dataframe(value: pd.DataFrame | Any, name: str) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    raise ValueError(f"{name} must be a DataFrame.")
