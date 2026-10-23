# Governed Factory + REA — destination adoption contract

Status: **CANDIDATE / NOT DEPLOYED**. This adapter is a proposal, not a statement that running agents have received a new skill.

Canonical upstream: [Agente de Aprendizagem e Inovação PR #23](https://github.com/luisfabricioviana-dev/Apredizagem-e-Inova-o/pull/23), merged as `857618df6a33f963dafde98f39d3ba359fad275b`.

Destination applicability: Runtime and agent compilation; require trusted release evidence, immutable SHA and idempotent adoption.

## Portable contracts (adopt selectively)
- `SHIPPED_ARTIFACT_THREAT_MODEL_v1`: treat every client-delivered binary as inspectable; no hiding secrets in compiled artifacts.
- `SECRET_PLACEMENT_GATE_v1`: long-lived credentials remain in controlled server/key-management boundaries, never distributed source or assets.
- `BINARY_RECONSTRUCTION_EVIDENCE_GATE_v1`: distinguish pseudocode, recovered source, behavioral equivalence and byte-identical rebuild.
- `REA_LEARNING_ROUTER_v1`: route learning through evidence, provenance, security, sandbox, regression and approval; REA is an optional external adapter.
- Factory release requires exact-SHA CI, authenticated reviewer/owner gates, effective provider policies and auditable recovery.

## Destination acceptance before merge
1. Map every proposed rule to an existing destination runtime hook or create an explicit integration design; documentation alone does not activate the behavior.
2. Verify the upstream merge SHA and provenance; pin immutable versions rather than tracking unreviewed branch heads.
3. Test unsafe-client-secret rejection, fake proof rejection, stale-SHA rejection, and release fail-closed behavior in this destination.
4. Run this repository's native regression and CI; preserve existing domain and channel contracts.
5. Obtain destination approval before merge or declaring `CANONICAL_IMPLEMENTED`.

## Isolation and rollback
No domain documents, process facts, editorial profiles, training data or credentials cross repositories. Revert this destination PR to roll back the candidate integration without mutating upstream. After tests, record the real runtime hook, test evidence and resulting destination merge SHA here.
