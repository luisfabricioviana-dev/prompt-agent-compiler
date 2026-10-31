"""Post-run read-only audit of a downloaded GitHub evidence artifact ZIP.

Operator supplies the archive, run identity, and API-observed artifact record.
No release or dispatch capability is present.
"""
import hashlib
import io
import json
import zipfile
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory

from contracts.release_gate_artifact_reconciliation import reconcile_artifact_metadata
from contracts.release_gate_evidence_verifier import verify_evidence


def audit_postrun_archive(archive: str | Path, artifact: dict, *,
                          run_id: str, commit_sha: str, attempt: str,
                          source_root: str | Path) -> dict:
    archive = Path(archive)
    try:
        raw = archive.read_bytes()
        expected = artifact.get("digest")
        # Verify provider's archive digest when present, before extracting.
        if expected != "sha256:" + hashlib.sha256(raw).hexdigest():
            return {"status": "BLOCK", "violations": ["archive_digest_mismatch"]}
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = zf.namelist()
            expected_names = {
                "release-gate-differential-report.json",
                "release-gate-evidence-manifest.json",
            }
            if len(names) != len(expected_names) or set(names) != expected_names:
                return {"status": "BLOCK", "violations": ["archive_inventory_mismatch"]}
            for info in zf.infolist():
                mode = (info.external_attr >> 16) & 0o170000
                if (info.is_dir() or info.flag_bits & 0x1
                        or mode not in (0, 0o100000)):
                    return {"status": "BLOCK", "violations": ["unsafe_archive_entry"]}
            if any(info.file_size > 1_000_000 for info in zf.infolist()):
                return {"status": "BLOCK", "violations": ["archive_entry_too_large"]}
            try:
                report = zf.read("release-gate-differential-report.json")
                manifest_raw = zf.read("release-gate-evidence-manifest.json")
            except (EOFError, RuntimeError, zipfile.BadZipFile, zlib.error):
                return {"status": "BLOCK", "violations": ["archive_entry_integrity_failure"]}
            for info in zf.infolist():
                content = report if info.filename == "release-gate-differential-report.json" else manifest_raw
                if len(content) != info.file_size:
                    return {"status": "BLOCK", "violations": ["archive_entry_size_mismatch"]}
        manifest = json.loads(manifest_raw)
        metadata = reconcile_artifact_metadata(
            manifest, artifact, expected_run_id=run_id,
            expected_commit_sha=commit_sha)
        with TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "release-gate-differential-report.json"
            manifest_path = Path(tmp) / "release-gate-evidence-manifest.json"
            report_path.write_bytes(report)
            manifest_path.write_bytes(manifest_raw)
            integrity = verify_evidence(
                report_path, manifest_path, commit_sha=commit_sha,
                run_id=run_id, run_attempt=attempt, source_root=source_root)
        errors = metadata["violations"] + integrity["violations"]
        return {"status": "BLOCK" if errors else "PASS_SCOPED",
                "violations": sorted(set(errors)),
                "scope": "archive_bytes_plus_local_source_integrity_not_external_attestation"}
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile):
        return {"status": "BLOCK", "violations": ["archive_unverifiable"]}
