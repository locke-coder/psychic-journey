"""Next close-day requirement calculations."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from math import isnan
from typing import Any

import pandas as pd

from src.actual_engine import add_actual_daily_columns
from src.close_cycle_engine import assign_close_cycle_ids, get_next_close_date
from src.schema import get_metric_columns


NextCloseResult = dict[str, object]


def calculate_next_close_required(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | None,
) -> NextCloseResult:
    """Calculate required performance through the next user-marked close day."""
    columns = get_metric_columns(metric)
    _require_columns(
        df,
        ("date", "is_close_day", columns["target_daily"], columns["actual_cum"]),
    )

    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    as_of = as_of_timestamp.date()

    with_actuals = add_actual_daily_columns(df, metric, as_of_date, config)
    with_cycles = assign_close_cycle_ids(with_actuals)

    dates = pd.to_datetime(with_cycles["date"], errors="raise").dt.normalize()
    target_daily = pd.to_numeric(
        with_cycles[columns["target_daily"]],
        errors="raise",
    ).astype("float64")
    actual_cum = _coerce_actual_cum(with_cycles[columns["actual_cum"]])
    actual_daily = pd.to_numeric(
        with_cycles[columns["actual_daily"]],
        errors="coerce",
    ).astype("float64")

    as_of_mask = dates == as_of_timestamp
    past_or_current_mask = dates <= as_of_timestamp

    warnings: list[str] = []
    current_actual_cum = _actual_cum_at_as_of(actual_cum, as_of_mask, warnings)
    current_target_cum = float(target_daily.loc[past_or_current_mask].sum())

    if _has_negative_actual(with_cycles):
        warnings.append("Negative actual_daily values are present before or at as_of_date.")

    next_close = get_next_close_date(df, as_of_date)
    if next_close is None:
        warnings.append("No next close day is present after as_of_date.")
        next_close_target_cum = None
        required_to_recover_next_close_cum = None
        current_cycle_target = None
        current_cycle_actual_to_date = None
        required_to_hit_current_cycle = None
    else:
        next_close_timestamp = pd.Timestamp(next_close).normalize()
        next_close_target_cum = float(
            target_daily.loc[dates <= next_close_timestamp].sum()
        )
        required_to_recover_next_close_cum = _required_gap(
            next_close_target_cum,
            current_actual_cum,
        )

        cycle_mask = _cycle_mask_for_close_date(
            with_cycles,
            dates,
            next_close_timestamp,
        )
        current_cycle_target = float(target_daily.loc[cycle_mask].sum())
        current_cycle_actual_to_date = _cycle_actual_to_date(
            actual_daily,
            cycle_mask,
            past_or_current_mask,
            current_actual_cum,
        )
        required_to_hit_current_cycle = _required_gap(
            current_cycle_target,
            current_cycle_actual_to_date,
        )

    return {
        "as_of_date": as_of,
        "next_close_date": next_close,
        "current_actual_cum": current_actual_cum,
        "current_target_cum": current_target_cum,
        "next_close_target_cum": next_close_target_cum,
        "required_to_recover_next_close_cum": required_to_recover_next_close_cum,
        "current_cycle_target": current_cycle_target,
        "current_cycle_actual_to_date": current_cycle_actual_to_date,
        "required_to_hit_current_cycle": required_to_hit_current_cycle,
        "warnings": warnings,
    }


def _actual_cum_at_as_of(
    actual_cum: pd.Series,
    as_of_mask: pd.Series,
    warnings: list[str],
) -> float:
    if not as_of_mask.any():
        warnings.append("Calculation unavailable: as_of_date is not present in input rows.")
        return float("nan")

    as_of_actuals = actual_cum.loc[as_of_mask].dropna()
    if as_of_actuals.empty:
        warnings.append(
            "Calculation unavailable: actual cumulative value is missing at as_of_date."
        )
        return float("nan")

    return float(as_of_actuals.iloc[-1])


def _cycle_mask_for_close_date(
    with_cycles: pd.DataFrame,
    dates: pd.Series,
    close_timestamp: pd.Timestamp,
) -> pd.Series:
    close_rows = with_cycles.loc[dates == close_timestamp, "cycle_id"]
    if close_rows.empty:
        return pd.Series(False, index=with_cycles.index, dtype=bool)

    cycle_id = close_rows.iloc[-1]
    return with_cycles["cycle_id"] == cycle_id


def _cycle_actual_to_date(
    actual_daily: pd.Series,
    cycle_mask: pd.Series,
    past_or_current_mask: pd.Series,
    current_actual_cum: float,
) -> float | None:
    if _is_nan(current_actual_cum):
        return None

    return float(actual_daily.loc[cycle_mask & past_or_current_mask].sum())


def _required_gap(target: float | None, actual: float | None) -> float | None:
    if target is None or actual is None or _is_nan(actual):
        return None

    return max(0.0, target - actual)


def _coerce_actual_cum(values: pd.Series) -> pd.Series:
    cleaned = values.replace(r"^\s*$", pd.NA, regex=True)
    return pd.to_numeric(cleaned, errors="raise").astype("float64")


def _has_negative_actual(df: pd.DataFrame) -> bool:
    if "negative_actual_flag" not in df.columns:
        return False

    return bool(df["negative_actual_flag"].fillna(False).any())


def _is_nan(value: float) -> bool:
    try:
        return isnan(value)
    except TypeError:
        return False


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required input columns: {missing}")
