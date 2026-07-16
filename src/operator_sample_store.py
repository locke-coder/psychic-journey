"""Operator-managed sample storage for Streamlit defaults."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from numbers import Real
from pathlib import Path
from typing import Any, Literal, Mapping
from zoneinfo import ZoneInfo

import pandas as pd

from src.loader import load_input
from src.private_data_store import (
    PrivateDataStoreConfigurationError,
    PrivateDataStoreConflictError,
    PrivateDataStoreUnavailableError,
    get_private_data_store_config,
    write_private_data_files_atomic,
)
from src.schema import REQUIRED_INPUT_COLUMNS


OperatorSampleKind = Literal["current_input", "historical_input"]

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPERATOR_SAMPLE_DIR = REPO_ROOT / "runtime_storage" / "operator_samples"
OPERATOR_SAMPLE_DIR_ENV = "OPERATOR_SAMPLE_DIR"
GITHUB_OPERATOR_SAMPLE_REPO_ENV = "GITHUB_OPERATOR_SAMPLE_REPO"
GITHUB_OPERATOR_SAMPLE_TOKEN_ENV = "GITHUB_OPERATOR_SAMPLE_TOKEN"
GITHUB_OPERATOR_SAMPLE_BRANCH_ENV = "GITHUB_OPERATOR_SAMPLE_BRANCH"
GITHUB_OPERATOR_SAMPLE_PREFIX_ENV = "GITHUB_OPERATOR_SAMPLE_PREFIX"
GITHUB_OPERATOR_SAMPLE_TIMEOUT_ENV = "GITHUB_OPERATOR_SAMPLE_TIMEOUT_SECONDS"
METADATA_FILE_NAME = "metadata.json"
BACKUP_DIR_NAME = "backups"
BACKUP_KEEP_COUNT = 20
APP_TIMEZONE = "Asia/Seoul"
GITHUB_API_BASE_URL = "https://api.github.com"

KIND_TO_OPERATOR_FILE = {
    "current_input": "current_input_sample.csv",
    "historical_input": "historical_input_sample.csv",
}
KIND_TO_PACKAGED_FILE = {
    "current_input": REPO_ROOT / "data" / "sample" / "input_sample.csv",
    "historical_input": REPO_ROOT / "data" / "sample" / "historical_input_sample.csv",
}
TARGET_DAILY_COLUMNS = (
    "sales_target_daily",
    "recognized_target_daily",
)
ACTUAL_CUM_COLUMNS = (
    "sales_actual_cum",
    "recognized_actual_cum",
)
TRUE_TOKENS = {"Y", "YES", "TRUE", "1"}
FALSE_TOKENS = {"N", "NO", "FALSE", "0", ""}

PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:0\d{1,2}[-.\s]?)?\d{3,4}[-.\s]?\d{4}")
RESIDENT_ID_PATTERN = re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b")
CONTRACT_PATTERN = re.compile(r"\b(?:contract|ctr|cntr|계약)[-_\s]?[A-Z0-9]{4,}\b", re.IGNORECASE)
ADDRESS_PATTERN = re.compile(r"(?:시|군|구|동|로|길)\s*\d{1,4}(?:-\d{1,4})?")
PERSON_NAME_PATTERN = re.compile(r"(?:고객명|성명|이름)\s*[:=]\s*\S+")
SENSITIVE_PATTERNS = (
    ("phone_like", PHONE_PATTERN),
    ("resident_id_like", RESIDENT_ID_PATTERN),
    ("contract_like", CONTRACT_PATTERN),
    ("address_like", ADDRESS_PATTERN),
    ("name_like", PERSON_NAME_PATTERN),
)


def get_operator_sample_dir() -> Path:
    """Return the operator sample directory."""
    configured = os.environ.get(OPERATOR_SAMPLE_DIR_ENV, "").strip()
    if not configured:
        return DEFAULT_OPERATOR_SAMPLE_DIR

    configured_path = Path(configured).expanduser()
    if configured_path.is_absolute():
        return configured_path
    return REPO_ROOT / configured_path


def get_operator_sample_path(kind: str) -> Path:
    """Return the operator-managed CSV path for a sample kind."""
    normalized_kind = _validate_kind(kind)
    return get_operator_sample_dir() / KIND_TO_OPERATOR_FILE[normalized_kind]


def get_operator_sample_location(kind: str) -> str:
    """Return the active operator sample location for UI display."""
    normalized_kind = _validate_kind(kind)
    config = _github_store_config()
    if config["error"]:
        raise PrivateDataStoreConfigurationError(str(config["error"]))
    if config["enabled"]:
        return _github_display_path(config, _github_operator_file_path(normalized_kind, config))
    return str(get_operator_sample_path(normalized_kind))


def get_packaged_sample_path(kind: str) -> Path:
    """Return the packaged fallback CSV path for a sample kind."""
    normalized_kind = _validate_kind(kind)
    return KIND_TO_PACKAGED_FILE[normalized_kind]


def load_sample_with_source(kind: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load an operator sample first, falling back to the packaged sample."""
    normalized_kind = _validate_kind(kind)
    operator_path = get_operator_sample_path(normalized_kind)
    packaged_path = get_packaged_sample_path(normalized_kind)
    fallback_warnings: list[str] = []
    github_config = _github_store_config()
    if github_config["error"]:
        raise PrivateDataStoreConfigurationError(str(github_config["error"]))
    metadata = read_operator_metadata()

    if github_config["enabled"]:
        github_path = _github_operator_file_path(normalized_kind, github_config)
        github_file = _github_get_file(github_path, github_config)
        if github_file is None:
            raise PrivateDataStoreUnavailableError(
                f"required private operator sample is missing: {KIND_TO_OPERATOR_FILE[normalized_kind]}"
            )
        github_df = _load_sample_bytes(normalized_kind, github_file["content"])
        errors = validate_operator_sample(normalized_kind, github_df)
        if errors:
            raise PrivateDataStoreUnavailableError(
                "private operator sample failed validation: " + "; ".join(errors)
            )
        return github_df, {
            "kind": normalized_kind,
            "source": "github",
            "path": _github_display_path(github_config, github_path),
            "metadata": dict(metadata.get(normalized_kind) or {}),
            "warnings": [],
        }

    if operator_path.is_file():
        try:
            operator_df = _load_sample_path(normalized_kind, operator_path)
            errors = validate_operator_sample(normalized_kind, operator_df)
            if errors:
                fallback_warnings.extend(
                    f"operator sample validation failed: {message}" for message in errors
                )
            else:
                return operator_df, {
                    "kind": normalized_kind,
                    "source": "operator",
                    "path": str(operator_path),
                    "metadata": dict(metadata.get(normalized_kind) or {}),
                    "warnings": [],
                }
        except Exception as exc:  # noqa: BLE001 - keep app startup recoverable.
            fallback_warnings.append(f"operator sample load failed: {exc}")

    packaged_df = _load_sample_path(normalized_kind, packaged_path)
    return packaged_df, {
        "kind": normalized_kind,
        "source": "packaged",
        "path": str(packaged_path),
        "metadata": dict(metadata.get(normalized_kind) or {}),
        "warnings": fallback_warnings,
    }


