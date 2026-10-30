"""Run-scoped, digest-bound gate evidence (no signature/provenance attestation)."""
from dataclasses import dataclass
import hashlib

@dataclass(frozen=True)
class GateEvidence:
    run_id: str
    node_id: str
    gate_id: str
    payload: bytes
    artifact_id: str | None = None
    artifact_sha256: str | None = None

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()
