from __future__ import annotations

import pandas as pd
import pytest

import app
from src.private_data_store import (
    PrivateDataStoreConfigurationError,
    PrivateDataStoreConflictError,
    PrivateDataStoreRateLimitError,
    PrivateDataStoreUnavailableError,
)


class _MessageRecorder:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def error(self, message: str) -> None:
        self.messages.append(message)

    def caption(self, message: str) -> None:
        self.messages.append(message)


def test_operator_sample_save_error_is_returned_for_ui(monkeypatch) -> None:
    working_df = pd.DataFrame({"business_day_no": [1]})
    expected_error = PrivateDataStoreUnavailableError(
        "private data store request failed with HTTP 503"
    )

    def fail_save(_kind: str, _df: pd.DataFrame) -> dict[str, object]:
        raise expected_error

    monkeypatch.setattr(app, "save_operator_sample", fail_save)

    result, error = app._try_save_operator_sample_for_ui("current_input", working_df)

    assert result is None
    assert error is expected_error
    assert working_df.to_dict(orient="records") == [{"business_day_no": 1}]


def test_operator_sample_save_success_is_returned_for_ui(monkeypatch) -> None:
    working_df = pd.DataFrame({"business_day_no": [1]})
    expected_result = {"ok": True, "df": working_df.copy()}
    monkeypatch.setattr(
        app,
        "save_operator_sample",
        lambda _kind, _df: expected_result,
    )

    result, error = app._try_save_operator_sample_for_ui("current_input", working_df)

    assert result is expected_result
    assert error is None


def test_operator_metadata_error_is_returned_for_ui(monkeypatch) -> None:
    expected_error = PrivateDataStoreUnavailableError(
        "private data store request failed with HTTP 503"
    )

    def fail_read() -> dict[str, object]:
        raise expected_error

    monkeypatch.setattr(app, "read_operator_metadata", fail_read)

    metadata, error = app._try_read_operator_metadata_for_ui("current_input")

    assert metadata == {}
    assert error is expected_error


def test_operator_reload_error_is_returned_for_ui(monkeypatch) -> None:
    expected_error = PrivateDataStoreUnavailableError(
        "private data store network request failed"
    )

    def fail_load(_kind: str):
        raise expected_error

    monkeypatch.setattr(app, "load_sample_with_source", fail_load)

    loaded_df, source_info, error = app._try_load_operator_sample_for_ui(
        "current_input"
    )

    assert loaded_df is None
    assert source_info is None
    assert error is expected_error


@pytest.mark.parametrize(
    ("error", "expected_guidance"),
    [
        (PrivateDataStoreConflictError("reload and retry"), "다른 저장 작업"),
        (PrivateDataStoreConfigurationError("token is missing"), "PRIVATE_DATA_REPO"),
        (
            PrivateDataStoreRateLimitError(
                "private data store rate limited with HTTP 403"
            ),
            "요청 제한",
        ),
        (
            PrivateDataStoreUnavailableError(
                "private data store access failed with HTTP 403"
            ),
            "Contents: Read and write",
        ),
        (
            PrivateDataStoreUnavailableError(
                "private data store request failed with HTTP 503"
            ),
            "일시적 장애",
        ),
    ],
)
def test_operator_store_error_guidance_matches_failure_type(
    monkeypatch,
    error,
    expected_guidance: str,
) -> None:
    recorder = _MessageRecorder()
    monkeypatch.setattr(app, "st", recorder)

    app._render_operator_sample_store_error("저장", error)

    assert expected_guidance in " ".join(recorder.messages)