def save_operator_sample(
    kind: str,
    df: pd.DataFrame,
    *,
    related_private_files: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Validate and persist an operator sample with backup and metadata."""
    normalized_kind = _validate_kind(kind)
    cleaned = _prepare_operator_sample(df)
    errors = _validate_prepared_sample(normalized_kind, cleaned)
    warnings = detect_sensitive_data_warnings(cleaned)
    warnings.extend(_date_order_warnings(cleaned))
    if errors:
        github_config = _github_store_config()
        error_path = (
            _github_display_path(
                github_config,
                _github_operator_file_path(normalized_kind, github_config),
            )
            if github_config["enabled"]
            else str(get_operator_sample_path(normalized_kind))
        )
        return {
            "ok": False,
            "kind": normalized_kind,
            "errors": errors,
            "warnings": warnings,
            "path": error_path,
        }

    github_config = _github_store_config()
    if github_config["error"]:
        raise PrivateDataStoreConfigurationError(str(github_config["error"]))
    if github_config["enabled"]:
        return _save_github_operator_sample(
            normalized_kind,
            cleaned,
            warnings,
            github_config,
            related_private_files=related_private_files,
        )

    storage_dir = get_operator_sample_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    target_path = get_operator_sample_path(normalized_kind)
    backup_path = create_backup_if_exists(normalized_kind)

    saved_df = _normalize_for_storage(cleaned)
    staging_path = target_path.with_name(f".{target_path.name}.{_timestamp_token()}.tmp")
    saved_df.to_csv(staging_path, index=False, encoding="utf-8-sig")
    staging_path.replace(target_path)

    metadata = read_operator_metadata()
    previous = dict(metadata.get(normalized_kind) or {})
    version = int(previous.get("version") or 0) + 1
    entry: dict[str, Any] = {
        "saved_at": _now_iso(),
        "rows": int(len(saved_df)),
        "source": "app_editor",
        "version": version,
    }
    if normalized_kind == "historical_input":
        entry["months"] = _month_labels(saved_df)
    metadata[normalized_kind] = entry
    write_operator_metadata(metadata)

    return {
        "ok": True,
        "kind": normalized_kind,
        "path": str(target_path),
        "backup_path": str(backup_path) if backup_path is not None else None,
        "metadata": entry,
        "rows": int(len(saved_df)),
        "warnings": warnings,
        "df": saved_df,
    }


def validate_operator_sample(kind: str, df: pd.DataFrame) -> list[str]:
    """Return blocking validation errors for an operator sample."""
    normalized_kind = _validate_kind(kind)
    cleaned = _prepare_operator_sample(df)
    return _validate_prepared_sample(normalized_kind, cleaned)


def reset_operator_sample(kind: str) -> dict[str, Any]:
    """Remove an operator sample so the packaged sample becomes the default."""
    normalized_kind = _validate_kind(kind)
    github_config = _github_store_config()
    if github_config["error"]:
        raise PrivateDataStoreConfigurationError(str(github_config["error"]))
    if github_config["enabled"]:
        raise PrivateDataStoreConfigurationError(
            "remote operator samples cannot fall back to packaged data; save a replacement instead"
        )
    target_path = get_operator_sample_path(normalized_kind)
    backup_path = create_backup_if_exists(normalized_kind)
    if target_path.exists():
        target_path.unlink()

    metadata = read_operator_metadata()
    previous = dict(metadata.get(normalized_kind) or {})
    version = int(previous.get("version") or 0) + 1
    metadata[normalized_kind] = {
        "reset_at": _now_iso(),
        "source": "packaged_reset",
        "version": version,
    }
    write_operator_metadata(metadata)
    return {
        "ok": True,
        "kind": normalized_kind,
        "path": str(target_path),
        "backup_path": str(backup_path) if backup_path is not None else None,
    }


def create_backup_if_exists(kind: str) -> Path | None:
    """Create a timestamped backup for the current operator sample when present."""
    normalized_kind = _validate_kind(kind)
    source_path = get_operator_sample_path(normalized_kind)
    if not source_path.is_file():
        return None

    backup_dir = get_operator_sample_dir() / BACKUP_DIR_NAME
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{source_path.stem}_{_timestamp_token()}{source_path.suffix}"
    shutil.copy2(source_path, backup_path)
    _prune_backups(normalized_kind, backup_dir)
    return backup_path


def read_operator_metadata() -> dict[str, Any]:
    """Read operator sample metadata, returning an empty mapping when absent."""
    github_config = _github_store_config()
    if github_config["error"]:
        raise PrivateDataStoreConfigurationError(str(github_config["error"]))
    if github_config["enabled"]:
        return _read_github_metadata(github_config)

    metadata_path = get_operator_sample_dir() / METADATA_FILE_NAME
    if not metadata_path.is_file():
        return {}
    try:
        return _loads_json_object(metadata_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_operator_metadata(metadata: dict[str, Any]) -> None:
    """Persist operator sample metadata atomically."""
    github_config = _github_store_config()
    if github_config["error"]:
        raise PrivateDataStoreConfigurationError(str(github_config["error"]))
    if github_config["enabled"]:
        _write_github_metadata(metadata, github_config)
        return

    storage_dir = get_operator_sample_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = storage_dir / METADATA_FILE_NAME
    staging_path = metadata_path.with_name(f".{metadata_path.name}.{_timestamp_token()}.tmp")
    staging_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    staging_path.replace(metadata_path)


def detect_sensitive_data_warnings(df: pd.DataFrame) -> list[str]:
    """Return warning messages for values that look like real operator data."""
    cleaned = _prepare_operator_sample(df)
    warnings: list[str] = []
    for column in cleaned.columns:
        if pd.api.types.is_numeric_dtype(cleaned[column]):
            continue
        values = cleaned[column].dropna().astype(str)
        if values.empty:
            continue
        for pattern_name, pattern in SENSITIVE_PATTERNS:
            match_count = int(values.map(lambda value: bool(pattern.search(value))).sum())
            if match_count:
                warnings.append(
                    f"{column}: {pattern_name} pattern detected in {match_count} row(s)."
                )
    return warnings


def _github_store_config() -> dict[str, Any]:
    config = get_private_data_store_config()
    return {
        "enabled": config.enabled,
        "configured": config.configured,
        "error": config.error,
        "repo": config.repo,
        "token": config.token,
        "branch": config.branch,
        "prefix": config.prefix,
        "timeout": config.timeout,
    }


def _config_value(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value.strip()
    try:
        import streamlit as st_module  # type: ignore

        raw_value = st_module.secrets.get(name, "")
    except Exception:
        return ""
    return str(raw_value).strip()


def _github_operator_file_path(kind: OperatorSampleKind, config: dict[str, Any]) -> str:
    file_name = KIND_TO_OPERATOR_FILE[kind]
    prefix = str(config.get("prefix") or "").strip("/")
    return f"{prefix}/{file_name}" if prefix else file_name


def _github_metadata_file_path(config: dict[str, Any]) -> str:
    prefix = str(config.get("prefix") or "").strip("/")
    return f"{prefix}/{METADATA_FILE_NAME}" if prefix else METADATA_FILE_NAME


def _github_display_path(config: dict[str, Any], path: str) -> str:
    return f"github://{config['repo']}@{config['branch']}/{path}"


def _load_sample_bytes(kind: OperatorSampleKind, csv_bytes: bytes) -> pd.DataFrame:
    temp_path: Path | None = None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as handle:
        handle.write(csv_bytes)
        temp_path = Path(handle.name)
    try:
        return _load_sample_path(kind, temp_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _read_github_metadata(config: dict[str, Any]) -> dict[str, Any]:
    github_file = _github_get_file(_github_metadata_file_path(config), config)
    if github_file is None:
        return {}
    try:
        return _loads_json_object(github_file["content"].decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PrivateDataStoreUnavailableError(
            "private operator metadata could not be decoded"
        ) from exc


def _loads_json_object(text: str) -> dict[str, Any]:
    payload = json.loads(text.lstrip("\ufeff \t\r\n"))
    return payload if isinstance(payload, dict) else {}


def _write_github_metadata(metadata: dict[str, Any], config: dict[str, Any]) -> None:
    payload = json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")
    _github_put_file(
        _github_metadata_file_path(config),
        payload + b"\n",
        "Update operator sample metadata",
        config,
    )


def _save_github_operator_sample(
    kind: OperatorSampleKind,
    cleaned: pd.DataFrame,
    warnings: list[str],
    config: dict[str, Any],
    *,
    related_private_files: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    saved_df = _normalize_for_storage(cleaned)
    metadata = _read_github_metadata(config)
    previous = dict(metadata.get(kind) or {})
    version = int(previous.get("version") or 0) + 1
    entry: dict[str, Any] = {
        "saved_at": _now_iso(),
        "rows": int(len(saved_df)),
        "source": "github_app_editor",
        "version": version,
        "repo": config["repo"],
        "branch": config["branch"],
    }
    if kind == "historical_input":
        entry["months"] = _month_labels(saved_df)

    csv_bytes = saved_df.to_csv(index=False).encode("utf-8-sig")
    metadata[kind] = entry
    files: dict[str, bytes] = {
        KIND_TO_OPERATOR_FILE[kind]: csv_bytes,
        METADATA_FILE_NAME: (
            json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        ),
    }
    for related_path, related_content in (related_private_files or {}).items():
        normalized_related_path = str(related_path).replace("\\", "/").strip("/")
        if normalized_related_path in files:
            raise ValueError(f"duplicate private data path: {normalized_related_path}")
        files[normalized_related_path] = bytes(related_content)
    commit_result = write_private_data_files_atomic(
        files,
        f"Update {kind} operator data",
    )
    csv_path = _github_operator_file_path(kind, config)
    return {
        "ok": True,
        "kind": kind,
        "path": _github_display_path(config, csv_path),
        "backup_path": None,
        "metadata": entry,
        "rows": int(len(saved_df)),
        "warnings": warnings,
        "df": saved_df,
        "github_commit_sha": (commit_result.get("commit") or {}).get("sha"),
    }


def _github_get_file(path: str, config: dict[str, Any]) -> dict[str, Any] | None:
    api_path = _github_contents_api_path(config, path)
    query = urllib.parse.urlencode({"ref": str(config["branch"])})
    payload = _github_api_request("GET", f"{api_path}?{query}", config)
    if payload is None:
        return None
    content_text = str(payload.get("content") or "")
    content = base64.b64decode(content_text.encode("ascii"), validate=False)
    return {
        "content": content,
        "sha": str(payload.get("sha") or ""),
        "html_url": str(payload.get("html_url") or ""),
    }


def _github_put_file(
    path: str,
    content: bytes,
    message: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    existing = _github_get_file(path, config)
    body: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": config["branch"],
    }
    if existing and existing.get("sha"):
        body["sha"] = existing["sha"]
    payload = _github_api_request("PUT", _github_contents_api_path(config, path), config, body)
    return payload if isinstance(payload, dict) else {}


def _github_contents_api_path(config: dict[str, Any], path: str) -> str:
    encoded_path = urllib.parse.quote(path, safe="/")
    return f"/repos/{config['repo']}/contents/{encoded_path}"


def _github_api_request(
    method: str,
    api_path: str,
    config: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    url = f"{GITHUB_API_BASE_URL}{api_path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {config['token']}",
            "Content-Type": "application/json",
            "User-Agent": "sales-closing-forecast",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=int(config["timeout"])) as response:
            response_body = response.read()
    except urllib.error.HTTPError as exc:
        if method == "GET" and exc.code == 404:
            return None
        if exc.code in {409, 422}:
            raise PrivateDataStoreConflictError(
                "private data changed before this operation completed; reload and retry"
            ) from exc
        raise PrivateDataStoreUnavailableError(
            f"private data store access failed with HTTP {exc.code}"
        ) from exc
    except urllib.error.URLError as exc:
        raise PrivateDataStoreUnavailableError(
            "private data store network request failed"
        ) from exc

    if not response_body:
        return {}
    decoded = json.loads(response_body.decode("utf-8"))
    return decoded if isinstance(decoded, dict) else {}


def _validate_kind(kind: str) -> OperatorSampleKind:
    if kind not in KIND_TO_OPERATOR_FILE:
        supported = ", ".join(sorted(KIND_TO_OPERATOR_FILE))
        raise ValueError(f"Unsupported operator sample kind: {kind}. Supported: {supported}.")
    return kind  # type: ignore[return-value]


def _load_sample_path(kind: OperatorSampleKind, path: Path) -> pd.DataFrame:
    if kind == "historical_input":
        return load_input(path, sort_by="date", strict_business_day_no=False)
    return load_input(path)


def _prepare_operator_sample(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = _drop_empty_unnamed_columns(cleaned)
    if cleaned.empty:
        return cleaned
    blank_checked = cleaned.replace(r"^\s*$", pd.NA, regex=True)
    fully_blank = blank_checked.isna().all(axis=1)
    return cleaned.loc[~fully_blank].reset_index(drop=True)


def _drop_empty_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    removable = []
    for column in df.columns:
        column_name = str(column)
        if not column_name.startswith("Unnamed:"):
            continue
        values = df[column].replace(r"^\s*$", pd.NA, regex=True)
        if values.isna().all():
            removable.append(column)
    if not removable:
        return df.copy()
    return df.drop(columns=removable).copy()


def _validate_prepared_sample(kind: OperatorSampleKind, df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    errors.extend(_required_column_errors(df))
    if errors:
        return errors
    if df.empty:
        return ["operator sample must contain at least one valid row."]

    parsed_dates = _parsed_dates(df)
    if parsed_dates.isna().any():
        errors.append("date must be parseable for every valid row.")

    business_day_no = _business_day_numbers(df)
    if business_day_no.isna().any():
        errors.append("business_day_no must be numeric for every valid row.")
    elif _has_fractional_values(business_day_no):
        errors.append("business_day_no must contain whole-number values.")

    close_errors = _validate_close_day_values(df["is_close_day"])
    errors.extend(close_errors)
    errors.extend(_target_column_errors(df))
    errors.extend(_actual_column_errors(df, require_all_values=(kind == "historical_input")))

    if not errors:
        if kind == "current_input":
            errors.extend(_current_input_errors(df, parsed_dates, business_day_no))
        else:
            errors.extend(_historical_input_errors(df, parsed_dates, business_day_no))
    return errors


def _required_column_errors(df: pd.DataFrame) -> list[str]:
    missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if not missing:
        return []
    return [f"missing required columns: {', '.join(missing)}"]


def _parsed_dates(df: pd.DataFrame) -> pd.Series:
    raw_dates = df["date"].replace(r"^\s*$", pd.NA, regex=True)
    return pd.to_datetime(raw_dates, errors="coerce")


def _business_day_numbers(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(
        df["business_day_no"].replace(r"^\s*$", pd.NA, regex=True),
        errors="coerce",
    )


def _target_column_errors(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    for column in TARGET_DAILY_COLUMNS:
        values = pd.to_numeric(
            df[column].replace(r"^\s*$", pd.NA, regex=True),
            errors="coerce",
        )
        if values.isna().any():
            errors.append(f"{column} must be numeric for every valid row.")
        elif (values < 0).any():
            errors.append(f"{column} must not be negative.")
    return errors


def _actual_column_errors(df: pd.DataFrame, *, require_all_values: bool) -> list[str]:
    errors: list[str] = []
    for column in ACTUAL_CUM_COLUMNS:
        raw_values = df[column].replace(r"^\s*$", pd.NA, regex=True)
        values = pd.to_numeric(raw_values, errors="coerce")
        invalid = raw_values.notna() & values.isna()
        if invalid.any():
            errors.append(f"{column} must be numeric when populated.")
        if require_all_values and raw_values.isna().any():
            errors.append(f"{column} is required for every historical row.")
    return errors


def _validate_close_day_values(values: pd.Series) -> list[str]:
    invalid_values = []
    for value in values:
        try:
            _to_bool(value)
        except ValueError:
            invalid_values.append(value)
    if not invalid_values:
        return []
    return [f"is_close_day contains unsupported values: {_display_values(invalid_values)}"]


def _current_input_errors(
    df: pd.DataFrame,
    parsed_dates: pd.Series,
    business_day_no: pd.Series,
) -> list[str]:
    errors: list[str] = []
    if business_day_no.duplicated().any():
        errors.append("current_input business_day_no values must be unique.")
    if not parsed_dates.isna().any():
        months = parsed_dates.dt.to_period("M").astype(str).unique()
        if len(months) > 1:
            errors.append("current_input must describe one target month.")
    return errors


def _historical_input_errors(
    df: pd.DataFrame,
    parsed_dates: pd.Series,
    business_day_no: pd.Series,
) -> list[str]:
    if parsed_dates.isna().any() or business_day_no.isna().any():
        return []

    errors: list[str] = []
    check_df = pd.DataFrame(
        {
            "month": parsed_dates.dt.to_period("M").astype(str),
            "date": parsed_dates,
            "business_day_no": business_day_no.astype(int),
        }
    )
    for month, month_df in check_df.groupby("month", sort=False):
        if month_df["business_day_no"].duplicated().any():
            errors.append(f"historical_input business_day_no values must be unique within {month}.")
        if not month_df["date"].is_monotonic_increasing:
            errors.append(f"historical_input dates must be ascending within {month}.")
    return errors


def _normalize_for_storage(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized["date"] = _parsed_dates(normalized).dt.strftime("%Y-%m-%d")
    normalized["business_day_no"] = _business_day_numbers(normalized).astype(int)
    normalized["is_close_day"] = normalized["is_close_day"].map(_to_bool)
    for column in TARGET_DAILY_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="raise").astype(float)
    for column in ACTUAL_CUM_COLUMNS:
        raw_values = normalized[column].replace(r"^\s*$", pd.NA, regex=True)
        normalized[column] = pd.to_numeric(raw_values, errors="coerce").astype(float)

    ordered_columns = [
        *REQUIRED_INPUT_COLUMNS,
        *[column for column in normalized.columns if column not in REQUIRED_INPUT_COLUMNS],
    ]
    return normalized.loc[:, ordered_columns].reset_index(drop=True)


def _date_order_warnings(df: pd.DataFrame) -> list[str]:
    if "date" not in df.columns or df.empty:
        return []
    parsed_dates = _parsed_dates(df)
    if parsed_dates.isna().any() or parsed_dates.is_monotonic_increasing:
        return []
    return ["date is not ascending; rows were saved without creating or filling dates."]


def _to_bool(value: object) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().upper()
        if token in TRUE_TOKENS:
            return True
        if token in FALSE_TOKENS:
            return False
    if isinstance(value, Real) and value in (0, 1):
        return bool(value)
    raise ValueError(f"unsupported boolean value: {value!r}")


def _month_labels(df: pd.DataFrame) -> list[str]:
    if df.empty or "date" not in df.columns:
        return []
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    labels = dates.dt.to_period("M").astype(str).tolist()
    result: list[str] = []
    for label in labels:
        if label not in result:
            result.append(label)
    return result


def _prune_backups(kind: OperatorSampleKind, backup_dir: Path) -> None:
    stem = Path(KIND_TO_OPERATOR_FILE[kind]).stem
    backups = sorted(
        backup_dir.glob(f"{stem}_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old_backup in backups[BACKUP_KEEP_COUNT:]:
        old_backup.unlink()


def _has_fractional_values(values: pd.Series) -> bool:
    valid_values = values.dropna()
    if valid_values.empty:
        return False
    return bool((valid_values % 1 != 0).any())


def _display_values(values: list[object]) -> str:
    unique_values: list[str] = []
    for value in values:
        text = repr(value)
        if text not in unique_values:
            unique_values.append(text)
    return ", ".join(unique_values[:5])


def _now_iso() -> str:
    return datetime.now(ZoneInfo(APP_TIMEZONE)).isoformat(timespec="seconds")


def _timestamp_token() -> str:
    return datetime.now(ZoneInfo(APP_TIMEZONE)).strftime("%Y%m%d_%H%M%S_%f")
