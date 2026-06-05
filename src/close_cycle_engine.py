"""Close-cycle helpers for user-provided close day schedules."""

from __future__ import annotations

from datetime import date
from numbers import Real

import pandas as pd

from src.actual_engine import add_actual_daily_columns
from src.schema import get_metric_columns


_TRUE_TOKENS = {"Y", "YES", "TRUE", "1"}
_FALSE_TOKENS = {"N", "NO", "FALSE", "0", ""}


def get_completed_close_dates(df: pd.DataFrame, as_of_date: object) -> list[date]:
    """Return close dates on or before as_of_date from input rows only."""
    _require_columns(df, ("date", "is_close_day"))
    dates = _coerce_dates(df["date"])
    is_close_day = _coerce_is_close_day(df["is_close_day"])
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()

    completed_mask = is_close_day & (dates <= as_of_timestamp)
    return _to_date_list(dates.loc[completed_mask].sort_values())


def get_last_two_completed_close_dates(
    df: pd.DataFrame,
    as_of_date: object,
) -> list[date]:
    """Return the two most recent completed close dates in input order."""
    return get_completed_close_dates(df, as_of_date)[-2:]


def get_next_close_date(df: pd.DataFrame, as_of_date: object) -> date | None:
    """Return the first close date after as_of_date, or None when absent."""
    _require_columns(df, ("date", "is_close_day"))
    dates = _coerce_dates(df["date"])
    is_close_day = _coerce_is_close_day(df["is_close_day"])
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()

    next_mask = is_close_day & (dates > as_of_timestamp)
    next_dates = dates.loc[next_mask]
    if next_dates.empty:
        return None
    return next_dates.sort_values().iloc[0].date()


def assign_close_cycle_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with cycle_id assigned from the input close-day rows."""
    _require_columns(df, ("is_close_day",))
    result = df.copy()
    is_close_day = _coerce_is_close_day(result["is_close_day"])

    cycle_ids: list[int] = []
    current_cycle_id = 1
    for is_close in is_close_day:
        cycle_ids.append(current_cycle_id)
        if is_close:
            current_cycle_id += 1

    result["cycle_id"] = cycle_ids
    return result


def build_close_cycle_summary(
    df: pd.DataFrame,
    metric: str,
    as_of_date: object,
) -> pd.DataFrame:
    """Build cycle-level target, actual, and achievement summaries."""
    _require_columns(df, ("date", "is_close_day", "close_type"))
    columns = get_metric_columns(metric)
    with_actuals = add_actual_daily_columns(df, metric, as_of_date, None)
    with_cycles = assign_close_cycle_ids(with_actuals)

    dates = _coerce_dates(with_cycles["date"])
    is_close_day = _coerce_is_close_day(with_cycles["is_close_day"])
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()

    target_daily = pd.to_numeric(
        with_cycles[columns["target_daily"]],
        errors="raise",
    ).astype("float64")
    actual_daily = pd.to_numeric(
        with_cycles[columns["actual_daily"]],
        errors="raise",
    ).astype("float64")

    rows: list[dict[str, object]] = []
    for cycle_id, group in with_cycles.groupby("cycle_id", sort=False):
        group_index = group.index
        group_dates = dates.loc[group_index]
        group_close_mask = is_close_day.loc[group_index]
        group_close_dates = group_dates.loc[group_close_mask]

        target_sum = float(target_daily.loc[group_index].sum())
        actual_mask = group_dates <= as_of_timestamp
        actual_sum = float(actual_daily.loc[group_index].loc[actual_mask].sum())
        achievement_rate = (
            round(actual_sum / target_sum * 100, 1) if target_sum else pd.NA
        )

        has_close_day = not group_close_dates.empty
        cycle_end_timestamp = (
            group_close_dates.iloc[-1] if has_close_day else group_dates.iloc[-1]
        )
        is_completed = bool(has_close_day and cycle_end_timestamp <= as_of_timestamp)
        close_type = (
            group.loc[group_close_mask, "close_type"].iloc[-1]
            if has_close_day
            else pd.NA
        )

        rows.append(
            {
                "cycle_id": int(cycle_id),
                "cycle_start_date": group_dates.iloc[0].date(),
                "cycle_end_date": cycle_end_timestamp.date(),
                "is_completed": is_completed,
                "target_sum": round(target_sum, 1),
                "actual_sum": round(actual_sum, 1),
                "achievement_rate": achievement_rate,
                "row_count": int(len(group)),
                "close_type": close_type,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "cycle_id",
            "cycle_start_date",
            "cycle_end_date",
            "is_completed",
            "target_sum",
            "actual_sum",
            "achievement_rate",
            "row_count",
            "close_type",
        ],
    )


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required input columns: {missing}")


def _coerce_dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="raise").dt.normalize()


def _coerce_is_close_day(values: pd.Series) -> pd.Series:
    coerced: list[bool] = []

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

        raise ValueError(f"Unsupported is_close_day value: {value!r}")

    return pd.Series(coerced, index=values.index, dtype=bool)


def _is_missing(value: object) -> bool:
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _to_date_list(values: pd.Series) -> list[date]:
    return [timestamp.date() for timestamp in values]
