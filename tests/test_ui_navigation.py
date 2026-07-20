from src.ui_navigation import (
    NAV_GROUPS,
    PAGE_ALIASES,
    PAGE_DEFINITIONS,
    get_current_page,
    nav_item_class,
    page_subtitle,
    page_title,
    render_nav_item_html,
    render_nav_rail_html,
    render_page_flow_html,
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
    assert FakeStreamlit.query_params["page"] == "forecast_strategy"

    FakeStreamlit.query_params = {"page": "scenarios"}
    assert get_current_page(FakeStreamlit) == "forecast_strategy"
    assert FakeStreamlit.query_params["page"] == "forecast_strategy"


def test_removed_raw_dashboard_query_canonicalizes_to_home() -> None:
    class FakeStreamlit:
        query_params = {"page": "raw_dashboard", "audit_readonly": "1"}
        session_state = {}

    assert get_current_page(FakeStreamlit) == "home"
    assert FakeStreamlit.query_params == {"page": "home", "audit_readonly": "1"}
    assert FakeStreamlit.session_state["pace_current_page"] == "home"


def test_visible_nav_exposes_unified_forecast_strategy_once() -> None:
    visible_titles = [definition["title"] for definition in PAGE_DEFINITIONS.values()]

    assert PAGE_ALIASES["forecast"] == "forecast_strategy"
    assert PAGE_ALIASES["scenarios"] == "forecast_strategy"
    assert visible_titles.count("예측 · 전략 통합") == 1
    assert "KPI · 예측" not in visible_titles
    assert "시나리오" not in visible_titles


def test_navigation_groups_cover_every_page_once_in_workflow_order() -> None:
    grouped_pages = [
        page_key
        for group in NAV_GROUPS.values()
        for page_key in group["pages"]
    ]

    assert grouped_pages == list(PAGE_DEFINITIONS)
    assert len(grouped_pages) == len(set(grouped_pages))
    assert [group["title"] for group in NAV_GROUPS.values()] == [
        "1. 일일 운영",
        "2. 비교 · 보고",
        "3. 공유 · 검증",
    ]


def test_page_metadata_connects_related_tabs_and_next_step() -> None:
    for page_key, definition in PAGE_DEFINITIONS.items():
        assert definition["group"] in NAV_GROUPS
        assert page_subtitle(page_key)
        assert definition["next_page"] in PAGE_DEFINITIONS
        assert all(key in PAGE_DEFINITIONS for key in definition["related"])

    flow_html = render_page_flow_html("forecast_strategy")
    assert "함께 보기" in flow_html
    assert "?page=history" in flow_html
    assert "?page=report" in flow_html


def test_nav_rail_and_page_header_render_without_streamlit() -> None:
    nav_html = render_nav_rail_html("home")
    header_html = render_page_header_html("forecast", subtitle="detail")

    assert "nav-rail" in nav_html
    assert "nav-item active" in nav_html
    assert "1. 일일 운영" in nav_html
    assert "2. 비교 · 보고" in nav_html
    assert "3. 공유 · 검증" in nav_html
    assert "page-header" in header_html
    assert "예측 · 전략 통합" in header_html
    assert "1. 일일 운영" in header_html
    assert "함께 보기" in header_html
    assert "다음 단계" in header_html
