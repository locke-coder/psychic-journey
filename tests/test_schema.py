import pytest

from src import schema


def test_model_config_loads_expected_values() -> None:
    config = schema.load_model_config()

    assert config == {
        "amount_unit": "억",
        "amount_decimal_places": 1,
        "rate_decimal_places": 1,
        "allow_negative_daily_actual": True,
        "close_day_cap_rate": 1.30,
        "non_close_day_cap_rate": 1.50,
        "provision_overflow_fallback": "ALL_REMAINING",
        "fallback_forecast_model": "F1",
        "monthly_target_source": "sum_daily_target",
        "not_applicable_strategy_behavior": "RETURN_STATUS",
    }


def test_only_sales_and_recognized_metrics_are_allowed() -> None:
    assert schema.VALID_METRICS == ("sales", "recognized")
    assert schema.validate_metric("sales") == "sales"
    assert schema.validate_metric("recognized") == "recognized"


def test_invalid_metric_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported metric"):
        schema.validate_metric("profit")


def test_required_input_columns_are_not_empty() -> None:
    assert schema.REQUIRED_INPUT_COLUMNS


def test_metric_column_mappings_are_correct() -> None:
    assert schema.get_metric_columns("sales") == {
        "target_daily": "sales_target_daily",
        "actual_cum": "sales_actual_cum",
        "actual_daily": "sales_actual_daily",
        "target_cum": "sales_target_cum",
    }
    assert schema.get_metric_columns("recognized") == {
        "target_daily": "recognized_target_daily",
        "actual_cum": "recognized_actual_cum",
        "actual_daily": "recognized_actual_daily",
        "target_cum": "recognized_target_cum",
    }


def test_is_close_day_allowed_values_are_defined() -> None:
    assert schema.IS_CLOSE_DAY_ALLOWED_VALUES
