"""Actual daily calculations for cumulative forecast inputs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from src.schema import get_metric_columns


def add_actual_daily_columns(
    df: pd.DataFrame,
    metric: str,
    as_of_date: object,
    config: Mapping[str, Any] | None,
) -> pd.DataFrame:
    """Return a copy with target cumulative and actual daily columns added."""
    _ = config
    columns = get_metric_columns(metric)
    target_daily_col = columns["target_daily"]
    actual_cum_col = columns["actual_cum"]
    target_cum_col = columns["target_cum"]
    actual_daily_col = columns["actual_daily"]

    missing_columns = [
        column
        for column in ("date", target_daily_col, actual_cum_col)
        if column not in df.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required input columns: {missing}")

    result = df.copy()
    dates = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    target_daily = pd.to_numeric(result[target_daily_col], errors="raise").astype(
        "float64"
    )
    actual_cum = _coerce_actual_cum(result[actual_cum_col])

    is_past_or_current = dates <= as_of_timestamp
    is_remaining = dates > as_of_timestamp
    missing_actual_cum = is_past_or_current & actual_cum.isna()
    if missing_actual_cum.any():
        raise ValueError("actual_cum must be populated through as_of_date.")

    actual_input_mask = is_past_or_current & actual_cum.notna()

    actual_daily = pd.Series(float("nan"), index=result.index, dtype="float64")
    negative_actual_flag = pd.Series(False, index=result.index, dtype=bool)

    actual_values = actual_cum.loc[actual_input_mask]
    if not actual_values.empty:
        daily_values = actual_values.diff()
        daily_values.iloc[0] = actual_values.iloc[0]
        actual_daily.loc[daily_values.index] = daily_values
        negative_actual_flag.loc[daily_values[daily_values < 0].index] = True

    result[target_cum_col] = target_daily.cumsum()
    result[actual_daily_col] = actual_daily
    result["negative_actual_flag"] = negative_actual_flag
    result["is_past_or_current"] = is_past_or_current
    result["is_remaining"] = is_remaining

    return result


def _coerce_actual_cum(values: pd.Series) -> pd.Series:
    cleaned = values.replace(r"^\s*$", pd.NA, regex=True)
    return pd.to_numeric(cleaned, errors="raise").astype("float64")
