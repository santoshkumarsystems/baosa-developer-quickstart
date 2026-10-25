"""Verify that all project Python functions, classes and tests have docstrings.

Author: Santosh Kumar | BAOSA developer quickstart | MIT License."""
from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
missing = []
for relative in ("baosa", "tests"):
    for path in (ROOT / relative).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
                missing.append(f"{path.relative_to(ROOT)}:{node.lineno} {node.name}")
for name in ("app.py", "cli.py"):
    path = ROOT / name
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
            missing.append(f"{name}:{node.lineno} {node.name}")
if missing:
    raise SystemExit("Missing docstrings:\n" + "\n".join(missing))
print("PASS: all Python functions, classes and tests have docstrings")
