"""Validation helpers for user-driven forecast input tables."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any

import pandas as pd

from src.schema import VALID_METRICS, get_metric_columns


_TRUE_TOKENS = {"Y", "YES", "TRUE", "1"}
_FALSE_TOKENS = {"N", "NO", "FALSE", "0", ""}


def validate_input(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate input rows and return core cumulative calculation values."""
    errors: list[str] = []
    warnings: list[str] = []
    settings = config or {}

    dates = _coerce_dates(_column_or_na(df, "date", errors), errors)
    business_day_no = _coerce_numeric(
        _column_or_na(df, "business_day_no", errors),
        "business_day_no",
        errors,
    )
    is_close_day = _coerce_is_close_day(
        _column_or_na(df, "is_close_day", errors),
        errors,
    )

    _validate_duplicates(dates, "date", errors)
    _validate_duplicates(business_day_no, "business_day_no", errors)
    if not business_day_no.dropna().is_monotonic_increasing:
        errors.append("business_day_no must be in ascending order.")

    as_of_timestamp = _coerce_as_of_date(as_of_date, errors)
    as_of_mask = pd.Series(False, index=df.index)
    past_or_current_mask = pd.Series(False, index=df.index)
    future_mask = pd.Series(False, index=df.index)
    if as_of_timestamp is not None:
        as_of_mask = dates == as_of_timestamp
        past_or_current_mask = dates <= as_of_timestamp
        future_mask = dates > as_of_timestamp
        if not as_of_mask.any():
            errors.append("as_of_date must exist in the input table.")

    if metric not in VALID_METRICS:
        allowed = ", ".join(VALID_METRICS)
        errors.append(f"metric must be one of: {allowed}.")
        target_daily = pd.Series([pd.NA] * len(df), index=df.index, dtype="float64")
        actual_cum = pd.Series([pd.NA] * len(df), index=df.index, dtype="float64")
    else:
        columns = get_metric_columns(metric)
        target_daily = _coerce_numeric(
            _column_or_na(df, columns["target_daily"], errors),
            columns["target_daily"],
            errors,
        )
        actual_cum = _coerce_numeric(
            _column_or_na(df, columns["actual_cum"], errors),
            columns["actual_cum"],
            errors,
        )

    if target_daily.isna().any():
        errors.append("target_daily must not contain missing or invalid values.")
    if (target_daily < 0).any():
        errors.append("target_daily must not be negative.")

    monthly_target = _safe_sum(target_daily)
    current_target_cum = _safe_sum(target_daily[past_or_current_mask])
    remaining_target = _safe_sum(target_daily[future_mask])

    if monthly_target <= 0:
        errors.append("monthly_target must be greater than 0.")

    if past_or_current_mask.any() and actual_cum[past_or_current_mask].isna().any():
        errors.append("actual_cum must be populated through as_of_date.")

    if future_mask.any() and actual_cum[future_mask].notna().any():
        warnings.append("actual_cum after as_of_date is populated.")

    current_actual_cum = 0.0
    as_of_actual = actual_cum[as_of_mask].dropna()
    if not as_of_actual.empty:
        current_actual_cum = float(as_of_actual.iloc[-1])

    if not is_close_day.any():
        errors.append("At least one is_close_day=True row is required.")

    completed_close_day_count = int((is_close_day & past_or_current_mask).sum())
    if completed_close_day_count < 2:
        warnings.append(
            "F2 fallback warning: fewer than two completed close days exist "
            "through as_of_date."
        )

    _validate_actual_daily(actual_cum, settings, errors, warnings)
    _warn_blank_close_type(df, is_close_day, warnings)

    return {
        "errors": errors,
        "warnings": warnings,
        "monthly_target": monthly_target,
        "current_target_cum": current_target_cum,
        "current_actual_cum": current_actual_cum,
        "remaining_target": remaining_target,
    }


def _column_or_na(
    df: pd.DataFrame,
    column: str,
    errors: list[str],
) -> pd.Series:
    if column not in df.columns:
        errors.append(f"Missing required input column: {column}.")
        return pd.Series([pd.NA] * len(df), index=df.index)
    return df[column]


def _coerce_dates(values: pd.Series, errors: list[str]) -> pd.Series:
    converted = pd.to_datetime(values, errors="coerce").dt.normalize()
    invalid_mask = values.notna() & converted.isna()
    if invalid_mask.any():
        errors.append("date contains missing or invalid values.")
    return converted


def _coerce_as_of_date(value: object, errors: list[str]) -> pd.Timestamp | None:
    try:
        timestamp = pd.Timestamp(value).normalize()
    except (TypeError, ValueError):
        errors.append("as_of_date must be a valid date.")
        return None

    if pd.isna(timestamp):
        errors.append("as_of_date must be a valid date.")
        return None

    return timestamp


def _coerce_numeric(
    values: pd.Series,
    column_name: str,
    errors: list[str],
) -> pd.Series:
    cleaned = values.replace(r"^\s*$", pd.NA, regex=True)
    converted = pd.to_numeric(cleaned, errors="coerce")
    invalid_mask = cleaned.notna() & converted.isna()
    if invalid_mask.any():
        errors.append(f"{column_name} contains invalid numeric values.")
    return converted.astype("float64")


def _coerce_is_close_day(values: pd.Series, errors: list[str]) -> pd.Series:
    coerced: list[bool] = []
    invalid_values: list[object] = []

    for value in values:
        if _is_missing(value):
            coerced.append(False)
            continue

        if isinstance(value, bool):
            coerced.append(value)
            continue

        if isinstance(value, str):
            token = value.strip().upper()
            if token in _TRUE_TOKENS:
                coerced.append(True)
                continue
            if token in _FALSE_TOKENS:
                coerced.append(False)
                continue

        if isinstance(value, Real) and value in (0, 1):
            coerced.append(bool(value))
            continue

        invalid_values.append(value)
        coerced.append(False)

    if invalid_values:
        errors.append("is_close_day contains unsupported values.")

    return pd.Series(coerced, index=values.index)


def _is_missing(value: object) -> bool:
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _validate_duplicates(
    values: pd.Series,
    column_name: str,
    errors: list[str],
) -> None:
    if values.dropna().duplicated().any():
        errors.append(f"{column_name} contains duplicate values.")


def _safe_sum(values: pd.Series) -> float:
    return float(values.dropna().sum())


def _validate_actual_daily(
    actual_cum: pd.Series,
    config: Mapping[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    actual_values = actual_cum.dropna()
    if actual_values.empty:
        return

    actual_daily = actual_values.diff()
    actual_daily.iloc[0] = actual_values.iloc[0]
    negative_daily = actual_daily < 0

    if actual_values.diff().lt(0).any():
        warnings.append("actual_cum decreases in the input table.")

    if negative_daily.any():
        message = "actual_daily calculated from actual_cum is negative."
        if bool(config.get("allow_negative_daily_actual", False)):
            warnings.append(message)
        else:
            errors.append(message)


def _warn_blank_close_type(
    df: pd.DataFrame,
    is_close_day: pd.Series,
    warnings: list[str],
) -> None:
    if "close_type" not in df.columns:
        warnings.append("close_type is missing; blank close_type is allowed.")
        return

    close_type = df["close_type"]
    blank_close_type = close_type.isna() | close_type.astype(str).str.strip().eq("")
    if (is_close_day & blank_close_type).any():
        warnings.append("close_type is blank for one or more close days.")
