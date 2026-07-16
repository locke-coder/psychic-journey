from __future__ import annotations

import ast
from pathlib import Path


APP_SOURCE = Path("app.py").read_text(encoding="utf-8")


def _function_source(function_name: str) -> str:
    module = ast.parse(APP_SOURCE)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            source = ast.get_source_segment(APP_SOURCE, node)
            assert source is not None
            return source
    raise AssertionError(f"{function_name} not found")


def test_home_keeps_decision_surfaces_and_removes_detail_tab_duplicates() -> None:
    source = _function_source("_render_home_workbench_page")

    assert "_render_month_close_status_panel" in source
    assert "_render_projection_chart_card" in source
    assert "_render_home_decision_panel" in source
    assert "_build_home_achievement_donut_html" in source
    assert "st.columns([1, 2], gap=\"small\")" in source
    assert "_render_home_status_facts" not in source
    assert "_render_home_scenario_summary" not in source
    assert "_render_home_overachievement_strategy_summary" not in source
    assert "보고 메모 preview" not in source
    assert "Excel 공유 readiness" not in source


def test_home_decision_panel_contains_only_qualitative_decisions() -> None:
    source = _function_source("_render_home_decision_panel")

    for label in ("운영모드", "권장 전략", "리스크 수준", "다음 액션"):
        assert label in source
    for duplicated_metric in (
        '"목표 상태"',
        '"월마감 예상"',
        '"목표 대비 차이"',
        '"다음 마감 누적선 필요실적"',
    ):
        assert duplicated_metric not in source


def test_home_achievement_donut_separates_base_and_excess_progress() -> None:
    source = _function_source("_build_home_achievement_donut_html")

    assert "forecast_after_provision" in source
    assert "monthly_target" in source
    assert "--achievement-angle" in source
    assert "--excess-angle" in source
    assert "목표 초과" in source
    assert "월말 예상 달성률" in source


def test_forecast_summary_is_limited_to_four_decision_metrics() -> None:
    source = _function_source("_render_forecast_strategy_summary_board")

    for label in (
        "목표 상태",
        "월마감 예상 실적",
        "목표 대비 차이",
        "다음 마감 누적선 필요실적",
    ):
        assert label in source
    for detail_label in ("초과 예상분", "운영모드", "권장 전략", "다음 액션"):
        assert detail_label not in source


def test_forecast_exact_tables_are_collapsed_below_visual_summaries() -> None:
    source = _function_source("_render_forecast_strategy_detail_page")

    chart_index = source.index("_render_forecast_model_mini_chart")
    model_table_index = source.index('st.expander("모델별 정확 수치표"')
    strategy_cards_index = source.index("_render_strategy_reference_sections")
    operation_table_index = source.index('st.expander("운영 판단표"')

    assert chart_index < model_table_index
    assert strategy_cards_index < operation_table_index
    assert 'render_next_action_panel("forecast_strategy"' not in source
