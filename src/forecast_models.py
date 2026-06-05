"""Forecast models for input-driven sales closing forecasts."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from src.actual_engine import add_actual_daily_columns
from src.close_cycle_engine import _coerce_is_close_day, assign_close_cycle_ids
from src.schema import get_metric_columns


F1_CUMULATIVE_RATE = "F1_CUMULATIVE_RATE"
F2_LAST_TWO_CLOSES = "F2_LAST_TWO_CLOSES"
F3_DAY_CLOSE_WEIGHTED = "F3_DAY_CLOSE_WEIGHTED"

UNDER_TARGET = "UNDER_TARGET"
ON_TARGET = "ON_TARGET"
OVER_TARGET = "OVER_TARGET"
UNKNOWN_TARGET_STATUS = "UNKNOWN"
TARGET_STATUS_TOLERANCE = 1e-9

ForecastResult = dict[str, object]


def forecast_f1_cumulative_rate(
    df: pd.DataFrame,
    metric: str,
    as_of_date: object,
    config: dict[str, Any] | None = None,
) -> ForecastResult:
    """Forecast remaining input rows with the cumulative achievement rate."""
    context = _prepare_context(df, metric, as_of_date, config)
    invalid_result = _build_invalid_result(context, F1_CUMULATIVE_RATE)
    if invalid_result is not None:
        return invalid_result

    r_cum = context.current_actual_cum / context.current_target_cum
    forecast_amount = context.current_actual_cum + context.remaining_target * r_cum
    expected_rate_by_day = _constant_expected_rates(context.remaining_rows, r_cum)

    return _build_result(
        context=context,
        model_id=F1_CUMULATIVE_RATE,
        forecast_amount=forecast_amount,
        expected_rate_by_day=expected_rate_by_day,
        warnings=[],
        comment="Forecast uses cumulative achievement rate through as_of_date.",
    )


def forecast_f2_last_two_closes(
    df: pd.DataFrame,
    metric: str,
    as_of_date: object,
    config: dict[str, Any] | None = None,
) -> ForecastResult:
    """Forecast remaining input rows with the last two completed close cycles."""
    context = _prepare_context(df, metric, as_of_date, config)
    invalid_result = _build_invalid_result(context, F2_LAST_TWO_CLOSES)
    if invalid_result is not None:
        return invalid_result

    last_two_cycles = _last_two_completed_close_cycles(context)
    if len(last_two_cycles) < 2:
        fallback = forecast_f1_cumulative_rate(df, metric, as_of_date, config)
        return _with_fallback(
            fallback,
            requested_model_id=F2_LAST_TWO_CLOSES,
            warning=(
                "F2_LAST_TWO_CLOSES fallback to F1_CUMULATIVE_RATE: "
                "fewer than two completed close cycles are available."
            ),
        )

    target_sum = sum(cycle["target_sum"] for cycle in last_two_cycles)
    actual_sum = sum(cycle["actual_sum"] for cycle in last_two_cycles)
    if target_sum <= 0:
        fallback = forecast_f1_cumulative_rate(df, metric, as_of_date, config)
        return _with_fallback(
            fallback,
            requested_model_id=F2_LAST_TWO_CLOSES,
            warning=(
                "F2_LAST_TWO_CLOSES fallback to F1_CUMULATIVE_RATE: "
                "last two completed close cycles have zero target."
            ),
        )

    r_last2 = actual_sum / target_sum
    forecast_amount = context.current_actual_cum + context.remaining_target * r_last2
    expected_rate_by_day = _constant_expected_rates(context.remaining_rows, r_last2)

    return _build_result(
        context=context,
        model_id=F2_LAST_TWO_CLOSES,
        forecast_amount=forecast_amount,
        expected_rate_by_day=expected_rate_by_day,
        warnings=[],
        comment="Forecast uses actual/target rate from the last two completed close cycles.",
    )


def forecast_f3_day_close_weighted(
    df: pd.DataFrame,
    metric: str,
    as_of_date: object,
    config: dict[str, Any] | None = None,
) -> ForecastResult:
    """Forecast remaining input rows with separate close/non-close day rates."""
    context = _prepare_context(df, metric, as_of_date, config)
    invalid_result = _build_invalid_result(context, F3_DAY_CLOSE_WEIGHTED)
    if invalid_result is not None:
        return invalid_result

    past_rows = context.with_actuals.loc[context.past_or_current_mask]
    close_past = context.is_close_day.loc[past_rows.index]
    target_daily = context.target_daily.loc[past_rows.index]
    actual_daily = context.actual_daily.loc[past_rows.index]

    close_target_sum = float(target_daily.loc[close_past].sum())
    non_close_target_sum = float(target_daily.loc[~close_past].sum())
    if close_target_sum <= 0 or non_close_target_sum <= 0:
        fallback = forecast_f2_last_two_closes(df, metric, as_of_date, config)
        return _with_fallback(
            fallback,
            requested_model_id=F3_DAY_CLOSE_WEIGHTED,
            warning=(
                "F3_DAY_CLOSE_WEIGHTED fallback: close-day and non-close-day "
                "historical targets are both required."
            ),
        )

    r_close = float(actual_daily.loc[close_past].sum()) / close_target_sum
    r_non_close = float(actual_daily.loc[~close_past].sum()) / non_close_target_sum

    forecast_amount = context.current_actual_cum
    expected_rate_by_day: dict[date, float] = {}
    for index, row in context.remaining_rows.iterrows():
        expected_rate = r_close if context.is_close_day.loc[index] else r_non_close
        target = float(row[context.columns["target_daily"]])
        forecast_amount += target * expected_rate
        expected_rate_by_day[pd.Timestamp(row["date"]).date()] = expected_rate

    return _build_result(
        context=context,
        model_id=F3_DAY_CLOSE_WEIGHTED,
        forecast_amount=forecast_amount,
        expected_rate_by_day=expected_rate_by_day,
        warnings=[],
        comment="Forecast uses separate historical rates for close and non-close days.",
    )


def run_forecast_model(
    df: pd.DataFrame,
    metric: str,
    as_of_date: object,
    model_id: str,
    config: dict[str, Any] | None = None,
) -> ForecastResult:
    """Run a forecast model by model_id."""
    model_map = {
        F1_CUMULATIVE_RATE: forecast_f1_cumulative_rate,
        F2_LAST_TWO_CLOSES: forecast_f2_last_two_closes,
        F3_DAY_CLOSE_WEIGHTED: forecast_f3_day_close_weighted,
    }
    try:
        model = model_map[model_id]
    except KeyError as exc:
        allowed = ", ".join(model_map)
        raise ValueError(f"Unsupported forecast model: {model_id}. Allowed: {allowed}.") from exc

    return model(df, metric, as_of_date, config)


class _ForecastContext:
    def __init__(
        self,
        *,
        with_actuals: pd.DataFrame,
        columns: dict[str, str],
        dates: pd.Series,
        is_close_day: pd.Series,
        target_daily: pd.Series,
        actual_cum: pd.Series,
        actual_daily: pd.Series,
        metric: str,
        as_of_timestamp: pd.Timestamp,
        as_of_date: date,
        monthly_target: float,
        current_target_cum: float,
        current_actual_cum: float,
        remaining_target: float,
        remaining_rows: pd.DataFrame,
        past_or_current_mask: pd.Series,
        warnings: list[str],
    ) -> None:
        self.with_actuals = with_actuals
        self.columns = columns
        self.dates = dates
        self.is_close_day = is_close_day
        self.target_daily = target_daily
        self.actual_cum = actual_cum
        self.actual_daily = actual_daily
        self.metric = metric
        self.as_of_timestamp = as_of_timestamp
        self.as_of_date = as_of_date
        self.monthly_target = monthly_target
        self.current_target_cum = current_target_cum
        self.current_actual_cum = current_actual_cum
        self.remaining_target = remaining_target
        self.remaining_rows = remaining_rows
        self.past_or_current_mask = past_or_current_mask
        self.warnings = warnings


def _prepare_context(
    df: pd.DataFrame,
    metric: str,
    as_of_date: object,
    config: dict[str, Any] | None,
) -> _ForecastContext:
    columns = get_metric_columns(metric)
    _require_columns(df, ("date", "is_close_day", columns["target_daily"], columns["actual_cum"]))

    with_actuals = add_actual_daily_columns(df, metric, as_of_date, config).copy()
    dates = pd.to_datetime(with_actuals["date"], errors="raise").dt.normalize()
    is_close_day = _coerce_is_close_day(with_actuals["is_close_day"])
    target_daily = pd.to_numeric(
        with_actuals[columns["target_daily"]],
        errors="raise",
    ).astype("float64")
    actual_cum = _coerce_actual_cum(with_actuals[columns["actual_cum"]])
    actual_daily = pd.to_numeric(
        with_actuals[columns["actual_daily"]],
        errors="coerce",
    ).astype("float64")

    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    past_or_current_mask = dates <= as_of_timestamp
    remaining_mask = dates > as_of_timestamp
    as_of_mask = dates == as_of_timestamp

    current_target_cum = float(target_daily.loc[past_or_current_mask].sum())
    monthly_target = float(target_daily.sum())
    remaining_target = float(target_daily.loc[remaining_mask].sum())

    warnings: list[str] = []
    current_actual_cum = float("nan")
    if not as_of_mask.any():
        warnings.append("Calculation unavailable: as_of_date is not present in the input rows.")
    else:
        as_of_actuals = actual_cum.loc[as_of_mask].dropna()
        if as_of_actuals.empty:
            warnings.append("Calculation unavailable: actual cumulative value is missing at as_of_date.")
        else:
            current_actual_cum = float(as_of_actuals.iloc[-1])

    if monthly_target == 0:
        warnings.append("Calculation unavailable: monthly_target is zero.")
    if current_target_cum == 0:
        warnings.append("Calculation unavailable: current_target_cum is zero.")

    remaining_rows = with_actuals.loc[remaining_mask].copy()

    return _ForecastContext(
        with_actuals=with_actuals,
        columns=columns,
        dates=dates,
        is_close_day=is_close_day,
        target_daily=target_daily,
        actual_cum=actual_cum,
        actual_daily=actual_daily,
        metric=metric,
        as_of_timestamp=as_of_timestamp,
        as_of_date=as_of_timestamp.date(),
        monthly_target=monthly_target,
        current_target_cum=current_target_cum,
        current_actual_cum=current_actual_cum,
        remaining_target=remaining_target,
        remaining_rows=remaining_rows,
        past_or_current_mask=past_or_current_mask,
        warnings=warnings,
    )


def _build_invalid_result(
    context: _ForecastContext,
    model_id: str,
) -> ForecastResult | None:
    if not context.warnings:
        return None

    return {
        "model_id": model_id,
        "metric": context.metric,
        "as_of_date": context.as_of_date,
        "monthly_target": context.monthly_target,
        "current_actual_cum": context.current_actual_cum,
        "current_target_cum": context.current_target_cum,
        "remaining_target": context.remaining_target,
        "forecast_amount": float("nan"),
        "forecast_rate": float("nan"),
        "gap_to_target": float("nan"),
        "target_variance": float("nan"),
        "surplus_to_target": float("nan"),
        "target_status": UNKNOWN_TARGET_STATUS,
        "expected_rate_by_day": {},
        "warnings": list(context.warnings),
        "comment": "Forecast calculation is unavailable for the provided input.",
    }


def _build_result(
    *,
    context: _ForecastContext,
    model_id: str,
    forecast_amount: float,
    expected_rate_by_day: dict[date, float],
    warnings: list[str],
    comment: str,
) -> ForecastResult:
    forecast_rate = forecast_amount / context.monthly_target
    target_variance = forecast_amount - context.monthly_target
    gap_to_target = max(0.0, context.monthly_target - forecast_amount)
    surplus_to_target = max(0.0, forecast_amount - context.monthly_target)
    target_status = _target_status(target_variance)

    return {
        "model_id": model_id,
        "metric": context.metric,
        "as_of_date": context.as_of_date,
        "monthly_target": context.monthly_target,
        "current_actual_cum": context.current_actual_cum,
        "current_target_cum": context.current_target_cum,
        "remaining_target": context.remaining_target,
        "forecast_amount": forecast_amount,
        "forecast_rate": forecast_rate,
        "gap_to_target": gap_to_target,
        "target_variance": target_variance,
        "surplus_to_target": surplus_to_target,
        "target_status": target_status,
        "expected_rate_by_day": expected_rate_by_day,
        "warnings": warnings,
        "comment": comment,
    }


def _target_status(target_variance: float) -> str:
    if target_variance > TARGET_STATUS_TOLERANCE:
        return OVER_TARGET
    if target_variance < -TARGET_STATUS_TOLERANCE:
        return UNDER_TARGET
    return ON_TARGET


def _with_fallback(
    result: ForecastResult,
    *,
    requested_model_id: str,
    warning: str,
) -> ForecastResult:
    fallback = dict(result)
    fallback["model_id"] = requested_model_id
    fallback["warnings"] = [warning, *list(result["warnings"])]
    fallback["comment"] = f"{warning} {result['comment']}"
    return fallback


def _last_two_completed_close_cycles(context: _ForecastContext) -> list[dict[str, float]]:
    with_cycles = assign_close_cycle_ids(context.with_actuals)
    cycles: list[dict[str, float]] = []

    for _, group in with_cycles.groupby("cycle_id", sort=False):
        group_index = group.index
        group_dates = context.dates.loc[group_index]
        group_close_mask = context.is_close_day.loc[group_index]
        group_close_dates = group_dates.loc[group_close_mask]
        if group_close_dates.empty:
            continue

        cycle_end_timestamp = group_close_dates.iloc[-1]
        if cycle_end_timestamp > context.as_of_timestamp:
            continue

        cycles.append(
            {
                "target_sum": float(context.target_daily.loc[group_index].sum()),
                "actual_sum": float(context.actual_daily.loc[group_index].sum()),
            }
        )

    return cycles[-2:]


def _constant_expected_rates(
    remaining_rows: pd.DataFrame,
    expected_rate: float,
) -> dict[date, float]:
    return {
        pd.Timestamp(row["date"]).date(): expected_rate
        for _, row in remaining_rows.iterrows()
    }


def _coerce_actual_cum(values: pd.Series) -> pd.Series:
    cleaned = values.replace(r"^\s*$", pd.NA, regex=True)
    return pd.to_numeric(cleaned, errors="raise").astype("float64")


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required input columns: {missing}")
