"""Fail-closed bounded handoff to an explicit downstream release callback.

The callback is invoked only with immutable verified bytes; the caller is
responsible for authenticated approvals, environment credentials and policy.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import hashlib

try:
    from .rea_security_gate import ArtifactEvidence, Verdict, evaluate_artifact, verify_artifact_bytes
except ImportError:
    from rea_security_gate import ArtifactEvidence, Verdict, evaluate_artifact, verify_artifact_bytes

@dataclass(frozen=True)
class HandoffResult:
    accepted: bool
    reasons: tuple[str, ...]
    digest: str | None = None

def governed_artifact_handoff(
    payload: bytes,
    evidence: ArtifactEvidence,
    *,
    authorized_for_release: bool,
    callback: Callable[[bytes, str], None],
    max_size_bytes: int = 20_000_000,
) -> HandoffResult:
    """Compatibility API: never dispatches regardless of caller's boolean.

    The caller must use authorized_handoff with a destination-bound signature
    and a durable release claim. A truthy boolean is not authorization.
    """
    return HandoffResult(False, ("authenticated_release_authority_required",))


def verify_handoff_candidate(
    payload: bytes,
    evidence: ArtifactEvidence,
    *,
    max_size_bytes: int = 20_000_000,
) -> HandoffResult:
    """Pure byte/policy validation. Does not invoke downstream callbacks."""
    if (not isinstance(max_size_bytes, int) or isinstance(max_size_bytes, bool)
        or max_size_bytes <= 0 or not isinstance(payload, bytes)
        or not payload or len(payload) > max_size_bytes):
        return HandoffResult(False, ("payload_unavailable_or_oversized",))
    if not isinstance(evidence, ArtifactEvidence):
        return HandoffResult(False, ("artifact_evidence_missing",))
    policy = evaluate_artifact(evidence)
    if not policy.allowed:
        return HandoffResult(False, policy.reasons)
    verified = verify_artifact_bytes(payload, evidence.artifact_sha256)
    if not verified.allowed:
        return HandoffResult(False, verified.reasons)
    return HandoffResult(True, (), hashlib.sha256(payload).hexdigest())
