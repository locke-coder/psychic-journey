"""Pure builders for the visual decision headline and summary rows."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import pandas as pd

from src.ui_formatters import (
    _as_float,
    _is_missing,
    format_amount,
    format_date as _format_date,
    format_signed_amount as _format_signed_amount,
    operation_mode_label as _operation_mode_label,
)


def build_visual_headline(
    selected_row: pd.Series,
    validation_result: dict[str, Any],
    next_close_result: dict[str, Any],
) -> str:
    """Return the first sentence users should read before the charts."""
    _ = validation_result
    target_status = str(selected_row.get("target_status", "UNKNOWN_TARGET_STATUS"))
    target_variance = _as_float(selected_row.get("target_variance"))
    surplus = _as_float(selected_row.get("surplus_to_target"))
    next_close_sentence = _visual_next_close_sentence(next_close_result)

    if target_status == "UNDER_TARGET" or (
        math.isfinite(target_variance) and target_variance < 0
    ):
        shortage = abs(target_variance) if math.isfinite(target_variance) else selected_row.get("gap_to_target")
        return (
            f"결론: 목표선보다 {format_amount(shortage)} 부족할 가능성이 큽니다. "
            "먼저 전략 반영 후 예상이 공식 월 목표선까지 회복되는지 보고, "
            f"그다음 잔여 일자별 추가 배분이 감당 가능한지 확인하세요. {next_close_sentence}"
        )

    if target_status == "OVER_TARGET" or (
        math.isfinite(target_variance) and target_variance > 0
    ):
        surplus_amount = surplus if math.isfinite(surplus) and surplus > 0 else target_variance
        return (
            f"결론: 목표선보다 {format_amount(surplus_amount)} 여유가 예상됩니다. "
            "초과분을 안전버퍼로 남길지, Stretch 목표로 전환할지 차트에서 확인하세요. "
            f"{next_close_sentence}"
        )

    return (
        "결론: 목표선 근처의 유지/모니터링 구간입니다. "
        "시각화에서는 예측모델별 흔들림과 다음 마감 누적선을 함께 확인하세요. "
        f"{next_close_sentence}"
    )


def build_visual_decision_summary(
    selected_row: pd.Series,
    validation_result: dict[str, Any],
    next_close_result: dict[str, Any],
    *,
    localize_display_value: Callable[[object], object],
) -> pd.DataFrame:
    """Return chart interpretation rows in a fixed reading order."""
    target_status = selected_row.get("target_status", "UNKNOWN_TARGET_STATUS")
    risk_level = selected_row.get("risk_level", "N/A")
    operation_mode = _operation_mode_label(target_status)
    monthly_target = validation_result.get("monthly_target")
    forecast_after = selected_row.get("forecast_after_provision")
    target_variance = selected_row.get("target_variance")
    next_close_date = next_close_result.get("next_close_date")
    next_close_required = next_close_result.get("required_to_recover_next_close_cum")

    return pd.DataFrame(
        [
            {
                "확인 순서": "1",
                "볼 것": "목표 판정",
                "현재 값": (
                    f"{localize_display_value(target_status)} / "
                    f"위험 {localize_display_value(risk_level)}"
                ),
                "해석": _visual_status_sentence(target_status, operation_mode),
            },
            {
                "확인 순서": "2",
                "볼 것": "목표선 대비 예상 실적",
                "현재 값": (
                    f"{format_amount(forecast_after)} / "
                    f"목표 {format_amount(monthly_target)}"
                ),
                "해석": "막대가 목표선보다 낮으면 잔여 목표 보정이 필요하고, 높으면 초과분 관리가 핵심입니다.",
            },
            {
                "확인 순서": "3",
                "볼 것": "목표 대비 차이",
                "현재 값": _format_signed_amount(target_variance),
                "해석": _visual_variance_sentence(target_variance),
            },
            {
                "확인 순서": "4",
                "볼 것": "다음 마감선",
                "현재 값": (
                    f"{_format_date(next_close_date)} / "
                    f"{format_amount(next_close_required)}"
                ),
                "해석": _visual_next_close_sentence(next_close_result),
            },
        ]
    )


def _visual_status_sentence(target_status: object, operation_mode: object) -> str:
    status = str(target_status)
    mode = str(operation_mode)
    if status == "UNDER_TARGET":
        return f"{mode} 상태입니다. 시나리오별 예상 탭에서 어떤 F/P 조합이 부족분을 줄이는지 보세요."
    if status == "OVER_TARGET":
        return f"{mode} 상태입니다. 초과분을 버퍼로 둘지, 상향 목표로 전환할지 전략 수준 탭에서 보세요."
    if status == "ON_TARGET":
        return f"{mode} 상태입니다. 목표선은 맞지만 마감차수 흐름이 흔들리는지 함께 확인하세요."
    return "목표 판정에 필요한 값이 부족합니다. 입력값 점검 결과를 먼저 확인하세요."


def _visual_variance_sentence(value: object) -> str:
    number = _as_float(value)
    if not math.isfinite(number):
        return "목표 대비 차이를 계산할 수 없습니다. 선택 시나리오 상세 값을 확인하세요."
    if number < 0:
        return f"월말 기준 {format_amount(abs(number))}를 더 채워야 목표선에 도달합니다."
    if number > 0:
        return f"월말 기준 {format_amount(number)}가 목표선 위에 있어 버퍼 또는 Stretch 후보입니다."
    return "월말 예상이 공식 월 목표와 거의 같습니다. 남은 기간의 변동 리스크를 봅니다."


def _visual_next_close_sentence(next_close_result: dict[str, Any]) -> str:
    next_close_date = next_close_result.get("next_close_date")
    required = _as_float(next_close_result.get("required_to_recover_next_close_cum"))
    if _is_missing(next_close_date) or not math.isfinite(required):
        return "다음 마감 기준선은 계산 가능한 데이터가 있을 때 표시됩니다."
    if required <= 0:
        return f"{_format_date(next_close_date)}까지 다음 마감 기준선에 대한 추가 회복 부담은 없습니다."
    return f"{_format_date(next_close_date)}까지 누적 기준으로 최소 {format_amount(required)}을 더 확보해야 합니다."
