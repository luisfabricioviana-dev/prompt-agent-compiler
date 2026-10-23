"""Fail-closed artifact admission at the point of distribution.

Local immutable bytes are checked before any downstream publisher is invoked.
A successful verdict permits a subsequent governed decision; it does not publish.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

try:
    from .rea_security_gate import ArtifactEvidence, Verdict, evaluate_artifact, verify_artifact_bytes
except ImportError:
    from rea_security_gate import ArtifactEvidence, Verdict, evaluate_artifact, verify_artifact_bytes

@dataclass(frozen=True)
class Admission:
    verdict: Verdict
    path: str
    checked_digest: str | None = None

def admit_local_artifact(path: str, evidence: ArtifactEvidence, *,
                         max_size_bytes: int = 20_000_000) -> Admission:
    import hashlib
    if not isinstance(max_size_bytes, int) or isinstance(max_size_bytes, bool) or max_size_bytes < 1:
        return Admission(Verdict(False, ("artifact_size_policy_invalid",)), path)
    preliminary = evaluate_artifact(evidence)
    if not preliminary.allowed:
        return Admission(preliminary, path)
    try:
        candidate = Path(path)
        if not candidate.is_file() or candidate.is_symlink():
            return Admission(Verdict(False, ("artifact_source_not_regular_file",)), path)
        with candidate.open("rb") as source:
            payload = source.read(max_size_bytes + 1)
        if len(payload) > max_size_bytes:
            return Admission(Verdict(False, ("artifact_exceeds_size_limit",)), path)
    except (OSError, TypeError, ValueError):
        return Admission(Verdict(False, ("artifact_read_failed",)), path)
    checked = verify_artifact_bytes(payload, evidence.artifact_sha256)
    return Admission(checked, path, hashlib.sha256(payload).hexdigest() if checked.allowed else None)
