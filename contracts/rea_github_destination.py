"""Opt-in GitHub repository identity resolver.

Read-only metadata retrieval over TLS using a caller-provisioned GitHub token.
The resolver is NOT a dispatch adapter and never publishes artifacts.
"""
from __future__ import annotations
import json
import re
import urllib.request

_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")

def resolve_github_destination(repository: str, *, token: str, opener=None,
                               expected_repository_id: int | None = None) -> str:
    if not isinstance(repository, str) or not _REPO.fullmatch(repository):
        raise ValueError("invalid_repository")
    if (expected_repository_id is not None and
        (type(expected_repository_id) is not int or expected_repository_id <= 0)):
        raise ValueError("expected_repository_id_invalid")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("github_token_missing")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + repository,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        method="GET",
    )
    transport = opener if opener is not None else urllib.request.urlopen
    with transport(request, timeout=10) as response:
        data = response.read(65_537)
    if len(data) > 65_536:
        raise ValueError("metadata_oversized")
    try:
        metadata = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("metadata_invalid") from exc
    actual = metadata.get("full_name") if isinstance(metadata, dict) else None
    if not isinstance(actual, str) or not _REPO.fullmatch(actual):
        raise ValueError("github_identity_unverified")
    if actual != repository:
        raise ValueError("github_identity_mismatch")
    if expected_repository_id is not None:
        remote_id = metadata.get("id")
        if type(remote_id) is not int or remote_id != expected_repository_id:
            raise ValueError("github_repository_id_mismatch")
    return actual
