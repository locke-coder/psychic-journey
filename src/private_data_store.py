"""Private GitHub repository storage for durable application data.

The deployed app uses a dedicated private repository as its durable data plane.
Local filesystem access remains available only when no private repository is
configured, which keeps explicit-path unit tests and local development usable.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


PRIVATE_DATA_REPO_ENV = "PRIVATE_DATA_REPO"
PRIVATE_DATA_TOKEN_ENV = "PRIVATE_DATA_TOKEN"
PRIVATE_DATA_BRANCH_ENV = "PRIVATE_DATA_BRANCH"
PRIVATE_DATA_PREFIX_ENV = "PRIVATE_DATA_PREFIX"
PRIVATE_DATA_TIMEOUT_ENV = "PRIVATE_DATA_TIMEOUT_SECONDS"
PRIVATE_DATA_MODE_ENV = "PRIVATE_DATA_MODE"

# Backward-compatible aliases already configured in the deployed app.
LEGACY_REPO_ENV = "GITHUB_OPERATOR_SAMPLE_REPO"
LEGACY_TOKEN_ENV = "GITHUB_OPERATOR_SAMPLE_TOKEN"
LEGACY_BRANCH_ENV = "GITHUB_OPERATOR_SAMPLE_BRANCH"
LEGACY_PREFIX_ENV = "GITHUB_OPERATOR_SAMPLE_PREFIX"
LEGACY_TIMEOUT_ENV = "GITHUB_OPERATOR_SAMPLE_TIMEOUT_SECONDS"

DEFAULT_BRANCH = "main"
DEFAULT_PREFIX = "operator_samples"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_DATA_MODE = "private"
PRIVATE_DATA_MODE = "private"
LOCAL_DEMO_DATA_MODE = "local_demo"
GITHUB_API_BASE_URL = "https://api.github.com"
_REPO_PATTERN = re.compile(r"[\w.-]+/[\w.-]+")
_AUTO_SHA = object()


class PrivateDataStoreError(RuntimeError):
    """Base error for private data store operations."""


class PrivateDataStoreConfigurationError(PrivateDataStoreError):
    """Raised when a partially configured private store would be unsafe."""


class PrivateDataStoreUnavailableError(PrivateDataStoreError):
    """Raised when the configured private store cannot be reached."""


class PrivateDataStoreConflictError(PrivateDataStoreError):
    """Raised when another writer changed a file before this write."""


@dataclass(frozen=True)
class PrivateDataStoreConfig:
    repo: str
    token: str
    branch: str
    prefix: str
    timeout: int
    configured: bool
    enabled: bool
    error: str = ""

    def redacted(self) -> dict[str, object]:
        """Return safe diagnostics without exposing the credential."""
        return {
            "repo": self.repo,
            "branch": self.branch,
            "prefix": self.prefix,
            "timeout": self.timeout,
            "configured": self.configured,
            "enabled": self.enabled,
            "error": self.error,
        }


@dataclass(frozen=True)
class PrivateDataFile:
    path: str
    content: bytes
    sha: str
    size: int


@dataclass(frozen=True)
class PrivateDataEntry:
    name: str
    path: str
    sha: str
    size: int
    type: str


def get_private_data_store_config() -> PrivateDataStoreConfig:
    """Resolve generic settings first and deployed legacy aliases second."""
    repo = _first_config_value(PRIVATE_DATA_REPO_ENV, LEGACY_REPO_ENV)
    token = _first_config_value(PRIVATE_DATA_TOKEN_ENV, LEGACY_TOKEN_ENV)
    branch = (
        _first_config_value(PRIVATE_DATA_BRANCH_ENV, LEGACY_BRANCH_ENV)
        or DEFAULT_BRANCH
    )
    prefix = (
        _first_config_value(PRIVATE_DATA_PREFIX_ENV, LEGACY_PREFIX_ENV)
        or DEFAULT_PREFIX
    ).strip("/")
    timeout_raw = _first_config_value(PRIVATE_DATA_TIMEOUT_ENV, LEGACY_TIMEOUT_ENV)
    try:
        timeout = max(1, int(timeout_raw)) if timeout_raw else DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        timeout = DEFAULT_TIMEOUT_SECONDS

    configured = bool(repo or token)
    error = ""
    if configured and not repo:
        error = "private data repository is missing"
    elif configured and not token:
        error = "private data token is missing"
    elif repo and not _REPO_PATTERN.fullmatch(repo):
        error = "private data repository must use owner/name format"
    elif not branch.strip():
        error = "private data branch is missing"

    return PrivateDataStoreConfig(
        repo=repo,
        token=token,
        branch=branch.strip() or DEFAULT_BRANCH,
        prefix=prefix,
        timeout=timeout,
        configured=configured,
        enabled=bool(configured and not error),
        error=error,
    )


def is_private_data_store_enabled() -> bool:
    """Return True for a valid remote store and fail closed for partial config."""
    config = get_private_data_store_config()
    if config.error:
        raise PrivateDataStoreConfigurationError(config.error)
    return config.enabled


def private_data_store_status() -> dict[str, object]:
    """Return redacted configuration status for UI and diagnostics."""
    status = get_private_data_store_config().redacted()
    status["mode"] = get_private_data_mode()
    return status


def get_private_data_mode() -> str:
    """Return the explicit app data mode, defaulting to fail-closed private."""
    mode = (_config_value(PRIVATE_DATA_MODE_ENV) or DEFAULT_DATA_MODE).lower()
    if mode not in {PRIVATE_DATA_MODE, LOCAL_DEMO_DATA_MODE}:
        raise PrivateDataStoreConfigurationError(
            "PRIVATE_DATA_MODE must be 'private' or 'local_demo'"
        )
    return mode


def require_private_data_store() -> bool:
    """Require remote storage unless an explicit local demo mode was selected."""
    if get_private_data_mode() == LOCAL_DEMO_DATA_MODE:
        return False
    config = get_private_data_store_config()
    if config.error:
        raise PrivateDataStoreConfigurationError(config.error)
    if not config.enabled:
        raise PrivateDataStoreConfigurationError(
            "private data store is required but not configured"
        )
    return True


def private_data_display_path(path: str) -> str:
    """Return a credential-free display path for a logical data file."""
    config = _require_config()
    full_path = _full_path(path, config)
    return f"github://{config.repo}@{config.branch}/{full_path}"


def read_private_data_file(
    path: str,
    *,
    required: bool = False,
) -> PrivateDataFile | None:
    """Read one file from the configured private repository."""
    config = _require_config()
    full_path = _full_path(path, config)
    api_path = _contents_api_path(config, full_path)
    query = urllib.parse.urlencode({"ref": config.branch})
    payload = _api_request("GET", f"{api_path}?{query}", config)
    if payload is None:
        if required:
            raise PrivateDataStoreUnavailableError(
                f"required private data file is missing: {path}"
            )
        return None
    if not isinstance(payload, Mapping):
        raise PrivateDataStoreUnavailableError(
            f"private data path is not a file: {path}"
        )
    try:
        encoded = str(payload.get("content") or "").encode("ascii")
        content = base64.b64decode(encoded, validate=False)
    except (UnicodeEncodeError, ValueError) as exc:
        raise PrivateDataStoreUnavailableError(
            f"private data file could not be decoded: {path}"
        ) from exc
    return PrivateDataFile(
        path=path,
        content=content,
        sha=str(payload.get("sha") or ""),
        size=int(payload.get("size") or len(content)),
    )


def write_private_data_file(
    path: str,
    content: bytes,
    message: str,
    *,
    expected_sha: str | None | object = _AUTO_SHA,
) -> dict[str, Any]:
    """Create or replace one file with optimistic concurrency protection."""
    config = _require_config()
    normalized_path = _normalize_relative_path(path)
    if expected_sha is _AUTO_SHA:
        existing = read_private_data_file(normalized_path)
        resolved_sha: str | None = existing.sha if existing is not None else None
    else:
        resolved_sha = str(expected_sha) if expected_sha else None

    body: dict[str, Any] = {
        "message": str(message),
        "content": base64.b64encode(bytes(content)).decode("ascii"),
        "branch": config.branch,
    }
    if resolved_sha:
        body["sha"] = resolved_sha
    payload = _api_request(
        "PUT",
        _contents_api_path(config, _full_path(normalized_path, config)),
        config,
        body,
    )
    if not isinstance(payload, Mapping):
        return {}
    return dict(payload)


def write_private_data_files_atomic(
    files: Mapping[str, bytes],
    message: str,
) -> dict[str, Any]:
    """Publish multiple files in one commit with a non-forced ref update.

    The branch head is captured before blobs are created. If another writer
    advances the branch first, GitHub rejects the final non-fast-forward ref
    update and the caller receives ``PrivateDataStoreConflictError``. Orphaned
    blobs/trees are harmless because the branch never points to them.
    """
    config = _require_config()
    normalized_files = {
        _normalize_relative_path(path): bytes(content)
        for path, content in files.items()
    }
    if not normalized_files:
        raise ValueError("at least one private data file is required")

    encoded_branch = urllib.parse.quote(config.branch, safe="/")
    ref_payload = _api_request(
        "GET",
        f"/repos/{config.repo}/git/ref/heads/{encoded_branch}",
        config,
    )
    if not isinstance(ref_payload, Mapping):
        raise PrivateDataStoreUnavailableError(
            f"private data branch is missing: {config.branch}"
        )
    object_payload = ref_payload.get("object")
    if not isinstance(object_payload, Mapping):
        raise PrivateDataStoreUnavailableError("private data branch head is invalid")
    head_sha = str(object_payload.get("sha") or "")
    if not head_sha:
        raise PrivateDataStoreUnavailableError("private data branch head is missing")

    commit_payload = _api_request(
        "GET",
        f"/repos/{config.repo}/git/commits/{head_sha}",
        config,
    )
    if not isinstance(commit_payload, Mapping):
        raise PrivateDataStoreUnavailableError("private data commit could not be read")
    tree_payload = commit_payload.get("tree")
    if not isinstance(tree_payload, Mapping):
        raise PrivateDataStoreUnavailableError("private data base tree is missing")
    base_tree_sha = str(tree_payload.get("sha") or "")
    if not base_tree_sha:
        raise PrivateDataStoreUnavailableError("private data base tree is invalid")

    tree_entries: list[dict[str, str]] = []
    for path, content in sorted(normalized_files.items()):
        blob_payload = _api_request(
            "POST",
            f"/repos/{config.repo}/git/blobs",
            config,
            {
                "content": base64.b64encode(content).decode("ascii"),
                "encoding": "base64",
            },
        )
        if not isinstance(blob_payload, Mapping) or not blob_payload.get("sha"):
            raise PrivateDataStoreUnavailableError(
                f"private data blob could not be created: {path}"
            )
        tree_entries.append(
            {
                "path": _full_path(path, config),
                "mode": "100644",
                "type": "blob",
                "sha": str(blob_payload["sha"]),
            }
        )

    new_tree_payload = _api_request(
        "POST",
        f"/repos/{config.repo}/git/trees",
        config,
        {"base_tree": base_tree_sha, "tree": tree_entries},
    )
    if not isinstance(new_tree_payload, Mapping) or not new_tree_payload.get("sha"):
        raise PrivateDataStoreUnavailableError("private data tree could not be created")
    new_commit_payload = _api_request(
        "POST",
        f"/repos/{config.repo}/git/commits",
        config,
        {
            "message": str(message),
            "tree": str(new_tree_payload["sha"]),
            "parents": [head_sha],
        },
    )
    if not isinstance(new_commit_payload, Mapping) or not new_commit_payload.get("sha"):
        raise PrivateDataStoreUnavailableError("private data commit could not be created")
    new_commit_sha = str(new_commit_payload["sha"])
    _api_request(
        "PATCH",
        f"/repos/{config.repo}/git/refs/heads/{encoded_branch}",
        config,
        {"sha": new_commit_sha, "force": False},
    )
    return {
        "commit": {"sha": new_commit_sha},
        "parent_sha": head_sha,
        "paths": sorted(normalized_files),
    }


def delete_private_data_file(
    path: str,
    message: str,
    *,
    expected_sha: str | None | object = _AUTO_SHA,
) -> bool:
    """Delete one private data file, returning False when it is absent."""
    config = _require_config()
    normalized_path = _normalize_relative_path(path)
    if expected_sha is _AUTO_SHA:
        existing = read_private_data_file(normalized_path)
        if existing is None:
            return False
        resolved_sha = existing.sha
    else:
        resolved_sha = str(expected_sha) if expected_sha else ""
    if not resolved_sha:
        return False
    _api_request(
        "DELETE",
        _contents_api_path(config, _full_path(normalized_path, config)),
        config,
        {
            "message": str(message),
            "sha": resolved_sha,
            "branch": config.branch,
        },
    )
    return True


def list_private_data_files(path: str) -> list[PrivateDataEntry]:
    """List direct children of a private data directory without reading content."""
    config = _require_config()
    normalized_path = _normalize_relative_path(path)
    full_path = _full_path(normalized_path, config)
    query = urllib.parse.urlencode({"ref": config.branch})
    payload = _api_request(
        "GET",
        f"{_contents_api_path(config, full_path)}?{query}",
        config,
    )
    if payload is None:
        return []
    items = payload if isinstance(payload, list) else [payload]
    entries: list[PrivateDataEntry] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        item_full_path = str(item.get("path") or "")
        item_relative_path = _strip_prefix(item_full_path, config.prefix)
        entries.append(
            PrivateDataEntry(
                name=str(item.get("name") or ""),
                path=item_relative_path,
                sha=str(item.get("sha") or ""),
                size=int(item.get("size") or 0),
                type=str(item.get("type") or ""),
            )
        )
    return entries


def _require_config() -> PrivateDataStoreConfig:
    config = get_private_data_store_config()
    if config.error:
        raise PrivateDataStoreConfigurationError(config.error)
    if not config.enabled:
        raise PrivateDataStoreConfigurationError(
            "private data store is not configured"
        )
    return config


def _first_config_value(*names: str) -> str:
    for name in names:
        value = _config_value(name)
        if value:
            return value
    return ""


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


def _normalize_relative_path(path: str) -> str:
    text = str(path or "").replace("\\", "/").strip("/")
    parts = [part for part in text.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise ValueError(f"invalid private data path: {path}")
    return "/".join(parts)


def _full_path(path: str, config: PrivateDataStoreConfig) -> str:
    normalized = _normalize_relative_path(path)
    return f"{config.prefix}/{normalized}" if config.prefix else normalized


def _strip_prefix(path: str, prefix: str) -> str:
    normalized = str(path or "").strip("/")
    normalized_prefix = str(prefix or "").strip("/")
    if normalized_prefix and normalized.startswith(f"{normalized_prefix}/"):
        return normalized[len(normalized_prefix) + 1 :]
    return normalized


def _contents_api_path(config: PrivateDataStoreConfig, full_path: str) -> str:
    encoded_path = urllib.parse.quote(full_path, safe="/")
    return f"/repos/{config.repo}/contents/{encoded_path}"


def _api_request(
    method: str,
    api_path: str,
    config: PrivateDataStoreConfig,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    url = f"{GITHUB_API_BASE_URL}{api_path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
            "User-Agent": "sales-closing-forecast",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout) as response:
            response_body = response.read()
    except urllib.error.HTTPError as exc:
        if method == "GET" and exc.code == 404:
            return None
        if exc.code in {409, 422}:
            raise PrivateDataStoreConflictError(
                "private data changed before this operation completed; reload and retry"
            ) from exc
        if exc.code in {401, 403, 404}:
            raise PrivateDataStoreUnavailableError(
                f"private data store access failed with HTTP {exc.code}"
            ) from exc
        raise PrivateDataStoreUnavailableError(
            f"private data store request failed with HTTP {exc.code}"
        ) from exc
    except urllib.error.URLError as exc:
        raise PrivateDataStoreUnavailableError(
            "private data store network request failed"
        ) from exc

    if not response_body:
        return {}
    try:
        decoded = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PrivateDataStoreUnavailableError(
            "private data store returned an invalid response"
        ) from exc
    return decoded if isinstance(decoded, (dict, list)) else {}
