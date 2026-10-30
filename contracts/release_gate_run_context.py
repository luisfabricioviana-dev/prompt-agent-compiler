"""Cross-check CI run metadata against a differential evidence manifest.

This validates runner-provided metadata, not a remotely signed GitHub attestation.
"""
import re


def verify_run_context(manifest: dict, *, repository: str, workflow: str,
                       event: str, sha: str, run_id: str, attempt: str,
                       expected_repository: str) -> dict:
    failures = []
    if repository != expected_repository or not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        failures.append("repository_identity_mismatch")
    if workflow != "Full project regression":
        failures.append("workflow_identity_mismatch")
    if event not in {"pull_request", "push", "workflow_dispatch"}:
        failures.append("unapproved_workflow_event")
    for field, value in (("commit_sha", sha), ("workflow_run_id", run_id),
                         ("workflow_run_attempt", attempt)):
        if manifest.get(field) != value:
            failures.append(field + "_mismatch")
    if not re.fullmatch("[0-9a-f]{40}", sha):
        failures.append("invalid_commit_identity")
    if not run_id.isdecimal() or not attempt.isdecimal():
        failures.append("invalid_workflow_run_identity")
    return {"status": "BLOCK" if failures else "PASS_SCOPED",
            "violations": sorted(set(failures)),
            "scope": "runner_metadata_consistency_not_external_github_attestation"}
