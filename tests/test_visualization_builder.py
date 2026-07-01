import pandas as pd

from src.visualization_builder import (
    VISUALIZATION_KEYS,
    build_close_day_markers,
    build_close_cycle_cumulative_source,
    build_forecast_trend_df,
    build_forecast_model_mini_chart_source,
    build_gap_surplus_trend_df,
    build_model_error_df,
    build_projection_band_data,
    build_strategy_arrival_compare_source,
    build_strategy_mix_df,
    build_target_status_distribution_df,
    build_visualization,
)


def _forecast_history() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "target_month": "2026-06",
                "as_of_date": "2026-06-10",
                "metric": "sales",
                "forecast_model": "F1_CUMULATIVE_RATE",
                "strategy_id": "P1_ALL_REMAINING",
                "strategy_type": "PROVISION",
                "forecast_amount": 100.0,
                "target_status": "UNDER_TARGET",
                "gap_to_target": 10.0,
                "surplus_to_target": 0.0,
            },
            {
                "target_month": "2026-06",
                "as_of_date": "2026-06-10",
                "metric": "sales",
                "forecast_model": "F2_LAST_TWO_CLOSES",
                "strategy_id": "O1_TARGET_HOLD_BUFFER",
                "strategy_type": "OVERACHIEVEMENT",
                "forecast_amount": 125.0,
                "target_status": "OVER_TARGET",
                "gap_to_target": 0.0,
                "surplus_to_target": 15.0,
            },
        ]
    )


def _backtest() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "forecast_model": "F1_CUMULATIVE_RATE",
                "forecast_error": 8.0,
                "abs_error": 8.0,
                "error_rate": 0.08,
            },
            {
                "forecast_model": "F2_LAST_TWO_CLOSES",
                "forecast_error": -3.0,
                "abs_error": 3.0,
                "error_rate": 0.03,
            },
        ]
    )


def test_visualization_builder_functions_return_dataframes() -> None:
    forecast_history = _forecast_history()
    backtest = _backtest()

    frames = [
        build_forecast_trend_df(forecast_history),
        build_model_error_df(backtest),
        build_target_status_distribution_df(forecast_history),
        build_gap_surplus_trend_df(forecast_history),
        build_strategy_mix_df(forecast_history),
    ]

    assert all(isinstance(frame, pd.DataFrame) for frame in frames)
    assert all(not frame.empty for frame in frames)


def test_build_visualization_returns_required_keys() -> None:
    result = build_visualization(_forecast_history(), _backtest())

    assert set(VISUALIZATION_KEYS) <= set(result)
    assert isinstance(result["forecast_trend"], pd.DataFrame)
    assert isinstance(result["model_error"], pd.DataFrame)
    assert result["warnings"] == []


def test_status_and_strategy_distribution_shares_sum_to_one() -> None:
    forecast_history = _forecast_history()

    status_distribution = build_target_status_distribution_df(forecast_history)
    strategy_mix = build_strategy_mix_df(forecast_history)

    assert status_distribution["scenario_share"].sum() == 1.0
    assert strategy_mix["scenario_share"].sum() == 1.0


def _projection_input() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2026-06-01",
                "day_name": "display_a",
                "business_day_no": 1,
                "is_close_day": "Y",
                "sales_target_daily": 10.0,
                "sales_actual_cum": 11.0,
            },
            {
                "date": "2026-06-02",
                "day_name": "display_b",
                "business_day_no": 2,
                "is_close_day": "N",
                "sales_target_daily": 10.0,
                "sales_actual_cum": 21.0,
            },
            {
                "date": "2026-06-03",
                "day_name": "display_c",
                "business_day_no": 3,
                "is_close_day": False,
                "sales_target_daily": 10.0,
                "sales_actual_cum": None,
            },
            {
                "date": "2026-06-04",
                "day_name": "display_d",
                "business_day_no": 4,
                "is_close_day": True,
                "sales_target_daily": 10.0,
                "sales_actual_cum": None,
            },
        ]
    )


