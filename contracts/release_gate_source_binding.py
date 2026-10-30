"""Pinned source inventory for the scoped differential release gate."""
import hashlib
from pathlib import Path

SOURCE_PATHS = (
    "compiler.py",
    "contracts/rea_pipeline.py",
    "contracts/release_import_identity_gate.py",
    "tests/fixtures/frozen_release_import_identity_wave55.py",
    "tools/build_release_gate_differential_report.py",
)


def source_digests(root: str | Path) -> dict[str, str]:
    root = Path(root)
    return {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
            for path in SOURCE_PATHS}
