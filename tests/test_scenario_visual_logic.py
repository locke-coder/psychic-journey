import pandas as pd

import app
from src.visualization_builder import build_strategy_arrival_compare_source


def _overachievement_same_forecast() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "scenario_id": "F1_O1",
                "strategy_type": "OVERACHIEVEMENT",
                "target_status": "OVER_TARGET",
                "monthly_target": 100.0,
                "current_actual_cum": 105.0,
                "forecast_amount": 130.0,
                "forecast_after_provision": 130.0,
                "target_variance": 30.0,
                "revised_monthly_target": 100.0,
                "remaining_surplus_buffer": 30.0,
                "stretch_uplift": 0.0,
                "relief_amount": 0.0,
                "minimum_remaining_to_hit_target": 0.0,
                "recommended_action": "버퍼 유지",
            },
            {
                "scenario_id": "F1_O2",
                "strategy_type": "OVERACHIEVEMENT",
                "target_status": "OVER_TARGET",
                "monthly_target": 100.0,
                "current_actual_cum": 105.0,
                "forecast_amount": 130.0,
                "forecast_after_provision": 130.0,
                "target_variance": 30.0,
                "revised_monthly_target": 116.0,
                "remaining_surplus_buffer": 14.0,
                "stretch_uplift": 16.0,
                "relief_amount": 0.0,
                "minimum_remaining_to_hit_target": 0.0,
                "recommended_action": "상향 목표 전환",
            },
            {
                "scenario_id": "F1_O3",
                "strategy_type": "OVERACHIEVEMENT",
                "target_status": "OVER_TARGET",
                "monthly_target": 100.0,
                "current_actual_cum": 105.0,
                "forecast_amount": 130.0,
                "forecast_after_provision": 130.0,
                "target_variance": 30.0,
                "revised_monthly_target": 100.0,
                "remaining_surplus_buffer": 30.0,
                "stretch_uplift": 0.0,
                "relief_amount": 6.0,
                "minimum_remaining_to_hit_target": 0.0,
                "recommended_action": "품질 방어",
            },
        ]
    )


def test_same_overachievement_forecast_falls_back_to_operation_basis() -> None:
    source = build_strategy_arrival_compare_source(_overachievement_same_forecast(), "F1_O1")

    assert source.attrs["identical_forecast_values"]
    assert source.attrs["fallback_used"]
    assert source.attrs["display_mode"] == "table"
    assert source.attrs["classification"] == "TRUE_IDENTICAL_BY_DESIGN"
    assert source.attrs["compare_metric"] == "revised_monthly_target"


def test_same_forecast_values_are_not_perturbed_for_visual_difference() -> None:
    source = build_strategy_arrival_compare_source(_overachievement_same_forecast(), "F1_O1")

    assert source["forecast_after_provision"].tolist() == [130.0, 130.0, 130.0]
    assert source["compare_value"].tolist() == [100.0, 116.0, 100.0]


def test_active_strategy_group_follows_current_target_status() -> None:
    assert app.active_strategy_suffixes_for_status("OVER_TARGET") == ("O1", "O2", "O3")
    assert app.active_strategy_suffixes_for_status("UNDER_TARGET") == ("P1", "P2", "P3")
    assert app.active_strategy_suffixes_for_status("ON_TARGET") == ("N1", "N2", "N3")


def test_home_scenario_summary_uses_f1_f2_f3_model_rows() -> None:
    scenarios = pd.DataFrame(
        [
            {
                "scenario_id": "F1_O1",
                "forecast_model": "F1_CUMULATIVE_RATE",
                "forecast_amount": 130.0,
                "target_variance": 30.0,
                "target_status": "OVER_TARGET",
            },
            {
                "scenario_id": "F1_O2",
                "forecast_model": "F1_CUMULATIVE_RATE",
                "forecast_amount": 130.0,
                "target_variance": 30.0,
                "target_status": "OVER_TARGET",
            },
            {
                "scenario_id": "F1_O3",
                "forecast_model": "F1_CUMULATIVE_RATE",
                "forecast_amount": 130.0,
                "target_variance": 30.0,
                "target_status": "OVER_TARGET",
            },
            {
                "scenario_id": "F2_O1",
                "forecast_model": "F2_LAST_TWO_CLOSES",
                "forecast_amount": 142.0,
                "target_variance": 42.0,
                "target_status": "OVER_TARGET",
            },
            {
                "scenario_id": "F3_O1",
                "forecast_model": "F3_DAY_CLOSE_WEIGHTED",
                "forecast_amount": 155.0,
                "target_variance": 55.0,
                "target_status": "OVER_TARGET",
            },
        ]
    )

    summary = app.build_home_forecast_model_summary(scenarios)
    html = "".join(
        app._render_forecast_model_summary_card(row)
        for row in summary.to_dict("records")
    )

    assert summary["forecast_key"].tolist() == ["F1", "F2", "F3"]
    assert summary["forecast_model"].tolist() == [
        "F1_CUMULATIVE_RATE",
        "F2_LAST_TWO_CLOSES",
        "F3_DAY_CLOSE_WEIGHTED",
    ]
    assert summary["expected_month_end_amount"].tolist() == [130.0, 142.0, 155.0]
    assert "expected_month_end_amount" in html
    assert "target_variance" in html
    assert "target_status" in html
    assert "F1_O2" not in html
    assert "F1_O3" not in html