def test_projection_band_uses_existing_rows_without_generating_dates() -> None:
    df = _projection_input()

    projection = build_projection_band_data(
        df,
        {
            "F1": 39.0,
            "F2": 42.0,
            "F3": 45.0,
            "forecast_mid": 42.0,
        },
        "OVER_TARGET",
        current_day_no=2,
    )

    assert projection["date"].dt.strftime("%Y-%m-%d").tolist() == df["date"].tolist()
    assert projection["business_day_no"].tolist() == [1, 2, 3, 4]
    assert projection.attrs["forecast_low_final"] == 39.0
    assert projection.attrs["forecast_mid_final"] == 42.0
    assert projection.attrs["forecast_high_final"] == 45.0
    assert projection.loc[projection["is_current_point"], "actual_cum"].iloc[0] == 21.0
    assert projection.loc[projection["business_day_no"] == 4, "is_next_close_day"].iloc[0]
    assert "예상" not in str(projection.attrs.get("empty_state", ""))


def test_projection_band_has_visible_band_and_marker_flags() -> None:
    projection = build_projection_band_data(
        _projection_input(),
        {
            "F1_CUMULATIVE_RATE": 39.0,
            "F2_LAST_TWO_CLOSES": 42.0,
            "F3_DAY_CLOSE_WEIGHTED": 45.0,
            "representative_forecast": 42.0,
        },
        "OVER_TARGET",
        current_day_no=2,
    )

    assert not projection.empty
    visible_band = projection.loc[projection["is_projection_period"]]
    assert visible_band["forecast_low"].notna().any()
    assert visible_band["forecast_high"].notna().any()
    assert visible_band["projection_mid"].notna().any()
    assert projection["is_current_point"].sum() == 1
    assert projection["is_next_close_day"].sum() == 1


def test_projection_band_separates_actual_and_projection_periods() -> None:
    projection = build_projection_band_data(
        _projection_input(),
        {
            "F1_CUMULATIVE_RATE": 39.0,
            "F2_LAST_TWO_CLOSES": 42.0,
            "F3_DAY_CLOSE_WEIGHTED": 45.0,
            "representative_forecast": 42.0,
        },
        "OVER_TARGET",
        current_day_no=2,
    )

    by_day = projection.set_index("business_day_no")
    assert bool(by_day.loc[1, "is_actual_period"])
    assert bool(by_day.loc[2, "is_actual_period"])
    assert not bool(by_day.loc[3, "is_actual_period"])
    assert bool(by_day.loc[2, "is_projection_period"])
    assert bool(by_day.loc[3, "is_projection_period"])
    assert bool(by_day.loc[4, "is_projection_period"])
    assert by_day.loc[1, "point_type"] == "actual"
    assert by_day.loc[4, "point_type"] == "projection"
    assert projection["forecast_low"].notna().sum() >= 2
    assert projection["forecast_high"].notna().sum() >= 2


def test_close_day_markers_use_only_user_close_day_column() -> None:
    df = _projection_input().copy()
    df.loc[1, "day_name"] = "misleading_display_label"
    df.loc[1, "is_close_day"] = False

    markers = build_close_day_markers(df, current_day_no=2)

    assert markers["business_day_no"].tolist() == [1, 4]
    assert markers["is_close_day"].eq(True).all()
    assert markers.loc[markers["business_day_no"] == 4, "is_next_close_day"].iloc[0]


def test_projection_band_empty_states_are_graceful() -> None:
    df = _projection_input()

    missing_forecast = build_projection_band_data(
        df,
        {"F1": 39.0},
        "UNDER_TARGET",
        current_day_no=2,
    )
    missing_actual = build_projection_band_data(
        df.assign(sales_actual_cum=[None, None, None, None]),
        {
            "F1": 39.0,
            "F2": 42.0,
            "F3": 45.0,
            "forecast_mid": 42.0,
        },
        "UNDER_TARGET",
    )
    missing_input = build_projection_band_data(
        pd.DataFrame(),
        {
            "F1": 39.0,
            "F2": 42.0,
            "F3": 45.0,
            "forecast_mid": 42.0,
        },
        "UNDER_TARGET",
    )

    assert missing_forecast.empty
    assert missing_forecast.attrs["empty_state"] == "예측 계산 후 Projection 차트를 표시합니다."
    assert missing_actual.empty
    assert missing_actual.attrs["empty_state"] == "현재 누적 실적이 입력되면 실제 추이선이 표시됩니다."
    assert missing_input.empty
    assert (
        missing_input.attrs["empty_state"]
        == "입력 데이터를 불러오면 달성 추이와 잔여기간 예측 구간이 표시됩니다."
    )


