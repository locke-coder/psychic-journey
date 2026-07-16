from __future__ import annotations

import ast
from pathlib import Path


APP_SOURCE = Path("app.py").read_text(encoding="utf-8")
UI_PAGES_SOURCE = Path("src/ui_pages.py").read_text(encoding="utf-8")
UI_STYLES_SOURCE = Path("src/ui_styles.py").read_text(encoding="utf-8")


def _function_source(source: str, function_name: str) -> str:
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            function_source = ast.get_source_segment(source, node)
            assert function_source is not None
            return function_source
    raise AssertionError(f"{function_name} not found")


def test_sidebar_renders_workflow_groups_before_page_buttons() -> None:
    source = _function_source(APP_SOURCE, "_render_same_window_side_nav")

    assert "NAV_GROUPS.values()" in source
    assert "same-window-nav-group" in source
    assert source.index("same-window-nav-group") < source.index("st_module.button(")


def test_detail_pages_use_centralized_page_header_metadata() -> None:
    callback_source = _function_source(UI_PAGES_SOURCE, "_render_callback_page")

    assert "subtitle" not in callback_source.split("context:", 1)[0]
    assert "render_page_header_html(page_key)" in callback_source


def test_page_flow_and_sidebar_group_styles_exist() -> None:
    for token in (
        ".page-header__flow",
        ".page-header__flow-item",
        ".same-window-nav-group",
    ):
        assert token in UI_STYLES_SOURCE
