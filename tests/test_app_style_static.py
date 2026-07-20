from __future__ import annotations

import ast
from pathlib import Path

import src.ui_styles as ui_styles


APP_SOURCE = Path("app.py").read_text(encoding="utf-8")
UI_STYLES_SOURCE = Path("src/ui_styles.py").read_text(encoding="utf-8")


def _function_source(source: str, function_name: str) -> str:
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            function_source = ast.get_source_segment(source, node)
            assert function_source is not None
            return function_source
    raise AssertionError(f"{function_name} not found")


def test_ui_styles_exports_app_css() -> None:
    assert hasattr(ui_styles, "get_app_styles_css")
    assert hasattr(ui_styles, "inject_app_styles")

    css = ui_styles.get_app_styles_css()

    assert isinstance(css, str)
    assert "<style>" in css
    assert "</style>" in css


def test_app_css_contains_key_selectors() -> None:
    css = ui_styles.get_app_styles_css()
    required_tokens = (
        ".page-shell",
        ".metric-card",
        ".same-window-top-status",
        ".strategy-section",
        ".scenario-card",
        ".pace-mode-card.status-under-target",
    )

    for token in required_tokens:
        assert token in css


def test_global_dashboard_theme_keeps_shared_component_tone() -> None:
    css = ui_styles.get_global_styles()

    required_tokens = (
        "--dashboard-navy: #17213d",
        "--brand-action: #2f65e8",
        "--teal: #2f65e8",
        ".page-header",
        ".section-header",
        'div[data-testid="stSelectbox"]',
        'div[data-testid="stExpander"] details',
        'div[data-testid="stTabs"] button[aria-selected="true"]',
    )

    for token in required_tokens:
        assert token in css


def test_file_uploader_keeps_streamlit_native_type_instructions() -> None:
    css = ui_styles.get_app_styles_css()

    assert 'content: "CSV 또는 XLSX 파일을 업로드할 수 있습니다."' not in css
    assert '[data-testid="stFileUploaderDropzoneInstructions"] {' not in css


def test_app_uses_ui_styles_injection() -> None:
    assert "from src.ui_styles import inject_app_styles" in APP_SOURCE
    assert "inject_app_styles(st" in APP_SOURCE


def test_app_no_large_inline_css_payload_remaining() -> None:
    style_function = _function_source(APP_SOURCE, "_inject_app_styles")

    assert "st.markdown(" not in style_function
    assert "<style>" not in style_function
    assert len(style_function.splitlines()) <= 3


def test_ui_styles_does_not_import_formula_modules() -> None:
    forbidden_modules = (
        "forecast_models",
        "provision_models",
        "overachievement_models",
        "scenario_runner",
        "excel_exporter",
        "history_store",
        "backtest_engine",
        "model_weight_engine",
    )

    for module in forbidden_modules:
        assert f"import {module}" not in UI_STYLES_SOURCE
        assert f"from src.{module}" not in UI_STYLES_SOURCE
        assert f"from .{module}" not in UI_STYLES_SOURCE


def test_main_order_set_page_config_before_style_injection() -> None:
    main_source = _function_source(APP_SOURCE, "main")

    assert main_source.index("st.set_page_config") < main_source.index("_inject_app_styles()")
    assert main_source.index("_inject_app_styles()") < main_source.index(
        "base_config = load_model_config()"
    )


def test_no_forbidden_close_day_inference_terms_in_style_sources() -> None:
    forbidden_terms = (
        "weekday",
        "WEEKDAY",
        "dt.weekday",
        "date.weekday",
        "next_monday",
        "next_thursday",
        "day_name ==",
        "day_name in",
        "월요일",
        "목요일",
    )

    for source_name, source in {
        "app.py": APP_SOURCE,
        "src/ui_styles.py": UI_STYLES_SOURCE,
    }.items():
        for term in forbidden_terms:
            assert term not in source, f"{source_name} contains {term}"


def test_primary_and_form_submit_buttons_keep_white_text() -> None:
    css = ui_styles.get_global_styles()

    assert 'button[kind="primary"] p' in css
    assert 'div[data-testid="stFormSubmitButton"] button p' in css
    assert "color: #ffffff !important;" in css
