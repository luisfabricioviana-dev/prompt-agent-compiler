"""Read-only GitHub API artifact reconciliation, for post-run audit only.

Never invoked by release dispatch. Uses the externally supplied GITHUB_TOKEN
with minimum actions:read permission; no credential is persisted or logged.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from contracts.release_gate_artifact_reconciliation import (
    ARTIFACT_NAME, reconcile_artifact_metadata,
)


def audit_published_artifact(*, repository: str, run_id: str, commit_sha: str,
                             manifest_path: str | Path, token: str,
                             opener=None) -> dict:
    if not token:
        return {"status": "BLOCK", "violations": ["missing_api_credential"]}
    if repository != "luisfabricioviana-dev/prompt-agent-compiler" or not run_id.isdecimal():
        return {"status": "BLOCK", "violations": ["invalid_api_target"]}
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        url = ("https://api.github.com/repos/" + repository +
               "/actions/runs/" + run_id + "/artifacts?per_page=100")
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
        })
        response = (opener or urllib.request.urlopen)(request, timeout=20)
        with response as handle:
            payload = json.load(handle)
        artifacts = payload.get("artifacts", [])
        matches = [item for item in artifacts if item.get("name") == ARTIFACT_NAME]
        if len(matches) != 1 or payload.get("total_count", 0) > 100:
            return {"status": "BLOCK", "violations": ["artifact_inventory_ambiguous"]}
        return reconcile_artifact_metadata(
            manifest, matches[0], expected_run_id=run_id,
            expected_commit_sha=commit_sha)
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError):
        return {"status": "BLOCK", "violations": ["api_artifact_unverifiable"]}


if __name__ == "__main__":
    result = audit_published_artifact(
        repository=os.environ["GITHUB_REPOSITORY"],
        run_id=os.environ["EVIDENCE_RUN_ID"],
        commit_sha=os.environ["EVIDENCE_COMMIT_SHA"],
        manifest_path=os.environ["EVIDENCE_MANIFEST_PATH"],
        token=os.environ.get("GITHUB_TOKEN", ""),
    )
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS_SCOPED" else 1)
