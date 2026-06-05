"""Scenario-grid orchestration for forecast and provision combinations."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from math import isfinite
from typing import Any

import pandas as pd

from src.actual_engine import add_actual_daily_columns
from src.close_cycle_engine import build_close_cycle_summary
from src.forecast_models import (
    F1_CUMULATIVE_RATE,
    F2_LAST_TWO_CLOSES,
    F3_DAY_CLOSE_WEIGHTED,
    ForecastResult,
    ON_TARGET,
    OVER_TARGET,
    UNDER_TARGET,
    UNKNOWN_TARGET_STATUS,
    run_forecast_model,
)
from src.next_close import calculate_next_close_required
from src.overachievement_models import (
    NEUTRAL,
    NEUTRAL_STRATEGIES,
    OVERACHIEVEMENT,
    OVERACHIEVEMENT_STRATEGIES,
    PROVISION,
    run_neutral_strategy,
    run_overachievement_strategy,
)
from src.provision_models import (
    CALCULATION_ERROR,
    CAPACITY_LIMITED,
    NO_GAP,
    NOT_APPLICABLE,
    OK,
    P1_ALL_REMAINING,
    P2_CLOSE_DAY_FOCUSED,
    P3_NON_CLOSE_DAY_FOCUSED,
    ProvisionResult,
    run_provision_model,
)
from src.schema import get_metric_columns


SCENARIO_OUTPUT_COLUMNS = [
    "scenario_id",
    "forecast_model",
    "provision_strategy",
    "metric",
    "as_of_date",
    "monthly_target",
    "current_actual_cum",
    "current_target_cum",
    "remaining_target",
    "forecast_amount",
    "forecast_rate",
    "gap_to_target",
    "target_variance",
    "surplus_to_target",
    "target_status",
    "strategy_type",
    "overachievement_strategy",
    "required_uplift",
    "allocated_uplift",
    "unallocated_uplift",
    "revised_remaining_target",
    "stretch_uplift",
    "revised_monthly_target",
    "remaining_surplus_buffer",
    "minimum_remaining_to_hit_target",
    "relief_amount",
    "forecast_after_provision",
    "gap_after_provision",
    "next_close_date",
    "next_close_required",
    "risk_level",
    "status",
    "recommended_action",
    "comment",
    "warnings",
]

FORECAST_MODELS = (
    F1_CUMULATIVE_RATE,
    F2_LAST_TWO_CLOSES,
    F3_DAY_CLOSE_WEIGHTED,
)
PROVISION_STRATEGIES = (
    P1_ALL_REMAINING,
    P2_CLOSE_DAY_FOCUSED,
    P3_NON_CLOSE_DAY_FOCUSED,
)

_FORECAST_SHORT_IDS = {
    F1_CUMULATIVE_RATE: "F1",
    F2_LAST_TWO_CLOSES: "F2",
    F3_DAY_CLOSE_WEIGHTED: "F3",
}
_PROVISION_SHORT_IDS = {
    P1_ALL_REMAINING: "P1",
    P2_CLOSE_DAY_FOCUSED: "P2",
    P3_NON_CLOSE_DAY_FOCUSED: "P3",
}
_STRATEGY_SHORT_IDS = {
    **_PROVISION_SHORT_IDS,
    OVERACHIEVEMENT_STRATEGIES[0]: "O1",
    OVERACHIEVEMENT_STRATEGIES[1]: "O2",
    OVERACHIEVEMENT_STRATEGIES[2]: "O3",
    NEUTRAL_STRATEGIES[0]: "N1",
    NEUTRAL_STRATEGIES[1]: "N2",
    NEUTRAL_STRATEGIES[2]: "N3",
}


def run_scenario_grid(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | None,
) -> pd.DataFrame:
    """Run all forecast/provision scenarios and return one row per combination."""
    preprocessing_warnings: list[str] = []
    scenario_input = _calculate_actual_daily(df, as_of_date, metric, config, preprocessing_warnings)
    _build_close_cycle_summary(scenario_input, as_of_date, metric, preprocessing_warnings)
    next_close = _calculate_next_close(df, as_of_date, metric, config)

    rows: list[dict[str, object]] = []
    for forecast_model in FORECAST_MODELS:
        forecast_result = _run_forecast(
            scenario_input,
            as_of_date,
            metric,
            config,
            forecast_model,
            preprocessing_warnings,
        )
        for strategy_id, strategy_result in _run_strategies_for_forecast(
            scenario_input,
            forecast_result,
            as_of_date,
            metric,
            config,
        ):
            rows.append(
                _build_scenario_row(
                    forecast_model=forecast_model,
                    strategy_id=strategy_id,
                    metric=metric,
                    forecast_result=forecast_result,
                    strategy_result=strategy_result,
                    next_close_result=next_close,
                )
            )

    return pd.DataFrame(rows, columns=SCENARIO_OUTPUT_COLUMNS)


def _run_strategies_for_forecast(
    df: pd.DataFrame,
    forecast_result: Mapping[str, Any],
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | None,
) -> list[tuple[str, Mapping[str, Any]]]:
    target_status = str(forecast_result.get("target_status", ""))
    if target_status == OVER_TARGET:
        return [
            (
                strategy_id,
                run_overachievement_strategy(forecast_result, strategy_id, config),
            )
            for strategy_id in OVERACHIEVEMENT_STRATEGIES
        ]
    if target_status == ON_TARGET:
        return [
            (strategy_id, run_neutral_strategy(forecast_result, strategy_id))
            for strategy_id in NEUTRAL_STRATEGIES
        ]

    return [
        (
            provision_strategy,
            run_provision_model(
                df,
                forecast_result,
                as_of_date,
                metric,
                provision_strategy,
                config,
            ),
        )
        for provision_strategy in PROVISION_STRATEGIES
    ]


def _calculate_actual_daily(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | None,
    warnings: list[str],
) -> pd.DataFrame:
    try:
        return add_actual_daily_columns(df, metric, as_of_date, config)
    except Exception as exc:  # noqa: BLE001 - scenario grid must preserve rows.
        warnings.append(f"Actual daily calculation failed: {exc}")
        return df.copy()


def _build_close_cycle_summary(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    warnings: list[str],
) -> None:
    try:
        build_close_cycle_summary(df, metric, as_of_date)
    except Exception as exc:  # noqa: BLE001 - scenario grid must preserve rows.
        warnings.append(f"Close-cycle summary failed: {exc}")


def _calculate_next_close(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | None,
) -> dict[str, object]:
    try:
        result = calculate_next_close_required(df, as_of_date, metric, config)
        return {
            "next_close_date": result.get("next_close_date"),
            "next_close_required": result.get("required_to_recover_next_close_cum"),
            "warnings": list(result.get("warnings", [])),
        }
    except Exception as exc:  # noqa: BLE001 - scenario grid must preserve rows.
        return {
            "next_close_date": None,
            "next_close_required": None,
            "warnings": [f"Next close calculation failed: {exc}"],
        }


def _run_forecast(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: Mapping[str, Any] | None,
    forecast_model: str,
    preprocessing_warnings: list[str],
) -> ForecastResult:
    try:
        result = run_forecast_model(df, metric, as_of_date, forecast_model, config)
        result["warnings"] = [*preprocessing_warnings, *list(result.get("warnings", []))]
        return result
    except Exception as exc:  # noqa: BLE001 - scenario grid must preserve rows.
        return _forecast_error_result(df, as_of_date, metric, forecast_model, exc, preprocessing_warnings)


def _forecast_error_result(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    forecast_model: str,
    exc: Exception,
    preprocessing_warnings: list[str],
) -> ForecastResult:
    context = _basic_forecast_context(df, as_of_date, metric)
    return {
        "model_id": forecast_model,
        "metric": metric,
        "as_of_date": _as_date(as_of_date),
        "monthly_target": context["monthly_target"],
        "current_actual_cum": context["current_actual_cum"],
        "current_target_cum": context["current_target_cum"],
        "remaining_target": context["remaining_target"],
        "forecast_amount": float("nan"),
        "forecast_rate": float("nan"),
        "gap_to_target": float("nan"),
        "target_variance": float("nan"),
        "surplus_to_target": float("nan"),
        "target_status": UNKNOWN_TARGET_STATUS,
        "expected_rate_by_day": {},
        "warnings": [
            *preprocessing_warnings,
            f"{forecast_model} calculation failed: {exc}",
        ],
        "comment": "Forecast calculation is unavailable for the provided input.",
    }


def _basic_forecast_context(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
) -> dict[str, float]:
    try:
        columns = get_metric_columns(metric)
        if "date" not in df or columns["target_daily"] not in df:
            raise ValueError("date and target columns are required.")

        dates = pd.to_datetime(df["date"], errors="raise").dt.normalize()
        as_of_timestamp = pd.Timestamp(as_of_date).normalize()
        target_daily = pd.to_numeric(df[columns["target_daily"]], errors="raise").astype("float64")
        past_or_current = dates <= as_of_timestamp
        remaining = dates > as_of_timestamp
        monthly_target = float(target_daily.sum())
        current_target_cum = float(target_daily.loc[past_or_current].sum())
        remaining_target = float(target_daily.loc[remaining].sum())
        current_actual_cum = _current_actual_at_as_of(df, dates, as_of_timestamp, columns["actual_cum"])
        return {
            "monthly_target": monthly_target,
            "current_actual_cum": current_actual_cum,
            "current_target_cum": current_target_cum,
            "remaining_target": remaining_target,
        }
    except Exception:  # noqa: BLE001 - best-effort context for failed rows.
        return {
            "monthly_target": float("nan"),
            "current_actual_cum": float("nan"),
            "current_target_cum": float("nan"),
            "remaining_target": float("nan"),
        }


def _current_actual_at_as_of(
    df: pd.DataFrame,
    dates: pd.Series,
    as_of_timestamp: pd.Timestamp,
    actual_cum_column: str,
) -> float:
    if actual_cum_column not in df:
        return float("nan")

    actual_cum = df[actual_cum_column].replace(r"^\s*$", pd.NA, regex=True)
    actual_cum = pd.to_numeric(actual_cum, errors="raise").astype("float64")
    as_of_actuals = actual_cum.loc[dates == as_of_timestamp].dropna()
    if as_of_actuals.empty:
        return float("nan")
    return float(as_of_actuals.iloc[-1])


def _build_scenario_row(
    *,
    forecast_model: str,
    strategy_id: str,
    metric: str,
    forecast_result: Mapping[str, Any],
    strategy_result: Mapping[str, Any],
    next_close_result: Mapping[str, Any],
) -> dict[str, object]:
    status = str(strategy_result.get("status", CALCULATION_ERROR))
    strategy_type = str(strategy_result.get("strategy_type", PROVISION))
    target_status = str(forecast_result.get("target_status", UNKNOWN_TARGET_STATUS))
    forecast_rate = _as_float_or_nan(forecast_result.get("forecast_rate"))
    remaining_target = _as_float_or_nan(forecast_result.get("remaining_target"))
    required_uplift = _as_float_or_nan(strategy_result.get("required_uplift"))
    warnings = [
        *list(forecast_result.get("warnings", [])),
        *list(strategy_result.get("warnings", [])),
        *list(next_close_result.get("warnings", [])),
    ]

    return {
        "scenario_id": _scenario_id(forecast_model, strategy_id),
        "forecast_model": forecast_model,
        "provision_strategy": strategy_id,
        "metric": metric,
        "as_of_date": forecast_result.get("as_of_date"),
        "monthly_target": _round_amount(forecast_result.get("monthly_target")),
        "current_actual_cum": _round_amount(forecast_result.get("current_actual_cum")),
        "current_target_cum": _round_amount(forecast_result.get("current_target_cum")),
        "remaining_target": _round_amount(remaining_target),
        "forecast_amount": _round_amount(forecast_result.get("forecast_amount")),
        "forecast_rate": _round_rate(forecast_rate),
        "gap_to_target": _round_amount(forecast_result.get("gap_to_target")),
        "target_variance": _round_amount(forecast_result.get("target_variance")),
        "surplus_to_target": _round_amount(forecast_result.get("surplus_to_target")),
        "target_status": target_status,
        "strategy_type": strategy_type,
        "overachievement_strategy": strategy_result.get("overachievement_strategy"),
        "required_uplift": _round_amount(required_uplift),
        "allocated_uplift": _round_amount(strategy_result.get("allocated_uplift")),
        "unallocated_uplift": _round_amount(strategy_result.get("unallocated_uplift")),
        "revised_remaining_target": _round_amount(strategy_result.get("revised_remaining_target")),
        "stretch_uplift": _round_amount(strategy_result.get("stretch_uplift", 0.0)),
        "revised_monthly_target": _round_amount(
            strategy_result.get("revised_monthly_target", forecast_result.get("monthly_target"))
        ),
        "remaining_surplus_buffer": _round_amount(
            strategy_result.get("remaining_surplus_buffer", 0.0)
        ),
        "minimum_remaining_to_hit_target": _round_amount(
            strategy_result.get("minimum_remaining_to_hit_target", 0.0)
        ),
        "relief_amount": _round_amount(strategy_result.get("relief_amount", 0.0)),
        "forecast_after_provision": _round_amount(strategy_result.get("forecast_after_provision")),
        "gap_after_provision": _round_amount(strategy_result.get("gap_after_provision")),
        "next_close_date": next_close_result.get("next_close_date"),
        "next_close_required": _round_amount(next_close_result.get("next_close_required")),
        "risk_level": _risk_level(
            forecast_rate,
            status,
            required_uplift,
            remaining_target,
            target_status,
            strategy_type,
        ),
        "status": status,
        "recommended_action": strategy_result.get(
            "recommended_action",
            _provision_recommended_action(strategy_id, status),
        ),
        "comment": strategy_result.get("comment", forecast_result.get("comment", "")),
        "warnings": _dedupe_warnings(warnings),
    }


def _scenario_id(forecast_model: str, strategy_id: str) -> str:
    forecast_id = _FORECAST_SHORT_IDS.get(forecast_model, forecast_model)
    short_strategy_id = _STRATEGY_SHORT_IDS.get(strategy_id, strategy_id)
    return f"{forecast_id}_{short_strategy_id}"


def _risk_level(
    forecast_rate: float,
    status: str,
    required_uplift: float,
    remaining_target: float,
    target_status: str,
    strategy_type: str,
) -> str:
    if status == NOT_APPLICABLE:
        return "N/A"
    if status in {CAPACITY_LIMITED, CALCULATION_ERROR}:
        return "Black"
    if strategy_type == OVERACHIEVEMENT and target_status == OVER_TARGET:
        return "Green"
    if strategy_type == NEUTRAL and target_status == ON_TARGET:
        return "Green"

    uplift_ratio = _uplift_ratio(required_uplift, remaining_target)
    if _is_finite(forecast_rate) and forecast_rate >= 1.00 and status in {OK, NO_GAP}:
        return "Green"
    if (_is_finite(forecast_rate) and forecast_rate >= 0.95) or (
        _is_finite(uplift_ratio) and uplift_ratio <= 0.05
    ):
        return "Yellow"
    if (_is_finite(forecast_rate) and forecast_rate >= 0.90) or (
        _is_finite(uplift_ratio) and uplift_ratio <= 0.15
    ):
        return "Red"
    return "Black"


def _provision_recommended_action(strategy_id: str, status: str) -> str:
    if status == CAPACITY_LIMITED:
        return "배분 상한 부족으로 목표 달성이 불확실합니다. 상한 설정과 잔여 목표 배분 여력을 재검토하세요."
    if strategy_id == P1_ALL_REMAINING:
        return "잔여 모든 영업일에 목표 상향분을 고르게 배분합니다."
    if strategy_id == P2_CLOSE_DAY_FOCUSED:
        return "잔여 마감일을 중심으로 목표 상향분을 우선 배분합니다."
    if strategy_id == P3_NON_CLOSE_DAY_FOCUSED:
        return "잔여 비마감일을 중심으로 목표 상향분을 우선 배분합니다."
    return "계산 결과와 경고 메시지를 확인해 후속 조치를 결정합니다."


def _uplift_ratio(required_uplift: float, remaining_target: float) -> float:
    if not _is_finite(required_uplift) or not _is_finite(remaining_target):
        return float("nan")
    if remaining_target <= 0:
        return float("nan")
    return required_uplift / remaining_target


def _dedupe_warnings(warnings: list[object]) -> list[str]:
    result: list[str] = []
    for warning in warnings:
        if warning is None:
            continue
        text = str(warning)
        if text and text not in result:
            result.append(text)
    return result


def _round_amount(value: object) -> float | None:
    number = _as_float_or_nan(value)
    if not _is_finite(number):
        return number
    return round(number, 1)


def _round_rate(value: object) -> float:
    number = _as_float_or_nan(value)
    if not _is_finite(number):
        return number
    return round(number, 3)


def _as_float_or_nan(value: object) -> float:
    if value is None:
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _is_finite(value: object) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _as_date(value: object) -> date | object:
    try:
        return pd.Timestamp(value).normalize().date()
    except Exception:  # noqa: BLE001 - keep original value for failed-row context.
        return value
