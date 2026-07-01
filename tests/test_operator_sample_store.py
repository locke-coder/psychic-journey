from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.loader import load_input
from src.operator_sample_store import (
    get_operator_sample_path,
    get_packaged_sample_path,
    load_sample_with_source,
    read_operator_metadata,
    save_operator_sample,
    validate_operator_sample,
)


def _use_temp_operator_dir(tmp_path: Path, monkeypatch) -> Path:
    operator_dir = tmp_path / "operator_samples"
    monkeypatch.setenv("OPERATOR_SAMPLE_DIR", str(operator_dir))
    return operator_dir


def _sample_df(kind: str) -> pd.DataFrame:
    path = get_packaged_sample_path(kind)
    if kind == "historical_input":
        return load_input(path, sort_by="date", strict_business_day_no=False)
    return load_input(path)


def _complete_historical_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-04-01",
                    "2026-04-02",
                    "2026-05-01",
                    "2026-05-04",
                ]
            ),
            "day_name": ["Wed", "Thu", "Fri", "Mon"],
            "business_day_no": [1, 2, 1, 2],
            "is_close_day": [True, False, True, False],
            "close_type": ["start", "normal", "start", "normal"],
            "sales_target_daily": [10.0, 20.0, 11.0, 21.0],
            "recognized_target_daily": [9.0, 18.0, 10.0, 19.0],
            "sales_actual_cum": [10.0, 31.0, 12.0, 34.0],
            "recognized_actual_cum": [9.0, 28.0, 11.0, 31.0],
            "memo": ["sample", "sample", "sample", "sample"],
        }
    )


def test_load_falls_back_to_packaged_sample_when_operator_store_is_absent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)

    df, source = load_sample_with_source("current_input")

    assert source["source"] == "packaged"
    assert Path(source["path"]).as_posix().endswith("data/sample/input_sample.csv")
    assert len(df) == len(_sample_df("current_input"))


def test_saved_operator_sample_loads_before_packaged_sample(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)
    df = _sample_df("current_input")
    df.loc[0, "sales_target_daily"] = 999.0

    result = save_operator_sample("current_input", df)
    loaded, source = load_sample_with_source("current_input")

    assert result["ok"] is True
    assert source["source"] == "operator"
    assert loaded.loc[0, "sales_target_daily"] == 999.0


def test_save_does_not_modify_packaged_sample_file(tmp_path: Path, monkeypatch) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)
    packaged_path = get_packaged_sample_path("current_input")
    before = packaged_path.read_bytes()

    result = save_operator_sample("current_input", _sample_df("current_input"))

    assert result["ok"] is True
    assert packaged_path.read_bytes() == before


def test_save_removes_fully_blank_rows_before_persisting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)
    df = _sample_df("current_input")
    blank_row = {column: "" for column in df.columns}
    df = pd.concat([df, pd.DataFrame([blank_row])], ignore_index=True)

    result = save_operator_sample("current_input", df)
    saved = pd.read_csv(get_operator_sample_path("current_input"), encoding="utf-8-sig")

    assert result["ok"] is True
    assert len(saved) == len(_sample_df("current_input"))


def test_current_input_rejects_duplicate_business_day_no(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)
    df = _sample_df("current_input")
    df.loc[1, "business_day_no"] = df.loc[0, "business_day_no"]

    errors = validate_operator_sample("current_input", df)

    assert any("current_input business_day_no" in error for error in errors)


def test_historical_input_rejects_monthly_duplicate_business_day_no(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)
    df = _complete_historical_df()
    first_month = df["date"].dt.to_period("M").iloc[0]
    same_month_rows = df.index[df["date"].dt.to_period("M") == first_month].tolist()
    df.loc[same_month_rows[1], "business_day_no"] = df.loc[same_month_rows[0], "business_day_no"]

    errors = validate_operator_sample("historical_input", df)

    assert any("unique within" in error for error in errors)


def test_historical_input_requires_actual_cum_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)
    df = _complete_historical_df()
    df.loc[0, "sales_actual_cum"] = pd.NA

    errors = validate_operator_sample("historical_input", df)

    assert any("sales_actual_cum is required" in error for error in errors)


def test_day_name_text_does_not_change_is_close_day_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)
    df = _sample_df("current_input").head(2).copy()
    df.loc[:, "day_name"] = ["월요일", "목요일"]
    df.loc[:, "is_close_day"] = [False, True]

    result = save_operator_sample("current_input", df)
    loaded, source = load_sample_with_source("current_input")

    assert result["ok"] is True
    assert source["source"] == "operator"
    assert loaded["is_close_day"].tolist() == [False, True]


def test_is_close_day_tokens_are_normalized_on_save(tmp_path: Path, monkeypatch) -> None:
    _use_temp_operator_dir(tmp_path, monkeypatch)
    df = _sample_df("current_input").head(2).copy()
    df["is_close_day"] = df["is_close_day"].astype(object)
    df.loc[:, "is_close_day"] = ["Y", "N"]

    result = save_operator_sample("current_input", df)
    loaded, _source = load_sample_with_source("current_input")

    assert result["ok"] is True
    assert loaded["is_close_day"].tolist() == [True, False]


def test_existing_operator_sample_is_backed_up_and_metadata_is_written(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator_dir = _use_temp_operator_dir(tmp_path, monkeypatch)
    df = _sample_df("current_input")

    first = save_operator_sample("current_input", df)
    df.loc[0, "sales_target_daily"] = 123.0
    second = save_operator_sample("current_input", df)
    metadata = read_operator_metadata()
    backups = list((operator_dir / "backups").glob("current_input_sample_*.csv"))

    assert first["ok"] is True
    assert second["ok"] is True
    assert backups
    assert metadata["current_input"]["rows"] == len(df)
    assert metadata["current_input"]["source"] == "app_editor"
    assert metadata["current_input"]["saved_at"]
    assert metadata["current_input"]["version"] == 2


def test_operator_sample_dir_env_keeps_repo_runtime_storage_clean(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator_dir = _use_temp_operator_dir(tmp_path, monkeypatch)

    result = save_operator_sample("historical_input", _complete_historical_df())

    assert result["ok"] is True
    assert get_operator_sample_path("historical_input").is_relative_to(operator_dir)
