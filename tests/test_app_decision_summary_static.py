from __future__ import annotations

import ast
from pathlib import Path


APP_PATH = Path("app.py")
DECISION_SUMMARY_PATH = Path("src/ui_decision_summary.py")
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")
DECISION_SUMMARY_SOURCE = DECISION_SUMMARY_PATH.read_text(encoding="utf-8")

MOVED_FUNCTIONS = {
    "build_visual_headline",
    "build_visual_decision_summary",
    "_visual_status_sentence",
    "_visual_variance_sentence",
    "_visual_next_close_sentence",
}
REMOVED_RENDER_FUNCTIONS = {
    "_render_body",
    "_render_visuals",
    "_render_visual_decision_panel",
}


def _top_level_function_names(source: str) -> set[str]:
    module = ast.parse(source)
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


def test_app_imports_and_binds_visual_decision_summary_builders() -> None:
    assert DECISION_SUMMARY_PATH.exists()
    assert "from src.ui_decision_summary import (" in APP_SOURCE
    assert "build_visual_headline," in APP_SOURCE
    assert "build_visual_decision_summary as _build_visual_decision_summary," in APP_SOURCE
    assert "build_visual_decision_summary = partial(" in APP_SOURCE
    assert "localize_display_value=_localize_display_value," in APP_SOURCE


def test_visual_decision_summary_definitions_are_removed_from_app() -> None:
    assert _top_level_function_names(APP_SOURCE).isdisjoint(MOVED_FUNCTIONS)
    assert MOVED_FUNCTIONS.issubset(_top_level_function_names(DECISION_SUMMARY_SOURCE))


def test_obsolete_visual_render_chain_stays_removed() -> None:
    app_function_names = _top_level_function_names(APP_SOURCE)
    assert app_function_names.isdisjoint(REMOVED_RENDER_FUNCTIONS)
    for name in REMOVED_RENDER_FUNCTIONS:
        assert name not in APP_SOURCE


def test_visual_decision_summary_module_stays_presentation_only() -> None:
    forbidden_modules = (
        "streamlit",
        "altair",
        "forecast_models",
        "provision_models",
        "overachievement_models",
        "scenario_runner",
        "report_builder",
        "excel_exporter",
        "history_store",
        "backtest_engine",
    )
    forbidden_terms = (
        "st.session_state",
        "open(",
        "Path(",
        "OUTPUT_DIR",
        ".sum(",
        ".groupby(",
        ".cumsum(",
        ".diff(",
    )

    for module in forbidden_modules:
        assert f"import {module}" not in DECISION_SUMMARY_SOURCE
        assert f"from src.{module}" not in DECISION_SUMMARY_SOURCE
        assert f"from .{module}" not in DECISION_SUMMARY_SOURCE
    for term in forbidden_terms:
        assert term not in DECISION_SUMMARY_SOURCE


def test_visual_decision_summary_module_has_no_close_day_inference() -> None:
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

    for term in forbidden_terms:
        assert term not in DECISION_SUMMARY_SOURCE
