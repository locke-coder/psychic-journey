"""Page renderers for the Month-End Pace Check Streamlit interface."""

from __future__ import annotations

from html import escape
from typing import Any, Callable, Mapping

import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - local test runtime may omit Streamlit.
    st = None

from src.ui_components import (
    format_krw,
    render_download_card,
    render_history_card,
    render_kpi_card,
    render_operation_mode_card,
    render_report_card,
    render_scenario_card,
    render_section_header,
    status_label,
)
from src.ui_navigation import render_page_header_html, validate_page_key
from src.ui_pages_raw_dashboard import render_raw_dashboard_page


def render_page(page_key: object, context: Mapping[str, Any]) -> None:
    """Render the current page through the internal Streamlit router."""
    key = validate_page_key(page_key)
    renderer = {
        "home": render_home_page,
        "input": render_input_page,
        "forecast_strategy": render_forecast_strategy_page,
        "report": render_report_page,
        "history": render_history_page,
        "raw_dashboard": render_raw_dashboard_page,
        "excel": render_excel_page,
        "audit": render_audit_page,
    }.get(key, render_home_page)
    renderer(context)


def render_home_page(context: Mapping[str, Any]) -> None:
    """Render the summary front page."""
    _require_streamlit()
    st.markdown(_home_hero_html(), unsafe_allow_html=True)

    selected_row = _as_series(context.get("selected_row"))
    validation_result = dict(context.get("validation_result") or {})
    next_close_result = dict(context.get("next_close_result") or {})
    target_status = selected_row.get("target_status")

    st.markdown(
        render_operation_mode_card(
            target_status,
            target_variance=selected_row.get("target_variance"),
            surplus_to_target=selected_row.get("surplus_to_target"),
        ),
        unsafe_allow_html=True,
    )

    kpi_cards = (
        render_kpi_card(
            "현재 누적 실적",
            format_krw(validation_result.get("current_actual_cum")),
            sub="입력 기준 누적 실적",
            target_status=target_status,
        ),
        render_kpi_card(
            "월마감 예상 실적",
            format_krw(selected_row.get("forecast_after_provision")),
            sub=str(selected_row.get("scenario_id") or "입력 후 계산됩니다"),
            focus=True,
            target_status=target_status,
        ),
        render_kpi_card(
            "월 목표",
            format_krw(validation_result.get("monthly_target")),
            sub="일별 목표 합계",
            target_status=target_status,
        ),
        render_kpi_card(
            "목표 대비 차이",
            format_krw(selected_row.get("target_variance")),
            sub="양수는 초과, 음수는 미달",
            focus=True,
            target_status=target_status,
        ),
        render_kpi_card(
            "목표 상태",
            status_label(target_status),
            sub="보정/유지/초과달성 관리",
            target_status=target_status,
        ),
        render_kpi_card(
            "다음 마감 누적선 필요실적",
            format_krw(next_close_result.get("required_to_recover_next_close_cum")),
            sub="다음 마감일까지의 누적 기준",
            focus=True,
            target_status=target_status,
        ),
    )
    st.markdown(f'<div class="kpi-grid">{"".join(kpi_cards)}</div>', unsafe_allow_html=True)

    _render_scenario_preview(_as_dataframe(context.get("scenario_df")))
    _render_report_preview(str(context.get("report_text") or "입력 후 계산됩니다"))
    _render_bottom_previews(context)
    st.markdown(_home_cta_html(), unsafe_allow_html=True)


def render_input_page(context: Mapping[str, Any]) -> None:
    _render_callback_page(
        "input",
        context,
        "render_input_page",
    )


def render_forecast_page(context: Mapping[str, Any]) -> None:
    render_forecast_strategy_page(context)


def render_scenarios_page(context: Mapping[str, Any]) -> None:
    render_forecast_strategy_page(context)


def render_forecast_strategy_page(context: Mapping[str, Any]) -> None:
    _render_callback_page(
        "forecast_strategy",
        context,
        "render_forecast_strategy_page",
    )


def render_report_page(context: Mapping[str, Any]) -> None:
    _render_callback_page(
        "report",
        context,
        "render_report_page",
    )


def render_history_page(context: Mapping[str, Any]) -> None:
    _render_callback_page(
        "history",
        context,
        "render_history_page",
    )


def render_excel_page(context: Mapping[str, Any]) -> None:
    _render_callback_page(
        "excel",
        context,
        "render_excel_page",
    )


