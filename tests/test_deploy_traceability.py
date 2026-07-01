import subprocess
from pathlib import Path

import pytest

from tools import check_deploy_traceability


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_identical_core_files_hash_match(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    deploy_source = tmp_path / "deploy"
    _write(local_root / "app.py", "print('same')\n")
    _write(deploy_source / "app.py", "print('same')\n")

    result = check_deploy_traceability.compare_core_files(local_root, deploy_source)

    assert result["hash_match"] is True
    assert result["compared_files_count"] == 1
    assert result["mismatched_files"] == []


def test_core_file_mismatch_is_detected(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    deploy_source = tmp_path / "deploy"
    _write(local_root / "app.py", "print('local')\n")
    _write(deploy_source / "app.py", "print('deploy')\n")

    result = check_deploy_traceability.compare_core_files(local_root, deploy_source)

    assert result["hash_match"] is False
    assert result["mismatched_files"] == ["app.py"]


def test_sensitive_files_are_excluded_from_collection(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write(root / ".streamlit" / "config.toml", "[server]\n")
    _write(root / ".streamlit" / "secrets.toml", "do-not-read\n")
    _write(root / ".env", "do-not-read\n")
    _write(root / "private.key", "do-not-read\n")

    files = check_deploy_traceability.collect_files(
        root,
        [".streamlit/*.toml", ".env", "*.key"],
    )

    assert set(files) == {".streamlit/config.toml"}


def test_l3_dirty_is_conditional_and_l4_dirty_fails() -> None:
    comparison = {
        "hash_match": True,
        "mismatched_files": [],
        "missing_required_files": [],
    }
    git_status = {
        "deploy_git_available": True,
        "deploy_dirty": True,
        "remote_head_verified": True,
    }

    l3_result, l4_result, recommendations = (
        check_deploy_traceability.decide_release_results(comparison, git_status)
    )

    assert l3_result == check_deploy_traceability.RESULT_CONDITIONAL
    assert l4_result == check_deploy_traceability.RESULT_FAIL
    assert any("uncommitted" in item for item in recommendations)


def test_deploy_source_dirty_state_is_detected_with_temp_git_repo(tmp_path: Path) -> None:
    git_executable = check_deploy_traceability.resolve_git_executable()
    if git_executable is None:
        pytest.skip("git executable is not available")

    deploy_source = tmp_path / "deploy"
    deploy_source.mkdir()
    subprocess.run([git_executable, "init"], cwd=deploy_source, check=True)
    _write(deploy_source / "app.py", "print('dirty')\n")

    status = check_deploy_traceability.inspect_deploy_git(
        deploy_source,
        verify_remote=False,
        git_runner=check_deploy_traceability.run_git_command,
    )

    assert status["deploy_git_available"] is True
    assert status["deploy_dirty"] is True
    assert status["deploy_dirty_count"] >= 1


def test_remote_head_failure_is_recorded_safely(tmp_path: Path) -> None:
    def fake_git_runner(
        args: list[str] | tuple[str, ...],
        cwd: Path,
        timeout: int,
    ) -> check_deploy_traceability.GitCommandResult:
        return check_deploy_traceability.GitCommandResult(
            128,
            "",
            "fatal: unable to access 'https://token@example.com/repo.git/': SSL certificate problem",
        )

    result = check_deploy_traceability.verify_remote_head(
        tmp_path,
        branch="main",
        remote_name="origin",
        git_runner=fake_git_runner,
    )

    assert result["remote_head_verified"] is False
    assert result["remote_head_error_type"] == "BLOCKED_REMOTE_HEAD_TLS"
    assert "token@example.com" not in result["remote_head_error"]
