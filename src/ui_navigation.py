"""Navigation helpers for the Month-End Pace Check Streamlit router."""

from __future__ import annotations

from collections import OrderedDict
from html import escape
from typing import Any, Mapping
from urllib.parse import urlencode


PAGE_STATE_KEY = "pace_current_page"
NAV_COLLAPSED_STATE_KEY = "pace_nav_collapsed"

PAGE_DEFINITIONS = OrderedDict(
    (
        ("home", {"title": "마감 페이스 체크", "short_title": "홈"}),
        ("input", {"title": "입력 · 데이터", "short_title": "입력"}),
        ("forecast_strategy", {"title": "예측 · 전략 통합", "short_title": "예측전략"}),
        ("report", {"title": "보고 메모", "short_title": "보고"}),
        ("history", {"title": "예측 이력", "short_title": "이력"}),
        ("excel", {"title": "Excel 공유", "short_title": "Excel"}),
        ("audit", {"title": "검증 · 운영관리", "short_title": "검증"}),
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
    items = "".join(
        render_nav_item_html(page_key, active_page, collapsed=collapsed)
        for page_key in PAGE_DEFINITIONS
    )
    collapsed_class = " is-collapsed" if collapsed else ""
    return (
        f'<aside class="nav-rail{collapsed_class}">'
        f'<div class="nav-rail__title">{escape(title)}</div>'
        f'<div class="nav-rail__items">{items}</div>'
        "</aside>"
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
    subtitle_html = (
        f'<div class="page-header__subtitle">{escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    return (
        '<header class="page-header">'
        f'<div class="page-header__eyebrow">Month-End Pace Check</div>'
        f'<h1>{escape(page_title(page_key))}</h1>'
        f"{subtitle_html}"
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
