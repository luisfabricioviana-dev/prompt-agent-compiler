# REA multi-agent consumer candidate — compiler

This repository opts into **contract review only**, not automatic execution.
Canonical shared runtime: `luisfabricioviana-dev/Apredizagem-e-Inova-o` PR #156.
AVIA integration contract: `luisfabricioviana-dev/agente-youtube` PR #549.

## Domain invariant
Compiler validates specs; cannot silently elevate tool privileges.

## Adoption conditions
- Import tested REA package only after approved release/version pin; do not copy core source into this domain repository.
- Use explicit local allowlisted scope, authenticated operator-controlled executor and externally sandboxed runner.
- Default role is read-only scout; no delegation, remote access, edits or publication without distinct authorization.
- Require SHA-anchored cross-repo CI, independence of critique, task evidence, and independent domain gate.
- `PUBLICATION=BLOCKED`. This manifest is not an agent deployment, credential provisioning or an authorization to act.
