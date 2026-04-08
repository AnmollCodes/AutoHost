"""Codebase Analyzer Tool for AutoHost.

Recursively scans a software repository to detect languages, frameworks,
entry points, and dependencies. Generates architecture.md and repo_map.json.
"""

import ast
import json
import os
import re
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Directories to always skip
_SKIP_DIRS = frozenset({
    "node_modules", "venv", "env", ".venv", ".env",
    "__pycache__", ".git", ".hg", ".svn", "dist", "build",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
})

# Framework detection patterns
_FRAMEWORK_PATTERNS: dict[str, re.Pattern] = {
    "Django": re.compile(r"import django|from django"),
    "Flask": re.compile(r"from flask|import flask"),
    "FastAPI": re.compile(r"from fastapi|import fastapi"),
    "React": re.compile(r"import React|from ['\"]react['\"]"),
    "Next.js": re.compile(r"next/link|next/router|from ['\"]next"),
    "Vue": re.compile(r"from ['\"]vue['\"]|import Vue"),
    "Express": re.compile(r"require\(['\"]express['\"]|from ['\"]express"),
    "Typer": re.compile(r"import typer|from typer"),
    "Streamlit": re.compile(r"import streamlit|from streamlit"),
    "Pytest": re.compile(r"import pytest|from pytest"),
}

# Well-known entry point filenames
_ENTRY_POINTS = frozenset({
    "main.py", "app.py", "index.js", "index.ts", "server.js",
    "server.ts", "manage.py", "cli.py", "wsgi.py", "asgi.py",
})


def analyze_codebase(target_path: str) -> str:
    """Analyze a software repository and generate architecture artifacts.

    Args:
        target_path: Path to the root of the repository.

    Returns:
        A human-readable summary string. Starts with "Error:" on failure.
    """
    target = Path(target_path).resolve()
    if not target.exists() or not target.is_dir():
        return f"Error: '{target_path}' is not a valid directory."

    files_list: list[str] = []
    languages: dict[str, int] = {}
    frameworks: set[str] = set()
    entry_points: list[str] = []
    dependencies: dict[str, list[str]] = {}  # file -> list of imports

    for root, dirs, files in os.walk(target):
        # Prune directories we don't care about
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]

        for filename in files:
            filepath = Path(root) / filename
            rel_path = str(filepath.relative_to(target))
            ext = filepath.suffix.lower()

            # Skip binary / non-source files
            if ext in (".pyc", ".pyo", ".exe", ".dll", ".so", ".o", ".class"):
                continue

            files_list.append(rel_path)
            languages[ext] = languages.get(ext, 0) + 1

            if filename in _ENTRY_POINTS:
                entry_points.append(rel_path)

            # Python analysis
            if ext == ".py":
                _analyze_python_file(filepath, rel_path, frameworks, dependencies)

            # JavaScript / TypeScript analysis
            elif ext in (".js", ".jsx", ".ts", ".tsx"):
                _analyze_js_file(filepath, frameworks)

    # Build repo_map
    repo_map = {
        "project_name": target.name,
        "total_files": len(files_list),
        "languages": dict(sorted(languages.items(), key=lambda x: -x[1])),
        "frameworks": sorted(frameworks),
        "entry_points": entry_points,
        "files": files_list,
    }

    # Write artifacts
    map_path = target / "repo_map.json"
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(repo_map, f, indent=2)

    arch_path = target / "architecture.md"
    _write_architecture_md(arch_path, target.name, repo_map, dependencies)

    fw_text = ", ".join(repo_map["frameworks"]) if repo_map["frameworks"] else "unknown frameworks"
    return (
        f"Codebase successfully analyzed. "
        f"Generated {arch_path.name} and {map_path.name} in {target_path}. "
        f"Project uses {fw_text} with {len(files_list)} files."
    )


def _analyze_python_file(
    filepath: Path,
    rel_path: str,
    frameworks: set[str],
    dependencies: dict[str, list[str]],
) -> None:
    """Parse a Python file for imports and framework detection."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(filepath))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        if imports:
            dependencies[rel_path] = imports

        for name, pattern in _FRAMEWORK_PATTERNS.items():
            if pattern.search(content):
                frameworks.add(name)
    except (SyntaxError, UnicodeDecodeError, OSError):
        pass


def _analyze_js_file(filepath: Path, frameworks: set[str]) -> None:
    """Scan a JS/TS file for framework detection."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in _FRAMEWORK_PATTERNS.items():
            if pattern.search(content):
                frameworks.add(name)
    except (UnicodeDecodeError, OSError):
        pass


def _write_architecture_md(
    path: Path,
    project_name: str,
    repo_map: dict,
    dependencies: dict[str, list[str]],
) -> None:
    """Write a well-formatted architecture.md file."""
    lines = [
        f"# Architecture Overview: {project_name}",
        "",
        "## Languages",
        "",
    ]
    for ext, count in repo_map["languages"].items():
        lines.append(f"- `{ext or '(no extension)'}`: {count} file{'s' if count != 1 else ''}")

    lines += ["", "## Frameworks Detected", ""]
    if repo_map["frameworks"]:
        for fw in repo_map["frameworks"]:
            lines.append(f"- {fw}")
    else:
        lines.append("- None automatically detected")

    lines += ["", "## Key Entry Points", ""]
    if repo_map["entry_points"]:
        for ep in repo_map["entry_points"]:
            lines.append(f"- `{ep}`")
    else:
        lines.append("- No standard entry points found")

    lines += ["", "## Project Size", ""]
    lines.append(f"- Total tracked files: **{repo_map['total_files']}**")

    if dependencies:
        lines += ["", "## Key Dependencies (top files)", ""]
        # Show top 10 most-connected files
        sorted_deps = sorted(dependencies.items(), key=lambda x: -len(x[1]))[:10]
        for file, imports in sorted_deps:
            lines.append(f"- `{file}` → {len(imports)} imports")

    lines.append("")  # trailing newline
    path.write_text("\n".join(lines), encoding="utf-8")
