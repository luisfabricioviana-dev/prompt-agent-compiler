"""Static release-consumer inventory; deliberately narrow and fail-closed.

Only code paths listed here are assessed. External consumers and dynamic imports
are explicitly outside the scope. This file never performs release operations.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ConsumerCoverage:
    consumer: str
    operation: str
    governed: bool
    limitation: str


INVENTORY = (
    ConsumerCoverage("contracts.rea_release_node.ReleaseNode.inspect_delivery",
                     "read_only_audit", True, "opt_in_callers"),
    ConsumerCoverage("contracts.release_audit_service.ReleaseAuditService.inspect",
                     "read_only_audit", True, "opt_in_callers"),
    ConsumerCoverage("contracts.release_audit_service.ReleaseAuditService.inspect_legacy",
                     "legacy_quarantine", True, "opt_in_callers"),
    ConsumerCoverage("contracts.rea_release_node.ReleaseNode.execute",
                     "optional_dispatch", False, "separate_authorization_and_replay_contract"),
    ConsumerCoverage("compiler.run_optional_rea_release",
                     "legacy_optional_release", False, "not_governed_audit_consumer"),
    ConsumerCoverage("compiler.run_optional_rea_github_release",
                     "legacy_optional_release", False, "not_governed_audit_consumer"),
    ConsumerCoverage("contracts.rea_pipeline.run_governed_pipeline",
                     "legacy_optional_release", False, "returns_pipeline_result"),
)


def review_consumer_coverage(*, require_all_governed: bool = False) -> dict:
    if require_all_governed and any(not entry.governed for entry in INVENTORY):
        return {"status": "BLOCK", "reason": "legacy_consumers_not_migrated",
                "inventory": INVENTORY}
    return {"status": "INCOMPLETE", "reason": "external_consumers_unverified",
            "inventory": INVENTORY}
