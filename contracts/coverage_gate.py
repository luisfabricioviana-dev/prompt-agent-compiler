"""Deterministic statement-line coverage proxy for v0.2.10 contracts.

This is intentionally not presented as coverage.py line coverage. It compares
executed lines reported by the stdlib trace module with source lines that carry
AST statements, excluding structural docstrings.
"""
from __future__ import annotations

import ast
from typing import Iterable


def _docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    bodies = []
    if isinstance(tree, ast.Module):
        bodies.append(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bodies.append(node.body)
    for body in bodies:
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            lines.add(first.lineno)
    return lines


def executable_statement_lines(source: str) -> set[int]:
    if not isinstance(source, str):
        raise TypeError("coverage_source_text_required")
    tree = ast.parse(source)
    lines = {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.stmt) and hasattr(node, "lineno")
    }
    return lines - _docstring_lines(tree)


def coverage_percent(
    executed_lines: Iterable[int],
    executable_lines: Iterable[int],
) -> float:
    executed = set(executed_lines)
    total = set(executable_lines)
    if not total:
        return 100.0
    return len(executed & total) * 100.0 / len(total)


def enforce_minimum_coverage(value: float, minimum: float) -> float:
    value = float(value)
    minimum = float(minimum)
    if value < minimum:
        raise RuntimeError(
            f"coverage_below_threshold:{value:.2f}<{minimum:.2f}"
        )
    return value
