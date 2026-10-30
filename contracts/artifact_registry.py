"""In-process artifact registry for v0.2.10 runtime execution.

Records are bound to ArtifactContract identity and producer, digest-addressed,
idempotent for identical bytes, and fail closed on conflicting rewrites.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable, Mapping

from .execution_spec_v2 import ArtifactContract, ExecutionNode


class ArtifactRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    artifact_type: str
    producer_node: str
    sha256: str
    byte_size: int
    state: str
    sequence: int


class ArtifactRegistry:
    def __init__(self, contracts: Iterable[ArtifactContract] = ()) -> None:
        self._contracts: dict[str, ArtifactContract] = {}
        self._records: dict[str, ArtifactRecord] = {}
        self._sequence = 0
        for contract in contracts:
            if not isinstance(contract, ArtifactContract):
                raise TypeError("artifact_contract_invalid")
            if contract.artifact_id in self._contracts:
                raise ArtifactRegistryError(
                    f"artifact_contract_duplicate:{contract.artifact_id}"
                )
            self._contracts[contract.artifact_id] = contract

    def matches_contracts(self, contracts: Iterable[ArtifactContract]) -> bool:
        """Compare complete declared artifact contracts, not only IDs."""
        expected = tuple(contracts)
        return (
            len(expected) == len(self._contracts)
            and all(
                isinstance(contract, ArtifactContract)
                and self._contracts.get(contract.artifact_id) == contract
                for contract in expected
            )
        )

    @property
    def sequence(self) -> int:
        return self._sequence

    def get(self, artifact_id: str) -> ArtifactRecord:
        try:
            return self._records[artifact_id]
        except KeyError as exc:
            raise ArtifactRegistryError(
                f"artifact_record_missing:{artifact_id}"
            ) from exc

    def register_bytes(
        self,
        artifact_id: str,
        payload: bytes,
        *,
        producer_node: str,
    ) -> ArtifactRecord:
        contract = self._contracts.get(artifact_id)
        if contract is None:
            raise ArtifactRegistryError(
                f"artifact_contract_missing:{artifact_id}"
            )
        if producer_node != contract.producer_node:
            raise ArtifactRegistryError(
                f"artifact_producer_mismatch:{artifact_id}"
            )
        if not isinstance(payload, bytes):
            raise TypeError("artifact_payload_bytes_required")

        digest = hashlib.sha256(payload).hexdigest()
        existing = self._records.get(artifact_id)
        if existing is not None:
            if existing.sha256 != digest:
                raise ArtifactRegistryError(
                    f"artifact_digest_conflict:{artifact_id}"
                )
            return existing

        self._sequence += 1
        record = ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=contract.artifact_type,
            producer_node=producer_node,
            sha256=digest,
            byte_size=len(payload),
            state="VALID",
            sequence=self._sequence,
        )
        self._records[artifact_id] = record
        return record

    def record_node_outputs(
        self,
        node: ExecutionNode,
        outputs: Mapping[str, bytes],
    ) -> tuple[ArtifactRecord, ...]:
        if not isinstance(node, ExecutionNode):
            raise TypeError("execution_node_required")
        if not isinstance(outputs, Mapping):
            raise TypeError("artifact_outputs_mapping_required")

        expected = tuple(node.output_artifacts)
        expected_set = set(expected)
        supplied_set = set(outputs)

        for artifact_id in expected:
            if artifact_id not in supplied_set:
                raise ArtifactRegistryError(
                    f"artifact_output_missing:{artifact_id}"
                )
        for artifact_id in supplied_set - expected_set:
            raise ArtifactRegistryError(
                f"artifact_output_unexpected:{artifact_id}"
            )

        # Validate all contracts/producers/payload types before writing any
        # record so the operation is atomic from the registry's perspective.
        for artifact_id in expected:
            contract = self._contracts.get(artifact_id)
            if contract is None:
                raise ArtifactRegistryError(
                    f"artifact_contract_missing:{artifact_id}"
                )
            if contract.producer_node != node.node_id:
                raise ArtifactRegistryError(
                    f"artifact_producer_mismatch:{artifact_id}"
                )
            if not isinstance(outputs[artifact_id], bytes):
                raise TypeError("artifact_payload_bytes_required")

        # Preflight conflicting rewrites before applying any new record.
        for artifact_id in expected:
            existing = self._records.get(artifact_id)
            if existing is not None:
                digest = hashlib.sha256(outputs[artifact_id]).hexdigest()
                if existing.sha256 != digest:
                    raise ArtifactRegistryError(
                        f"artifact_digest_conflict:{artifact_id}"
                    )

        return tuple(
            self.register_bytes(
                artifact_id,
                outputs[artifact_id],
                producer_node=node.node_id,
            )
            for artifact_id in expected
        )
