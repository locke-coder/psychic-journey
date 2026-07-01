from datetime import date

import pandas as pd
import pytest

from src.forecast_models import forecast_f1_cumulative_rate
from src.provision_models import (
    CAPACITY_LIMITED,
    NO_GAP,
    NOT_APPLICABLE,
    OK,
    P1_ALL_REMAINING,
    P2_CLOSE_DAY_FOCUSED,
    P3_NON_CLOSE_DAY_FOCUSED,
    provision_p1_all_remaining,
    provision_p2_close_day_focused,
    provision_p3_non_close_day_focused,
)


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-06-01",
                    "2026-06-02",
                    "2026-06-03",
                    "2026-06-04",
                    "2026-06-05",
                ]
            ),
            "day_name": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "business_day_no": [1, 2, 3, 4, 5],
            "is_close_day": ["N", "Y", "N", "Y", "N"],
            "close_type": ["", "mid", "", "month", ""],
            "sales_target_daily": [10.0, 10.0, 20.0, 30.0, 50.0],
            "recognized_target_daily": [1.0, 1.0, 2.0, 3.0, 5.0],
            "sales_actual_cum": [8.0, 16.0, pd.NA, pd.NA, pd.NA],
            "recognized_actual_cum": [1.0, 2.0, pd.NA, pd.NA, pd.NA],
            "memo": [""] * 5,
        }
    )


def _forecast(df: pd.DataFrame | None = None) -> dict[str, object]:
    source = _df() if df is None else df
    result = forecast_f1_cumulative_rate(source, "sales", "2026-06-02")
    return {
        **result,
        "expected_rate_by_day": {
            date(2026, 6, 3): 1.0,
            date(2026, 6, 4): 1.0,
            date(2026, 6, 5): 1.0,
        },
    }


def _config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "close_day_cap_rate": 10.0,
        "non_close_day_cap_rate": 10.0,
        "provision_overflow_fallback": "ALL_REMAINING",
    }
    config.update(overrides)
    return config


def test_p1_weight_target_is_all_remaining_rows() -> None:
    result = provision_p1_all_remaining(_df(), _forecast(), "2026-06-02", "sales", _config())
    allocation = result["allocation_by_day"]

    assert result["strategy_id"] == P1_ALL_REMAINING
    assert result["status"] == OK
    assert allocation["date"].tolist() == [
        date(2026, 6, 3),
        date(2026, 6, 4),
        date(2026, 6, 5),
    ]
    assert allocation["allocation_weight"].tolist() == pytest.approx([0.2, 0.3, 0.5])
    assert allocation["allocation_weight"].sum() == pytest.approx(1.0)


def test_p2_weight_target_is_remaining_close_days_only() -> None:
    result = provision_p2_close_day_focused(
        _df(),
        _forecast(),
        "2026-06-02",
        "sales",
        _config(),
    )
    allocation = result["allocation_by_day"]

    assert result["strategy_id"] == P2_CLOSE_DAY_FOCUSED
    assert result["status"] == OK
    assert allocation["allocation_weight"].tolist() == pytest.approx([0.0, 1.0, 0.0])
    assert allocation["allocation_weight"].sum() == pytest.approx(1.0)
    assert allocation.loc[allocation["uplift"] > 0, "is_close_day"].tolist() == [True]


def test_p3_weight_target_is_remaining_non_close_days_only() -> None:
    result = provision_p3_non_close_day_focused(
        _df(),
        _forecast(),
        "2026-06-02",
        "sales",
        _config(),
    )
    allocation = result["allocation_by_day"]

    assert result["strategy_id"] == P3_NON_CLOSE_DAY_FOCUSED
    assert result["status"] == OK
    assert allocation["allocation_weight"].tolist() == pytest.approx([2 / 7, 0.0, 5 / 7])
    assert allocation["allocation_weight"].sum() == pytest.approx(1.0)
    assert allocation.loc[allocation["uplift"] > 0, "is_close_day"].tolist() == [False, False]


def test_gap_zero_returns_no_gap_status() -> None:
    df = _df()
    forecast = _forecast(df)
    forecast["current_actual_cum"] = 20.0
    forecast["monthly_target"] = 100.0

    result = provision_p1_all_remaining(df, forecast, "2026-06-02", "sales", _config())

    assert result["status"] == NO_GAP
    assert result["gap_to_target"] == pytest.approx(0.0)
    assert result["required_uplift"] == pytest.approx(0.0)
    assert result["allocated_uplift"] == pytest.approx(0.0)
    assert result["unallocated_uplift"] == pytest.approx(0.0)


def test_required_uplift_lifts_forecast_to_monthly_target_or_more() -> None:
    result = provision_p1_all_remaining(_df(), _forecast(), "2026-06-02", "sales", _config())

    assert result["required_uplift"] == pytest.approx(4.0)
    assert result["forecast_after_provision"] >= 120.0 - 1e-9
    assert result["gap_after_provision"] == pytest.approx(0.0)


def test_strategy_without_target_rows_returns_not_applicable() -> None:
    df = _df()
    df.loc[df["date"] > pd.Timestamp("2026-06-02"), "is_close_day"] = "N"

    result = provision_p2_close_day_focused(df, _forecast(df), "2026-06-02", "sales", _config())

    assert result["status"] == NOT_APPLICABLE
    assert result["required_uplift"] == pytest.approx(0.0)
    assert result["allocated_uplift"] == pytest.approx(0.0)
    assert result["unallocated_uplift"] == pytest.approx(0.0)


def test_cap_limited_when_primary_and_fallback_capacity_are_insufficient() -> None:
    config = _config(close_day_cap_rate=1.01, non_close_day_cap_rate=1.01)

    result = provision_p1_all_remaining(_df(), _forecast(), "2026-06-02", "sales", config)
    allocation = result["allocation_by_day"]

    assert result["status"] == CAPACITY_LIMITED
    assert result["allocated_uplift"] == pytest.approx(1.0)
    assert result["unallocated_uplift"] == pytest.approx(3.0)
    assert result["unallocated_uplift"] >= 0
    assert allocation["revised_target"].le(allocation["cap_target"] + 1e-9).all()
    assert allocation["cap_exceeded"].any()


def test_overflow_fallback_redistributes_to_all_remaining_capacity() -> None:
    config = _config(close_day_cap_rate=1.01, non_close_day_cap_rate=10.0)

    result = provision_p2_close_day_focused(_df(), _forecast(), "2026-06-02", "sales", config)
    allocation = result["allocation_by_day"]

    assert result["status"] == OK
    assert result["allocated_uplift"] == pytest.approx(result["required_uplift"])
    assert result["unallocated_uplift"] == pytest.approx(0.0)
    assert allocation.loc[allocation["is_close_day"], "uplift"].iloc[0] == pytest.approx(0.3)
    assert allocation.loc[~allocation["is_close_day"], "uplift"].sum() == pytest.approx(3.7)
    assert result["forecast_after_provision"] >= 120.0 - 1e-9
