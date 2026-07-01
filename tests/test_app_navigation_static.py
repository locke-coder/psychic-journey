from pathlib import Path


APP_SOURCE = Path("app.py").read_text(encoding="utf-8")


def test_internal_navigation_does_not_open_new_windows() -> None:
    forbidden_terms = (
        'target="_blank"',
        "target='_blank'",
        "window.open",
    )

    for term in forbidden_terms:
        assert term not in APP_SOURCE


def test_navigation_uses_same_window_query_param_buttons() -> None:
    required_terms = (
        "_render_same_window_side_nav",
        "_navigate_same_window",
        'query_params["page"]',
        ".button(",
        "pace_current_page",
    )

    for term in required_terms:
        assert term in APP_SOURCE


def test_navigation_collapse_toggle_is_removed_from_app() -> None:
    forbidden_terms = (
        "네비게이션 접기",
        "same_window_nav_toggle",
        "pace_nav_collapsed",
    )

    for term in forbidden_terms:
        assert term not in APP_SOURCE


def test_legacy_link_navigation_is_not_called_from_app() -> None:
    forbidden_calls = (
        "render_side_nav(st, active_page)",
        "render_quick_links(st, active_page)",
        "render_top_nav(st, active_page",
    )

    for call in forbidden_calls:
        assert call not in APP_SOURCE


def test_no_external_cdn_or_internal_external_urls() -> None:
    forbidden_terms = (
        "@import" + " url(",
        "https" + "://",
        "http" + "://",
        'href="http',
        "href='http",
    )

    for term in forbidden_terms:
        assert term not in APP_SOURCE
