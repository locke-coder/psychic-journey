"""Single display-label layer for status, metric, and strategy copy."""

from __future__ import annotations

import re
from typing import Final


STATUS_LABELS: Final[dict[str, str]] = {
    "UNDER_TARGET": "목표 보정 필요",
    "ON_TARGET": "유지/모니터링",
    "OVER_TARGET": "초과달성 관리",
    "UNKNOWN_TARGET_STATUS": "계산 불가",
}

OPERATION_MODE_LABELS: Final[dict[str, str]] = {
    "UNDER_TARGET": "목표 보정 필요",
    "ON_TARGET": "유지/모니터링",
    "OVER_TARGET": "초과달성 관리",
}

STATUS_TONES: Final[dict[str, str]] = {
    "UNDER_TARGET": "warning",
    "ON_TARGET": "stable",
    "OVER_TARGET": "surplus",
}

METRIC_LABELS: Final[dict[str, str]] = {
    "target_status": "목표 상태",
    "target_variance": "목표 대비 차이",
    "surplus_to_target": "초과 예상분",
    "next_close_required_amount": "다음 마감 누적선 필요실적",
    "next_close_required": "다음 마감 누적선 필요실적",
    "expected_month_end_amount": "월마감 예상 실적",
    "forecast_after_provision": "월마감 예상 실적",
    "forecast_amount": "월마감 예상 실적",
    "current_cumulative_actual": "현재 누적 실적",
    "current_actual_cum": "현재 누적 실적",
}

STRATEGY_LABELS: Final[dict[str, str]] = {
    "P1_ALL_REMAINING": "잔여목표 균등 배분",
    "P2_CLOSE_DAY_FOCUSED": "마감일 집중 보정",
    "P3_NON_CLOSE_DAY_FOCUSED": "비마감일 분산 보정",
    "O1_TARGET_HOLD_BUFFER": "버퍼 유지",
    "O2_STRETCH_TARGET_CAPTURE": "Stretch 전환",
    "O3_QUALITY_GUARD_RELIEF": "품질 방어",
    "N1_MAINTAIN_TARGET": "유지/모니터링",
    "N2_MONITOR_BUFFER": "유지/모니터링",
    "N3_QUALITY_CHECK": "유지/모니터링",
    "NEUTRAL": "유지/모니터링",
    "MAINTAIN": "유지/모니터링",
}

SHORT_STRATEGY_LABELS: Final[dict[str, str]] = {
    "P1": STRATEGY_LABELS["P1_ALL_REMAINING"],
    "P2": STRATEGY_LABELS["P2_CLOSE_DAY_FOCUSED"],
    "P3": STRATEGY_LABELS["P3_NON_CLOSE_DAY_FOCUSED"],
    "O1": STRATEGY_LABELS["O1_TARGET_HOLD_BUFFER"],
    "O2": STRATEGY_LABELS["O2_STRETCH_TARGET_CAPTURE"],
    "O3": STRATEGY_LABELS["O3_QUALITY_GUARD_RELIEF"],
    "N1": STRATEGY_LABELS["N1_MAINTAIN_TARGET"],
    "N2": STRATEGY_LABELS["N2_MONITOR_BUFFER"],
    "N3": STRATEGY_LABELS["N3_QUALITY_CHECK"],
}

STRATEGY_SHORT_CODES: Final[dict[str, str]] = {
    "P1_ALL_REMAINING": "P1",
    "P2_CLOSE_DAY_FOCUSED": "P2",
    "P3_NON_CLOSE_DAY_FOCUSED": "P3",
    "O1_TARGET_HOLD_BUFFER": "O1",
    "O2_STRETCH_TARGET_CAPTURE": "O2",
    "O3_QUALITY_GUARD_RELIEF": "O3",
    "N1_MAINTAIN_TARGET": "N1",
    "N2_MONITOR_BUFFER": "N2",
    "N3_QUALITY_CHECK": "N3",
}

