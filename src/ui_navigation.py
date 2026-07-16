"""Navigation helpers for the Month-End Pace Check Streamlit router."""

from __future__ import annotations

from collections import OrderedDict
from html import escape
from typing import Any, Mapping
from urllib.parse import urlencode


PAGE_STATE_KEY = "pace_current_page"
NAV_COLLAPSED_STATE_KEY = "pace_nav_collapsed"

NAV_GROUPS = OrderedDict(
    (
        ("daily", {"title": "1. 일일 운영", "pages": ("home", "input", "forecast_strategy")}),
        ("review", {"title": "2. 비교 · 보고", "pages": ("history", "raw_dashboard", "report")}),
        ("control", {"title": "3. 공유 · 검증", "pages": ("excel", "audit")}),
    )
)

PAGE_DEFINITIONS = OrderedDict(
    (
        (
            "home",
            {
                "title": "마감 페이스 체크",
                "short_title": "홈",
                "group": "daily",
                "subtitle": "오늘의 월마감 현황과 다음 판단을 먼저 확인합니다.",
                "related": ("input", "forecast_strategy"),
                "next_page": "input",
            },
        ),
        (
            "input",
            {
                "title": "입력 · 데이터",
                "short_title": "입력",
                "group": "daily",
                "subtitle": "기준일, 영업일정, is_close_day와 누적 실적 입력 상태를 함께 확인합니다.",
                "related": ("audit",),
                "next_page": "forecast_strategy",
            },
        ),
        (
            "forecast_strategy",
            {
                "title": "예측 · 전략 통합",
                "short_title": "예측전략",
                "group": "daily",
                "subtitle": "F1/F2/F3 예측과 선택 시나리오, 운영전략을 한 흐름에서 판단합니다.",
                "related": ("history", "raw_dashboard"),
                "next_page": "report",
            },
        ),
        (
            "history",
            {
                "title": "예측 이력",
                "short_title": "이력",
                "group": "review",
                "subtitle": "완료월 예측 정확도, Backtest와 모델 신뢰도를 확인합니다.",
                "related": ("raw_dashboard",),
                "next_page": "report",
            },
        ),
        (
            "raw_dashboard",
            {
                "title": "N영업일 Raw 비교",
                "short_title": "Raw비교",
                "group": "review",
                "subtitle": "HTM 기초자료를 동일 영업일차로 비교하며 예측 입력과 분리해 검증합니다.",
                "related": ("history",),
                "next_page": "report",
            },
        ),
        (
            "report",
            {
                "title": "보고 메모",
                "short_title": "보고",
                "group": "review",
                "subtitle": "선택한 예측·전략의 판단 요약과 복사용 보고문을 함께 확인합니다.",
                "related": ("forecast_strategy",),
                "next_page": "excel",
            },
        ),
        (
            "excel",
            {
                "title": "Excel 공유",
                "short_title": "Excel",
                "group": "control",
                "subtitle": "실제 최신 공유본과 현재 생성 예정 파일을 구분해 확인합니다.",
                "related": ("report",),
                "next_page": "audit",
            },
        ),
        (
            "audit",
            {
                "title": "검증 · 운영관리",
                "short_title": "검증",
                "group": "control",
                "subtitle": "입력 검증과 저장된 테스트·Gate·보안 운영 상태를 확인합니다.",
                "related": ("input", "excel"),
                "next_page": "home",
            },
        ),
    )
)

PAGE_ALIASES = {
    "forecast": "forecast_strategy",
    "scenarios": "forecast_strategy",
    "scenario": "forecast_strategy",
}


def validate_page_key(page_key: object) -> str:
    """Return a safe page key, falling back to home."""
    key = str(page_key or "").strip()
    key = PAGE_ALIASES.get(key, key)
    if key in PAGE_DEFINITIONS:
        return key
    return "home"


def page_title(page_key: object) -> str:
    """Return the display title for a page key."""
    return PAGE_DEFINITIONS[validate_page_key(page_key)]["title"]


def page_subtitle(page_key: object) -> str:
    """Return the centralized purpose statement for a page."""
    return str(PAGE_DEFINITIONS[validate_page_key(page_key)].get("subtitle") or "")


