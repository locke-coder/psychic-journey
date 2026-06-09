"""Standard schemas for forecast history and final actual records."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml


FORECAST_HISTORY = "forecast_history"
FINAL_ACTUALS = "final_actuals"

FORECAST_HISTORY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "run_datetime",
    "target_month",
    "as_of_date",
    "metric",
    "forecast_model",
    "strategy_id",
    "strategy_type",
    "forecast_amount",
    "forecast_rate",
    "target_status",
    "target_variance",
    "gap_to_target",
    "surplus_to_target",
    "risk_level",
    "monthly_target",
    "current_actual_cum",
    "current_target_cum",
    "remaining_target",
)

FINAL_ACTUALS_COLUMNS: tuple[str, ...] = (
    "target_month",
    "metric",
    "final_actual",
    "final_achievement_rate",
    "final_status",
    "cancellation_amount",
    "net_actual",
    "memo",
    "updated_at",
)

SCHEMA_COLUMNS: dict[str, tuple[str, ...]] = {
    FORECAST_HISTORY: FORECAST_HISTORY_COLUMNS,
    FINAL_ACTUALS: FINAL_ACTUALS_COLUMNS,
}

FORECAST_HISTORY_RUN_ID_KEY: tuple[str, ...] = ("run_id",)
FORECAST_HISTORY_FALLBACK_KEY: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "forecast_model",
    "strategy_id",
    "run_datetime",
)
FINAL_ACTUALS_UPSERT_KEY: tuple[str, ...] = ("target_month", "metric")

DUPLICATE_KEY_POLICIES: dict[str, dict[str, object]] = {
    FORECAST_HISTORY: {
        "run_id_unique": True,
        "unique_key": FORECAST_HISTORY_RUN_ID_KEY,
        "fallback_key": FORECAST_HISTORY_FALLBACK_KEY,
    },
    FINAL_ACTUALS: {
        "upsert": True,
        "upsert_key": FINAL_ACTUALS_UPSERT_KEY,
    },
}

DEFAULT_HISTORY_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "history_config.yaml"
)


def get_schema_columns(schema_name: str) -> tuple[str, ...]:
    """Return the required column order for a history schema."""
    try:
        return SCHEMA_COLUMNS[schema_name]
    except KeyError as exc:
        supported = ", ".join(sorted(SCHEMA_COLUMNS))
        raise ValueError(
            f"Unsupported history schema: {schema_name}. Supported: {supported}."
        ) from exc


def validate_required_columns(columns: Iterable[str], schema_name: str) -> None:
    """Raise when required schema columns are absent."""
    present_columns = set(columns)
    missing_columns = [
        column for column in get_schema_columns(schema_name) if column not in present_columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required {schema_name} columns: {missing}")


def load_history_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate history storage configuration."""
    path = Path(config_path) if config_path is not None else DEFAULT_HISTORY_CONFIG_PATH
    with path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise ValueError("History config must be a mapping.")

    _validate_history_config(config)
    return config


def get_storage_paths(
    config_path: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Path]:
    """Return configured history output paths as absolute paths."""
    config = load_history_config(config_path)
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    storage_paths = config["storage_paths"]

    resolved_paths: dict[str, Path] = {}
    for schema_name in (FORECAST_HISTORY, FINAL_ACTUALS):
        raw_path = Path(storage_paths[schema_name])
        resolved_paths[schema_name] = raw_path if raw_path.is_absolute() else root / raw_path
    return resolved_paths


def get_duplicate_key_policy(schema_name: str) -> dict[str, object]:
    """Return duplicate-key policy metadata for a history schema."""
    if schema_name not in DUPLICATE_KEY_POLICIES:
        get_schema_columns(schema_name)
    return dict(DUPLICATE_KEY_POLICIES[schema_name])


def select_forecast_history_key_columns(record: Mapping[str, Any]) -> tuple[str, ...]:
    """Use run_id as the unique key when present, otherwise use the fallback key."""
    return (
        FORECAST_HISTORY_RUN_ID_KEY
        if _has_record_value(record, "run_id")
        else FORECAST_HISTORY_FALLBACK_KEY
    )


def build_duplicate_key(schema_name: str, record: Mapping[str, Any]) -> tuple[Any, ...]:
    """Build the duplicate-detection key for one schema record."""
    if schema_name == FORECAST_HISTORY:
        key_columns = select_forecast_history_key_columns(record)
    elif schema_name == FINAL_ACTUALS:
        key_columns = FINAL_ACTUALS_UPSERT_KEY
    else:
        get_schema_columns(schema_name)
        raise AssertionError("unreachable")

    _validate_key_columns_present(record, key_columns, schema_name)
    return tuple(record[column] for column in key_columns)


def _validate_history_config(config: Mapping[str, Any]) -> None:
    storage_paths = _mapping_value(config, "storage_paths")
    for schema_name in (FORECAST_HISTORY, FINAL_ACTUALS):
        if not isinstance(storage_paths.get(schema_name), str) or not storage_paths[
            schema_name
        ]:
            raise ValueError(f"History config missing storage path for {schema_name}.")

    configured_schemas = _mapping_value(config, "schemas")
    for schema_name, expected_columns in SCHEMA_COLUMNS.items():
        schema_config = _mapping_value(configured_schemas, schema_name)
        required_columns = tuple(schema_config.get("required_columns", ()))
        if required_columns != expected_columns:
            raise ValueError(
                f"History config schema mismatch for {schema_name}: "
                "required_columns must match history_schema constants."
            )

    duplicate_keys = _mapping_value(config, "duplicate_keys")
    forecast_policy = _mapping_value(duplicate_keys, FORECAST_HISTORY)
    final_policy = _mapping_value(duplicate_keys, FINAL_ACTUALS)
    if forecast_policy.get("run_id_unique") is not True:
        raise ValueError("forecast_history duplicate policy must enable run_id_unique.")
    if tuple(forecast_policy.get("fallback_key", ())) != FORECAST_HISTORY_FALLBACK_KEY:
        raise ValueError("forecast_history fallback key does not match schema policy.")
    if tuple(final_policy.get("upsert_key", ())) != FINAL_ACTUALS_UPSERT_KEY:
        raise ValueError("final_actuals upsert key does not match schema policy.")


def _mapping_value(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"History config section must be a mapping: {key}.")
    return value


def _validate_key_columns_present(
    record: Mapping[str, Any],
    key_columns: tuple[str, ...],
    schema_name: str,
) -> None:
    missing_columns = [
        column for column in key_columns if not _has_record_value(record, column)
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required {schema_name} key values: {missing}")


def _has_record_value(record: Mapping[str, Any], column: str) -> bool:
    value = record.get(column)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, float):
        return not math.isnan(value)
    return True
