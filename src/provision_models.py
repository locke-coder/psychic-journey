"""Provision allocation models for remaining input rows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from math import isfinite
from typing import Any

import pandas as pd

from src.close_cycle_engine import _coerce_is_close_day
from src.schema import get_metric_columns


P1_ALL_REMAINING = "P1_ALL_REMAINING"
P2_CLOSE_DAY_FOCUSED = "P2_CLOSE_DAY_FOCUSED"
P3_NON_CLOSE_DAY_FOCUSED = "P3_NON_CLOSE_DAY_FOCUSED"

OK = "OK"
NO_GAP = "NO_GAP"
NOT_APPLICABLE = "NOT_APPLICABLE"
CAPACITY_LIMITED = "CAPACITY_LIMITED"
CALCULATION_ERROR = "CALCULATION_ERROR"

ALLOCATION_COLUMNS = [
    "date",
    "day_name",
    "business_day_no",
    "is_close_day",
    "close_type",
    "original_target",
    "expected_rate",
    "allocation_weight",
    "uplift",
    "revised_target",
    "cap_target",
    "cap_exceeded",
    "expected_after_revision",
]

_TOLERANCE = 1e-9

ProvisionResult = dict[str, object]


def provision_p1_all_remaining(
    df: pd.DataFrame,
    forecast_result: Mapping[str, Any],
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | object | None = None,
) -> ProvisionResult:
    """Allocate uplift to every remaining input row by target_daily weight."""
    return _run_strategy(
        df=df,
        forecast_result=forecast_result,
        as_of_date=as_of_date,
        metric=metric,
        config=config,
        strategy_id=P1_ALL_REMAINING,
    )


def provision_p2_close_day_focused(
    df: pd.DataFrame,
    forecast_result: Mapping[str, Any],
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | object | None = None,
) -> ProvisionResult:
    """Allocate uplift first to remaining rows marked is_close_day=True."""
    return _run_strategy(
        df=df,
        forecast_result=forecast_result,
        as_of_date=as_of_date,
        metric=metric,
        config=config,
        strategy_id=P2_CLOSE_DAY_FOCUSED,
    )


def provision_p3_non_close_day_focused(
    df: pd.DataFrame,
    forecast_result: Mapping[str, Any],
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | object | None = None,
) -> ProvisionResult:
    """Allocate uplift first to remaining rows marked is_close_day=False."""
    return _run_strategy(
        df=df,
        forecast_result=forecast_result,
        as_of_date=as_of_date,
        metric=metric,
        config=config,
        strategy_id=P3_NON_CLOSE_DAY_FOCUSED,
    )


def run_provision_model(
    df: pd.DataFrame,
    forecast_result: Mapping[str, Any],
    as_of_date: object,
    metric: str,
    strategy_id: str,
    config: Mapping[str, Any] | object | None = None,
) -> ProvisionResult:
    """Run a provision model by strategy_id."""
    strategy_map = {
        P1_ALL_REMAINING: provision_p1_all_remaining,
        P2_CLOSE_DAY_FOCUSED: provision_p2_close_day_focused,
        P3_NON_CLOSE_DAY_FOCUSED: provision_p3_non_close_day_focused,
    }
    try:
        strategy = strategy_map[strategy_id]
    except KeyError as exc:
        allowed = ", ".join(strategy_map)
        raise ValueError(f"Unsupported provision strategy: {strategy_id}. Allowed: {allowed}.") from exc

    return strategy(df, forecast_result, as_of_date, metric, config)


def run_all_provision_models(
    df: pd.DataFrame,
    forecast_result: Mapping[str, Any],
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | object | None = None,
) -> list[ProvisionResult]:
    """Run all provision models in strategy order."""
    return [
        provision_p1_all_remaining(df, forecast_result, as_of_date, metric, config),
        provision_p2_close_day_focused(df, forecast_result, as_of_date, metric, config),
        provision_p3_non_close_day_focused(df, forecast_result, as_of_date, metric, config),
    ]


class _ProvisionContext:
    def __init__(
        self,
        *,
        remaining_rows: pd.DataFrame,
        target_daily: pd.Series,
        is_close_day: pd.Series,
        expected_rate: pd.Series,
        cap_target: pd.Series,
        monthly_target: float,
        current_actual_cum: float,
        base_forecast: float,
        gap_to_target: float,
        warnings: list[str],
    ) -> None:
        self.remaining_rows = remaining_rows
        self.target_daily = target_daily
        self.is_close_day = is_close_day
        self.expected_rate = expected_rate
        self.cap_target = cap_target
        self.monthly_target = monthly_target
        self.current_actual_cum = current_actual_cum
        self.base_forecast = base_forecast
        self.gap_to_target = gap_to_target
        self.warnings = warnings


def _run_strategy(
    *,
    df: pd.DataFrame,
    forecast_result: Mapping[str, Any],
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | object | None,
    strategy_id: str,
) -> ProvisionResult:
    try:
        context = _prepare_context(df, forecast_result, as_of_date, metric, config)
        allocation_weight = _build_allocation_weight(context, strategy_id)
        allocation_by_day = _build_allocation_by_day(
            context=context,
            allocation_weight=allocation_weight,
            uplift=_zero_series(context.remaining_rows.index),
            cap_exceeded=_false_series(context.remaining_rows.index),
        )

        target_index = allocation_weight.loc[allocation_weight > 0].index
        if target_index.empty:
            return _build_result(
                strategy_id=strategy_id,
                context=context,
                uplift_effective_rate=0.0,
                required_uplift=0.0,
                allocated_uplift=0.0,
                unallocated_uplift=0.0,
                forecast_after_provision=context.base_forecast,
                allocation_by_day=allocation_by_day,
                status=NOT_APPLICABLE,
            )

        uplift_effective_rate = float(
            (allocation_weight.loc[target_index] * context.expected_rate.loc[target_index]).sum()
        )
        if context.gap_to_target <= _TOLERANCE:
            return _build_result(
                strategy_id=strategy_id,
                context=context,
                uplift_effective_rate=uplift_effective_rate,
                required_uplift=0.0,
                allocated_uplift=0.0,
                unallocated_uplift=0.0,
                forecast_after_provision=context.base_forecast,
                allocation_by_day=allocation_by_day,
                status=NO_GAP,
            )

        if uplift_effective_rate <= _TOLERANCE:
            return _build_result(
                strategy_id=strategy_id,
                context=context,
                uplift_effective_rate=uplift_effective_rate,
                required_uplift=0.0,
                allocated_uplift=0.0,
                unallocated_uplift=0.0,
                forecast_after_provision=context.base_forecast,
                allocation_by_day=allocation_by_day,
                status=CALCULATION_ERROR,
                extra_warnings=["Calculation unavailable: uplift_effective_rate is zero."],
            )

        required_uplift = context.gap_to_target / uplift_effective_rate
        uplift_capacity = (context.cap_target - context.target_daily).clip(lower=0.0)
        requested_uplift = required_uplift * allocation_weight

        uplift, unallocated_uplift = _allocate_with_caps(
            amount=required_uplift,
            candidate_index=target_index,
            weight_basis=context.target_daily,
            uplift_capacity=uplift_capacity,
        )

        if (
            unallocated_uplift > _TOLERANCE
            and str(_config_get(config, "provision_overflow_fallback", "")).upper() == "ALL_REMAINING"
        ):
            fallback_uplift, unallocated_uplift = _allocate_with_caps(
                amount=unallocated_uplift,
                candidate_index=context.remaining_rows.index,
                weight_basis=context.target_daily,
                uplift_capacity=uplift_capacity,
                existing_uplift=uplift,
            )
            uplift = fallback_uplift

        allocated_uplift = float(uplift.sum())
        forecast_after_provision = context.base_forecast + float(
            (uplift * context.expected_rate).sum()
        )
        cap_exceeded = requested_uplift > uplift_capacity + _TOLERANCE
        allocation_by_day = _build_allocation_by_day(
            context=context,
            allocation_weight=allocation_weight,
            uplift=uplift,
            cap_exceeded=cap_exceeded,
        )
        status = CAPACITY_LIMITED if unallocated_uplift > _TOLERANCE else OK

        return _build_result(
            strategy_id=strategy_id,
            context=context,
            uplift_effective_rate=uplift_effective_rate,
            required_uplift=required_uplift,
            allocated_uplift=allocated_uplift,
            unallocated_uplift=unallocated_uplift,
            forecast_after_provision=forecast_after_provision,
            allocation_by_day=allocation_by_day,
            status=status,
        )
    except Exception as exc:  # noqa: BLE001 - public model should return status on bad inputs.
        return _calculation_error_result(strategy_id, exc)


def _prepare_context(
    df: pd.DataFrame,
    forecast_result: Mapping[str, Any],
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | object | None,
) -> _ProvisionContext:
    columns = get_metric_columns(metric)
    _require_columns(
        df,
        (
            "date",
            "is_close_day",
            columns["target_daily"],
        ),
    )

    result = df.copy()
    dates = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    remaining_mask = dates > as_of_timestamp
    remaining_rows = result.loc[remaining_mask].copy()
    remaining_dates = dates.loc[remaining_mask]

    target_daily = pd.to_numeric(
        remaining_rows[columns["target_daily"]],
        errors="raise",
    ).astype("float64")
    is_close_day = _coerce_is_close_day(remaining_rows["is_close_day"])
    expected_rate = _build_expected_rate_series(remaining_dates, forecast_result)
    cap_target = _build_cap_target(target_daily, is_close_day, config)

    monthly_target = _as_float(forecast_result.get("monthly_target", float("nan")))
    if not isfinite(monthly_target):
        target_all = pd.to_numeric(result[columns["target_daily"]], errors="raise").astype("float64")
        monthly_target = float(target_all.sum())

    current_actual_cum = _as_float(forecast_result.get("current_actual_cum", float("nan")))
    if not isfinite(current_actual_cum):
        raise ValueError("Forecast result is missing current_actual_cum.")

    base_forecast = current_actual_cum + float((target_daily * expected_rate).sum())
    gap_to_target = max(0.0, monthly_target - base_forecast)

    return _ProvisionContext(
        remaining_rows=remaining_rows,
        target_daily=target_daily,
        is_close_day=is_close_day,
        expected_rate=expected_rate,
        cap_target=cap_target,
        monthly_target=monthly_target,
        current_actual_cum=current_actual_cum,
        base_forecast=base_forecast,
        gap_to_target=gap_to_target,
        warnings=list(forecast_result.get("warnings", [])),
    )


def _build_expected_rate_series(
    remaining_dates: pd.Series,
    forecast_result: Mapping[str, Any],
) -> pd.Series:
    expected_rate_by_day = forecast_result.get("expected_rate_by_day", {})
    if not isinstance(expected_rate_by_day, Mapping):
        raise ValueError("Forecast result expected_rate_by_day must be a mapping.")

    normalized_rates = {
        pd.Timestamp(day).date(): _as_float(rate)
        for day, rate in expected_rate_by_day.items()
    }

    expected_rates: list[float] = []
    missing_dates: list[date] = []
    for timestamp in remaining_dates:
        day = pd.Timestamp(timestamp).date()
        expected_rate = normalized_rates.get(day)
        if expected_rate is None or not isfinite(expected_rate):
            missing_dates.append(day)
            expected_rates.append(float("nan"))
        else:
            expected_rates.append(expected_rate)

    if missing_dates:
        missing = ", ".join(str(day) for day in missing_dates)
        raise ValueError(f"Forecast result is missing expected rates for remaining dates: {missing}.")

    return pd.Series(expected_rates, index=remaining_dates.index, dtype="float64")


def _build_cap_target(
    target_daily: pd.Series,
    is_close_day: pd.Series,
    config: Mapping[str, Any] | object | None,
) -> pd.Series:
    close_day_cap_rate = _as_float(_config_get(config, "close_day_cap_rate", 1.30))
    non_close_day_cap_rate = _as_float(_config_get(config, "non_close_day_cap_rate", 1.50))
    cap_rates = pd.Series(non_close_day_cap_rate, index=target_daily.index, dtype="float64")
    cap_rates.loc[is_close_day] = close_day_cap_rate
    return target_daily * cap_rates


def _build_allocation_weight(context: _ProvisionContext, strategy_id: str) -> pd.Series:
    if strategy_id == P1_ALL_REMAINING:
        candidate_mask = pd.Series(True, index=context.remaining_rows.index)
    elif strategy_id == P2_CLOSE_DAY_FOCUSED:
        candidate_mask = context.is_close_day
    elif strategy_id == P3_NON_CLOSE_DAY_FOCUSED:
        candidate_mask = ~context.is_close_day
    else:
        raise ValueError(f"Unsupported provision strategy: {strategy_id}.")

    weights = _zero_series(context.remaining_rows.index)
    candidate_targets = context.target_daily.loc[candidate_mask]
    total_target = float(candidate_targets.sum())
    if total_target > _TOLERANCE:
        weights.loc[candidate_targets.index] = candidate_targets / total_target
    return weights


def _allocate_with_caps(
    *,
    amount: float,
    candidate_index: pd.Index,
    weight_basis: pd.Series,
    uplift_capacity: pd.Series,
    existing_uplift: pd.Series | None = None,
) -> tuple[pd.Series, float]:
    uplift = (
        _zero_series(uplift_capacity.index)
        if existing_uplift is None
        else existing_uplift.copy()
    )
    remaining_amount = max(0.0, float(amount))
    candidate_index = pd.Index(candidate_index)

    while remaining_amount > _TOLERANCE:
        remaining_capacity = (uplift_capacity.loc[candidate_index] - uplift.loc[candidate_index]).clip(
            lower=0.0
        )
        open_index = remaining_capacity.loc[remaining_capacity > _TOLERANCE].index
        if open_index.empty:
            break

        bases = weight_basis.loc[open_index].clip(lower=0.0)
        basis_sum = float(bases.sum())
        if basis_sum <= _TOLERANCE:
            break

        proposed = remaining_amount * bases / basis_sum
        accepted = pd.concat(
            [proposed, remaining_capacity.loc[open_index]],
            axis=1,
        ).min(axis=1)
        accepted_sum = float(accepted.sum())
        if accepted_sum <= _TOLERANCE:
            break

        uplift.loc[open_index] += accepted
        remaining_amount -= accepted_sum

    return uplift, max(0.0, remaining_amount)


def _build_allocation_by_day(
    *,
    context: _ProvisionContext,
    allocation_weight: pd.Series,
    uplift: pd.Series,
    cap_exceeded: pd.Series,
) -> pd.DataFrame:
    rows = context.remaining_rows
    revised_target = context.target_daily + uplift
    result = pd.DataFrame(index=rows.index)
    result["date"] = pd.to_datetime(rows["date"], errors="raise").dt.date
    result["day_name"] = rows["day_name"] if "day_name" in rows else pd.NA
    result["business_day_no"] = rows["business_day_no"] if "business_day_no" in rows else pd.NA
    result["is_close_day"] = context.is_close_day
    result["close_type"] = rows["close_type"] if "close_type" in rows else pd.NA
    result["original_target"] = context.target_daily
    result["expected_rate"] = context.expected_rate
    result["allocation_weight"] = allocation_weight
    result["uplift"] = uplift
    result["revised_target"] = revised_target
    result["cap_target"] = context.cap_target
    result["cap_exceeded"] = cap_exceeded.reindex(rows.index, fill_value=False).astype(bool)
    result["expected_after_revision"] = revised_target * context.expected_rate
    return result.loc[:, ALLOCATION_COLUMNS].reset_index(drop=True)


def _build_result(
    *,
    strategy_id: str,
    context: _ProvisionContext,
    uplift_effective_rate: float,
    required_uplift: float,
    allocated_uplift: float,
    unallocated_uplift: float,
    forecast_after_provision: float,
    allocation_by_day: pd.DataFrame,
    status: str,
    extra_warnings: list[str] | None = None,
) -> ProvisionResult:
    warnings = list(context.warnings)
    if extra_warnings:
        warnings.extend(extra_warnings)
    gap_after_provision = max(0.0, context.monthly_target - forecast_after_provision)

    return {
        "strategy_id": strategy_id,
        "gap_to_target": context.gap_to_target,
        "uplift_effective_rate": uplift_effective_rate,
        "required_uplift": max(0.0, required_uplift),
        "allocated_uplift": max(0.0, allocated_uplift),
        "unallocated_uplift": max(0.0, unallocated_uplift),
        "revised_remaining_target": float(allocation_by_day["revised_target"].sum()),
        "forecast_after_provision": forecast_after_provision,
        "gap_after_provision": gap_after_provision,
        "allocation_by_day": allocation_by_day,
        "status": status,
        "warnings": warnings,
    }


def _calculation_error_result(strategy_id: str, exc: Exception) -> ProvisionResult:
    return {
        "strategy_id": strategy_id,
        "gap_to_target": float("nan"),
        "uplift_effective_rate": float("nan"),
        "required_uplift": 0.0,
        "allocated_uplift": 0.0,
        "unallocated_uplift": 0.0,
        "revised_remaining_target": 0.0,
        "forecast_after_provision": float("nan"),
        "gap_after_provision": float("nan"),
        "allocation_by_day": pd.DataFrame(columns=ALLOCATION_COLUMNS),
        "status": CALCULATION_ERROR,
        "warnings": [f"Calculation error: {exc}"],
    }


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required input columns: {missing}")


def _config_get(
    config: Mapping[str, Any] | object | None,
    key: str,
    default: object,
) -> object:
    if config is None:
        return default
    if isinstance(config, Mapping):
        return config.get(key, default)
    return getattr(config, key, default)


def _as_float(value: object) -> float:
    if value is None:
        return float("nan")
    return float(value)


def _zero_series(index: pd.Index) -> pd.Series:
    return pd.Series(0.0, index=index, dtype="float64")


def _false_series(index: pd.Index) -> pd.Series:
    return pd.Series(False, index=index, dtype=bool)
