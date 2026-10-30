"""Independent, read-only validation of differential report and CI manifest."""
import hashlib
import json
from pathlib import Path


def verify_evidence(report_path: str | Path, manifest_path: str | Path,
                    *, commit_sha: str, run_id: str, run_attempt: str) -> dict:
    try:
        raw = Path(report_path).read_bytes()
        report = json.loads(raw)
        manifest = json.loads(Path(manifest_path).read_bytes())
    except (OSError, ValueError, UnicodeError) as exc:
        return {"status": "BLOCK", "violations": ["unreadable_evidence:" + type(exc).__name__]}
    violations = []
    if report.get("schema") != "release-gate-differential-report-v1":
        violations.append("unexpected_report_schema")
    if manifest.get("schema") != "release-gate-evidence-manifest-v1":
        violations.append("unexpected_manifest_schema")
    if manifest.get("report_file") != Path(report_path).name:
        violations.append("report_name_mismatch")
    if manifest.get("report_sha256") != hashlib.sha256(raw).hexdigest():
        violations.append("report_digest_mismatch")
    for key, expected in (("commit_sha", commit_sha),
                          ("workflow_run_id", run_id),
                          ("workflow_run_attempt", run_attempt)):
        if manifest.get(key) != expected:
            violations.append(key + "_mismatch")
    cases = report.get("cases")
    if not isinstance(cases, list) or not cases:
        violations.append("missing_cases")
    else:
        if len(cases) != report.get("case_count"):
            violations.append("case_count_mismatch")
        if sum(x.get("matched") is True for x in cases if isinstance(x, dict)) != report.get("match_count"):
            violations.append("match_count_mismatch")
        if any(not isinstance(x, dict) or x.get("old") != x.get("current") or x.get("matched") is not True for x in cases):
            violations.append("case_diagnostic_mismatch")
    if report.get("status") != "PASS" or report.get("match_count") != report.get("case_count"):
        violations.append("report_not_pass")
    for key in ("status", "case_count", "match_count", "scope"):
        manifest_key = "report_status" if key == "status" else key
        if manifest.get(manifest_key) != report.get(key):
            violations.append("manifest_" + key + "_mismatch")
    return {"status": "BLOCK" if violations else "PASS_SCOPED",
            "violations": sorted(set(violations)),
            "scope": "offline_integrity_and_consistency_not_external_attestation"}
