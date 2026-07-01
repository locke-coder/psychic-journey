from src.ui_theme import get_control_room_css, get_pace_check_css


def test_pace_check_css_returns_required_classes() -> None:
    css = get_pace_check_css()

    assert isinstance(css, str)
    for class_name in (
        "pace-check-shell",
        "pace-topbar",
        "pace-hero",
        "pace-mode-card",
        "kpi-card",
        "status-badge",
        "scenario-card",
        "report-card",
        "download-card",
        "nav-rail",
        "nav-item",
        "page-shell",
        "page-header",
        "detail-panel",
        "report-card__section",
        "report-card__section-title",
    ):
        assert class_name in css


def test_pace_check_css_has_no_external_imports_or_gradients() -> None:
    css = get_pace_check_css()

    forbidden_values = (
        "@import" + " url(",
        "https" + "://",
        "http" + "://",
        "linear" + "-gradient",
        "radial" + "-gradient",
    )
    for forbidden in forbidden_values:
        assert forbidden not in css


def test_pace_check_css_has_no_retired_ui_terms() -> None:
    css = get_pace_check_css()

    forbidden_values = (
        "Control" + " Room",
        "Command" + " Center",
        "월마감 실적 " + "관" + "제" + "실",
        "관" + "제" + "실",
        "command" + "-hero",
        "control" + "-room-shell",
    )
    for forbidden in forbidden_values:
        assert forbidden not in css


def test_pace_check_css_limits_shadow_to_emphasis_classes() -> None:
    css = get_pace_check_css()

    assert ".kpi-card {\n" in css
    kpi_block = css.split(".kpi-card {\n", 1)[1].split("\n    }", 1)[0]
    assert "box-shadow" not in kpi_block

    body_block = css.split(".stApp {\n", 1)[1].split("\n    }", 1)[0]
    assert "box-shadow" not in body_block

    for allowed_selector in (
        ".kpi-card.is-focus",
        ".scenario-card.is-emphasis",
        ".report-card.is-focus",
        ".download-card",
        ".nav-rail",
    ):
        assert allowed_selector in css


def test_pace_check_css_keeps_card_text_inside_boxes() -> None:
    css = get_pace_check_css()

    for required in (
        ".page-header {\n        display: flow-root;",
        ".page-header > *:first-child",
        ".page-header > *:last-child",
        "overflow-wrap: anywhere;",
    ):
        assert required in css


def test_pace_check_css_uses_compact_colored_operation_mode_card() -> None:
    css = get_pace_check_css()

    for required in (
        "grid-template-columns: minmax(0, 1fr) minmax(260px, .86fr);",
        "border-left: 4px solid var(--teal);",
        "border-radius: 8px;",
        ".pace-mode-card.status-over-target",
        ".pace-mode-card.status-under-target",
        ".pace-mode-card__mode {\n        grid-column: 1;",
        "font-size: 24px;",
    ):
        assert required in css

    mode_card_block = css.split(".pace-mode-card {\n", 1)[1].split("\n    }", 1)[0]
    assert "border-radius: 26px" not in mode_card_block
    assert "padding: 22px 24px" not in mode_card_block


def test_pace_check_css_keeps_seven_kpi_cards_on_one_row() -> None:
    css = get_pace_check_css()

    kpi_grid_block = css.split(".kpi-grid {\n", 1)[1].split("\n    }", 1)[0]
    assert "grid-template-columns: repeat(7, minmax(0, 1fr));" in kpi_grid_block
    assert "repeat(6" not in kpi_grid_block
    assert "minmax(145px" not in kpi_grid_block


def test_pace_check_css_keeps_streamlit_metric_cards_equal_height() -> None:
    css = get_pace_check_css()

    metric_block = css.split('div[data-testid="stMetric"] {\n', 1)[1].split("\n    }", 1)[0]
    for required in (
        "height: 100px !important;",
        "min-height: 100px !important;",
        "display: flex !important;",
        "flex-direction: column !important;",
        "justify-content: flex-start !important;",
    ):
        assert required in metric_block
    assert "height: auto" not in metric_block
    assert 'div[data-testid="stMetric"] > div' in css
    assert '[data-testid="stMetricDelta"]' in css


def test_legacy_css_wrapper_returns_pace_check_css() -> None:
    assert get_control_room_css() == get_pace_check_css()
    assert "control" + "-room-shell" not in get_control_room_css()
    assert "command" + "-hero" not in get_control_room_css()
