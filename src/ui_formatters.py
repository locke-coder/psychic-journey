"""Display-only value formatters for the Streamlit app."""

from __future__ import annotations

import math

import pandas as pd

from src.display_labels import get_operation_mode


def format_amount(value: object) -> str:
    """Format an amount in hundred-million KRW."""
    number = _as_float(value)
    if not math.isfinite(number):
        return "계산 불가"
    return f"{number:.1f}억 원"


def format_rate(value: object) -> str:
    """Format a decimal ratio as a percentage."""
    number = _as_float(value)
    if not math.isfinite(number):
        return "계산 불가"
    return f"{number * 100:.1f}%"


def format_signed_amount(value: object) -> str:
    number = _as_float(value)
    if not math.isfinite(number):
        return "계산 불가"
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.1f}억 원"


def format_optional_amount(value: object) -> str:
    number = _as_float(value)
    if not math.isfinite(number):
        return "-"
    return format_amount(number)


def format_date(value: object) -> str:
    if _is_missing(value):
        return "계산 불가"
    try:
        return str(pd.Timestamp(value).date())
    except Exception:  # noqa: BLE001 - display only.
        return str(value)


def chart_value_format(unit: str) -> str:
    """Return a number format for values already stored in display units."""
    _ = unit
    return ",.1f"


def target_status_arrival_label(target_status: object) -> str:
    labels = {
        "UNDER_TARGET": "UNDER_TARGET 목표선 미달 구간",
        "ON_TARGET": "ON_TARGET 계획선 근접 구간",
        "OVER_TARGET": "OVER_TARGET 초과달성 관리 구간",
    }
    return labels.get(str(target_status), "계산 확인 구간")


def operation_mode_label(target_status: object) -> object:
    if _is_missing(target_status):
        return "계산 불가"
    return get_operation_mode(target_status)


def _as_float(value: object) -> float:
    if _is_missing(value):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
