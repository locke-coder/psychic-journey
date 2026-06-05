"""Schema constants and config loading for the forecast tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


VALID_METRICS: tuple[str, ...] = ("sales", "recognized")

METRIC_COLUMN_MAP: dict[str, dict[str, str]] = {
    "sales": {
        "target_daily": "sales_target_daily",
        "actual_cum": "sales_actual_cum",
        "actual_daily": "sales_actual_daily",
        "target_cum": "sales_target_cum",
    },
    "recognized": {
        "target_daily": "recognized_target_daily",
        "actual_cum": "recognized_actual_cum",
        "actual_daily": "recognized_actual_daily",
        "target_cum": "recognized_target_cum",
    },
}

REQUIRED_INPUT_COLUMNS: tuple[str, ...] = (
    "date",
    "day_name",
    "business_day_no",
    "is_close_day",
    "close_type",
    "sales_target_daily",
    "recognized_target_daily",
    "sales_actual_cum",
    "recognized_actual_cum",
    "memo",
)

IS_CLOSE_DAY_TRUE_VALUES: tuple[object, ...] = ("Y", "YES", "TRUE", "1", True, 1)
IS_CLOSE_DAY_FALSE_VALUES: tuple[object, ...] = ("N", "NO", "FALSE", "0", False, 0)
IS_CLOSE_DAY_ALLOWED_VALUES: tuple[object, ...] = (
    *IS_CLOSE_DAY_TRUE_VALUES,
    *IS_CLOSE_DAY_FALSE_VALUES,
)


def validate_metric(metric: str) -> str:
    """Return a valid metric name or raise for unsupported metrics."""
    if metric not in VALID_METRICS:
        allowed = ", ".join(VALID_METRICS)
        raise ValueError(f"Unsupported metric: {metric}. Allowed metrics: {allowed}.")
    return metric


def get_metric_columns(metric: str) -> dict[str, str]:
    """Return column mappings for a metric."""
    return dict(METRIC_COLUMN_MAP[validate_metric(metric)])


def load_model_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load model configuration from YAML."""
    path = (
        Path(config_path)
        if config_path is not None
        else Path(__file__).resolve().parents[1] / "config" / "model_config.yaml"
    )

    with path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    return config or {}