def test_home_forecast_summary_collapses_converged_f_values() -> None:
    scenarios = pd.DataFrame(
        [
            {
                "scenario_id": scenario_id,
                "forecast_model": forecast_model,
                "forecast_amount": 130.0,
                "target_variance": 30.0,
                "target_status": "OVER_TARGET",
            }
            for scenario_id, forecast_model in [
                ("F1_O1", "F1_CUMULATIVE_RATE"),
                ("F2_O1", "F2_LAST_TWO_CLOSES"),
                ("F3_O1", "F3_DAY_CLOSE_WEIGHTED"),
            ]
        ]
    )

    summary = app.build_home_forecast_model_summary(scenarios)
    display_rows = app._dedupe_converged_forecast_summary_rows(summary)
    html = "".join(
        app._render_forecast_model_summary_card(row)
        for row in display_rows.to_dict("records")
    )

    assert len(display_rows) == 1
    assert display_rows.iloc[0]["forecast_key"] == "F1/F2/F3"
    assert display_rows.iloc[0]["model_name"] == "예측값 수렴"
    assert "예측값 수렴" in html
    assert html.count("<article") == 1


def test_home_o_strategy_summary_does_not_repeat_same_strategy_expected_amount() -> None:
    summary = app.build_home_overachievement_strategy_summary(
        _overachievement_same_forecast(),
        "F1_O1",
    )

    assert summary["strategy_key"].tolist() == ["O1", "O2", "O3"]
    assert summary["base_forecast_amount"].tolist() == [130.0, 130.0, 130.0]
    assert summary["strategy_expected_amount"].tolist() == [130.0, 116.0, 105.0]
    assert summary["strategy_expected_amount"].nunique() > 1

    html = "".join(
        app._render_overachievement_strategy_summary_card(row)
        for row in summary.to_dict("records")
    )

    assert "운영 기준 목표" in html
    assert "Stretch 전환분" in html
    assert "품질관리 여유분" in html
    assert "base_forecast_amount" not in html
    assert "strategy_expected_amount" not in html


def test_active_strategy_card_badge_and_class_are_generated() -> None:
    html = app._strategy_section_cards_html(
        _overachievement_same_forecast(),
        "F1",
        ("O1", "O2", "O3"),
        {
            "O1": "O1_TARGET_HOLD_BUFFER",
            "O2": "O2_STRETCH_TARGET_CAPTURE",
            "O3": "O3_QUALITY_GUARD_RELIEF",
        },
        is_active=True,
        selected_strategy_key="O2",
    )

    assert "권장" in html
    assert "is-recommended-badge" in html
    assert "권장 · 현재 관리 대상" not in html
    assert "strategy-card-active" in html
    assert "운영 기준 목표" in html
    assert "Stretch 전환분" in html
    assert "품질관리 여유분" in html
    assert "전략 반영 후 예상" not in html
    assert "P1" not in html


def test_all_identical_strategy_core_values_can_be_classified_for_logic_review() -> None:
    scenarios = pd.DataFrame(
        [
            {
                "scenario_id": "F1_O1",
                "strategy_type": "OVERACHIEVEMENT",
                "monthly_target": 100.0,
                "forecast_after_provision": 130.0,
                "target_variance": 30.0,
                "revised_monthly_target": 100.0,
                "remaining_surplus_buffer": 30.0,
                "stretch_uplift": 0.0,
                "relief_amount": 0.0,
                "minimum_remaining_to_hit_target": 0.0,
                "recommended_action": "동일 조치",
            },
            {
                "scenario_id": "F1_O2",
                "strategy_type": "OVERACHIEVEMENT",
                "monthly_target": 100.0,
                "forecast_after_provision": 130.0,
                "target_variance": 30.0,
                "revised_monthly_target": 100.0,
                "remaining_surplus_buffer": 30.0,
                "stretch_uplift": 0.0,
                "relief_amount": 0.0,
                "minimum_remaining_to_hit_target": 0.0,
                "recommended_action": "동일 조치",
            },
            {
                "scenario_id": "F1_O3",
                "strategy_type": "OVERACHIEVEMENT",
                "monthly_target": 100.0,
                "forecast_after_provision": 130.0,
                "target_variance": 30.0,
                "revised_monthly_target": 100.0,
                "remaining_surplus_buffer": 30.0,
                "stretch_uplift": 0.0,
                "relief_amount": 0.0,
                "minimum_remaining_to_hit_target": 0.0,
                "recommended_action": "동일 조치",
            },
        ]
    )

    source = build_strategy_arrival_compare_source(scenarios, "F1_O1")

    assert source.attrs["classification"] == "NEEDS_LOGIC_REVIEW"
    assert source.attrs["fallback_used"]
