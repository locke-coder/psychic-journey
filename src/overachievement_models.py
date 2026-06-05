"""Overachievement and neutral operating strategies for scenario rows."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

import pandas as pd

from src.provision_models import ALLOCATION_COLUMNS


O1_TARGET_HOLD_BUFFER = "O1_TARGET_HOLD_BUFFER"
O2_STRETCH_TARGET_CAPTURE = "O2_STRETCH_TARGET_CAPTURE"
O3_QUALITY_GUARD_RELIEF = "O3_QUALITY_GUARD_RELIEF"

N1_MAINTAIN_TARGET = "N1_MAINTAIN_TARGET"
N2_MONITOR_BUFFER = "N2_MONITOR_BUFFER"
N3_QUALITY_CHECK = "N3_QUALITY_CHECK"

PROVISION = "PROVISION"
OVERACHIEVEMENT = "OVERACHIEVEMENT"
NEUTRAL = "NEUTRAL"

OVER_TARGET_MANAGED = "OVER_TARGET_MANAGED"
ON_TARGET_MAINTAIN = "ON_TARGET_MAINTAIN"

OVERACHIEVEMENT_STRATEGIES = (
    O1_TARGET_HOLD_BUFFER,
    O2_STRETCH_TARGET_CAPTURE,
    O3_QUALITY_GUARD_RELIEF,
)
NEUTRAL_STRATEGIES = (
    N1_MAINTAIN_TARGET,
    N2_MONITOR_BUFFER,
    N3_QUALITY_CHECK,
)

OverachievementResult = dict[str, object]


def run_overachievement_strategy(
    forecast_result: Mapping[str, Any],
    strategy_id: str,
    config: Mapping[str, Any] | object | None = None,
) -> OverachievementResult:
    """Return an operating strategy for an OVER_TARGET forecast."""
    context = _build_context(forecast_result)
    if strategy_id == O1_TARGET_HOLD_BUFFER:
        return _build_o1_result(context, strategy_id)
    if strategy_id == O2_STRETCH_TARGET_CAPTURE:
        stretch_capture_rate = _as_float(_config_get(config, "stretch_capture_rate", 0.5))
        if not isfinite(stretch_capture_rate):
            stretch_capture_rate = 0.5
        stretch_capture_rate = min(1.0, max(0.0, stretch_capture_rate))
        return _build_o2_result(context, strategy_id, stretch_capture_rate)
    if strategy_id == O3_QUALITY_GUARD_RELIEF:
        return _build_o3_result(context, strategy_id)

    raise ValueError(f"Unsupported overachievement strategy: {strategy_id}.")


def run_neutral_strategy(
    forecast_result: Mapping[str, Any],
    strategy_id: str,
) -> OverachievementResult:
    """Return a maintain/monitoring strategy for an ON_TARGET forecast."""
    context = _build_context(forecast_result)
    if strategy_id == N1_MAINTAIN_TARGET:
        action = "공식 월 목표를 유지하고 잔여 기간의 기본 실행 계획을 유지합니다."
    elif strategy_id == N2_MONITOR_BUFFER:
        action = "목표와 거의 같은 상태이므로 취소, 철회, 미결제 변동을 매일 모니터링합니다."
    elif strategy_id == N3_QUALITY_CHECK:
        action = "무리한 상향보다 계약 품질, 결제완료율, 순계약 상태를 점검합니다."
    else:
        raise ValueError(f"Unsupported neutral strategy: {strategy_id}.")

    return _base_result(
        context=context,
        strategy_id=strategy_id,
        strategy_type=NEUTRAL,
        overachievement_strategy=None,
        status=ON_TARGET_MAINTAIN,
        recommended_action=action,
        comment=f"{strategy_id} keeps the monthly target and monitors execution quality.",
    )


def _build_o1_result(context: dict[str, float], strategy_id: str) -> OverachievementResult:
    return _base_result(
        context=context,
        strategy_id=strategy_id,
        strategy_type=OVERACHIEVEMENT,
        overachievement_strategy=strategy_id,
        status=OVER_TARGET_MANAGED,
        remaining_surplus_buffer=context["surplus_to_target"],
        recommended_action=(
            "목표는 유지하고 초과 예상분을 안전버퍼로 둡니다. "
            "취소, 철회, 미결제, 실적 조정 리스크 방어용으로 관리합니다."
        ),
        comment="O1 keeps the official target and treats surplus as a risk buffer.",
    )


def _build_o2_result(
    context: dict[str, float],
    strategy_id: str,
    stretch_capture_rate: float,
) -> OverachievementResult:
    stretch_uplift = context["surplus_to_target"] * stretch_capture_rate
    remaining_surplus_buffer = max(0.0, context["surplus_to_target"] - stretch_uplift)
    revised_monthly_target = context["monthly_target"] + stretch_uplift
    return _base_result(
        context=context,
        strategy_id=strategy_id,
        strategy_type=OVERACHIEVEMENT,
        overachievement_strategy=strategy_id,
        status=OVER_TARGET_MANAGED,
        stretch_uplift=stretch_uplift,
        revised_monthly_target=revised_monthly_target,
        remaining_surplus_buffer=remaining_surplus_buffer,
        recommended_action=(
            "초과 예상분 일부를 Stretch Target으로 전환합니다. "
            "무리한 압박이 아니라 추가 성장 목표를 설정하는 용도로 사용합니다."
        ),
        comment="O2 captures part of the surplus as a stretch target.",
    )


def _build_o3_result(context: dict[str, float], strategy_id: str) -> OverachievementResult:
    minimum_remaining_to_hit_target = max(
        0.0,
        context["monthly_target"] - context["current_actual_cum"],
    )
    relief_amount = max(
        0.0,
        context["remaining_target"] - minimum_remaining_to_hit_target,
    )
    return _base_result(
        context=context,
        strategy_id=strategy_id,
        strategy_type=OVERACHIEVEMENT,
        overachievement_strategy=strategy_id,
        status=OVER_TARGET_MANAGED,
        remaining_surplus_buffer=context["surplus_to_target"],
        minimum_remaining_to_hit_target=minimum_remaining_to_hit_target,
        relief_amount=relief_amount,
        recommended_action=(
            "공식 목표는 유지하고 계약 품질을 방어합니다. "
            "취소, 철회, 미결제, 결제완료율, 순계약, 상담 품질 리스크를 우선 관리합니다."
        ),
        comment="O3 keeps the official target and uses surplus to protect sales quality.",
    )


def _base_result(
    *,
    context: dict[str, float],
    strategy_id: str,
    strategy_type: str,
    overachievement_strategy: str | None,
    status: str,
    recommended_action: str,
    comment: str,
    stretch_uplift: float = 0.0,
    revised_monthly_target: float | None = None,
    remaining_surplus_buffer: float = 0.0,
    minimum_remaining_to_hit_target: float = 0.0,
    relief_amount: float = 0.0,
) -> OverachievementResult:
    revised_monthly_target = (
        context["monthly_target"]
        if revised_monthly_target is None
        else revised_monthly_target
    )
    revised_remaining_target = max(0.0, revised_monthly_target - context["current_actual_cum"])

    return {
        "strategy_id": strategy_id,
        "strategy_type": strategy_type,
        "overachievement_strategy": overachievement_strategy,
        "gap_to_target": context["gap_to_target"],
        "required_uplift": 0.0,
        "allocated_uplift": 0.0,
        "unallocated_uplift": 0.0,
        "revised_remaining_target": revised_remaining_target,
        "forecast_after_provision": context["forecast_amount"],
        "gap_after_provision": context["gap_to_target"],
        "stretch_uplift": max(0.0, stretch_uplift),
        "revised_monthly_target": revised_monthly_target,
        "remaining_surplus_buffer": max(0.0, remaining_surplus_buffer),
        "minimum_remaining_to_hit_target": max(0.0, minimum_remaining_to_hit_target),
        "relief_amount": max(0.0, relief_amount),
        "recommended_action": recommended_action,
        "allocation_by_day": pd.DataFrame(columns=ALLOCATION_COLUMNS),
        "status": status,
        "warnings": list(context["warnings"]),
        "comment": comment,
    }


def _build_context(forecast_result: Mapping[str, Any]) -> dict[str, Any]:
    monthly_target = _as_float(forecast_result.get("monthly_target", 0.0))
    current_actual_cum = _as_float(forecast_result.get("current_actual_cum", 0.0))
    remaining_target = _as_float(forecast_result.get("remaining_target", 0.0))
    forecast_amount = _as_float(forecast_result.get("forecast_amount", 0.0))
    target_variance = _as_float(
        forecast_result.get("target_variance", forecast_amount - monthly_target)
    )
    surplus_to_target = _as_float(
        forecast_result.get("surplus_to_target", max(0.0, target_variance))
    )
    gap_to_target = _as_float(
        forecast_result.get("gap_to_target", max(0.0, -target_variance))
    )

    return {
        "monthly_target": monthly_target,
        "current_actual_cum": current_actual_cum,
        "remaining_target": remaining_target,
        "forecast_amount": forecast_amount,
        "target_variance": target_variance,
        "surplus_to_target": max(0.0, surplus_to_target),
        "gap_to_target": max(0.0, gap_to_target),
        "warnings": list(forecast_result.get("warnings", [])),
    }


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
