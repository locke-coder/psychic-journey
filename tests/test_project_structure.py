from pathlib import Path


def test_required_project_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]

    required_files = [
        "README.md",
        "requirements.txt",
        ".gitignore",
        "AGENTS.md",
        "app.py",
        "config/__init__.py",
        "src/__init__.py",
        "tests/__init__.py",
    ]

    for relative_path in required_files:
        assert (root / relative_path).is_file()
