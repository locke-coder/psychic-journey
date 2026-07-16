from __future__ import annotations

import ast
from pathlib import Path


APP_PATH = Path("app.py")
FORMATTERS_PATH = Path("src/ui_history_formatters.py")
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")
FORMATTERS_SOURCE = FORMATTERS_PATH.read_text(encoding="utf-8")


def _top_level_function_names(source: str) -> set[str]:
    module = ast.parse(source)
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


def test_history_formatter_module_and_app_aliases_exist() -> None:
    assert FORMATTERS_PATH.exists()
    assert "from src.ui_history_formatters import" in APP_SOURCE
    for name in (
        "format_historical_forecast_comparison_df as _format_historical_forecast_comparison_df",
        "format_historical_monthly_summary_df as _format_historical_monthly_summary_df",
        "format_historical_stage_df as _format_historical_stage_df",
    ):
        assert name in APP_SOURCE


def test_moved_history_formatter_definitions_are_removed_from_app() -> None:
    assert _top_level_function_names(APP_SOURCE).isdisjoint(
        {
            "_format_historical_forecast_comparison_df",
            "_format_historical_monthly_summary_df",
            "_format_historical_stage_df",
        }
    )


def test_history_formatter_module_stays_display_only() -> None:
    forbidden_modules = (
        "streamlit",
        "altair",
        "backtest_engine",
        "history_store",
        "history_schema",
        "forecast_models",
        "provision_models",
        "overachievement_models",
        "scenario_runner",
        "excel_exporter",
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
        assert f"import {module}" not in FORMATTERS_SOURCE
        assert f"from src.{module}" not in FORMATTERS_SOURCE
        assert f"from .{module}" not in FORMATTERS_SOURCE
    for term in forbidden_terms:
        assert term not in FORMATTERS_SOURCE


def test_history_formatter_module_has_no_close_day_inference() -> None:
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
        assert term not in FORMATTERS_SOURCE