def page_group_title(page_key: object) -> str:
    """Return the workflow group title for a page."""
    definition = PAGE_DEFINITIONS[validate_page_key(page_key)]
    group_key = str(definition.get("group") or "daily")
    group = NAV_GROUPS.get(group_key, {})
    return str(group.get("title") or "페이지")


def get_current_page(st_module: Any | None = None) -> str:
    """Resolve the current page from query params or Streamlit session state."""
    query_page = _query_param_page(st_module)
    if query_page:
        page_key = validate_page_key(query_page)
        _set_session_page(st_module, page_key)
        return page_key

    session_page = _session_get(st_module, PAGE_STATE_KEY)
    page_key = validate_page_key(session_page)
    _set_session_page(st_module, page_key)
    return page_key


def set_current_page(page_key: object, st_module: Any | None = None) -> str:
    """Persist the current page in Streamlit session state."""
    safe_key = validate_page_key(page_key)
    _set_session_page(st_module, safe_key)
    return safe_key


def nav_item_class(page_key: object, active_page: object) -> str:
    """Return the CSS classes for a navigation item."""
    safe_key = validate_page_key(page_key)
    active_key = validate_page_key(active_page)
    return "nav-item active" if safe_key == active_key else "nav-item"


def render_nav_item_html(
    page_key: object,
    active_page: object,
    *,
    collapsed: bool = False,
) -> str:
    """Render one link item for the navigation rail."""
    safe_key = validate_page_key(page_key)
    definition = PAGE_DEFINITIONS[safe_key]
    label = definition["short_title"] if collapsed else definition["title"]
    href = "?" + urlencode({"page": safe_key})
    css_class = nav_item_class(safe_key, active_page)
    active_marker = '<span class="nav-item__marker">현재</span>' if safe_key == validate_page_key(active_page) else ""
    return (
        f'<a class="{escape(css_class)}" href="{escape(href)}">'
        f'<span class="nav-item__label">{escape(label)}</span>'
        f"{active_marker}"
        "</a>"
    )


def render_nav_rail_html(active_page: object, *, collapsed: bool = False) -> str:
    """Render the left navigation rail as local HTML."""
    title = "NAV" if collapsed else "페이지 이동"
    groups = "".join(
        '<section class="nav-group">'
        f'<div class="nav-group__title">{escape(str(group["title"]))}</div>'
        + "".join(
            render_nav_item_html(page_key, active_page, collapsed=collapsed)
            for page_key in group["pages"]
        )
        + "</section>"
        for group in NAV_GROUPS.values()
    )
    collapsed_class = " is-collapsed" if collapsed else ""
    return (
        f'<aside class="nav-rail{collapsed_class}">'
        f'<div class="nav-rail__title">{escape(title)}</div>'
        f'<div class="nav-rail__items">{groups}</div>'
        "</aside>"
    )


def render_page_flow_html(page_key: object) -> str:
    """Render compact related-page and next-step links for a page header."""
    safe_key = validate_page_key(page_key)
    definition = PAGE_DEFINITIONS[safe_key]
    related_keys = tuple(definition.get("related") or ())
    next_key = validate_page_key(definition.get("next_page"))
    related_links = " · ".join(
        f'<a href="?{escape(urlencode({"page": validate_page_key(key)}))}">'
        f'{escape(page_title(key))}</a>'
        for key in related_keys
    )
    next_link = (
        f'<a href="?{escape(urlencode({"page": next_key}))}">'
        f'{escape(page_title(next_key))}</a>'
    )
    return (
        '<div class="page-header__flow">'
        '<span class="page-header__flow-item"><strong>함께 보기</strong>'
        f'{related_links or "-"}</span>'
        '<span class="page-header__flow-item is-next"><strong>다음 단계</strong>'
        f'{next_link}</span>'
        "</div>"
    )


def render_quick_links_html(active_page: object) -> str:
    """Render top quick links used on detail pages."""
    links = "".join(
        render_nav_item_html(page_key, active_page, collapsed=True)
        for page_key in PAGE_DEFINITIONS
        if page_key != "input"
    )
    return f'<div class="mini-nav">{links}</div>'


