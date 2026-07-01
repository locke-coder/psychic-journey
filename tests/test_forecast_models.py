from datetime import date

import pandas as pd
import pytest

from src.forecast_models import (
    F1_CUMULATIVE_RATE,
    F2_LAST_TWO_CLOSES,
    F3_DAY_CLOSE_WEIGHTED,
    OVER_TARGET,
    UNDER_TARGET,
    forecast_f1_cumulative_rate,
    forecast_f2_last_two_closes,
    forecast_f3_day_close_weighted,
)


def _forecast_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-06-01",
                    "2026-06-02",
                    "2026-06-03",
                    "2026-06-04",
                    "2026-06-05",
                    "2026-06-06",
                    "2026-06-07",
                    "2026-06-08",
                    "2026-06-09",
                ]
            ),
            "is_close_day": ["N", "Y", "N", "Y", "N", "Y", "N", "Y", "N"],
            "sales_target_daily": [10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0],
            "recognized_target_daily": [1.0] * 9,
            "sales_actual_cum": [5.0, 23.0, 33.0, 51.0, 66.0, 86.0, 96.0, pd.NA, pd.NA],
            "recognized_actual_cum": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, pd.NA, pd.NA],
        }
    )


def test_f1_cumulative_rate_calculation() -> None:
    result = forecast_f1_cumulative_rate(_forecast_df(), "sales", "2026-06-05")

    r_cum = 66.0 / 70.0

    assert result["model_id"] == F1_CUMULATIVE_RATE
    assert result["as_of_date"] == date(2026, 6, 5)
    assert result["monthly_target"] == pytest.approx(130.0)
    assert result["current_actual_cum"] == pytest.approx(66.0)
    assert result["current_target_cum"] == pytest.approx(70.0)
    assert result["remaining_target"] == pytest.approx(60.0)
    assert result["forecast_amount"] == pytest.approx(66.0 + 60.0 * r_cum)
    assert result["expected_rate_by_day"] == {
        date(2026, 6, 6): pytest.approx(r_cum),
        date(2026, 6, 7): pytest.approx(r_cum),
        date(2026, 6, 8): pytest.approx(r_cum),
        date(2026, 6, 9): pytest.approx(r_cum),
    }
    assert result["warnings"] == []


def test_f2_uses_only_last_two_completed_close_cycles() -> None:
    result = forecast_f2_last_two_closes(_forecast_df(), "sales", "2026-06-07")

    r_last2 = (28.0 + 35.0) / (30.0 + 30.0)

    assert result["model_id"] == F2_LAST_TWO_CLOSES
    assert result["forecast_amount"] == pytest.approx(96.0 + 30.0 * r_last2)
    assert result["expected_rate_by_day"] == {
        date(2026, 6, 8): pytest.approx(r_last2),
        date(2026, 6, 9): pytest.approx(r_last2),
    }
    assert result["warnings"] == []


def test_f3_returns_different_expected_rates_by_is_close_day() -> None:
    result = forecast_f3_day_close_weighted(_forecast_df(), "sales", "2026-06-07")

    r_close = (18.0 + 18.0 + 20.0) / (20.0 + 20.0 + 20.0)
    r_non_close = (5.0 + 10.0 + 15.0 + 10.0) / (10.0 + 10.0 + 10.0 + 10.0)

    assert result["model_id"] == F3_DAY_CLOSE_WEIGHTED
    assert result["expected_rate_by_day"][date(2026, 6, 8)] == pytest.approx(r_close)
    assert result["expected_rate_by_day"][date(2026, 6, 9)] == pytest.approx(r_non_close)
    assert result["forecast_amount"] == pytest.approx(
        96.0 + 20.0 * r_close + 10.0 * r_non_close
    )
    assert result["warnings"] == []


def test_f2_falls_back_to_f1_when_two_completed_close_cycles_are_missing() -> None:
    df = _forecast_df()

    f1 = forecast_f1_cumulative_rate(df, "sales", "2026-06-03")
    f2 = forecast_f2_last_two_closes(df, "sales", "2026-06-03")

    assert f2["model_id"] == F2_LAST_TWO_CLOSES
    assert f2["forecast_amount"] == pytest.approx(f1["forecast_amount"])
    assert f2["expected_rate_by_day"] == f1["expected_rate_by_day"]
    assert f2["warnings"][0].startswith("F2_LAST_TWO_CLOSES fallback")


def test_f3_falls_back_when_close_day_history_is_missing() -> None:
    df = _forecast_df()

    f1 = forecast_f1_cumulative_rate(df, "sales", "2026-06-01")
    f3 = forecast_f3_day_close_weighted(df, "sales", "2026-06-01")

    assert f3["model_id"] == F3_DAY_CLOSE_WEIGHTED
    assert f3["forecast_amount"] == pytest.approx(f1["forecast_amount"])
    assert f3["expected_rate_by_day"] == f1["expected_rate_by_day"]
    assert f3["warnings"][0].startswith("F3_DAY_CLOSE_WEIGHTED fallback")
    assert f3["warnings"][1].startswith("F2_LAST_TWO_CLOSES fallback")


def test_gap_to_target_never_becomes_negative() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01", "2026-06-02"]),
            "is_close_day": ["N", "Y"],
            "sales_target_daily": [10.0, 10.0],
            "recognized_target_daily": [1.0, 1.0],
            "sales_actual_cum": [30.0, pd.NA],
            "recognized_actual_cum": [1.0, pd.NA],
        }
    )

    result = forecast_f1_cumulative_rate(df, "sales", "2026-06-01")

    assert result["forecast_amount"] == pytest.approx(60.0)
    assert result["gap_to_target"] == pytest.approx(0.0)
    assert result["target_status"] == OVER_TARGET
    assert result["surplus_to_target"] == pytest.approx(40.0)
    assert result["target_variance"] == pytest.approx(40.0)


def test_under_target_status_and_variance_are_reported() -> None:
    result = forecast_f1_cumulative_rate(_forecast_df(), "sales", "2026-06-05")

    assert result["target_status"] == UNDER_TARGET
    assert result["target_variance"] == pytest.approx(
        result["forecast_amount"] - result["monthly_target"]
    )
    assert result["gap_to_target"] == pytest.approx(
        result["monthly_target"] - result["forecast_amount"]
    )
    assert result["surplus_to_target"] == pytest.approx(0.0)


def test_forecast_rate_is_forecast_amount_divided_by_monthly_target() -> None:
    result = forecast_f1_cumulative_rate(_forecast_df(), "sales", "2026-06-05")

    assert result["forecast_rate"] == pytest.approx(
        result["forecast_amount"] / result["monthly_target"]
    )
