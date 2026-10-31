"""Authenticated read-only retrieval and verification of a completed CI artifact.

All requests are GET-only; no release dispatch or GitHub mutation.
"""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tools.audit_postrun_release_archive import audit_postrun_archive

REPOSITORY = "luisfabricioviana-dev/prompt-agent-compiler"
ARTIFACT_NAME = "release-gate-differential-evidence"


def audit_remote_archive(*, run_id: str, commit_sha: str, attempt: str,
                         token: str, source_root: str | Path = ".",
                         opener=None) -> dict:
    if not token or not run_id.isdecimal() or len(commit_sha) != 40:
        return {"status": "BLOCK", "violations": ["invalid_remote_audit_inputs"]}
    open_url = opener or urlopen
    prefix = "https://api.github.com/repos/" + REPOSITORY
    headers = {"Accept": "application/vnd.github+json",
               "Authorization": "Bearer " + token,
               "X-GitHub-Api-Version": "2022-11-28"}
    try:
        listing_request = Request(prefix + "/actions/runs/" + run_id +
                                  "/artifacts?per_page=100", headers=headers)
        with open_url(listing_request, timeout=20) as handle:
            payload = json.load(handle)
        artifacts = payload.get("artifacts", [])
        matches = [a for a in artifacts if a.get("name") == ARTIFACT_NAME]
        if payload.get("total_count", 0) > 100 or len(matches) != 1:
            return {"status": "BLOCK", "violations": ["ambiguous_remote_artifacts"]}
        artifact = matches[0]
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, int) or artifact_id <= 0:
            return {"status": "BLOCK", "violations": ["invalid_remote_artifact_id"]}
        # The GitHub archive endpoint redirects to a short-lived download URL.
        download_request = Request(prefix + "/actions/artifacts/" +
                                   str(artifact_id) + "/zip", headers=headers)
        with open_url(download_request, timeout=30) as handle:
            raw = handle.read(10_000_001)
        if len(raw) > 10_000_000:
            return {"status": "BLOCK", "violations": ["remote_archive_too_large"]}
        with TemporaryDirectory() as temp:
            archive = Path(temp) / "evidence.zip"
            archive.write_bytes(raw)
            return audit_postrun_archive(
                archive, artifact, run_id=run_id, commit_sha=commit_sha,
                attempt=attempt, source_root=source_root)
    except (OSError, ValueError, TypeError, KeyError, HTTPError, URLError):
        return {"status": "BLOCK", "violations": ["remote_archive_unverifiable"]}


if __name__ == "__main__":
    result = audit_remote_archive(
        run_id=os.environ["EVIDENCE_RUN_ID"],
        commit_sha=os.environ["EVIDENCE_COMMIT_SHA"],
        attempt=os.environ["EVIDENCE_RUN_ATTEMPT"],
        token=os.environ.get("GITHUB_TOKEN", ""),
    )
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS_SCOPED" else 1)
