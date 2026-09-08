"""
tests/test_suspension_checkpoint_constraints.py

Verifies Google AntiGravity architectural constraints:
1. Files <= 250 lines.
2. Functions <= 40 lines.
3. Strict typing: zero `Any` from typing module.

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import ast
import os
import pytest

FILES_TO_CHECK = [
    "backend/storage/clarification_store.py",
    "backend/orchestration/suspension.py",
    "backend/storage/checkpoint_store.py",
    "backend/storage/clarification_persistence.py",
    "backend/storage/checkpoint_store_local.py",
]


def test_file_lengths_under_250_lines():
    """Verifies all upgraded files are strictly <= 250 lines."""
    for rel_path in FILES_TO_CHECK:
        abs_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", rel_path))
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) <= 250, f"File '{rel_path}' exceeds 250 lines: {len(lines)} lines"


def test_function_lengths_under_40_lines():
    """Verifies all functions and methods are strictly <= 40 lines."""
    for rel_path in FILES_TO_CHECK:
        abs_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", rel_path))
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                assert length <= 40, f"Function '{node.name}' in '{rel_path}' is {length} lines (> 40 lines)"


def test_strict_typing_no_any_imported_or_used():
    """Verifies that Any is neither imported nor used as a type annotation."""
    core_files = [
        "backend/storage/clarification_store.py",
        "backend/orchestration/suspension.py",
        "backend/storage/checkpoint_store.py",
        "backend/storage/clarification_persistence.py",
    ]
    for rel_path in core_files:
        abs_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", rel_path))
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "typing":
                    names = [alias.name for alias in node.names]
                    assert "Any" not in names, f"'Any' imported from typing in '{rel_path}'"
            elif isinstance(node, ast.Name) and node.id == "Any":
                pytest.fail(f"'Any' symbol referenced in '{rel_path}' at line {node.lineno}")