STRATEGY_DESCRIPTIONS: Final[dict[str, str]] = {
    "P1": "남은 목표를 잔여 영업일에 균등하게 나눠 보정한다.",
    "P2": "부족분 회복을 마감일에 우선 배분한다.",
    "P3": "부족분 회복을 비마감일에 분산해 흡수한다.",
    "O1": "목표를 유지하고 초과 예상분을 안전버퍼로 관리한다.",
    "O2": "일부 초과분을 Stretch 목표로 전환한다.",
    "O3": "무리한 추가 영업보다 계약 품질과 취소/철회/미결제 리스크 방어를 우선한다.",
    "N1": "현재 목표선을 유지하며 다음 마감 누적선을 확인한다.",
    "N2": "목표선 주변 변동과 버퍼 소진 여부를 모니터링한다.",
    "N3": "추가 압박보다 계약 품질과 실적인정 가능성을 점검한다.",
}

STRATEGY_GROUP_LABELS: Final[dict[str, str]] = {
    "PROVISION": "목표 보정",
    "OVERACHIEVEMENT": "초과달성 운영",
    "NEUTRAL": "유지/모니터링",
}

FORECAST_MODEL_LABELS: Final[dict[str, str]] = {
    "F1": "F1 누적 달성률 모델",
    "F2": "F2 직전 2개 완료 마감차수 모델",
    "F3": "F3 마감일/비마감일 가중 모델",
    "F1_CUMULATIVE_RATE": "F1 누적 달성률 모델",
    "F2_LAST_TWO_CLOSES": "F2 직전 2개 완료 마감차수 모델",
    "F3_DAY_CLOSE_WEIGHTED": "F3 마감일/비마감일 가중 모델",
}


def get_status_label(status: object) -> str:
    """Return the business-facing label for a target status."""
    text = _safe_text(status)
    return STATUS_LABELS.get(text, text or "계산 불가")


def get_operation_mode(status: object) -> str:
    """Return the operating mode label for a target status."""
    text = _safe_text(status)
    return OPERATION_MODE_LABELS.get(text, get_status_label(text))


def get_strategy_label(strategy_code: object) -> str:
    """Return the display label for a strategy id or short code."""
    text = _safe_text(strategy_code)
    if not text:
        return "유지/모니터링"
    if text in STRATEGY_LABELS:
        return STRATEGY_LABELS[text]
    short_code = get_strategy_code(text)
    if short_code in SHORT_STRATEGY_LABELS:
        return SHORT_STRATEGY_LABELS[short_code]
    upper_text = text.upper()
    if "NEUTRAL" in upper_text or "MAINTAIN" in upper_text:
        return STRATEGY_LABELS["NEUTRAL"]
    return text


def get_strategy_short_description(strategy_code: object) -> str:
    """Return a short operational description for a strategy."""
    short_code = get_strategy_code(strategy_code)
    return STRATEGY_DESCRIPTIONS.get(
        short_code,
        "선택한 전략의 계산 결과를 원본 시나리오 행 기준으로 확인한다.",
    )


def get_metric_label(metric_key: object) -> str:
    """Return the display label for a known metric key."""
    text = _safe_text(metric_key)
    return METRIC_LABELS.get(text, text)


def get_status_tone(status: object) -> str:
    """Return a semantic tone token for CSS and badges."""
    text = _safe_text(status)
    return STATUS_TONES.get(text, "unknown")


def get_strategy_group(strategy_code: object) -> str:
    """Return the display strategy group label."""
    short_code = get_strategy_code(strategy_code)
    if short_code in {"P1", "P2", "P3"}:
        return STRATEGY_GROUP_LABELS["PROVISION"]
    if short_code in {"O1", "O2", "O3"}:
        return STRATEGY_GROUP_LABELS["OVERACHIEVEMENT"]
    return STRATEGY_GROUP_LABELS["NEUTRAL"]


def get_strategy_code(strategy_code: object) -> str:
    """Normalize a strategy id, short code, or scenario id to P/O/N short code."""
    text = _safe_text(strategy_code)
    if not text:
        return ""
    upper_text = text.upper()
    if upper_text in SHORT_STRATEGY_LABELS:
        return upper_text
    if upper_text in STRATEGY_SHORT_CODES:
        return STRATEGY_SHORT_CODES[upper_text]
    scenario_match = re.search(r"(?:^|_)([PON][123])(?:_|$)", upper_text)
    if scenario_match:
        return scenario_match.group(1)
    return upper_text


def get_forecast_model_label(model_code: object) -> str:
    """Return the display label for an F1/F2/F3 forecast model."""
    text = _safe_text(model_code)
    return FORECAST_MODEL_LABELS.get(text, text)


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    try:
        import pandas as pd

        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)