def render_audit_page(context: Mapping[str, Any]) -> None:
    _render_callback_page(
        "audit",
        context,
        "render_audit_page",
    )


def _render_callback_page(
    page_key: str,
    context: Mapping[str, Any],
    callback_name: str,
) -> None:
    _require_streamlit()
    st.markdown(render_page_header_html(page_key), unsafe_allow_html=True)
    callback = context.get(callback_name)
    if callable(callback):
        callback()
        return
    st.info("이 페이지는 입력 후 계산됩니다.")


def _render_scenario_preview(scenario_df: pd.DataFrame) -> None:
    st.markdown(
        render_section_header(
            "시나리오 체크",
            "P1/P2/P3는 보정 전략, O1/O2/O3는 초과달성 운영 전략입니다.",
        ),
        unsafe_allow_html=True,
    )
    if scenario_df.empty:
        st.info("시나리오는 입력 후 계산됩니다.")
        return

    preview = scenario_df.head(6)
    cards = "".join(render_scenario_card(row) for row in preview.to_dict("records"))
    st.markdown(f'<div class="scenario-grid">{cards}</div>', unsafe_allow_html=True)
    if len(scenario_df) > len(preview):
        st.caption(f"전체 {len(scenario_df)}개 조합은 시나리오 상세 페이지에서 확인합니다.")


def _render_report_preview(report_text: str) -> None:
    st.markdown(
        render_section_header(
            "보고 메모",
            "report_builder.py가 생성한 원문을 요약 preview로 확인합니다.",
        ),
        unsafe_allow_html=True,
    )
    preview = report_text.strip()
    if len(preview) > 650:
        preview = preview[:650].rstrip() + "\n..."
    st.markdown(render_report_card(preview or "입력 후 계산됩니다"), unsafe_allow_html=True)


def _render_bottom_previews(context: Mapping[str, Any]) -> None:
    validation_result = dict(context.get("validation_result") or {})
    errors = list(validation_result.get("errors") or [])
    warnings = list(validation_result.get("warnings") or [])
    report_name = str(context.get("report_name") or "입력 후 계산됩니다")

    columns = st.columns(3)
    with columns[0]:
        st.markdown(
            render_history_card("완료월 이력이 충분하면 Backtest, 모델 가중치, 신뢰구간을 함께 확인합니다.", "예측 이력"),
            unsafe_allow_html=True,
        )
    with columns[1]:
        body = f"오류 {len(errors)}건 · 주의 {len(warnings)}건. 세부 검증은 검증 · 운영관리 페이지에서 확인합니다."
        st.markdown(render_history_card(body, "검증 상태"), unsafe_allow_html=True)
    with columns[2]:
        st.markdown(render_download_card(report_name), unsafe_allow_html=True)


def _home_hero_html() -> str:
    chips = "".join(
        f'<span class="pace-chip">{escape(chip)}</span>'
        for chip in ("오늘 기준 리포트", "Excel 최신본", "Backtest 확인")
    )
    return (
        '<section class="pace-hero">'
        '<div class="pace-hero-main">'
        '<div class="pace-eyebrow">Daily Close Review</div>'
        '<div class="pace-hero-title">마감 페이스 체크</div>'
        '<p class="pace-hero-copy">'
        "월 목표 대비 현재 흐름, 다음 마감 누적선, 부족분 보정과 초과달성 관리를 "
        "가볍게 점검하는 실무형 화면입니다."
        "</p>"
        f'<div class="pace-chip-row">{chips}</div>'
        "</div>"
        "</section>"
    )


def _home_cta_html() -> str:
    ctas = (
        ("예측 · 전략 보기", "forecast_strategy"),
        ("Excel 공유로 이동", "excel"),
        ("예측 이력 확인", "history"),
        ("보고 메모 열기", "report"),
    )
    links = "".join(
        f'<a class="pace-cta" href="?page={escape(page_key)}">{escape(label)}</a>'
        for label, page_key in ctas
    )
    return f'<div class="pace-cta-row">{links}</div>'


def _as_dataframe(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value
    if value is None:
        return pd.DataFrame()
    return pd.DataFrame(value)


def _as_series(value: Any) -> pd.Series:
    if isinstance(value, pd.Series):
        return value
    if isinstance(value, Mapping):
        return pd.Series(dict(value))
    return pd.Series(dtype=object)


def _require_streamlit() -> None:
    if st is None:
        raise RuntimeError("Streamlit is required to render UI pages.")
