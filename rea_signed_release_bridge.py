"""Fail-closed signed admission before the optional release pipeline.

This bridge accepts only bytes and externally signed fixture provenance.
It never enables dispatch by default. Real issuer custody and live runtime
adoption require independent evidence.
"""
from __future__ import annotations
from contracts.rea_pipeline import PipelineResult
from contracts.rea_security_gate import ArtifactEvidence
from rea_trusted_provenance_canary import inspect_signed_candidate


def run_signed_optional_release(conn, payload, statement, authorization, *,
                                trusted_provenance_issuer, verification_key,
                                issuer, issuer_key, destination_id,
                                observer_id, observer_key, dispatch, observe,
                                enable_dispatch=False, trusted_destination_resolver=None):
    admission = inspect_signed_candidate(
        payload, statement, trusted_issuer=trusted_provenance_issuer,
        verification_key=verification_key)
    if admission["state"] != "ADMISSIBLE_CANDIDATE":
        return PipelineResult("BLOCKED", ",".join(admission["reasons"]), admission["sha256"])
    evidence = ArtifactEvidence(
        client_delivered=True, embeds_long_lived_secret=False,
        includes_private_key=False, provenance_verified=True,
        artifact_sha256=admission["sha256"])
    from compiler import run_optional_rea_release
    return run_optional_rea_release(
        conn, payload, evidence, authorization, issuer=issuer, issuer_key=issuer_key,
        destination_id=destination_id, observer_id=observer_id, observer_key=observer_key,
        dispatch=dispatch, observe=observe, enable_dispatch=enable_dispatch,
        trusted_destination_resolver=trusted_destination_resolver)
