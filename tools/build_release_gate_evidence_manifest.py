"""Bind differential evidence to GitHub Actions run and commit with a manifest.

The SHA-256 is over the report's raw bytes, excluding this manifest.
"""
import hashlib
import json
import os
from contracts.release_gate_source_binding import source_digests
from pathlib import Path


def build_manifest(report_path: Path, *, sha: str, run_id: str, run_attempt: str) -> dict:
    report_path = Path(report_path)
    raw = report_path.read_bytes()
    report = json.loads(raw)
    if report.get("status") != "PASS" or report.get("match_count") != report.get("case_count"):
        raise ValueError("differential_report_not_pass")
    if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha):
        raise ValueError("invalid_commit_sha")
    if not run_id.isdecimal() or not run_attempt.isdecimal():
        raise ValueError("invalid_workflow_identity")
    return {
        "schema": "release-gate-evidence-manifest-v1",
        "commit_sha": sha,
        "workflow_run_id": run_id,
        "workflow_run_attempt": run_attempt,
        "report_file": report_path.name,
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "report_status": report["status"],
        "case_count": report["case_count"],
        "match_count": report["match_count"],
        "scope": report["scope"],
        "source_sha256": source_digests(Path(".")),
    }


if __name__ == "__main__":
    src = Path("artifacts/release-gate-differential-report.json")
    manifest = build_manifest(src, sha=os.environ["GITHUB_SHA"],
                              run_id=os.environ["GITHUB_RUN_ID"],
                              run_attempt=os.environ["GITHUB_RUN_ATTEMPT"])
    Path("artifacts/release-gate-evidence-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
