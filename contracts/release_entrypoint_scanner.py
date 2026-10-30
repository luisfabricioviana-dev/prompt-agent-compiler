"""Conservative AST scanner for known release entrypoints.

Scans Python syntax, never executes project code. Detects drift in monitored
entrypoint modules and names. This does NOT discover dynamic imports, external
callers, or every release-related function in the repository.
"""
from __future__ import annotations
import ast
from pathlib import Path

from .release_consumer_inventory import INVENTORY

MONITORED_FILES = (
    "compiler.py",
    "contracts/rea_release_node.py",
    "contracts/rea_pipeline.py",
    "contracts/release_audit_service.py",
)
RELEASE_PREFIXES = ("run_optional_rea_", "inspect_", "execute", "run_governed_pipeline")


def scan_release_entrypoints(root: str | Path) -> dict:
    root = Path(root)
    known = {entry.consumer for entry in INVENTORY}
    discovered: set[str] = set()
    errors: list[str] = []
    for relative in MONITORED_FILES:
        path = root / relative
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative)
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"unreadable_or_invalid:{relative}")
            continue
        module = relative.removesuffix(".py").replace("/", ".")
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith(RELEASE_PREFIXES):
                    discovered.add(module + "." + node.name)
            elif isinstance(node, ast.ClassDef) and node.name in ("ReleaseNode", "ReleaseAuditService"):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if method.name.startswith(RELEASE_PREFIXES):
                            discovered.add(module + "." + node.name + "." + method.name)
    unknown = tuple(sorted(discovered - known))
    missing = tuple(sorted(known & {
        "compiler.run_optional_rea_release",
        "compiler.run_optional_rea_github_release",
        "contracts.rea_pipeline.run_governed_pipeline",
        "contracts.rea_release_node.ReleaseNode.execute",
        "contracts.rea_release_node.ReleaseNode.inspect_delivery",
        "contracts.release_audit_service.ReleaseAuditService.inspect",
        "contracts.release_audit_service.ReleaseAuditService.inspect_legacy",
    } - discovered))
    if errors or unknown or missing:
        return {"status": "BLOCK", "reason": "release_entrypoint_inventory_drift",
                "unknown": unknown, "missing": missing, "errors": tuple(errors)}
    return {"status": "PASS_SCOPED", "reason": "monitored_release_entrypoints_classified",
            "unknown": (), "missing": (), "errors": ()}
