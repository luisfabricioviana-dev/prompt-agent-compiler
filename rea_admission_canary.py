"""Read-only local REA admission canary; not a runtime release or provenance attestation."""
import hashlib
from contracts.rea_security_gate import ArtifactEvidence, evaluate_artifact, verify_artifact_bytes

def inspect_candidate(payload: bytes):
    digest = hashlib.sha256(payload).hexdigest()
    # No independent provenance verifier is connected. Always fail closed.
    evidence = ArtifactEvidence(True, False, False, False, digest)
    policy = evaluate_artifact(evidence)
    checked = verify_artifact_bytes(payload, digest)
    reasons = sorted(set(policy.reasons + checked.reasons))
    return {"sha256": digest, "state": "BLOCKED" if reasons else "ADMISSIBLE_CANDIDATE",
            "reasons": reasons, "dispatch_performed": False, "publication_performed": False}
