import json
import subprocess
from pathlib import Path

from tools import run_audit


class _Completed:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_audit_importable() -> None:
    assert callable(run_audit.run_audit)
    assert callable(run_audit.run_gate_runner)


def test_log_path_creation(tmp_path: Path) -> None:
    log_dir = tmp_path / "audit" / "logs"

    created = run_audit.ensure_log_dir(log_dir)

    assert created == log_dir
    assert log_dir.is_dir()


def test_result_file_name_rule(tmp_path: Path) -> None:
    log_dir = tmp_path / "audit" / "logs"

    assert run_audit.gate_log_path("G09", log_dir).name == "gate_runner_G09.json"
    assert run_audit.gate_log_path("all", log_dir).name == "gate_runner_ALL.json"
    assert run_audit.pytest_log_path(log_dir).name == "pytest_result.txt"


def test_subprocess_failure_is_structured_and_logged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_run(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return _Completed(returncode=2, stdout="not-json", stderr="boom")

    monkeypatch.setattr(run_audit.subprocess, "run", fake_run)
    log_dir = tmp_path / "audit" / "logs"

    result = run_audit.run_gate_runner(
        "G10",
        repo_root=tmp_path,
        log_dir=log_dir,
        runner_path=tmp_path / "tools" / "gate_runner.py",
    )

    assert result["gate"] == "G10"
    assert result["status"] == "FAIL"
    assert result["tests_passed"] is False
    assert result["returncode"] == 2
    assert "non-JSON output" in result["errors"][0]
    assert result["stderr"] == "boom"

    log_path = log_dir / "gate_runner_G10.json"
    assert log_path.is_file()
    assert json.loads(log_path.read_text(encoding="utf-8")) == result


def test_parseable_gate_runner_output_is_persisted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = {
        "gate": "G12",
        "status": "PASS",
        "tests_passed": True,
        "required_files_missing": [],
        "required_keywords_missing": [],
        "forbidden_patterns_found": [],
        "warnings": [],
        "errors": [],
    }

    def fake_run(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return _Completed(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(run_audit.subprocess, "run", fake_run)
    log_dir = tmp_path / "audit" / "logs"

    result = run_audit.run_gate_runner(
        "G12",
        repo_root=tmp_path,
        log_dir=log_dir,
        runner_path=tmp_path / "tools" / "gate_runner.py",
    )

    assert result == payload
    assert json.loads((log_dir / "gate_runner_G12.json").read_text(encoding="utf-8")) == payload


def test_pytest_capture_writes_text_log(tmp_path: Path, monkeypatch) -> None:
    def fake_run(command, **kwargs):  # noqa: ANN001, ANN003
        assert command[:3] == [run_audit.sys.executable, "-m", "pytest"]
        return subprocess.CompletedProcess(command, 1, stdout="failed tests", stderr="")

    monkeypatch.setattr(run_audit.subprocess, "run", fake_run)
    log_dir = tmp_path / "audit" / "logs"

    result = run_audit.run_pytest_capture(repo_root=tmp_path, log_dir=log_dir)

    assert result["status"] == "FAIL"
    assert result["returncode"] == 1
    assert (log_dir / "pytest_result.txt").read_text(encoding="utf-8") == "failed tests\n"
