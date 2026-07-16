from __future__ import annotations

import base64
import io
import urllib.error
from typing import Any

import pytest

import src.private_data_store as private_store
from src.private_data_store import (
    PrivateDataFile,
    PrivateDataStoreConfig,
    PrivateDataStoreConflictError,
    PrivateDataStoreUnavailableError,
    get_private_data_store_config,
    read_private_data_file,
    write_private_data_file,
    write_private_data_files_atomic,
)


def _config() -> PrivateDataStoreConfig:
    return PrivateDataStoreConfig(
        repo="example/private-data",
        token="super-secret-token",
        branch="main",
        prefix="operator_samples",
        timeout=7,
        configured=True,
        enabled=True,
    )


def test_generic_config_takes_precedence_over_legacy_aliases(monkeypatch) -> None:
    values = {
        private_store.PRIVATE_DATA_REPO_ENV: "new-owner/new-data",
        private_store.PRIVATE_DATA_TOKEN_ENV: "new-token",
        private_store.PRIVATE_DATA_BRANCH_ENV: "data-main",
        private_store.PRIVATE_DATA_PREFIX_ENV: "durable",
        private_store.PRIVATE_DATA_TIMEOUT_ENV: "17",
        private_store.LEGACY_REPO_ENV: "old-owner/old-data",
        private_store.LEGACY_TOKEN_ENV: "old-token",
        private_store.LEGACY_BRANCH_ENV: "legacy-main",
        private_store.LEGACY_PREFIX_ENV: "legacy-prefix",
        private_store.LEGACY_TIMEOUT_ENV: "3",
    }
    monkeypatch.setattr(private_store, "_config_value", lambda name: values.get(name, ""))

    config = get_private_data_store_config()

    assert config.enabled is True
    assert config.repo == "new-owner/new-data"
    assert config.token == "new-token"
    assert config.branch == "data-main"
    assert config.prefix == "durable"
    assert config.timeout == 17
    assert "token" not in config.redacted()


def test_legacy_config_remains_supported(monkeypatch) -> None:
    values = {
        private_store.LEGACY_REPO_ENV: "legacy-owner/private-data",
        private_store.LEGACY_TOKEN_ENV: "legacy-token",
        private_store.LEGACY_BRANCH_ENV: "main",
        private_store.LEGACY_PREFIX_ENV: "operator_samples",
        private_store.LEGACY_TIMEOUT_ENV: "12",
    }
    monkeypatch.setattr(private_store, "_config_value", lambda name: values.get(name, ""))

    config = get_private_data_store_config()

    assert config.enabled is True
    assert config.configured is True
    assert config.repo == "legacy-owner/private-data"
    assert config.token == "legacy-token"
    assert config.timeout == 12


