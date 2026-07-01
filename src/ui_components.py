"""Display-only helpers for the Month-End Pace Check UI."""

from __future__ import annotations

from html import escape
from numbers import Real
from typing import Mapping

import pandas as pd

from src.display_labels import (
    SHORT_STRATEGY_LABELS,
    STATUS_LABELS,
    STRATEGY_GROUP_LABELS,
    STRATEGY_LABELS,
    get_status_label,
    get_strategy_code,
    get_strategy_group,
    get_strategy_label,
    get_strategy_short_description,
)

STATUS_CLASSES = {
    "UNDER_TARGET": "under-target",
    "ON_TARGET": "on-target",
    "OVER_TARGET": "over-target",
}

OPERATION_MODE_DESCRIPTIONS = {
    "UNDER_TARGET": "목표 대비 부족 흐름입니다. 남은 영업일과 마감일 기준으로 보정 필요실적을 확인합니다.",
    "ON_TARGET": "목표선에 근접한 흐름입니다. 다음 마감 누적선을 확인하며 유지 전략을 점검합니다.",
    "OVER_TARGET": "목표를 상회하는 흐름입니다. 초과분을 버퍼·Stretch·품질 기준으로 나눠 봅니다.",
}

SCENARIO_LABELS = dict(STRATEGY_LABELS)
SHORT_SCENARIO_LABELS = dict(SHORT_STRATEGY_LABELS)

SCENARIO_DESCRIPTIONS = {
    code: get_strategy_short_description(code) for code in SHORT_SCENARIO_LABELS
}


def format_krw(value: object) -> str:
    """Format an amount in the app's base amount unit."""
    if _is_missing(value):
        return "계산 불가"
    try:
        return f"{float(value):,.1f}억원"
    except (TypeError, ValueError):
        return str(value)


def status_label(target_status: object) -> str:
    """Return the business-facing label for a target status."""
    return get_status_label(target_status)


def status_class(target_status: object) -> str:
    """Return the CSS class suffix for a target status."""
    text = "" if _is_missing(target_status) else str(target_status)
    return STATUS_CLASSES.get(text, "unknown")


def operation_mode_description(target_status: object) -> str:
    """Return the operating mode explanation for a target status."""
    text = "" if _is_missing(target_status) else str(target_status)
    return OPERATION_MODE_DESCRIPTIONS.get(
        text,
        "입력값과 목표 상태를 기준으로 다음 운영 판단을 확인합니다.",
    )


def scenario_display_name(scenario_id: object) -> str:
    """Return the display name for a scenario or strategy id."""
    return get_strategy_label(scenario_id)


def scenario_description(scenario_id: object) -> str:
    """Return display-only scenario guidance."""
    if _is_missing(scenario_id):
        return "현재 목표선과 입력 흐름을 유지하며 모니터링합니다."
    text = str(scenario_id)
    token = _scenario_token(text)
    if token in SCENARIO_DESCRIPTIONS:
        return SCENARIO_DESCRIPTIONS[token]
    if "NEUTRAL" in text.upper() or "MAINTAIN" in text.upper():
        return "현재 목표선과 입력 흐름을 유지하며 모니터링합니다."
    return "선택한 전략의 계산 결과를 원본 시나리오 행 기준으로 확인합니다."


def scenario_kind_class(scenario_id: object) -> str:
    """Return the scenario kind class without changing source ids."""
    if _is_missing(scenario_id):
        return "neutral"
    token = get_strategy_code(scenario_id)
    if token in {"P1", "P2", "P3"}:
        return "p"
    if token in {"O1", "O2", "O3"}:
        return token.lower()
    return "neutral"


def scenario_is_emphasis(scenario_id: object) -> bool:
    """Return whether a scenario should receive a soft visual emphasis."""
    return scenario_kind_class(scenario_id) in {"o1", "o2", "o3"}


def render_section_header(title: str, subtitle: str | None = None) -> str:
    """Render a compact section heading."""
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="section-header__subtitle">{escape(subtitle)}</div>'
    return (
        '<div class="section-header">'
        f'<div class="section-header__title">{escape(title)}</div>'
        f"{subtitle_html}"
        "</div>"
    )


def render_status_badge(target_status: object) -> str:
    """Render a target status badge."""
    css_class = escape(status_class(target_status))
    label = escape(status_label(target_status))
    return f'<span class="status-badge status-{css_class}">{label}</span>'


