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
            # Imports nested in control flow are ambiguous: a conditional
            # import must not certify an unconditional call edge.
            for node in ast.walk(fn):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    direct = node in fn.body
                    if not direct and isinstance(node, ast.ImportFrom):
                        if any((item.asname or item.name) in target_names
                               for item in node.names):
                            violations.append(f"nested_import_target:{relative}:{owner}:{callee}")
                if isinstance(node, (ast.AugAssign, ast.For, ast.AsyncFor,
                                     ast.With, ast.AsyncWith, ast.ExceptHandler)):
                    candidates = []
                    if isinstance(node, ast.AugAssign):
                        candidates = [node.target]
                    elif isinstance(node, (ast.For, ast.AsyncFor)):
                        candidates = [node.target]
                    elif isinstance(node, (ast.With, ast.AsyncWith)):
                        candidates = [item.optional_vars for item in node.items
                                      if item.optional_vars is not None]
                    elif isinstance(node, ast.ExceptHandler) and node.name:
                        if node.name in target_names:
                            violations.append(f"indirect_rebind:{relative}:{owner}:{callee}")
                    if any(isinstance(name, ast.Name) and name.id in target_names
                           for candidate in candidates for name in ast.walk(candidate)):
                        violations.append(f"indirect_rebind:{relative}:{owner}:{callee}")
            # Dynamic namespace writes and reflective mutation cannot be
            # resolved statically. Quarantine them in pinned critical owners.
            for node in ast.walk(fn):
                if not isinstance(node, ast.Call):
                    continue
                symbol = node.func.id if isinstance(node.func, ast.Name) else (
                    node.func.attr if isinstance(node.func, ast.Attribute) else None)
                if symbol in {"exec", "eval", "globals", "locals", "setattr", "delattr"}:
                    violations.append(f"dynamic_namespace_mutation:{relative}:{owner}:{symbol}")
                elif symbol == "__import__":
                    violations.append(f"dynamic_import:{relative}:{owner}")
            # Resolve aliases to dangerous builtins conservatively. A local
            # alias assignment is unsafe even if the alias is never invoked:
            # static evidence cannot prove benign runtime effects.
            risky = {"exec", "eval", "globals", "locals", "setattr", "delattr", "__import__"}
            aliases = set(risky)
            changed = True
            while changed:
                changed = False
                for node in ast.walk(fn):
                    if isinstance(node, (ast.Assign, ast.NamedExpr)):
                        value = node.value
                        if not isinstance(value, ast.Name) or value.id not in aliases:
                            continue
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        for target_node in targets:
                            if isinstance(target_node, ast.Name) and target_node.id not in aliases:
                                aliases.add(target_node.id)
                                changed = True
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in aliases and node.func.id not in risky:
                        violations.append(f"aliased_dynamic_operation:{relative}:{owner}:{node.func.id}")
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
