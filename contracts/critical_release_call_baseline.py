"""Pinned, scoped AST callsite baseline for compiler and REA pipeline.

Line-independent counts detect call additions/removals within these two
critical modules only. Broader callsite scanner stays diagnostic.
"""
from __future__ import annotations
import ast
from pathlib import Path

BASELINE = {
    "compiler.py": {
        "run_governed_pipeline": 1,
        "run_optional_rea_release": 1,
    },
    "contracts/rea_pipeline.py": {
        "reconcile_delivery": 1,
    },
}


# Bind each watched call to its immediate lexical owner, not just its count.
OWNER_BASELINE = {
    "compiler.py": {
        ("run_optional_rea_release", "run_governed_pipeline"): 1,
        ("run_optional_rea_github_release", "run_optional_rea_release"): 1,
    },
    "contracts/rea_pipeline.py": {
        ("run_governed_pipeline", "reconcile_delivery"): 1,
    },
}


def validate_release_call_owners(root: str | Path) -> dict:
    root = Path(root)
    drift = {}
    errors = []
    for rel, expected in OWNER_BASELINE.items():
        try:
            tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError):
            errors.append(rel)
            continue
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in {name for _, name in expected}:
                        aliases[alias.asname or alias.name] = alias.name
        observed = {key: 0 for key in expected}
        for fn in tree.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(fn):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                name = aliases.get(f.id, f.id) if isinstance(f, ast.Name) else (
                    f.attr if isinstance(f, ast.Attribute) else None)
                key = (fn.name, name)
                if key in observed:
                    observed[key] += 1
        if observed != expected:
            drift[rel] = {"expected": expected, "observed": observed}
    return {"status": "BLOCK" if errors or drift else "PASS_SCOPED",
            "errors": tuple(errors), "drift": drift,
            "scope": "immediate_lexical_function_owners_only"}


def validate_critical_release_calls(root: str | Path) -> dict:
    root = Path(root)
    observed = {}
    errors = []
    for rel, expected in BASELINE.items():
        try:
            tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError):
            errors.append(rel)
            continue
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in expected:
                        aliases[alias.asname or alias.name] = alias.name
        actual = {name: 0 for name in expected}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = aliases.get(f.id, f.id) if isinstance(f, ast.Name) else (
                f.attr if isinstance(f, ast.Attribute) else None)
            if name in actual:
                actual[name] += 1
        observed[rel] = actual
    drift = {
        rel: {"expected": expected, "observed": observed.get(rel)}
        for rel, expected in BASELINE.items()
        if observed.get(rel) != expected
    }
    return {"status": "BLOCK" if errors or drift else "PASS_SCOPED",
            "errors": tuple(errors), "drift": drift,
            "scope": "compiler_and_rea_pipeline_call_counts"}
