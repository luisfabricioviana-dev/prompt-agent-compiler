---
name: governed-release
description: Orchestrate an opt-in fail-closed governed release after artifact, capability, provenance, authorization, destination, and reconciliation gates have passed.
---

# Governed Release

Use this skill only after an execution artifact has passed its required review and release is explicitly requested.

This skill orchestrates release policy. Authentication, secrets, signing keys, external writes, and destination-side state remain at controlled runtime or MCP/server boundaries.

## Preconditions

1. The source `ExecutionSpecV2` is not INVALID or BLOCKED.
2. Required release capabilities resolve through `CapabilityRegistry`.
3. The artifact bytes and digest match.
4. Artifact policy and secret scanning pass.
5. Provenance is independently verifiable.
6. Release authorization is destination-bound and signed.
7. The destination identity is pinned or otherwise strongly resolved.
8. A reconciliation observer or equivalent delivery-verification path is configured.

## Release procedure

1. Start in dry-run mode unless dispatch is explicitly enabled by the caller and all mandatory gates pass.
2. Re-evaluate artifact admission immediately before handoff.
3. Fail-closed on missing provenance, invalid digest, missing capability, missing authorization, destination mismatch, replayed release identifier, unavailable ledger, or failed policy.
4. Consume release authority according to the durable single-use claim contract.
5. Dispatch only through the approved destination adapter.
6. Treat callback return as dispatch evidence, not final delivery proof.
7. Require signed observation and reconciliation before reporting confirmed delivery.
8. Preserve IN_DOUBT state after ambiguous callback, crash, timeout, or acknowledgement loss; do not blindly retry a consumed release identifier.

## Secret boundary

Never embed long-lived credentials, private keys, bearer tokens, or signing material in a distributed artifact, Skill file, fixture, or generated prompt.

## Output states

Return a release result that distinguishes at least:

- blocked;
- dry-run / admissible candidate;
- dispatch returned;
- IN_DOUBT;
- confirmed by signed reconciliation.

This Skill is opt-in and fail-closed. It never turns green CI into automatic publication and never upgrades candidate REA components into production-ready infrastructure by declaration.
