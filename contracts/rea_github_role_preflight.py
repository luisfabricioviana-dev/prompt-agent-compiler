"""Read-only GitHub permission preflight for an authenticated token owner.

A repository role check does not establish token-scoped write permission.
Consequently this preflight is advisory, never a release authorization.
"""
from __future__ import annotations
import json
import re
import urllib.request

_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")

def check_github_actor_repository_role(repository: str, *, token: str, opener=None) -> str:
    if not isinstance(repository, str) or not _REPO.fullmatch(repository):
        raise ValueError("invalid_repository")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("github_token_missing")
    transport = opener if opener is not None else urllib.request.urlopen
    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    def retrieve(url):
        request = urllib.request.Request(url, headers=headers, method="GET")
        with transport(request, timeout=10) as response:
            raw = response.read(65_537)
        if len(raw) > 65_536:
            raise ValueError("response_oversized")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("response_invalid") from exc
        if not isinstance(data, dict):
            raise ValueError("response_invalid")
        return data

    actor = retrieve("https://api.github.com/user").get("login")
    if not isinstance(actor, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", actor):
        raise ValueError("actor_identity_unverified")
    data = retrieve("https://api.github.com/repos/" + repository +
                    "/collaborators/" + actor + "/permission")
    permission = data.get("permission")
    if permission not in ("admin", "maintain", "write"):
        raise ValueError("actor_write_role_unverified")
    return permission