def render_pace_header(
    *,
    as_of_date: object,
    current_business_day_no: object,
    total_business_days: object,
    close_day_label: str,
) -> str:
    """Render the topbar and hero for the pace-check screen."""
    meta = [
        ("기준월", _format_month_value(as_of_date)),
        ("영업일", f"{_format_meta_value(current_business_day_no)} / {_format_meta_value(total_business_days)}"),
        ("마감일 여부", close_day_label),
        ("운영", "로컬 운영"),
    ]
    badges = "".join(
        f'<span class="pace-pill{primary}">{escape(label)}: {escape(value)}</span>'
        for index, (label, value) in enumerate(meta)
        for primary in (" is-primary" if index == 0 else "",)
    )
    chips = "".join(
        f'<span class="pace-chip">{escape(chip)}</span>'
        for chip in ("오늘 기준 리포트", "Excel 최신본", "Backtest 확인")
    )
    return (
        '<div class="pace-check-shell">'
        '<nav class="pace-topbar">'
        '<div class="pace-brand"><span class="pace-brand-mark"></span>MONTH-END PACE CHECK</div>'
        f'<div class="pace-topbar-meta">{badges}</div>'
        "</nav>"
        '<section class="pace-hero">'
        '<div class="pace-hero-main">'
        '<div class="pace-eyebrow">Daily Close Review</div>'
        '<div class="pace-hero-title">마감 페이스 체크</div>'
        '<p class="pace-hero-copy">'
        "월 목표 대비 현재 흐름, 다음 마감 누적선, 부족분 보정과 초과달성 관리를 가볍게 점검하는 실무형 화면입니다."
        "</p>"
        f'<div class="pace-chip-row">{chips}</div>'
        "</div>"
        "</section>"
        "</div>"
    )


def render_control_header(
    *,
    as_of_date: object,
    current_business_day_no: object,
    total_business_days: object,
    close_day_label: str,
) -> str:
    """Compatibility wrapper for legacy imports."""
    return render_pace_header(
        as_of_date=as_of_date,
        current_business_day_no=current_business_day_no,
        total_business_days=total_business_days,
        close_day_label=close_day_label,
    )


def render_operation_mode_card(
    target_status: object,
    *,
    target_variance: object | None = None,
    surplus_to_target: object | None = None,
) -> str:
    """Render the current operating mode without changing calculations."""
    css_class = escape(status_class(target_status))
    return (
        f'<section class="pace-mode-card status-{css_class}">'
        '<div class="pace-mode-card__label">오늘의 운영모드</div>'
        f'<div class="pace-mode-card__mode">{escape(status_label(target_status))}</div>'
        f'<div class="pace-mode-card__description">{escape(operation_mode_description(target_status))}</div>'
        '<div class="pace-mode-card__facts">'
        '<div class="pace-mode-card__fact">'
        "<small>목표 대비 차이</small>"
        f"<strong>{escape(format_krw(target_variance))}</strong>"
        "</div>"
        '<div class="pace-mode-card__fact">'
        "<small>초과 예상분</small>"
        f"<strong>{escape(format_krw(surplus_to_target))}</strong>"
        "</div>"
        "</div>"
        "</section>"
    )


def render_kpi_card(
    label: str,
    value: object,
    sub: str | None = None,
    focus: bool = False,
    *,
    note: str | None = None,
    target_status: object | None = None,
) -> str:
    """Render a single flat KPI card."""
    sub_text = sub if sub is not None else note
    status_suffix = status_class(target_status)
    focus_class = " is-focus" if focus else ""
    sub_html = f'<div class="kpi-card__sub">{escape(sub_text)}</div>' if sub_text else ""
    return (
        f'<article class="kpi-card status-{escape(status_suffix)}{focus_class}">'
        f'<div class="kpi-card__label">{escape(label)}</div>'
        f'<div class="kpi-card__value">{escape(str(value))}</div>'
        f"{sub_html}"
        "</article>"
    )


def render_scenario_card(row: Mapping[str, object]) -> str:
    """Render a display-only scenario card without changing source rows."""
    scenario_id = _safe_text(row.get("scenario_id", ""))
    strategy_id = _best_strategy_id(row)
    display_id = strategy_id or scenario_id
    kind_class = scenario_kind_class(display_id)
    emphasis_class = " is-emphasis" if scenario_is_emphasis(display_id) else ""
    group_label = _scenario_group_label(row.get("strategy_type"), display_id)
    target_status = row.get("target_status")
    forecast_value = row.get("forecast_after_provision", row.get("forecast_amount"))
    variance_value = row.get("target_variance")

    return (
        f'<article class="scenario-card scenario-card--{escape(kind_class)}{emphasis_class}">'
        '<div class="scenario-card__topline">'
        f'<div><div class="scenario-card__id">{escape(scenario_id)}</div>'
        f'<div class="scenario-card__group">{escape(group_label)}</div></div>'
        f"{render_status_badge(target_status)}"
        "</div>"
        f'<div class="scenario-card__name">{escape(scenario_display_name(display_id))}</div>'
        f'<div class="scenario-card__description">{escape(scenario_description(display_id))}</div>'
        '<div class="scenario-card__metrics">'
        '<div class="scenario-card__metric">'
        '<div class="scenario-card__metric-label">전략 반영 후 예상</div>'
        f'<div class="scenario-card__metric-value">{escape(format_krw(forecast_value))}</div>'
        "</div>"
        '<div class="scenario-card__metric">'
        '<div class="scenario-card__metric-label">목표 대비 차이</div>'
        f'<div class="scenario-card__metric-value">{escape(format_krw(variance_value))}</div>'
        "</div>"
        "</div>"
        "</article>"
    )


