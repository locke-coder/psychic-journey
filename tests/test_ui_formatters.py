from __future__ import annotations

import math

import pandas as pd

from src.ui_formatters import (
    _as_float,
    _is_missing,
    chart_value_format,
    format_amount,
    format_date,
    format_optional_amount,
    format_rate,
    format_signed_amount,
    operation_mode_label,
    target_status_arrival_label,
)


def test_format_amount_preserves_existing_behavior() -> None:
    assert format_amount(12.34) == "12.3억 원"
    assert format_amount(0) == "0.0억 원"
    assert format_amount(-2.34) == "-2.3억 원"
    assert format_amount("7.89") == "7.9억 원"
    assert format_amount(None) == "계산 불가"
    assert format_amount(float("nan")) == "계산 불가"


def test_format_rate_preserves_existing_behavior() -> None:
    assert format_rate(1.0) == "100.0%"
    assert format_rate(0.123) == "12.3%"
    assert format_rate(-0.05) == "-5.0%"
    assert format_rate(None) == "계산 불가"
    assert format_rate(float("nan")) == "계산 불가"


def test_format_signed_amount() -> None:
    assert format_signed_amount(1.23) == "+1.2억 원"
    assert format_signed_amount(-1.23) == "-1.2억 원"
    assert format_signed_amount(0) == "0.0억 원"
    assert format_signed_amount("invalid") == "계산 불가"
    assert format_signed_amount(None) == "계산 불가"


def test_format_optional_amount() -> None:
    assert format_optional_amount(12.34) == format_amount(12.34)
    assert format_optional_amount(None) == "-"
    assert format_optional_amount(float("nan")) == "-"
    assert format_optional_amount("invalid") == "-"


def test_format_date() -> None:
    assert format_date(pd.Timestamp("2026-06-10")) == "2026-06-10"
    assert format_date("2026-06-10") == "2026-06-10"
    assert format_date("not-a-date") == "not-a-date"
    assert format_date(None) == "계산 불가"
    assert format_date(float("nan")) == "계산 불가"


def test_chart_value_format() -> None:
    assert chart_value_format("억원") == ",.1f"
    assert chart_value_format("%") == ",.1f"
    assert chart_value_format("") == ",.1f"


def test_target_status_arrival_label() -> None:
    assert target_status_arrival_label("UNDER_TARGET") == "UNDER_TARGET 목표선 미달 구간"
    assert target_status_arrival_label("ON_TARGET") == "ON_TARGET 계획선 근접 구간"
    assert target_status_arrival_label("OVER_TARGET") == "OVER_TARGET 초과달성 관리 구간"
    assert target_status_arrival_label("UNKNOWN") == "계산 확인 구간"


def test_operation_mode_label() -> None:
    assert operation_mode_label("UNDER_TARGET") == "목표 보정 필요"
    assert operation_mode_label("ON_TARGET") == "유지/모니터링"
    assert operation_mode_label("OVER_TARGET") == "초과달성 관리"
    assert operation_mode_label(None) == "계산 불가"
    assert operation_mode_label(float("nan")) == "계산 불가"


def test_private_missing_helper() -> None:
    assert _is_missing(None) is True
    assert _is_missing(float("nan")) is True
    assert _is_missing(pd.NA) is True
    assert _is_missing("value") is False
    assert _is_missing([1, 2, 3]) is False


def test_private_as_float() -> None:
    assert _as_float(1) == 1.0
    assert _as_float(1.5) == 1.5
    assert _as_float("2.5") == 2.5
    assert math.isnan(_as_float("invalid"))
    assert math.isnan(_as_float(None))
    assert math.isnan(_as_float(float("nan")))
