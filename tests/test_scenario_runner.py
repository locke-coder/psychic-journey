from datetime import date
from pathlib import Path

import pandas as pd

from src.forecast_models import (
    F1_CUMULATIVE_RATE,
    F2_LAST_TWO_CLOSES,
    F3_DAY_CLOSE_WEIGHTED,
    OVER_TARGET,
    UNDER_TARGET,
)
from src.overachievement_models import (
    O1_TARGET_HOLD_BUFFER,
    O2_STRETCH_TARGET_CAPTURE,
    O3_QUALITY_GUARD_RELIEF,
    OVERACHIEVEMENT,
)
from src.provision_models import (
    CALCULATION_ERROR,
    P1_ALL_REMAINING,
    P2_CLOSE_DAY_FOCUSED,
    P3_NON_CLOSE_DAY_FOCUSED,
)
from src.scenario_runner import SCENARIO_OUTPUT_COLUMNS, run_scenario_grid


def _scenario_df() -> pd.DataFrame:
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
            "day_name": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Mon", "Tue"],
            "business_day_no": list(range(1, 10)),
            "is_close_day": ["N", "Y", "N", "Y", "N", "Y", "N", "Y", "N"],
            "close_type": ["", "first", "", "mid", "", "final", "", "next", ""],
            "sales_target_daily": [10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0],
            "recognized_target_daily": [1.0] * 9,
            "sales_actual_cum": [5.0, 23.0, 33.0, 51.0, 66.0, 86.0, 96.0, pd.NA, pd.NA],
            "recognized_actual_cum": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, pd.NA, pd.NA],
            "memo": [""] * 9,
        }
    )


def _over_target_df() -> pd.DataFrame:
    df = _scenario_df()
    df["sales_actual_cum"] = [20.0, 45.0, 70.0, 95.0, 120.0, 145.0, 170.0, pd.NA, pd.NA]
    return df


def _config() -> dict[str, object]:
    return {
        "close_day_cap_rate": 10.0,
        "non_close_day_cap_rate": 10.0,
        "provision_overflow_fallback": "ALL_REMAINING",
    }


def test_sample_scenario_grid_outputs_nine_rows() -> None:
    result = run_scenario_grid(_scenario_df(), "2026-06-07", "sales", _config())

    assert result.shape[0] == 9
    assert list(result.columns) == SCENARIO_OUTPUT_COLUMNS


def test_f1_p1_f2_p2_and_f3_p3_combinations_exist() -> None:
    result = run_scenario_grid(_scenario_df(), "2026-06-07", "sales", _config())

    combinations = set(zip(result["forecast_model"], result["provision_strategy"]))

    assert (F1_CUMULATIVE_RATE, P1_ALL_REMAINING) in combinations
    assert (F2_LAST_TWO_CLOSES, P2_CLOSE_DAY_FOCUSED) in combinations
    assert (F3_DAY_CLOSE_WEIGHTED, P3_NON_CLOSE_DAY_FOCUSED) in combinations
    assert set(result["target_status"]) == {UNDER_TARGET}


def test_scenario_ids_are_unique() -> None:
    result = run_scenario_grid(_scenario_df(), "2026-06-07", "sales", _config())

    assert result["scenario_id"].is_unique
    assert {"F1_P1", "F2_P2", "F3_P3"}.issubset(set(result["scenario_id"]))


def test_risk_level_and_status_are_not_empty() -> None:
    result = run_scenario_grid(_scenario_df(), "2026-06-07", "sales", _config())

    assert result["risk_level"].notna().all()
    assert result["risk_level"].ne("").all()
    assert result["status"].notna().all()
    assert result["status"].ne("").all()


def test_failed_scenarios_keep_rows() -> None:
    df = _scenario_df()
    df.loc[df["date"] == pd.Timestamp("2026-06-07"), "sales_actual_cum"] = pd.NA

    result = run_scenario_grid(df, "2026-06-07", "sales", _config())

    assert result.shape[0] == 9
    assert set(result["status"]) == {CALCULATION_ERROR}
    assert result["warnings"].map(bool).all()


def test_next_close_date_is_included() -> None:
    result = run_scenario_grid(_scenario_df(), "2026-06-07", "sales", _config())

    assert result["next_close_date"].tolist() == [date(2026, 6, 8)] * 9
    assert result["next_close_required"].notna().all()


def test_over_target_scenario_grid_returns_o1_o2_o3_rows() -> None:
    result = run_scenario_grid(_over_target_df(), "2026-06-07", "sales", _config())

    assert result.shape[0] == 9
    assert set(result["target_status"]) == {OVER_TARGET}
    assert set(result["strategy_type"]) == {OVERACHIEVEMENT}
    assert set(result["provision_strategy"]) == {
        O1_TARGET_HOLD_BUFFER,
        O2_STRETCH_TARGET_CAPTURE,
        O3_QUALITY_GUARD_RELIEF,
    }
    assert {"F1_O1", "F1_O2", "F1_O3", "F2_O1", "F3_O3"}.issubset(
        set(result["scenario_id"])
    )
    assert (result["surplus_to_target"] > 0).all()
    assert (result["target_variance"] > 0).all()
    assert (result["gap_to_target"] == 0).all()
    assert "NO_GAP" not in set(result["status"])


def test_over_target_o2_and_o3_fields_are_populated() -> None:
    result = run_scenario_grid(_over_target_df(), "2026-06-07", "sales", _config())

    o2_rows = result.loc[result["scenario_id"].str.endswith("_O2")]
    o3_rows = result.loc[result["scenario_id"].str.endswith("_O3")]

    assert (o2_rows["stretch_uplift"] > 0).all()
    assert (o2_rows["revised_monthly_target"] > o2_rows["monthly_target"]).all()
    assert (o3_rows["minimum_remaining_to_hit_target"] >= 0).all()
    assert (o3_rows["relief_amount"] >= 0).all()
    assert o3_rows["recommended_action"].str.contains("취소").all()
    assert o3_rows["recommended_action"].str.contains("미결제").all()


def test_no_weekday_based_close_inference_code_is_added() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    checked_files = [
        repo_root / "src" / "forecast_models.py",
        repo_root / "src" / "scenario_runner.py",
        repo_root / "src" / "overachievement_models.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)

    assert ".weekday(" not in source
    assert "dt.weekday" not in source
    assert "dayofweek" not in source
