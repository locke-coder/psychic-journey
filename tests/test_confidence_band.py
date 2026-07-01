import pandas as pd

from src.confidence_band import (
    build_confidence_band,
    build_fallback_band,
    calculate_error_distribution,
)


def _backtest() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "forecast_model": [
                "F1_CUMULATIVE_RATE",
                "F2_LAST_TWO_CLOSES",
                "F3_DAY_CLOSE_WEIGHTED",
            ],
            "error_rate": [0.05, 0.10, 0.20],
        }
    )


def test_error_distribution_percentiles_are_ordered() -> None:
    distribution = calculate_error_distribution(_backtest())

    assert distribution["p10"] <= distribution["p50"] <= distribution["p90"]


def test_confidence_band_order_is_not_broken() -> None:
    distribution = calculate_error_distribution(_backtest())

    band = build_confidence_band(100.0, distribution)

    assert band["confidence_lower"] <= band["confidence_mid"] <= band["confidence_upper"]
    assert band["p10"] <= band["p50"] <= band["p90"]
    assert band["conservative_forecast"] == band["confidence_lower"]
    assert band["base_forecast"] == band["confidence_mid"]
    assert band["aggressive_forecast"] == band["confidence_upper"]


def test_fallback_band_uses_forecast_spread_when_backtest_is_sparse() -> None:
    forecasts = pd.DataFrame(
        {
            "forecast_model": [
                "F1_CUMULATIVE_RATE",
                "F2_LAST_TWO_CLOSES",
                "F3_DAY_CLOSE_WEIGHTED",
            ],
            "forecast_amount": [95.0, 110.0, 125.0],
        }
    )

    band = build_fallback_band(forecasts)

    assert band["confidence_lower"] == 95.0
    assert band["confidence_mid"] == 110.0
    assert band["confidence_upper"] == 125.0
    assert band["p10"] <= band["p50"] <= band["p90"]
    assert band["confidence_method"] == "fallback_forecast_min_max"


def test_fallback_band_prevents_negative_forecasts() -> None:
    forecasts = pd.DataFrame({"forecast_model": ["F1_CUMULATIVE_RATE"], "forecast_amount": [-1.0]})

    band = build_fallback_band(forecasts)

    assert band["confidence_lower"] == 0.0
    assert band["confidence_mid"] == 0.0
    assert band["confidence_upper"] == 0.0
