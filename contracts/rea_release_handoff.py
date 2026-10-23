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
    # A boolean is only a local invocation prerequisite, not authenticated proof.
    # Production callers must obtain this fact from a verified release authority.
    if authorized_for_release is not True:
        return HandoffResult(False, ("release_authorization_absent",))
    if (not isinstance(max_size_bytes, int) or isinstance(max_size_bytes, bool)
        or max_size_bytes <= 0 or not isinstance(payload, bytes)
        or not payload or len(payload) > max_size_bytes):
        return HandoffResult(False, ("payload_unavailable_or_oversized",))
    if not isinstance(evidence, ArtifactEvidence):
        return HandoffResult(False, ("artifact_evidence_missing",))
    if not callable(callback):
        return HandoffResult(False, ("callback_unavailable",))
    policy = evaluate_artifact(evidence)
    if not policy.allowed:
        return HandoffResult(False, policy.reasons)
    verified = verify_artifact_bytes(payload, evidence.artifact_sha256)
    if not verified.allowed:
        return HandoffResult(False, verified.reasons)
    digest = hashlib.sha256(payload).hexdigest()
    try:
        callback(payload, digest)
    except Exception:
        return HandoffResult(False, ("downstream_dispatch_failed",))
    return HandoffResult(True, (), digest)
