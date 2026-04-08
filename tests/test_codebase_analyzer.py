"""Tests for the Codebase Analyzer tool."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from agent.tools.codebase_analyzer import analyze_codebase


@pytest.fixture
def mock_repo():
    """Create a temporary repo structure to analyze."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Python files
        (root / "main.py").write_text(
            "import fastapi\nfrom fastapi import FastAPI\napp = FastAPI()\n",
            encoding="utf-8",
        )
        (root / "utils.py").write_text(
            "import os\ndef helper():\n    pass\n",
            encoding="utf-8",
        )

        # Sub-package
        models_dir = root / "models"
        models_dir.mkdir()
        (models_dir / "__init__.py").write_text("", encoding="utf-8")
        (models_dir / "user.py").write_text(
            "class User:\n    pass\n",
            encoding="utf-8",
        )

        # Ignored directories — should NOT appear in output
        venv_dir = root / "venv"
        venv_dir.mkdir()
        (venv_dir / "ignore.py").write_text("ignore me", encoding="utf-8")

        pycache_dir = root / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "cached.pyc").write_bytes(b"\\x00")

        yield tmpdir


def test_generates_architecture_and_map(mock_repo):
    """analyze_codebase should create architecture.md and repo_map.json."""
    summary = analyze_codebase(mock_repo)

    assert "Codebase successfully analyzed" in summary
    assert "FastAPI" in summary

    arch_path = Path(mock_repo) / "architecture.md"
    map_path = Path(mock_repo) / "repo_map.json"

    assert arch_path.exists()
    assert map_path.exists()

    # Verify architecture.md contains real newlines
    arch_text = arch_path.read_text(encoding="utf-8")
    assert "# Architecture Overview" in arch_text
    assert "## Languages" in arch_text
    assert "\\n" not in arch_text  # no literal \\n


def test_repo_map_structure(mock_repo):
    """repo_map.json should have correct structure and data."""
    analyze_codebase(mock_repo)
    map_path = Path(mock_repo) / "repo_map.json"

    with open(map_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "main.py" in data["entry_points"]
    assert "FastAPI" in data["frameworks"]
    assert ".py" in data["languages"]
    assert data["total_files"] > 0


def test_ignores_venv_and_pycache(mock_repo):
    """Virtual env and cache dirs should be excluded."""
    analyze_codebase(mock_repo)
    map_path = Path(mock_repo) / "repo_map.json"

    with open(map_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert not any("venv" in p for p in data["files"])
    assert not any("__pycache__" in p for p in data["files"])


def test_invalid_path():
    """Invalid path should return an error string."""
    summary = analyze_codebase("/this/path/does/not/exist/1234")
    assert summary.startswith("Error:")


def test_empty_directory():
    """Empty directory should still produce valid output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        summary = analyze_codebase(tmpdir)

        assert "Codebase successfully analyzed" in summary
        assert "0 files" in summary

        map_path = Path(tmpdir) / "repo_map.json"
        assert map_path.exists()

        with open(map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_files"] == 0
