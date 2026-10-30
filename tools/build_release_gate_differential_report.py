"""Wave 61: deterministic, inspectable differential report for release gate."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "tests/fixtures/frozen_release_import_identity_wave55.py"

CASES = (
    ("baseline", None, None, None),
    ("module_rebind", "contracts/rea_pipeline.py", None, "\nreconcile_delivery = None\n"),
    ("local_rebind", "contracts/rea_pipeline.py", "    confirmed, reason = reconcile_delivery(",
     "    reconcile_delivery = None\n"),
    ("shadow_import", "compiler.py", "    return run_governed_pipeline(",
     "    from attacker.api import run_governed_pipeline\n"),
    ("nested_capture", "compiler.py", "    return run_governed_pipeline(",
     "    capture = lambda: run_governed_pipeline\n"),
    ("dynamic_exec", "compiler.py", "    return run_governed_pipeline(",
     "    exec('pass')\n"),
)


def build_differential_report(root: Path = ROOT) -> dict:
    spec = importlib.util.spec_from_file_location("frozen_gate_wave61", root / FROZEN.relative_to(ROOT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = []
    for name, relative, anchor, text in CASES:
        with TemporaryDirectory() as tmp:
            fixture = Path(tmp)
            for path in EXPECTED:
                target = fixture / path
                target.parent.mkdir(parents=True, exist_ok=True)
                copyfile(root / path, target)
            if relative is not None:
                target = fixture / relative
                source = target.read_text(encoding="utf-8")
                if anchor is None:
                    source += text
                else:
                    if anchor not in source:
                        raise ValueError("differential_fixture_anchor_missing:" + name)
                    source = source.replace(anchor, text + anchor, 1)
                target.write_text(source, encoding="utf-8")
            previous = module.validate_frozen_release_import_identity(fixture)
            current = validate_critical_import_identity(fixture)
            cases.append({"case": name, "matched": previous == current,
                          "old": previous, "current": current})
    return {"schema": "release-gate-differential-report-v1",
            "scope": "six_scoped_deterministic_fixtures_not_exhaustive",
            "case_count": len(cases),
            "match_count": sum(item["matched"] for item in cases),
            "status": "PASS" if all(item["matched"] for item in cases) else "BLOCK",
            "cases": cases}


if __name__ == "__main__":
    report = build_differential_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
