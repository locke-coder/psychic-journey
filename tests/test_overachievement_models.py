import pytest

from src.overachievement_models import (
    O1_TARGET_HOLD_BUFFER,
    O2_STRETCH_TARGET_CAPTURE,
    O3_QUALITY_GUARD_RELIEF,
    OVERACHIEVEMENT,
    run_overachievement_strategy,
)


def _forecast_result() -> dict[str, object]:
    return {
        "monthly_target": 100.0,
        "current_actual_cum": 82.0,
        "remaining_target": 30.0,
        "forecast_amount": 112.0,
        "target_variance": 12.0,
        "gap_to_target": 0.0,
        "surplus_to_target": 12.0,
        "warnings": [],
    }


def test_o1_holds_target_and_keeps_surplus_as_buffer() -> None:
    result = run_overachievement_strategy(_forecast_result(), O1_TARGET_HOLD_BUFFER)

    assert result["strategy_type"] == OVERACHIEVEMENT
    assert result["required_uplift"] == pytest.approx(0.0)
    assert result["revised_monthly_target"] == pytest.approx(100.0)
    assert result["remaining_surplus_buffer"] == pytest.approx(12.0)
    assert "취소" in str(result["recommended_action"])
    assert "미결제" in str(result["recommended_action"])


def test_o2_captures_half_of_surplus_as_stretch_target_by_default() -> None:
    result = run_overachievement_strategy(_forecast_result(), O2_STRETCH_TARGET_CAPTURE)

    assert result["stretch_uplift"] == pytest.approx(6.0)
    assert result["revised_monthly_target"] == pytest.approx(106.0)
    assert result["remaining_surplus_buffer"] == pytest.approx(6.0)
    assert result["required_uplift"] == pytest.approx(0.0)


def test_o3_calculates_quality_guard_relief_amount() -> None:
    result = run_overachievement_strategy(_forecast_result(), O3_QUALITY_GUARD_RELIEF)

    assert result["minimum_remaining_to_hit_target"] == pytest.approx(18.0)
    assert result["relief_amount"] == pytest.approx(12.0)
    assert result["required_uplift"] == pytest.approx(0.0)
    assert "계약 품질" in str(result["recommended_action"])
    assert "철회" in str(result["recommended_action"])