def render_report_card(report_text: str) -> str:
    """Render generated report text as a light report memo."""
    chips = ("보고 요약", "운영 판단", "리스크", "권장 액션")
    chip_html = "".join(
        f'<span class="report-card__chip">{escape(chip)}</span>' for chip in chips
    )
    return (
        '<section class="report-card is-focus">'
        f'<div class="report-card__rail">{chip_html}</div>'
        f'<div class="report-card__body">{_report_body_html(report_text)}</div>'
        "</section>"
    )


def _report_body_html(report_text: str) -> str:
    text = str(report_text or "").strip()
    if not text:
        return '<p class="report-card__paragraph report-card__placeholder">예측 계산 후 보고 메모가 표시됩니다.</p>'

    sections = _parse_report_sections(text)
    if not sections:
        return f'<p class="report-card__paragraph">{escape(text)}</p>'

    section_html: list[str] = []
    for title, items in sections:
        item_html = "".join(f"<li>{escape(item)}</li>" for item in items)
        if item_html:
            body_html = f'<ul class="report-card__list">{item_html}</ul>'
        else:
            body_html = '<p class="report-card__paragraph report-card__placeholder">내용 없음</p>'
        section_html.append(
            '<section class="report-card__section">'
            f'<h3 class="report-card__section-title">{escape(title)}</h3>'
            f"{body_html}"
            "</section>"
        )
    return "".join(section_html)


def _parse_report_sections(report_text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_items: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_items
        if current_title:
            sections.append((current_title, current_items))
        current_title = ""
        current_items = []

    for raw_line in report_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line:
            flush()
            title, remainder = line[1:].split("]", maxsplit=1)
            current_title = title.strip()
            remainder = remainder.strip()
            if remainder.startswith("-"):
                remainder = remainder[1:].strip()
            if remainder:
                current_items.append(remainder)
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if current_title:
            current_items.append(line)
        else:
            sections.append(("", [line]))

    flush()
    return [(title or "보고 메모", items) for title, items in sections]


def render_history_card(body: str, label: str = "recent flow") -> str:
    """Render a short history/backtest note."""
    return (
        '<div class="history-card">'
        f'<div class="scenario-card__group">{escape(label)}</div>'
        f'<div class="scenario-card__description">{escape(body)}</div>'
        "</div>"
    )


def render_download_card(report_name: str) -> str:
    """Render the Excel sharing note."""
    return (
        '<div class="download-card">'
        '<div class="scenario-card__group">outputs/latest</div>'
        '<div class="scenario-card__name">최신 Excel 리포트</div>'
        '<div class="scenario-card__description">'
        f"파일명: {escape(report_name)}<br>"
        "운영 공유는 outputs/latest의 최신 산출물만 사용합니다. "
        "archive_invalid와 archive_old_format은 기본 공유 대상이 아닙니다."
        "</div>"
        "</div>"
    )


def _best_strategy_id(row: Mapping[str, object]) -> str:
    candidates = (
        row.get("overachievement_strategy"),
        row.get("provision_strategy"),
        row.get("neutral_strategy"),
        row.get("strategy_id"),
        row.get("scenario_id"),
    )
    for candidate in candidates:
        if not _is_missing(candidate):
            return str(candidate)
    return ""


def _scenario_group_label(strategy_type: object, scenario_id: object) -> str:
    if not _is_missing(strategy_type):
        text = str(strategy_type)
        if text in STRATEGY_GROUP_LABELS:
            return STRATEGY_GROUP_LABELS[text]
    return get_strategy_group(scenario_id)


def _scenario_token(identifier: str) -> str:
    return get_strategy_code(identifier)


def _format_month_value(value: object) -> str:
    if _is_missing(value):
        return "계산 불가"
    try:
        return pd.Timestamp(value).strftime("%Y-%m")
    except Exception:  # noqa: BLE001 - display fallback only.
        return str(value)


def _format_meta_value(value: object) -> str:
    if _is_missing(value):
        return "계산 불가"
    if isinstance(value, bool):
        return "예" if value else "아니오"
    if isinstance(value, Real):
        number = float(value)
        if number.is_integer():
            return str(int(number))
        return str(value)
    if isinstance(value, pd.Timestamp):
        return str(value.date())
    try:
        timestamp = pd.Timestamp(value)
        if not pd.isna(timestamp):
            return str(timestamp.date())
    except Exception:  # noqa: BLE001 - display fallback only.
        pass
    return str(value)


def _safe_text(value: object) -> str:
    if _is_missing(value):
        return ""
    return str(value)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
