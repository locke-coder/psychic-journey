"""Build readable Insights rows for history and Backtest artifacts."""

from __future__ import annotations

from typing import Any

import pandas as pd


INSIGHTS_COLUMNS: tuple[str, ...] = ("insight",)


def build_insights(
    forecast_history: pd.DataFrame | Any | None = None,
    backtest_df: pd.DataFrame | Any | None = None,
    model_weights: pd.DataFrame | Any | None = None,
    confidence_band: dict[str, Any] | pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return an Insights dataframe with concise interpretation rows."""
    insights: list[str] = []
    history = _as_dataframe(forecast_history)
    backtest = _as_dataframe(backtest_df)
    weights = _as_dataframe(model_weights)

    if history.empty:
        insights.append("forecast_history is empty; save forecast runs before comparing trends.")
    else:
        insights.append(f"forecast_history contains {len(history)} rows for visualization.")

    if backtest.empty:
        insights.append("Backtest data is empty; final_actuals are needed for error insights.")
    else:
        insights.append(f"Backtest contains {len(backtest)} rows for model error review.")

    if weights.empty:
        insights.append("ModelWeights are not available yet.")
    else:
        insights.append("ModelWeights are available as auxiliary decision support.")

    if _confidence_band_is_empty(confidence_band):
        insights.append("ConfidenceBand is not available yet.")
    else:
        insights.append("ConfidenceBand is available for conservative/base/aggressive views.")

    return pd.DataFrame({"insight": insights}).loc[:, list(INSIGHTS_COLUMNS)]


def _as_dataframe(value: pd.DataFrame | Any | None) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return pd.DataFrame()


def _confidence_band_is_empty(value: dict[str, Any] | pd.DataFrame | None) -> bool:
    if value is None:
        return True
    if isinstance(value, pd.DataFrame):
        return value.empty
    if isinstance(value, dict):
        return not any(key in value for key in ("confidence_lower", "confidence_upper"))
    return True
