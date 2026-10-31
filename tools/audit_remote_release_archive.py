"""Authenticated read-only retrieval and verification of a completed CI artifact.

All requests are GET-only; no release dispatch or GitHub mutation.
"""
import json
import os
import re
from urllib.parse import urlsplit
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler

from tools.audit_postrun_release_archive import audit_postrun_archive

REPOSITORY = "luisfabricioviana-dev/prompt-agent-compiler"
ARTIFACT_NAME = "release-gate-differential-evidence"

class SafeArtifactRedirect(HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (target.scheme != 'https' or not target.hostname or target.username is not None
                or target.password is not None or target.port not in (None, 443)):
            raise URLError('untrusted_archive_redirect')
        request = super().redirect_request(req, fp, code, msg, headers, newurl)
        if request is None:
            return None
        for key in list(request.headers):
            if key.lower() in {'authorization', 'cookie', 'proxy-authorization'}:
                del request.headers[key]
        for key in list(request.unredirected_hdrs):
            if key.lower() in {'authorization', 'cookie', 'proxy-authorization'}:
                del request.unredirected_hdrs[key]
        return request



def audit_remote_archive(*, run_id: str, commit_sha: str, attempt: str,
                         token: str, source_root: str | Path = ".",
                         opener=None) -> dict:
    if (not token or not run_id.isdecimal() or not attempt.isdecimal()
            or re.fullmatch(r'[0-9a-f]{40}', commit_sha) is None):
        return {"status": "BLOCK", "violations": ["invalid_remote_audit_inputs"]}
    open_url = opener or build_opener(SafeArtifactRedirect()).open
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
        if not isinstance(artifacts, list) or not isinstance(payload.get('total_count'), int):
            return {'status': 'BLOCK', 'violations': ['invalid_remote_inventory']}
        matches = [a for a in artifacts if a.get("name") == ARTIFACT_NAME]
        if payload['total_count'] != len(artifacts) or len(matches) != 1:
            return {"status": "BLOCK", "violations": ["ambiguous_remote_artifacts"]}
        artifact = matches[0]
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, int) or artifact_id <= 0:
            return {"status": "BLOCK", "violations": ["invalid_remote_artifact_id"]}
        # The GitHub archive endpoint redirects to a short-lived download URL.
        download_request = Request(prefix + "/actions/artifacts/" +
                                   str(artifact_id) + "/zip", headers=headers)
        with open_url(download_request, timeout=30) as handle:
            status = getattr(handle, "status", 200)
            if status != 200:
                return {"status": "BLOCK", "violations": ["unexpected_archive_http_status"]}
            final_url = getattr(handle, "url", None)
            if final_url is not None and urlsplit(final_url).scheme != "https":
                return {"status": "BLOCK", "violations": ["unexpected_archive_url_scheme"]}
            declared_length = getattr(handle, "headers", {}).get("Content-Length")
            if declared_length is not None:
                if not declared_length.isdecimal() or int(declared_length) > 10_000_000:
                    return {"status": "BLOCK", "violations": ["invalid_archive_content_length"]}
            chunks = []
            total_bytes = 0
            while True:
                requested = min(65536, 10_000_001 - total_bytes)
                chunk = handle.read(requested)
                if not isinstance(chunk, bytes):
                    return {"status": "BLOCK", "violations": ["invalid_archive_read_type"]}
                if len(chunk) > requested:
                    return {"status": "BLOCK", "violations": ["archive_overread"]}
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > 10_000_000:
                    return {"status": "BLOCK", "violations": ["remote_archive_too_large"]}
                chunks.append(chunk)
            raw = b"".join(chunks)
        if declared_length is not None and len(raw) != int(declared_length):
            return {"status": "BLOCK", "violations": ["truncated_archive_response"]}
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
