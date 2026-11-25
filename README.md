# Open Agent Reputation (OAR)

**Portable, verifiable reputation for AI agents — no blockchain, no wallet, no token, no service, no score.**

Agents are starting to hire, pay, and delegate to other agents — but there is no trustworthy way to know which ones are competent and which are fraudulent. The best-known answer, ERC-8004's on-chain Reputation Registry, was measured empirically in June 2026 and found wanting: *"cannot function as a trust signal: values are not commensurable, feedback records are rarely grounded in verifiable interactions, and reputation can be manipulated at minimal cost"* (Xiong et al., arXiv:2606.26028). Only 0.141% of its feedback rows trace to real paid work.

OAR defines a minimal, standalone, authority-free format for portable agent reputation: **client-signed receipts from real work**, publisher-signed chain inclusion, optional signed checkpoints, deterministic aggregation, and a portable bundle of ordinary files. A reputation record shows evidence and counts. There is no single trust score.

## Versions

| Version | Date | What changed |
|---|---|---|
| [v0.1](OAR-SPEC-v0.1.md) | 2026-11-19 | First draft: signed receipts, deterministic aggregation, one file per agent. |
| [v0.2](OAR-SPEC-v0.2.md) | 2026-11-19 | Receipts as separate files; receipt hash chain; revocation and agent response; receipt expiry; controlled task-type vocabulary; completion-rate threshold; key rotation; stated trust model. |
| [v0.3](OAR-SPEC-v0.3.md) | 2026-11-20 | **Current.** Client-signed receipts carry no chain fields — the publisher signs separate inclusion records (fixes concurrent-client ordering); optional signed checkpoints anchor history (git is not immutable); `did:key` is the only key encoding; `task.completed` → `task.ended`; two rates (`delivery_rate`, `clean_completion_rate`); verification reports validity and history as independent dimensions; 7 separate JSON Schemas; conformance classes and test vectors with real Ed25519 signatures. |

All versions are drafts. See §17 of the v0.3 specification for the full changelog and migration notes.

## Contents

```
OAR-SPEC-v0.1.md            # Specification v0.1
OAR-SPEC-v0.2.md            # Specification v0.2
OAR-SPEC-v0.3.md            # Specification v0.3 (current)
schemas/                    # 7 JSON Schemas (reputation, receipt, inclusion,
                            #   revocation, response, rotation, checkpoint)
test-vectors/               # 5 test cases with real Ed25519 signatures
generate-test-vectors.py    # Regenerates the test vectors and re-validates them
LICENSE.md                  # CC BY 4.0 — the specifications
LICENSE-CODE                # Apache 2.0 — reference code and schemas
NOTICE                      # Attribution notice
```

## How it works (in one minute)

1. A client hires an agent for a task.
2. The client issues a signed receipt: what the task was, what happened, and its Ed25519 signature. The client signs only the receipt content.
3. The agent (the publisher) writes and signs an inclusion record binding the receipt to its position in a hash chain.
4. Anyone verifies the bundle with no service: signatures, chain, revocations, aggregates.
5. Optionally, anyone publishes a signed checkpoint of the chain head, anchoring history outside the registry.

## Status

Draft. Open for comment. The specification is a file format and a set of rules — no server, no company, no account.

## Licenses

- Specifications: [CC BY 4.0](LICENSE.md)
- Reference code and schemas: [Apache 2.0](LICENSE-CODE)

## Author

Amirhossein Gorbaniyan
