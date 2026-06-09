"""Build auxiliary ConfidenceBand data from Backtest errors or forecast spread."""

from __future__ import annotations

from typing import Any

import pandas as pd


CONFIDENCE_BAND_FIELDS: tuple[str, ...] = (
    "confidence_lower",
    "confidence_mid",
    "confidence_upper",
    "conservative_forecast",
    "base_forecast",
    "aggressive_forecast",
    "p10",
    "p50",
    "p90",
    "confidence_method",
    "warnings",
)


def calculate_error_distribution(backtest_df: pd.DataFrame | Any) -> dict[str, object]:
    """Return Backtest error-rate percentiles for confidence band generation."""
    backtest = _as_dataframe(backtest_df, "backtest_df")
    warnings: list[str] = []
    if backtest.empty:
        return _empty_distribution(["backtest_df is empty."])

    if "error_rate" in backtest.columns:
        error_rate = pd.to_numeric(backtest["error_rate"], errors="coerce").abs()
    elif "signed_error_rate" in backtest.columns:
        error_rate = pd.to_numeric(backtest["signed_error_rate"], errors="coerce").abs()
    else:
        return _empty_distribution(["backtest_df requires error_rate or signed_error_rate."])

    finite_error = error_rate.dropna()
    finite_error = finite_error.loc[finite_error >= 0]
    if finite_error.empty:
        return _empty_distribution(["No finite error_rate values are available."])

    p10 = float(finite_error.quantile(0.10))
    p50 = float(finite_error.quantile(0.50))
    p90 = float(finite_error.quantile(0.90))
    return {
        "sample_count": int(len(finite_error)),
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "confidence_method": "backtest_error_distribution",
        "warnings": warnings,
    }


def build_confidence_band(
    current_forecast: float | int | dict[str, Any] | pd.Series,
    error_distribution: dict[str, Any],
) -> dict[str, object]:
    """Return confidence_lower, confidence_mid, and confidence_upper around a forecast."""
    base_forecast = _extract_forecast_amount(current_forecast)
    distribution = dict(error_distribution or {})
    warnings = list(distribution.get("warnings", []))
    if not _is_finite(base_forecast):
        base_forecast = 0.0
        warnings.append("current_forecast is not finite; base_forecast was set to 0.")

    p10 = _non_negative_float(distribution.get("p10"), 0.0)
    p50 = _non_negative_float(distribution.get("p50"), p10)
    p90 = _non_negative_float(distribution.get("p90"), p50)
    p10, p50, p90 = sorted((p10, p50, p90))

    confidence_mid = max(0.0, base_forecast)
    confidence_lower = max(0.0, confidence_mid * (1.0 - p90))
    confidence_upper = max(confidence_mid, confidence_mid * (1.0 + p90))

    return _band_result(
        confidence_lower=confidence_lower,
        confidence_mid=confidence_mid,
        confidence_upper=confidence_upper,
        p10=p10,
        p50=p50,
        p90=p90,
        confidence_method=str(
            distribution.get("confidence_method", "backtest_error_distribution")
        ),
        warnings=warnings,
    )


def build_fallback_band(forecast_results_df: pd.DataFrame | Any) -> dict[str, object]:
    """Return a fallback ConfidenceBand from the min/median/max forecast spread."""
    forecasts = _as_dataframe(forecast_results_df, "forecast_results_df")
    warnings = ["Fallback band used because Backtest error distribution is unavailable."]
    if forecasts.empty or "forecast_amount" not in forecasts.columns:
        return _band_result(
            confidence_lower=0.0,
            confidence_mid=0.0,
            confidence_upper=0.0,
            p10=0.0,
            p50=0.0,
            p90=0.0,
            confidence_method="fallback_empty",
            warnings=[*warnings, "forecast_results_df is empty or missing forecast_amount."],
        )

    values = pd.to_numeric(forecasts["forecast_amount"], errors="coerce").dropna()
    values = values.loc[values >= 0]
    if values.empty:
        return _band_result(
            confidence_lower=0.0,
            confidence_mid=0.0,
            confidence_upper=0.0,
            p10=0.0,
            p50=0.0,
            p90=0.0,
            confidence_method="fallback_empty",
            warnings=[*warnings, "No non-negative forecast_amount values are available."],
        )

    lower = float(values.min())
    mid = float(values.median())
    upper = float(values.max())
    p10 = float(values.quantile(0.10))
    p50 = float(values.quantile(0.50))
    p90 = float(values.quantile(0.90))
    p10, p50, p90 = sorted((p10, p50, p90))
    return _band_result(
        confidence_lower=lower,
        confidence_mid=mid,
        confidence_upper=max(upper, mid),
        p10=p10,
        p50=p50,
        p90=p90,
        confidence_method="fallback_forecast_min_max",
        warnings=warnings,
    )


def _band_result(
    *,
    confidence_lower: float,
    confidence_mid: float,
    confidence_upper: float,
    p10: float,
    p50: float,
    p90: float,
    confidence_method: str,
    warnings: list[str],
) -> dict[str, object]:
    lower, mid, upper = sorted(
        (
            max(0.0, confidence_lower),
            max(0.0, confidence_mid),
            max(0.0, confidence_upper),
        )
    )
    p10, p50, p90 = sorted((max(0.0, p10), max(0.0, p50), max(0.0, p90)))
    return {
        "confidence_lower": lower,
        "confidence_mid": mid,
        "confidence_upper": upper,
        "conservative_forecast": lower,
        "base_forecast": mid,
        "aggressive_forecast": upper,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "confidence_method": confidence_method,
        "warnings": warnings,
    }


def _empty_distribution(warnings: list[str]) -> dict[str, object]:
    return {
        "sample_count": 0,
        "p10": float("nan"),
        "p50": float("nan"),
        "p90": float("nan"),
        "confidence_method": "insufficient_backtest_data",
        "warnings": warnings,
    }


def _extract_forecast_amount(value: float | int | dict[str, Any] | pd.Series) -> float:
    if isinstance(value, dict):
        return float(value.get("forecast_amount", value.get("base_forecast", 0.0)))
    if isinstance(value, pd.Series):
        return float(value.get("forecast_amount", value.get("base_forecast", 0.0)))
    return float(value)


def _non_negative_float(value: object, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not _is_finite(number):
        return default
    return max(0.0, number)


def _is_finite(value: object) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and number not in (float("inf"), float("-inf"))


def _as_dataframe(value: pd.DataFrame | Any, name: str) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    raise ValueError(f"{name} must be a DataFrame.")
