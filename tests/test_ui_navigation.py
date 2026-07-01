from src.ui_navigation import (
    PAGE_ALIASES,
    PAGE_DEFINITIONS,
    get_current_page,
    nav_item_class,
    page_title,
    render_nav_item_html,
    render_nav_rail_html,
    render_page_header_html,
    validate_page_key,
)


def test_page_definitions_include_required_pages() -> None:
    assert {
        "home",
        "input",
        "forecast_strategy",
        "report",
        "history",
        "excel",
        "audit",
    }.issubset(PAGE_DEFINITIONS)
    assert "forecast" not in PAGE_DEFINITIONS
    assert "scenarios" not in PAGE_DEFINITIONS


def test_validate_page_key_uses_home_fallback() -> None:
    assert validate_page_key("home") == "home"
    assert validate_page_key("forecast") == "forecast_strategy"
    assert validate_page_key("scenarios") == "forecast_strategy"
    assert validate_page_key("scenario") == "forecast_strategy"
    assert validate_page_key("unknown") == "home"
    assert validate_page_key(None) == "home"


def test_page_title_maps_business_labels() -> None:
    assert page_title("forecast_strategy") == "예측 · 전략 통합"
    assert page_title("scenarios") == "예측 · 전략 통합"
    assert page_title("excel") == "Excel 공유"


def test_nav_item_marks_active_page() -> None:
    assert nav_item_class("scenarios", "scenarios") == "nav-item active"
    assert nav_item_class("report", "scenarios") == "nav-item"

    html = render_nav_item_html("scenarios", "scenarios")

    assert 'class="nav-item active"' in html
    assert "?page=forecast_strategy" in html


def test_legacy_query_page_aliases_normalize_to_unified_page() -> None:
    class FakeStreamlit:
        query_params = {"page": "forecast"}
        session_state = {}

    assert get_current_page(FakeStreamlit) == "forecast_strategy"
    assert FakeStreamlit.session_state["pace_current_page"] == "forecast_strategy"

    FakeStreamlit.query_params = {"page": "scenarios"}
    assert get_current_page(FakeStreamlit) == "forecast_strategy"


def test_visible_nav_exposes_unified_forecast_strategy_once() -> None:
    visible_titles = [definition["title"] for definition in PAGE_DEFINITIONS.values()]

    assert PAGE_ALIASES["forecast"] == "forecast_strategy"
    assert PAGE_ALIASES["scenarios"] == "forecast_strategy"
    assert visible_titles.count("예측 · 전략 통합") == 1
    assert "KPI · 예측" not in visible_titles
    assert "시나리오" not in visible_titles


def test_nav_rail_and_page_header_render_without_streamlit() -> None:
    nav_html = render_nav_rail_html("home")
    header_html = render_page_header_html("forecast", subtitle="detail")

    assert "nav-rail" in nav_html
    assert "nav-item active" in nav_html
    assert "page-header" in header_html
    assert "예측 · 전략 통합" in header_html
