from __future__ import annotations

import ast
from pathlib import Path


APP_PATH = Path("app.py")
BUILDERS_PATH = Path("src/ui_metadata_builders.py")
DECISION_SUMMARY_PATH = Path("src/ui_decision_summary.py")
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")
BUILDERS_SOURCE = BUILDERS_PATH.read_text(encoding="utf-8")
DECISION_SUMMARY_SOURCE = DECISION_SUMMARY_PATH.read_text(encoding="utf-8")


def _top_level_function_names(source: str) -> set[str]:
    module = ast.parse(source)
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


MOVED_BUILDERS = {
    "build_visual_metric_definition_df",
    "build_visual_reading_guide",
    "build_forecast_definition_df",
    "build_provision_definition_df",
    "build_overachievement_definition_df",
    "build_neutral_definition_df",
    "build_report_glossary_df",
    "build_risk_definition_df",
}


def test_app_imports_and_binds_metadata_builders() -> None:
    assert BUILDERS_PATH.exists()
    assert "from src.ui_metadata_builders import" in APP_SOURCE
    for name in MOVED_BUILDERS:
        assert f"{name} as _{name}" in APP_SOURCE
        assert f"{name} = partial(" in APP_SOURCE


def test_moved_metadata_builder_definitions_are_removed_from_app() -> None:
    assert _top_level_function_names(APP_SOURCE).isdisjoint(MOVED_BUILDERS)
    assert MOVED_BUILDERS.issubset(_top_level_function_names(BUILDERS_SOURCE))


def test_app_keeps_definition_constants_out_of_extracted_modules() -> None:
    for constant in (
        "FORECAST_MODEL_DEFINITIONS =",
        "PROVISION_STRATEGY_DEFINITIONS =",
        "OVERACHIEVEMENT_STRATEGY_DEFINITIONS =",
        "NEUTRAL_STRATEGY_DEFINITIONS =",
        "RISK_LEVEL_DEFINITIONS =",
        "REPORT_GLOSSARY_GROUPS =",
        "VISUAL_METRIC_DEFINITIONS =",
        "VISUAL_READING_GUIDES =",
    ):
        assert constant in APP_SOURCE
        assert constant not in BUILDERS_SOURCE
        assert constant not in DECISION_SUMMARY_SOURCE

    assert "build_visual_decision_summary" not in BUILDERS_SOURCE


def test_metadata_builder_module_stays_construction_only() -> None:
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
        assert f"import {module}" not in BUILDERS_SOURCE
        assert f"from src.{module}" not in BUILDERS_SOURCE
        assert f"from .{module}" not in BUILDERS_SOURCE
    for term in forbidden_terms:
        assert term not in BUILDERS_SOURCE


def test_metadata_builder_module_has_no_close_day_inference() -> None:
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
        assert term not in BUILDERS_SOURCE
