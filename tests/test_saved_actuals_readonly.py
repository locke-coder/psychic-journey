from pathlib import Path

import pandas as pd

import app
from src.loader import load_input


class _FakeColumnConfig:
    def DateColumn(self, *_: object, **__: object) -> object:
        return object()

    def TextColumn(self, *_: object, **__: object) -> object:
        return object()

    def NumberColumn(self, *_: object, **__: object) -> object:
        return object()

    def CheckboxColumn(self, *_: object, **__: object) -> object:
        return object()


class _FakeStreamlit:
    def __init__(self, clicked_keys: set[str] | None = None) -> None:
        self.session_state: dict[str, object] = {}
        self.column_config = _FakeColumnConfig()
        self.buttons: list[dict[str, object]] = []
        self.messages: list[str] = []
        self.clicked_keys = clicked_keys or set()

    def header(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def caption(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def info(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def success(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def warning(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def columns(self, spec: object, **_: object) -> list["_FakeStreamlit"]:
        count = spec if isinstance(spec, int) else len(spec)
        return [self for _ in range(count)]

    def button(self, label: str, **kwargs: object) -> bool:
        self.buttons.append({"label": label, "disabled": bool(kwargs.get("disabled", False))})
        return str(kwargs.get("key") or "") in self.clicked_keys

    def data_editor(self, df: pd.DataFrame, **_: object) -> pd.DataFrame:
        return df.copy()

    def rerun(self) -> None:
        raise AssertionError("rerun should not be called without a button click")


def test_load_saved_actuals_missing_file_does_not_create_file(tmp_path: Path) -> None:
    saved_path = tmp_path / "saved_actuals.csv"

    loaded = app.load_saved_actuals(saved_path)

    assert list(loaded.columns) == list(app.SAVED_ACTUAL_COLUMNS)
    assert loaded.empty
    assert not saved_path.exists()


def test_load_saved_actuals_schema_gap_is_normalized_in_memory_only(tmp_path: Path) -> None:
    saved_path = tmp_path / "saved_actuals.csv"
    saved_path.write_text("date,business_day_no,sales_actual_cum\n2026-06-10,8,88.8\n", encoding="utf-8")
    before_text = saved_path.read_text(encoding="utf-8")
    before_stat = saved_path.stat()

    loaded = app.load_saved_actuals(saved_path)

    after_stat = saved_path.stat()
    assert list(loaded.columns) == list(app.SAVED_ACTUAL_COLUMNS)
    assert "recognized_actual_cum" in loaded.columns
    assert loaded.loc[0, "sales_actual_cum"] == 88.8
    assert saved_path.read_text(encoding="utf-8") == before_text
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert after_stat.st_size == before_stat.st_size


def test_normalize_saved_actuals_schema_does_not_mutate_input_frame() -> None:
    source = pd.DataFrame(
        {
            "date": ["2026-06-10"],
            "business_day_no": [8],
            "sales_actual_cum": ["88.8"],
        }
    )

    normalized = app.normalize_saved_actuals_schema(source)

    assert list(source.columns) == ["date", "business_day_no", "sales_actual_cum"]
    assert list(normalized.columns) == list(app.SAVED_ACTUAL_COLUMNS)
    assert normalized.loc[0, "sales_actual_cum"] == 88.8


def test_save_saved_actuals_writes_only_when_called_explicitly(tmp_path: Path) -> None:
    saved_path = tmp_path / "saved_actuals.csv"
    saved_actuals = pd.DataFrame(
        {
            "date": ["2026-06-10"],
            "business_day_no": [8],
            "sales_actual_cum": [88.8],
            "recognized_actual_cum": [77.7],
        }
    )

    assert not saved_path.exists()
    returned_path = app.save_saved_actuals(saved_actuals, saved_path)

    assert returned_path == saved_path
    assert saved_path.exists()
    loaded = app.load_saved_actuals(saved_path)
    assert loaded.loc[0, "sales_actual_cum"] == 88.8
    assert loaded.loc[0, "recognized_actual_cum"] == 77.7


def test_save_current_input_defaults_promotes_full_input_to_operator_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator_dir = tmp_path / "operator_samples"
    saved_path = tmp_path / "saved_actuals.csv"
    df = load_input(app.SAMPLE_INPUT_PATH)
    edited_df = df.copy()
    edited_df.loc[edited_df["business_day_no"] == 8, "sales_actual_cum"] = 88.8
    edited_df.loc[edited_df["business_day_no"] == 8, "recognized_actual_cum"] = 77.7
    edited_df.loc[edited_df["business_day_no"] == 8, "sales_target_daily"] = 12.34
    monkeypatch.setenv("OPERATOR_SAMPLE_DIR", str(operator_dir))

    result = app.save_current_input_defaults(edited_df, saved_path)
    loaded_df, source_info = app.load_sample_with_source("current_input")

    loaded_row = loaded_df.loc[loaded_df["business_day_no"] == 8].iloc[0]
    assert result["ok"] is True
    assert saved_path.exists()
    assert source_info["source"] == "operator"
    assert loaded_row["sales_actual_cum"] == 88.8
    assert loaded_row["recognized_actual_cum"] == 77.7
    assert loaded_row["sales_target_daily"] == 12.34


def test_current_input_state_labels_saved_actual_overlay(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    base_df = pd.DataFrame(
        {
            "date": ["2026-06-10", "2026-06-11"],
            "day_name": ["수", "목"],
            "business_day_no": [7, 8],
            "is_close_day": [False, True],
            "close_type": ["일반", "목마감"],
            "sales_target_daily": [2.6, 11.5],
            "recognized_target_daily": [2.4, 10.5],
            "sales_actual_cum": [70.5, pd.NA],
            "recognized_actual_cum": [64.5, pd.NA],
            "memo": ["", ""],
        }
    )
    saved_actuals = pd.DataFrame(
        {
            "date": ["2026-06-11"],
            "business_day_no": [8],
            "sales_actual_cum": [88.8],
            "recognized_actual_cum": [77.7],
        }
    )

    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(
        app,
        "load_sample_with_source",
        lambda _kind: (
            base_df.copy(),
            {"source": "packaged", "path": "data/sample/input_sample.csv", "warnings": []},
        ),
    )
    monkeypatch.setattr(app, "_load_saved_actuals_for_ui", lambda: saved_actuals.copy())

    rendered, source_label = app._get_current_input_state()

    rendered_row = rendered.loc[rendered["business_day_no"] == 8].iloc[0]
    assert source_label == app.SAVED_ACTUALS_SOURCE_LABEL
    assert fake_st.session_state[app.CURRENT_INPUT_SOURCE_SESSION_KEY] == app.SAVED_ACTUALS_SOURCE_LABEL
    assert app._is_current_upload_source(app.SAVED_ACTUALS_SOURCE_LABEL) is False
    assert app._sample_source_display_label(app.SAVED_ACTUALS_SOURCE_LABEL) == app.SAVED_ACTUALS_SOURCE_LABEL
    assert rendered_row["sales_actual_cum"] == 88.8
    assert rendered_row["recognized_actual_cum"] == 77.7


def test_input_editor_save_marks_operator_default_source(monkeypatch, tmp_path: Path) -> None:
    fake_st = _FakeStreamlit(clicked_keys={"save_saved_actuals_explicit"})
    df = load_input(app.SAMPLE_INPUT_PATH)
    operator_path = tmp_path / "operator_samples" / "current_input_sample.csv"

    def fake_save_current_input_defaults(saved_df: pd.DataFrame) -> dict[str, object]:
        return {
            "ok": True,
            "df": saved_df.copy(),
            "saved_actuals_path": tmp_path / "saved_actuals.csv",
            "operator_result": {"ok": True, "path": str(operator_path), "warnings": []},
        }

    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "save_current_input_defaults", fake_save_current_input_defaults)

    rendered = app._render_input_editor(df, app.SAMPLE_INPUT_SOURCE_LABEL)

    assert rendered.shape == df.shape
    assert (
        fake_st.session_state[app.CURRENT_INPUT_SOURCE_OVERRIDE_SESSION_KEY]
        == app.OPERATOR_SAMPLE_SOURCE_LABEL
    )
    assert fake_st.session_state[app.CURRENT_INPUT_SOURCE_SESSION_KEY] == app.OPERATOR_SAMPLE_SOURCE_LABEL


def test_uploaded_policy_can_run_readonly_without_rewriting_existing_store(tmp_path: Path) -> None:
    df = load_input(app.SAMPLE_INPUT_PATH)
    saved_path = tmp_path / "saved_actuals.csv"
    app.save_actual_values(df, saved_path)
    before_stat = saved_path.stat()

    upload_df = df.copy()
    upload_df.loc[upload_df["business_day_no"] == 8, "sales_actual_cum"] = 99.9
    prepared, default_source = app.apply_latest_upload_policy(
        upload_df,
        "daily_upload.xlsx",
        app.load_saved_actuals(saved_path),
        saved_path,
        persist_uploaded_defaults=False,
    )

    assert default_source == "uploaded"
    assert prepared.loc[prepared["business_day_no"] == 8, "sales_actual_cum"].iloc[0] == 99.9
    assert saved_path.stat().st_mtime_ns == before_stat.st_mtime_ns


def test_input_editor_default_render_does_not_call_saved_actuals_write(monkeypatch, tmp_path: Path) -> None:
    fake_st = _FakeStreamlit()
    df = load_input(app.SAMPLE_INPUT_PATH)

    def fail_save(*_: object, **__: object) -> Path:
        raise AssertionError("saved_actuals write must be behind the explicit save button")

    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "SAVED_ACTUALS_PATH", tmp_path / "saved_actuals.csv")
    monkeypatch.setattr(app, "save_actual_values", fail_save)

    rendered = app._render_input_editor(df, app.SAMPLE_INPUT_SOURCE_LABEL)

    assert rendered.shape == df.shape
    assert not (tmp_path / "saved_actuals.csv").exists()


def test_input_editor_audit_readonly_disables_saved_actuals_write_buttons(monkeypatch, tmp_path: Path) -> None:
    fake_st = _FakeStreamlit()
    df = load_input(app.SAMPLE_INPUT_PATH)

    def fail_save(*_: object, **__: object) -> Path:
        raise AssertionError("audit_readonly render must not write saved_actuals")

    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "SAVED_ACTUALS_PATH", tmp_path / "saved_actuals.csv")
    monkeypatch.setattr(app, "save_actual_values", fail_save)

    app._render_input_editor(df, app.SAMPLE_INPUT_SOURCE_LABEL, audit_readonly=True)

    disabled_by_label = {str(item["label"]): item["disabled"] for item in fake_st.buttons}
    assert disabled_by_label["저장된 실적값 삭제"] is True
    assert disabled_by_label["완료월 실제 실적 저장"] is True
    assert not (tmp_path / "saved_actuals.csv").exists()
