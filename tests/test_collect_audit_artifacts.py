import json
import zipfile
from pathlib import Path

from tools import collect_audit_artifacts


def _write_file(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_dry_run_reports_planned_files_without_creating_outputs(tmp_path: Path) -> None:
    _write_file(tmp_path / "src" / "forecast_models.py", "target_status = 'ON_TARGET'\n")
    _write_file(tmp_path / "tests" / "test_forecast_models.py", "def test_ok(): pass\n")
    _write_file(tmp_path / "config" / "model_config.yaml", "x: 1\n")
    _write_file(tmp_path / "app.py", "print('app')\n")
    _write_file(tmp_path / "outputs" / "latest" / "report.md", "# report\n")

    result = collect_audit_artifacts.collect_audit_artifacts(
        tmp_path,
        dry_run=True,
    )

    assert result["status"] == "DRY_RUN"
    assert "src/forecast_models.py" in result["planned_files"]
    assert "tests/test_forecast_models.py" in result["planned_files"]
    assert "config/model_config.yaml" in result["planned_files"]
    assert "app.py" in result["planned_files"]
    assert "outputs/latest/report.md" in result["planned_files"]
    assert not (tmp_path / "audit_submit").exists()
    assert not (tmp_path / "audit_submit.zip").exists()
    assert result["manifest_created"] is False


def test_exclude_patterns_are_applied_to_copy_and_zip(tmp_path: Path) -> None:
    _write_file(tmp_path / "src" / "good.py", "value = 1\n")
    _write_file(tmp_path / "src" / "__pycache__" / "cached.py", "bad\n")
    _write_file(tmp_path / "tests" / "test_good.py", "def test_ok(): pass\n")
    _write_file(tmp_path / "tests" / "cached.pyc", "bad\n")
    _write_file(tmp_path / "tools" / "helper.py", "value = 1\n")
    _write_file(tmp_path / ".venv" / "ignored.py", "bad\n")
    _write_file(tmp_path / ".env", "SECRET=1\n")
    _write_file(tmp_path / ".streamlit" / "secrets.toml", "SECRET=1\n")
    _write_file(tmp_path / ".streamlit" / "secrets.example.toml", "placeholder='ok'\n")
    _write_file(tmp_path / "tools" / "service.key", "SECRET=1\n")
    _write_file(tmp_path / "docs" / "secret_plan.txt", "SECRET=1\n")
    _write_file(tmp_path / "audit" / "logs" / "pytest_result.txt", "ok\n")
    _write_file(tmp_path / "audit" / "logs" / "gate_runner_all.json", "{}\n")

    result = collect_audit_artifacts.collect_audit_artifacts(tmp_path)

    assert result["status"] == "COLLECTED"
    assert (tmp_path / "audit_submit" / "src" / "good.py").is_file()
    assert not (tmp_path / "audit_submit" / "src" / "__pycache__").exists()
    assert not (tmp_path / "audit_submit" / "tests" / "cached.pyc").exists()
    assert not (tmp_path / "audit_submit" / ".env").exists()
    assert not (tmp_path / "audit_submit" / "tools" / "service.key").exists()
    assert not (tmp_path / "audit_submit" / "docs" / "secret_plan.txt").exists()
    assert "__pycache__" in " ".join(result["skipped_paths"])
    assert "tests/cached.pyc" in result["skipped_paths"]
    assert ".streamlit/secrets.toml" in result["excluded_sensitive_files"]
    assert ".env" in result["excluded_sensitive_files"]
    assert "tools/service.key" in result["excluded_sensitive_files"]
    assert "docs/secret_plan.txt" in result["excluded_sensitive_files"]
    assert ".streamlit/secrets.example.toml" not in result["excluded_sensitive_files"]
    assert not collect_audit_artifacts.is_excluded_path(
        tmp_path / ".streamlit" / "secrets.example.toml",
        tmp_path,
    )
    assert result["manifest_created"] is True

    with zipfile.ZipFile(tmp_path / "audit_submit.zip") as archive:
        names = set(archive.namelist())

    assert "src/good.py" in names
    assert "src/__pycache__/cached.py" not in names
    assert "tests/cached.pyc" not in names
    assert ".env" not in names
    assert ".streamlit/secrets.toml" not in names
    assert "tools/service.key" not in names
    assert "docs/secret_plan.txt" not in names
    assert "manifest.md" in names

    manifest_text = (tmp_path / "audit_submit" / "manifest.md").read_text(encoding="utf-8")
    assert "excluded_sensitive_files" in manifest_text
    assert ".streamlit/secrets.toml" in manifest_text


def test_zip_file_name_rule_is_stable(tmp_path: Path) -> None:
    _write_file(tmp_path / "audit" / "logs" / "pytest_result.txt", "ok\n")
    _write_file(tmp_path / "audit" / "logs" / "gate_runner_all.json", "{}\n")

    result = collect_audit_artifacts.collect_audit_artifacts(tmp_path)

    assert collect_audit_artifacts.audit_zip_path(tmp_path).name == "audit_submit.zip"
    assert Path(result["zip_path"]).name == "audit_submit.zip"
    with zipfile.ZipFile(result["zip_path"]) as archive:
        assert "audit/logs/pytest_result.txt" in set(archive.namelist())


def test_gate_runner_log_is_valid_json_when_generated_from_bad_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_file(tmp_path / "audit" / "logs" / "pytest_result.txt", "ok\n")

    def fake_run(command, **kwargs):  # noqa: ANN001, ANN003
        return collect_audit_artifacts.subprocess.CompletedProcess(
            command,
            2,
            stdout="not-json",
            stderr="boom",
        )

    monkeypatch.setattr(collect_audit_artifacts.subprocess, "run", fake_run)

    result = collect_audit_artifacts.collect_audit_artifacts(tmp_path)

    gate_log = tmp_path / "audit" / "logs" / "gate_runner_all.json"
    payload = json.loads(gate_log.read_text(encoding="utf-8"))
    assert payload["gate"] == "ALL"
    assert payload["status"] == "FAIL"
    assert payload["returncode"] == 2
    assert "gate_runner_all.json" in " ".join(result["generated_logs"])


def test_latest_outputs_are_included_and_archives_are_policy_gated(tmp_path: Path) -> None:
    _write_file(tmp_path / "audit" / "logs" / "pytest_result.txt", "ok\n")
    _write_file(tmp_path / "audit" / "logs" / "gate_runner_all.json", "{}\n")
    _write_file(tmp_path / "outputs" / "latest" / "daily_report.xlsx", "xlsx placeholder\n")
    _write_file(
        tmp_path / "outputs" / "archive_old_format" / "old_report.xlsx",
        "xlsx placeholder\n",
    )
    _write_file(
        tmp_path / "outputs" / "archive_invalid" / "broken.xlsx",
        "xlsx placeholder\n",
    )

    default_result = collect_audit_artifacts.collect_audit_artifacts(
        tmp_path,
        dry_run=True,
    )
    archive_result = collect_audit_artifacts.collect_audit_artifacts(
        tmp_path,
        include_archives=True,
        dry_run=True,
    )
    no_outputs_result = collect_audit_artifacts.collect_audit_artifacts(
        tmp_path,
        exclude_outputs=True,
        dry_run=True,
    )

    assert "outputs/latest/daily_report.xlsx" in default_result["planned_files"]
    assert "outputs/archive_old_format/old_report.xlsx" not in default_result["planned_files"]
    assert "outputs/archive_invalid/broken.xlsx" not in default_result["planned_files"]
    assert "outputs/archive_old_format/old_report.xlsx" in archive_result["planned_files"]
    assert "outputs/archive_invalid/broken.xlsx" not in archive_result["planned_files"]
    assert "outputs/latest/daily_report.xlsx" not in no_outputs_result["planned_files"]


def test_runtime_operator_data_is_excluded_from_default_package(tmp_path: Path) -> None:
    _write_file(tmp_path / "audit" / "logs" / "pytest_result.txt", "ok\n")
    _write_file(tmp_path / "audit" / "logs" / "gate_runner_all.json", "{}\n")
    _write_file(tmp_path / "src" / "operator_sample_store.py", "value = 1\n")
    _write_file(
        tmp_path / "runtime_storage" / "operator_samples" / "current_input_sample.csv",
        "OPERATOR_SAMPLE_CONTENT_SHOULD_NOT_APPEAR\n",
    )
    _write_file(
        tmp_path / "operator_samples" / "historical_input_sample.csv",
        "HISTORICAL_OPERATOR_CONTENT_SHOULD_NOT_APPEAR\n",
    )
    _write_file(tmp_path / "local_data" / "local.csv", "LOCAL_CONTENT_SHOULD_NOT_APPEAR\n")
    _write_file(tmp_path / "operator.local.csv", "LOCAL_FILE_CONTENT_SHOULD_NOT_APPEAR\n")

    result = collect_audit_artifacts.collect_audit_artifacts(tmp_path)

    assert "src/operator_sample_store.py" in result["planned_files"]
    assert not any(path.startswith("runtime_storage/") for path in result["planned_files"])
    assert not any(path.startswith("operator_samples/") for path in result["planned_files"])
    assert "runtime_storage" in result["excluded_runtime_data"]
    assert "runtime_storage/operator_samples" in result["excluded_operator_data"]
    assert "operator_samples" in result["excluded_operator_data"]
    assert "operator.local.csv" in result["excluded_runtime_data"]

    manifest_text = (tmp_path / "audit_submit" / "manifest.md").read_text(encoding="utf-8")
    assert "excluded_runtime_data" in manifest_text
    assert "excluded_operator_data" in manifest_text
    assert "runtime_storage/operator_samples" in manifest_text
    assert "OPERATOR_SAMPLE_CONTENT_SHOULD_NOT_APPEAR" not in manifest_text
    assert "HISTORICAL_OPERATOR_CONTENT_SHOULD_NOT_APPEAR" not in manifest_text
    assert "LOCAL_CONTENT_SHOULD_NOT_APPEAR" not in manifest_text

    with zipfile.ZipFile(tmp_path / "audit_submit.zip") as archive:
        names = set(archive.namelist())

    assert "runtime_storage/operator_samples/current_input_sample.csv" not in names
    assert "operator_samples/historical_input_sample.csv" not in names
    assert "operator.local.csv" not in names