def render_top_nav_html(
    active_page: object,
    *,
    meta: Mapping[str, object] | None = None,
) -> str:
    """Render the sticky top navigation bar."""
    meta = dict(meta or {})
    meta_items = (
        ("기준월", meta.get("target_month", "입력 후 계산됩니다")),
        ("영업일", meta.get("business_day", "입력 후 계산됩니다")),
        ("마감일", meta.get("close_day", "입력 후 계산됩니다")),
        ("운영모드", meta.get("operation_mode", "로컬 운영")),
    )
    pills = "".join(
        f'<span class="pace-pill{primary}">{escape(label)}: {escape(str(value))}</span>'
        for index, (label, value) in enumerate(meta_items)
        for primary in (" is-primary" if index == 0 else "",)
    )
    return (
        '<div class="pace-check-shell">'
        '<nav class="pace-topbar is-sticky">'
        '<div class="pace-brand"><span class="pace-brand-mark"></span>'
        '<span><strong>MONTH-END PACE CHECK</strong><small>마감 페이스 체크</small></span></div>'
        f'<div class="pace-current-page">{escape(page_title(active_page))}</div>'
        f'<div class="pace-topbar-meta">{pills}</div>'
        "</nav>"
        "</div>"
    )


def render_page_header_html(
    page_key: object,
    *,
    subtitle: str | None = None,
) -> str:
    """Render the page header for detail pages."""
    resolved_subtitle = page_subtitle(page_key) if subtitle is None else str(subtitle)
    subtitle_html = (
        f'<div class="page-header__subtitle">{escape(resolved_subtitle)}</div>'
        if resolved_subtitle
        else ""
    )
    return (
        '<header class="page-header">'
        f'<div class="page-header__eyebrow">{escape(page_group_title(page_key))}</div>'
        f'<h1>{escape(page_title(page_key))}</h1>'
        f"{subtitle_html}"
        f"{render_page_flow_html(page_key)}"
        "</header>"
    )


def render_side_nav(st_module: Any, active_page: object) -> None:
    """Render the left toggle navigation in the Streamlit sidebar."""
    collapsed = bool(_session_get(st_module, NAV_COLLAPSED_STATE_KEY, False))
    with st_module.sidebar:
        if st_module.button("네비게이션 펼치기" if collapsed else "네비게이션 접기"):
            st_module.session_state[NAV_COLLAPSED_STATE_KEY] = not collapsed
            _rerun(st_module)
        st_module.markdown(
            render_nav_rail_html(active_page, collapsed=collapsed),
            unsafe_allow_html=True,
        )


def render_top_nav(st_module: Any, active_page: object, meta: Mapping[str, object] | None = None) -> None:
    """Render the sticky topbar."""
    st_module.markdown(
        render_top_nav_html(active_page, meta=meta),
        unsafe_allow_html=True,
    )


def render_quick_links(st_module: Any, active_page: object) -> None:
    """Render the top mini navigation links."""
    st_module.markdown(render_quick_links_html(active_page), unsafe_allow_html=True)


def _query_param_page(st_module: Any | None) -> str | None:
    if st_module is None:
        return None
    try:
        params = getattr(st_module, "query_params", {})
        value = params.get("page")
    except Exception:  # noqa: BLE001 - Streamlit compatibility only.
        value = None
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value) if value else None


def _session_get(st_module: Any | None, key: str, default: object = None) -> object:
    if st_module is None or not hasattr(st_module, "session_state"):
        return default
    return st_module.session_state.get(key, default)


def _set_session_page(st_module: Any | None, page_key: str) -> None:
    if st_module is not None and hasattr(st_module, "session_state"):
        st_module.session_state[PAGE_STATE_KEY] = page_key


def _rerun(st_module: Any) -> None:
    if hasattr(st_module, "rerun"):
        st_module.rerun()
    else:  # pragma: no cover - compatibility for older Streamlit runtimes.
        st_module.experimental_rerun()
