"""Scoped AST inventory of direct release imports and calls.

This is a diagnostic, not proof of exhaustive dataflow, dynamic imports,
external usage or safe runtime behavior. Does not execute application code.
"""
from __future__ import annotations
import ast
from pathlib import Path

WATCHED = frozenset({
    "run_optional_rea_release", "run_optional_rea_github_release",
    "run_governed_pipeline", "reconcile_delivery", "reconcile_confirmed",
    "inspect_delivery", "inspect_legacy",
})


def scan_release_calls(root: str | Path) -> dict:
    base = Path(root)
    hits: list[str] = []
    errors: list[str] = []
    files = [base / "compiler.py", base / "rea_signed_release_bridge.py"]
    files += sorted((base / "contracts").glob("*.py"))
    for path in files:
        relative = path.relative_to(base).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError):
            errors.append(relative)
            continue
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in WATCHED:
                        aliases[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    name = aliases.get(func.id, func.id)
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                else:
                    continue
                if name in WATCHED:
                    hits.append(f"{relative}:{node.lineno}:{name}")
    return {
        "status": "BLOCK" if errors else "INVENTORIED_SCOPED",
        "calls": tuple(sorted(hits)),
        "errors": tuple(sorted(errors)),
        "scope": "compiler_bridge_and_contracts_only",
    }
