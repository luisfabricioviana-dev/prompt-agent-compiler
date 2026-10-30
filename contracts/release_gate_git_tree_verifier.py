"""Verify source evidence against Git objects of an explicit commit (read-only)."""
import hashlib
import re
import subprocess
from pathlib import Path

from contracts.release_gate_source_binding import SOURCE_PATHS


def verify_git_tree_sources(root: str | Path, commit_sha: str, recorded: dict) -> dict:
    root = Path(root)
    errors = []
    if not isinstance(commit_sha, str) or re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None:
        return {"status": "BLOCK", "violations": ["invalid_git_commit_identity"]}
    try:
        head = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
                              check=True, capture_output=True, timeout=15).stdout.decode().strip()
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify",
                                 commit_sha + "^{commit}"],
                                check=True, capture_output=True, timeout=15).stdout.decode().strip()
        if head != commit_sha or commit != commit_sha:
            errors.append("git_head_commit_mismatch")
        if not isinstance(recorded, dict) or set(recorded) != set(SOURCE_PATHS):
            errors.append("git_source_inventory_mismatch")
        else:
            for path in SOURCE_PATHS:
                result = subprocess.run(["git", "-C", str(root), "show", commit_sha + ":" + path],
                                        check=True, capture_output=True, timeout=15)
                expected = hashlib.sha256(result.stdout).hexdigest()
                if recorded[path] != expected:
                    errors.append("git_blob_digest_mismatch:" + path)
    except (subprocess.SubprocessError, OSError, UnicodeError):
        errors.append("git_source_unverifiable")
    return {"status": "BLOCK" if errors else "PASS_SCOPED",
            "violations": sorted(set(errors)),
            "scope": "local_git_object_verification_not_remote_attestation"}