def test_forecast_model_mini_chart_source_has_three_model_rows_and_target_line() -> None:
    model_rows = pd.DataFrame(
        [
            {"forecast_model": "F1", "forecast_amount": 100.0, "target_status": "UNDER_TARGET"},
            {"forecast_model": "F2", "forecast_amount": 104.0, "target_status": "ON_TARGET"},
            {"forecast_model": "F3", "forecast_amount": 108.0, "target_status": "OVER_TARGET"},
        ]
    )

    source = build_forecast_model_mini_chart_source(
        model_rows,
        {"scenario_id": "F2_O1", "forecast_after_provision": 104.0},
        monthly_target=102.0,
    )

    assert len(source) == 3
    assert source["model_key"].tolist() == ["F1", "F2", "F3"]
    assert source["value"].notna().all()
    assert source.attrs["target_line_value"] == 102.0
    assert source.attrs["representative_value"] == 104.0
    assert source.loc[source["model_key"] == "F2", "is_selected_model"].iloc[0]


def test_forecast_model_mini_chart_source_requires_all_f1_f2_f3_values() -> None:
    source = build_forecast_model_mini_chart_source(
        pd.DataFrame(
            [
                {"forecast_model": "F1", "forecast_amount": 100.0},
                {"forecast_model": "F2", "forecast_amount": None},
            ]
        ),
        monthly_target=102.0,
    )

    assert source.empty
    assert "F1/F2/F3" in source.attrs["empty_state"]


def test_close_cycle_cumulative_source_keeps_rows_and_adds_cumulative_fields() -> None:
    close_cycle = pd.DataFrame(
        [
            {
                "cycle_id": 1,
                "cycle_end_date": "2026-06-01",
                "is_completed": True,
                "target_sum": 40.0,
                "actual_sum": 36.0,
                "achievement_rate": 90.0,
                "row_count": 1,
                "close_type": "초기",
            },
            {
                "cycle_id": 2,
                "cycle_end_date": "2026-06-05",
                "is_completed": True,
                "target_sum": 60.0,
                "actual_sum": 66.0,
                "achievement_rate": 110.0,
                "row_count": 4,
                "close_type": "중간",
            },
        ]
    )

    source = build_close_cycle_cumulative_source(close_cycle)

    assert len(source) == len(close_cycle)
    assert {"target_cum", "actual_cum", "cumulative_achievement_rate"} <= set(source.columns)
    assert source["target_cum"].tolist() == [40.0, 100.0]
    assert source["actual_cum"].tolist() == [36.0, 102.0]
    assert source["cumulative_achievement_rate"].round(2).tolist() == [0.9, 1.02]
    assert source.attrs["close_marker_basis"] == "is_close_day"


def test_strategy_compare_source_uses_operation_columns_when_arrival_values_match() -> None:
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
                "recommended_action": "버퍼 유지",
            },
            {
                "scenario_id": "F1_O2",
                "strategy_type": "OVERACHIEVEMENT",
                "monthly_target": 100.0,
                "forecast_after_provision": 130.0,
                "target_variance": 30.0,
                "revised_monthly_target": 115.0,
                "remaining_surplus_buffer": 15.0,
                "stretch_uplift": 15.0,
                "relief_amount": 0.0,
                "minimum_remaining_to_hit_target": 0.0,
                "recommended_action": "상향 목표 전환",
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
                "relief_amount": 5.0,
                "minimum_remaining_to_hit_target": 0.0,
                "recommended_action": "품질 방어",
            },
        ]
    )

    source = build_strategy_arrival_compare_source(scenarios, "F1_O1")

    assert source.attrs["identical_forecast_values"]
    assert source.attrs["fallback_used"]
    assert source.attrs["classification"] == "TRUE_IDENTICAL_BY_DESIGN"
    assert source.attrs["display_mode"] == "table"
    assert source.attrs["compare_metric"] == "revised_monthly_target"
    assert source["forecast_after_provision"].nunique() == 1
    assert source["compare_value"].nunique() > 1


def test_strategy_compare_source_keeps_arrival_chart_when_values_differ() -> None:
    scenarios = pd.DataFrame(
        [
            {"scenario_id": "F1_P1", "monthly_target": 100.0, "forecast_after_provision": 99.0},
            {"scenario_id": "F1_P2", "monthly_target": 100.0, "forecast_after_provision": 102.0},
            {"scenario_id": "F1_P3", "monthly_target": 100.0, "forecast_after_provision": 104.0},
        ]
    )

    source = build_strategy_arrival_compare_source(scenarios, "F1_P1")

    assert not source.attrs["identical_forecast_values"]
    assert not source.attrs["fallback_used"]
    assert source.attrs["display_mode"] == "chart"
    assert source.attrs["compare_metric"] == "forecast_after_provision"