def test_read_decodes_content_and_write_uses_current_sha_for_cas(monkeypatch) -> None:
    config = _config()
    calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def fake_request(
        method: str,
        api_path: str,
        actual_config: PrivateDataStoreConfig,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert actual_config is config
        calls.append((method, api_path, payload))
        if method == "GET":
            return {
                "content": base64.b64encode(b"before").decode("ascii"),
                "sha": "old-sha",
                "size": 6,
            }
        return {"commit": {"sha": "new-commit"}}

    monkeypatch.setattr(private_store, "_require_config", lambda: config)
    monkeypatch.setattr(private_store, "_api_request", fake_request)

    loaded = read_private_data_file("history/snapshots.csv", required=True)
    result = write_private_data_file(
        "history/snapshots.csv",
        b"after",
        "Update snapshot",
    )

    assert loaded == PrivateDataFile(
        path="history/snapshots.csv",
        content=b"before",
        sha="old-sha",
        size=6,
    )
    assert result["commit"]["sha"] == "new-commit"
    put_method, put_path, put_payload = calls[-1]
    assert put_method == "PUT"
    assert put_path == "/repos/example/private-data/contents/operator_samples/history/snapshots.csv"
    assert put_payload == {
        "message": "Update snapshot",
        "content": base64.b64encode(b"after").decode("ascii"),
        "branch": "main",
        "sha": "old-sha",
    }


@pytest.mark.parametrize("status_code", [409, 422])
def test_github_conflict_is_mapped_without_leaking_response_details(
    monkeypatch,
    status_code: int,
) -> None:
    config = _config()
    response_body = io.BytesIO(
        b'{"message":"conflict for super-secret-token","documentation_url":"private"}'
    )

    def fake_urlopen(_request, timeout: int):
        assert timeout == config.timeout
        raise urllib.error.HTTPError(
            "https://api.github.com/repos/example/private-data/contents/file.csv",
            status_code,
            "super-secret-token",
            {},
            response_body,
        )

    monkeypatch.setattr(private_store.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(PrivateDataStoreConflictError) as exc_info:
        private_store._api_request("PUT", "/repos/example/private-data/contents/file.csv", config, {})

    message = str(exc_info.value)
    assert "reload and retry" in message
    assert config.token not in message
    assert "documentation_url" not in message


@pytest.mark.parametrize("status_code", [401, 403])
def test_access_error_is_sanitized(monkeypatch, status_code: int) -> None:
    config = _config()

    def fake_urlopen(_request, timeout: int):
        assert timeout == config.timeout
        raise urllib.error.HTTPError(
            "https://api.github.com/repos/example/private-data/contents/file.csv",
            status_code,
            "Bad credentials: super-secret-token",
            {},
            io.BytesIO(b'{"message":"super-secret-token"}'),
        )

    monkeypatch.setattr(private_store.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(PrivateDataStoreUnavailableError) as exc_info:
        private_store._api_request("GET", "/repos/example/private-data/contents/file.csv", config)

    message = str(exc_info.value)
    assert f"HTTP {status_code}" in message
    assert config.token not in message
    assert "Bad credentials" not in message


@pytest.mark.parametrize(
    "path",
    ["", ".", "..", "../secret.csv", "folder/../secret.csv", "folder/./secret.csv"],
)
def test_unsafe_or_empty_paths_are_rejected_before_network_access(
    monkeypatch,
    path: str,
) -> None:
    config = _config()
    monkeypatch.setattr(private_store, "_require_config", lambda: config)

    def unexpected_request(*_args, **_kwargs):
        pytest.fail("invalid paths must not reach the network")

    monkeypatch.setattr(private_store, "_api_request", unexpected_request)

    with pytest.raises(ValueError, match="invalid private data path"):
        write_private_data_file(
            path,
            b"data",
            "Unsafe write",
            expected_sha=None,
        )


def test_atomic_multi_file_write_creates_one_commit_and_non_forced_ref_update(
    monkeypatch,
) -> None:
    config = _config()
    calls: list[tuple[str, str, dict[str, Any] | None]] = []
    blob_number = 0

    def fake_request(
        method: str,
        api_path: str,
        actual_config: PrivateDataStoreConfig,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nonlocal blob_number
        assert actual_config is config
        calls.append((method, api_path, payload))
        if (method, api_path) == (
            "GET",
            "/repos/example/private-data/git/ref/heads/main",
        ):
            return {"object": {"sha": "head-sha"}}
        if (method, api_path) == (
            "GET",
            "/repos/example/private-data/git/commits/head-sha",
        ):
            return {"tree": {"sha": "base-tree-sha"}}
        if (method, api_path) == (
            "POST",
            "/repos/example/private-data/git/blobs",
        ):
            blob_number += 1
            return {"sha": f"blob-{blob_number}"}
        if (method, api_path) == (
            "POST",
            "/repos/example/private-data/git/trees",
        ):
            return {"sha": "new-tree-sha"}
        if (method, api_path) == (
            "POST",
            "/repos/example/private-data/git/commits",
        ):
            return {"sha": "new-commit-sha"}
        if (method, api_path) == (
            "PATCH",
            "/repos/example/private-data/git/refs/heads/main",
        ):
            return {"object": {"sha": "new-commit-sha"}}
        pytest.fail(f"unexpected GitHub API call: {method} {api_path}")

    monkeypatch.setattr(private_store, "_require_config", lambda: config)
    monkeypatch.setattr(private_store, "_api_request", fake_request)

    result = write_private_data_files_atomic(
        {
            "metadata.json": b"{}",
            "actuals/saved.csv": b"date,value\n",
        },
        "Publish durable state",
    )

    assert result == {
        "commit": {"sha": "new-commit-sha"},
        "parent_sha": "head-sha",
        "paths": ["actuals/saved.csv", "metadata.json"],
    }
    tree_call = next(
        call
        for call in calls
        if call[:2] == ("POST", "/repos/example/private-data/git/trees")
    )
    assert tree_call[2] == {
        "base_tree": "base-tree-sha",
        "tree": [
            {
                "path": "operator_samples/actuals/saved.csv",
                "mode": "100644",
                "type": "blob",
                "sha": "blob-1",
            },
            {
                "path": "operator_samples/metadata.json",
                "mode": "100644",
                "type": "blob",
                "sha": "blob-2",
            },
        ],
    }
    commit_call = next(
        call
        for call in calls
        if call[:2] == ("POST", "/repos/example/private-data/git/commits")
    )
    assert commit_call[2] == {
        "message": "Publish durable state",
        "tree": "new-tree-sha",
        "parents": ["head-sha"],
    }
    assert calls[-1] == (
        "PATCH",
        "/repos/example/private-data/git/refs/heads/main",
        {"sha": "new-commit-sha", "force": False},
    )


def test_atomic_write_propagates_final_ref_conflict(monkeypatch) -> None:
    config = _config()

    def fake_request(
        method: str,
        api_path: str,
        _config: PrivateDataStoreConfig,
        _payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if method == "GET" and "/git/ref/heads/" in api_path:
            return {"object": {"sha": "head-sha"}}
        if method == "GET" and "/git/commits/" in api_path:
            return {"tree": {"sha": "base-tree-sha"}}
        if api_path.endswith("/git/blobs"):
            return {"sha": "blob-sha"}
        if api_path.endswith("/git/trees"):
            return {"sha": "tree-sha"}
        if api_path.endswith("/git/commits"):
            return {"sha": "commit-sha"}
        if method == "PATCH":
            raise PrivateDataStoreConflictError("reload and retry")
        pytest.fail(f"unexpected GitHub API call: {method} {api_path}")

    monkeypatch.setattr(private_store, "_require_config", lambda: config)
    monkeypatch.setattr(private_store, "_api_request", fake_request)

    with pytest.raises(PrivateDataStoreConflictError, match="reload and retry"):
        write_private_data_files_atomic({"file.csv": b"content"}, "Concurrent write")


def test_default_private_mode_rejects_missing_store(monkeypatch) -> None:
    monkeypatch.setattr(private_store, "_config_value", lambda _name: "")

    with pytest.raises(
        private_store.PrivateDataStoreConfigurationError,
        match="required but not configured",
    ):
        private_store.require_private_data_store()


def test_explicit_local_demo_mode_allows_no_remote_store(monkeypatch) -> None:
    values = {private_store.PRIVATE_DATA_MODE_ENV: "local_demo"}
    monkeypatch.setattr(private_store, "_config_value", lambda name: values.get(name, ""))

    assert private_store.require_private_data_store() is False
