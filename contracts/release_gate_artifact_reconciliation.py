"""Read-only reconciliation of API-observed workflow artifact metadata.

API responses must be fetched independently by the caller. This routine does
not claim signature verification or authenticate arbitrary supplied objects.
"""
import re


ARTIFACT_NAME = "release-gate-differential-evidence"


def reconcile_artifact_metadata(manifest: dict, artifact: dict, *,
                                expected_run_id: str, expected_commit_sha: str) -> dict:
    errors = []
    if not isinstance(manifest, dict) or not isinstance(artifact, dict):
        return {"status": "BLOCK", "violations": ["invalid_metadata_shape"]}
    if artifact.get("name") != ARTIFACT_NAME:
        errors.append("artifact_name_mismatch")
    if artifact.get("expired") is not False:
        errors.append("artifact_expired_or_unknown")
    if not isinstance(artifact.get("id"), int) or artifact["id"] <= 0:
        errors.append("invalid_artifact_id")
    digest = artifact.get("digest")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        errors.append("invalid_archive_digest")
    workflow_run = artifact.get("workflow_run")
    if not isinstance(workflow_run, dict):
        errors.append("missing_artifact_workflow_run")
    else:
        if str(workflow_run.get("id")) != expected_run_id:
            errors.append("artifact_run_id_mismatch")
        if workflow_run.get("head_sha") != expected_commit_sha:
            errors.append("artifact_commit_mismatch")
    if manifest.get("workflow_run_id") != expected_run_id:
        errors.append("manifest_run_id_mismatch")
    if manifest.get("commit_sha") != expected_commit_sha:
        errors.append("manifest_commit_mismatch")
    return {"status": "BLOCK" if errors else "PASS_SCOPED",
            "violations": sorted(set(errors)),
            "artifact_id": artifact.get("id"),
            "archive_digest": digest,
            "scope": "independently_fetched_api_metadata_not_signed_attestation"}
