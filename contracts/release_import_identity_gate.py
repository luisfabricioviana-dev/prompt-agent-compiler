"""Scoped, conservative import-identity verification for critical release calls.

Only three explicitly approved call edges are verified. This does not model
dynamic imports, monkeypatching, higher-order functions, or external users.
"""
from __future__ import annotations

import ast
from pathlib import Path

EXPECTED = {
    "compiler.py": {
        ("run_optional_rea_release", "run_governed_pipeline"):
            "contracts.rea_pipeline.run_governed_pipeline",
        ("run_optional_rea_github_release", "run_optional_rea_release"):
            "compiler.run_optional_rea_release",
    },
    "contracts/rea_pipeline.py": {
        ("run_governed_pipeline", "reconcile_delivery"):
            "contracts.rea_release_reconciliation.reconcile_delivery",
    },
}


def validate_critical_import_identity(root: str | Path) -> dict:
    root = Path(root)
    violations: list[str] = []
    for relative, edges in EXPECTED.items():
        try:
            tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError):
            violations.append(f"invalid_module:{relative}")
            continue
        module = relative.removesuffix(".py").replace("/", ".")
        functions = {node.name: node for node in tree.body if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        imports = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    prefix = node.module
                elif module.startswith("contracts.") and node.level == 1:
                    prefix = "contracts" + ("." + node.module if node.module else "")
                else:
                    violations.append(f"unresolved_module_import:{relative}")
                    continue
                for item in node.names:
                    imports[item.asname or item.name] = f"{prefix}.{item.name}"
        for (owner, callee), target in edges.items():
            fn = functions.get(owner)
            if fn is None:
                violations.append(f"missing_owner:{relative}:{owner}")
                continue
            local = imports.copy()
            # Resolve function-local imports too, but reject rebinding and
            # call-through attributes rather than guessing what they target.
            for node in ast.walk(fn):
                if isinstance(node, ast.ImportFrom):
                    if node.level == 0:
                        prefix = node.module
                    elif module.startswith("contracts.") and node.level == 1:
                        prefix = "contracts" + ("." + node.module if node.module else "")
                    else:
                        violations.append(f"unresolved_import:{relative}:{owner}")
                        continue
                    for item in node.names:
                        local[item.asname or item.name] = f"{prefix}.{item.name}"
            # Function parameters must not shadow a pinned imported callee.
            parameters = (fn.args.posonlyargs + fn.args.args +
                          fn.args.kwonlyargs)
            if fn.args.vararg is not None:
                parameters.append(fn.args.vararg)
            if fn.args.kwarg is not None:
                parameters.append(fn.args.kwarg)
            if any(arg.arg in local and local[arg.arg] == target
                   for arg in parameters):
                violations.append(f"shadowed_parameter:{relative}:{owner}:{callee}")
            # An assignment at module level can replace an imported or
            # same-module function without changing the apparent call syntax.
            target_names = {name for name, identity in local.items()
                            if identity == target}
            for statement in tree.body:
                if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                    targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                    if any(isinstance(name, ast.Name) and name.id in target_names
                           for target_node in targets for name in ast.walk(target_node)):
                        violations.append(f"module_rebound_target:{relative}:{callee}")
            calls = []
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    name = node.func.id
                    resolved = local.get(name, module + "." + name if name in functions else None)
                    if resolved == target:
                        calls.append(node)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == callee:
                        violations.append(f"unresolved_attribute:{relative}:{owner}:{callee}")
            if len(calls) != 1:
                violations.append(f"identity_mismatch:{relative}:{owner}:{callee}:{len(calls)}")
            for node in ast.walk(fn):
                if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    names = {n.id for target_node in targets for n in ast.walk(target_node) if isinstance(n, ast.Name)}
                    if any(name in names for name, resolved in local.items() if resolved == target):
                        violations.append(f"rebound_target:{relative}:{owner}:{callee}")
    return {"status": "BLOCK" if violations else "PASS_SCOPED",
            "violations": tuple(sorted(set(violations))),
            "scope": "three_critical_static_call_edges"}
