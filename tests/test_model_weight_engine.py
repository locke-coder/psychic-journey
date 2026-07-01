import pandas as pd
import pytest

from src.model_weight_engine import (
    apply_model_weights,
    calculate_model_weights,
    calculate_weighted_forecast,
)


def _model_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "forecast_model": "F1_CUMULATIVE_RATE",
                "sample_count": 5,
                "mean_error_rate": 0.10,
            },
            {
                "forecast_model": "F2_LAST_TWO_CLOSES",
                "sample_count": 5,
                "mean_error_rate": 0.05,
            },
            {
                "forecast_model": "F3_DAY_CLOSE_WEIGHTED",
                "sample_count": 5,
                "mean_error_rate": 0.20,
            },
        ]
    )


def _forecasts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"forecast_model": "F1_CUMULATIVE_RATE", "forecast_amount": 100.0},
            {"forecast_model": "F2_LAST_TWO_CLOSES", "forecast_amount": 120.0},
            {"forecast_model": "F3_DAY_CLOSE_WEIGHTED", "forecast_amount": 90.0},
        ]
    )


def test_model_weights_sum_to_one() -> None:
    weights = calculate_model_weights(_model_summary())

    assert weights["model_weight"].sum() == pytest.approx(1.0)


def test_lower_error_rate_receives_higher_weight() -> None:
    weights = calculate_model_weights(_model_summary())
    by_model = weights.set_index("forecast_model")["model_weight"]

    assert by_model["F2_LAST_TWO_CLOSES"] > by_model["F1_CUMULATIVE_RATE"]
    assert by_model["F1_CUMULATIVE_RATE"] > by_model["F3_DAY_CLOSE_WEIGHTED"]


def test_insufficient_sample_models_fallback_when_no_model_is_eligible() -> None:
    summary = _model_summary()
    summary["sample_count"] = 1

    weights = calculate_model_weights(summary, min_samples=3)

    assert weights["model_weight"].sum() == pytest.approx(1.0)
    assert set(weights["weight_status"]) == {"fallback_equal_weight"}


def test_apply_model_weights_and_weighted_forecast_are_auxiliary() -> None:
    weights = calculate_model_weights(_model_summary())

    annotated = apply_model_weights(_forecasts(), weights)
    weighted = calculate_weighted_forecast(_forecasts(), weights)

    assert "weighted_forecast_amount" in annotated.columns
    assert weighted["weighted_forecast"] == pytest.approx(
        weighted["model_contributions"]["weighted_forecast_amount"].sum()
    )
    assert set(weighted["model_contributions"]["forecast_model"]) == set(
        _forecasts()["forecast_model"]
    )
