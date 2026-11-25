# Open Agent Reputation (OAR)

**Specification — Version 0.1 (Draft)**
**Date:** 2026-11-19
**Author:** Amirhossein Gorbaniyan
**Status:** Draft — open for comment. Not yet final.
**License:** This specification is licensed under CC BY 4.0. Reference implementations are licensed under Apache 2.0.

## 0. Abstract

Agents are starting to hire, pay, and delegate to other agents — but there is no
trustworthy way to know which ones are competent and which are fraudulent. The
best-known answer, ERC-8004's on-chain Reputation Registry, was measured
empirically in June 2026 and found wanting: "cannot function as a trust signal:
values are not commensurable, feedback records are rarely grounded in verifiable
interactions, and reputation can be manipulated at minimal cost" (Xiong et al.,
arXiv:2606.26028). Only 0.141% of its feedback rows trace to real paid work.

The Open Agent Reputation (OAR) specification defines a minimal, standalone,
authority-free format for portable agent reputation: signed receipts from real
work, deterministic aggregation, and a single self-contained file that travels
with the agent. No blockchain, no wallet, no token, no service, no score, no one
to pay, no one to trust.

OAR does not claim to be the first portable agent reputation format. It claims
to be the minimal, standalone, authority-free, score-free one: a file, not a
service; evidence, not a score. See §10 for the honest comparison with adjacent
work.

## 1. Design principles

1. **Spec first, not a service.** OAR is a file format and a set of rules. No
   server, no registry, no company, no account.
2. **Receipts, not scores.** A reputation record shows evidence and counts. There
   is no single trust score: scores hide their inputs, cannot be compared across
   systems, and are exactly what the empirical study found broken.
3. **No authority.** No guild, no seed set, no operator, no meter. A receipt is
   verified against the client's own key; aggregates are recomputed by anyone
   from the receipts.
4. **Portable by design.** One self-contained file travels with the agent and is
   verifiable offline, with no query to any service.
5. **Aggregation by rule, not by model.** No LLM, no EigenTrust, no opaque
   algorithm. Counts and rates from a public rule (§5).
6. **Grounded in real work.** A receipt attests to a specific task the client
   hired the agent for. Praise without a task does not count.
7. **Privacy by design.** No PII in receipts; clients are pseudonymous keys;
   task descriptions are short summaries, not transcripts.
8. **Forkable and interoperable.** Anyone may extend the format. An OAR record
   may reference an ERC-8004 agentId, an A2A agent card, or an x402 payment
   receipt as supporting evidence.

## 2. The reputation file

A reputation file is one portable JSON file per agent. The file is self-contained:
identity, receipts, aggregates, and history. No external lookup is required to
verify it (except optional evidence URLs the issuer chose to include).

A registry — for git hosting — is a public repository with this layout:

```
/
├── README.md            # what this registry covers, who maintains it
├── agents/
│   ├── <agent-id>/
│   │   └── reputation.json
│   └── ...
├── SCHEMA.json          # JSON Schema for reputation files (Appendix B)
└── LICENSE              # CC BY 4.0 (recommended for the data)
```

The file may also live anywhere else: the agent's own site, an A2A agent card, a
personal page. The format is the standard; no registry is canonical.

## 3. The receipt

The receipt is the core unit. It is issued by the CLIENT — the party that hired
the agent for a specific task — never by the agent itself and never by a
platform.

### 3.1 Required fields

| Field | Type | Rule |
|---|---|---|
| `id` | string | UUID (v4 recommended). Unique across all receipts. |
| `spec_version` | string | `"0.1"` |
| `agent` | object | `{ "id": string (stable identifier, §6), "name": string }` |
| `client` | object | `{ "id": string (public-key fingerprint or did:key), "name": string (optional, pseudonymous) }` |
| `task` | object | `{ "id": string (client-assigned, unique per client — used for de-duplication), "type": string, "capabilities": string[], "description": string (short summary), "started": "YYYY-MM-DD", "completed": "YYYY-MM-DD" }` |
| `outcome` | object | `{ "status": "COMPLETED" \| "COMPLETED_WITH_ISSUES" \| "FAILED" \| "CANCELLED", "tags": string[] (e.g. "on-time", "as-specified"), "evidence_url": string (optional, link to the deliverable or proof) }` |
| `issued` | string | `YYYY-MM-DD` — when the client issued the receipt. |
| `signature` | object | `{ "algorithm": "Ed25519", "public_key": string, "signature": string }` |

### 3.2 Optional fields

`payment_ref` (string — e.g. an x402 receipt id, as supporting evidence; payment
is NOT required — many agent tasks are unpaid or test work).

### 3.3 Signature

- Algorithm: Ed25519.
- The signature covers the JCS-canonicalized (RFC 8785) JSON of the receipt
  with the `signature` object removed.
- `public_key` is the client's Ed25519 public key, as a hex-encoded SPKI DER
  string or a `did:key` identifier. The key travels in the receipt: verification
  needs no lookup.
- A receipt whose signature does not verify is ignored by aggregation (§5). It
  may remain in the file, marked by its failed check — the failure itself is
  information.

### 3.4 Outcome statuses

- `COMPLETED` — the task was delivered as agreed.
- `COMPLETED_WITH_ISSUES` — delivered, with problems the history note should
  name (late, partial, needed rework).
- `FAILED` — the agent did not deliver.
- `CANCELLED` — the task was cancelled before completion. Shown in the counts,
  excluded from the completion rate (§5): a cancellation is not, by itself,
  evidence about the agent.

## 4. The reputation record

| Field | Type | Rule |
|---|---|---|
| `id` | string | UUID of this reputation file. |
| `spec_version` | string | `"0.1"` |
| `agent` | object | `{ "id": string, "name": string, "identifiers": string[] }` — identifiers optional (website, A2A card URL, ERC-8004 agentId, did:web). |
| `receipts` | array | Receipt objects (§3). May be empty for a new agent. |
| `aggregates` | object | Derived values (§5), recomputed from `receipts`. |
| `history` | array | Records `{ "date", "note" }` — file updates, corrections, key changes. |

Aggregates are DERIVED, not asserted. Anyone recomputes them from `receipts`
using §5. If the stated aggregates do not match recomputation, the aggregates
are untrusted — but each receipt remains individually verifiable.

## 5. Aggregation rules

A receipt COUNTS if and only if ALL of the following hold:

1. Its signature verifies against the stated public key (§3.3).
2. Its `agent.id` matches the record's `agent.id`.
3. Its client key is not the agent's key (self-issued receipts never count).
4. Its dates are sane: `completed` ≥ `started`, `completed` ≤ today,
   `issued` ≥ `completed`.
5. It is not a duplicate: no earlier counted receipt shares the same client id
   and task id. The first one counts; later copies are ignored.
6. Its outcome status is one of the four in §3.4.

Derived values (all computed over counted receipts only):

- `total` — receipts in the file; `counted` — receipts passing the rules above.
- `distinct_clients` — distinct client ids among counted receipts.
- `by_task_type` — counts per task type and outcome.
- `by_outcome` — counts per outcome status.
- `completion_rate` — COMPLETED / (COMPLETED + COMPLETED_WITH_ISSUES + FAILED).
  CANCELLED is excluded (see §3.4).
- `first_receipt`, `last_receipt` — date range of counted receipts.
- `computed_at` — when the aggregates were computed.

There is no recency weighting in v0.1. Consumers filter by date from the
receipts themselves.

### Sybil honesty note

Distinct keys are cheap: key-based counting does NOT solve Sybil by itself. A
single actor can hold many keys. v0.1 mitigates by transparency, not by
claiming a solution: the record shows `distinct_clients` and the full receipt
list, so a consumer can see whether fifty receipts come from fifty clients or
from two. Grounding each receipt in a specific, signed, checkable task raises
the cost of fabrication compared with unsigned scores — but it does not
eliminate coordinated fakery. Stronger identity binding (verified
organizations, stake, web-of-trust) is explicitly future work for v0.2, not
claimed here.

## 6. Identity & keys

- An agent is identified by a stable identifier: a URL, a `did:web`, a `did:key`,
  or an ERC-8004 agentId. OAR does not create identity; it references it.
- A client is identified by its Ed25519 public key (fingerprint or `did:key`).
  Clients are pseudonymous by default.
- A new key is a new client id in v0.1 (key rotation is a known limitation).
- Interoperability: an OAR record MAY list an ERC-8004 agentId among its
  identifiers; a receipt MAY reference an x402 payment receipt (`payment_ref`);
  a receipt MAY be linked from an A2A agent card.

## 7. Verification

Anyone may verify a reputation file, with no service and no account:

1. Parse the file; check required fields against the schema (Appendix B).
2. Verify each receipt's signature (§3.3).
3. Apply the aggregation rules (§5) and compare the recomputed aggregates with
   the stated ones.
4. Check the history for corrections and key changes.

Verification levels, for consumers:

- **L0** — the file parses and receipts are present. No signatures checked.
  Not trusted.
- **L1** — all counted receipts' signatures verify. The v0.1 bar.
- **L2** — L1, plus every counted receipt's client key resolves to a published
  endpoint (did:web or URL). Future work.

A static, serverless verifier page is the planned reference tool. Verification
itself needs no service.

## 8. Privacy

- No PII in receipts: no names, emails, or wallet addresses, unless the client
  chooses to identify itself.
- Task descriptions are short summaries, never full transcripts.
- Evidence URLs are optional and the issuer's responsibility.
- A client may use a fresh key per agent (pseudonymity) — at the cost of its
  receipts counting as distinct clients. That trade-off is the client's choice,
  and the record makes it visible.

## 9. What OAR is not

- **Not a blockchain:** no chain, no token, no wallet, no gas.
- **Not a score:** no trust number, no ranking. Evidence and counts only.
- **Not a marketplace:** OAR records reputation; it does not match, hire, or pay.
- **Not an identity system:** it references identifiers; it does not issue them.
- **Not a guarantee:** a good record is evidence about the past, not insurance
  about the future.

## 10. Relation to prior art

- **ERC-8004 ("Trustless Agents", Draft):** the on-chain standard — Identity,
  Reputation, and Validation registries. The first empirical study (Xiong et
  al., arXiv:2606.26028, June 2026) found its Reputation Registry "cannot
  function as a trust signal"; only 3–15% of registrations (by chain) expose a
  valid file with a live endpoint; 73.5–90.6% of reviewers show coordinated
  Sybil behavior; only 0.141% of feedback rows trace to real paid work. OAR is
  interoperable with ERC-8004 (an OAR record may carry an ERC-8004 agentId) and
  off-chain by design.
- **Agent Guild / AGI-1:** the closest prior art — a live reputation network
  and an open interoperability standard (AGI-1) for portable reputation, built
  on W3C did:key identities and Verifiable Credentials, with Guild-signed Agent
  Passports and EigenTrust scoring, and metered reads. OAR differs on four
  points: (a) no central authority — no Guild signs anything; receipts are
  client-signed and self-verifying; (b) no score — evidence and counts only,
  no EigenTrust, no ranking; (c) no service and no meter — a file, free,
  verifiable offline; (d) reputation only — no discovery, routing, or escrow.
- **Kredo:** an open protocol (Scoping, v0.2.0) for skill attestations between
  agents, Ed25519-signed, no chain. OAR differs: receipts are issued by the
  client for specific hired work, not by agents about each other's skills, and
  OAR adds aggregation rules.
- **PARC (Portable Agent Reputation Credential):** a W3C Verifiable Credential
  wrapping a Verifiable Receipts Profile ledger commitment and nanda-rep scores,
  recomputable at admission. OAR differs: a standalone minimal format — no
  Merkle trees, no VRP/nanda-rep/ARP stack, no chapter or admission model.
- **ALMA (AdaSouls):** an open protocol (MIT) for agent identity, delegated
  authority, payments, and a marketplace, with reputation evidence (receipts,
  two-sided confirmations, delivery records) as one module — and no global
  score. OAR differs: reputation only, with no identity, delegation, or payment
  system.
- **Agent Colony:** one community's signed task receipts on A2A agent cards
  (blogged implementation; receipts are server-signed by the community key).
  OAR generalizes the receipt pattern into a published open specification with
  client-issued receipts.
- **x402:** payment receipts — the closest building block for grounding a
  receipt in a payment. OAR receipts MAY reference x402 receipts but do not
  require payment.
- **SENTINEL, VeriSwarm, Vorn:** adjacent products (attestations, incident
  registries, proprietary scoring) — not open formats.

The narrowed claim, stated plainly: OAR is not the first portable agent
reputation format. It is the minimal, standalone, authority-free, score-free
one — a file, not a service; evidence, not a score; no one to pay, no one to
trust.

## 11. Versioning

The specification follows Semantic Versioning. v0.1 is a draft.
Backward-incompatible changes bump the major version; new optional fields bump
the minor version.

## 12. Quickstart

Create a reputation file in ten minutes:

1. Generate an Ed25519 keypair for the agent's identity (any standard tool).
2. Write the reputation file: agent identity, empty receipts, zero aggregates.
3. After a client hires the agent for a task, the client issues a signed receipt
   (§3) and sends it to the agent.
4. The agent appends the receipt, recomputes the aggregates (§5), and publishes
   the file — in a git repository, on its own site, or linked from its A2A card.
5. Anyone verifies the file with the rules in §7 — no service required.

---

## Appendix A — Seed examples (ILLUSTRATIVE)

The examples below show the shape of a complete record. They are
ILLUSTRATIVE — invented to demonstrate the format, NOT real interactions.
Signatures and keys are placeholders, not real cryptographic values. Real seed
examples from public agent interactions are to be added after verification.

### A.1 — Illustrative research agent, strong record

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000001",
  "spec_version": "0.1",
  "agent": {
    "id": "https://example.org/agents/research-01",
    "name": "Example Research Agent",
    "identifiers": ["https://example.org/agents/research-01/card.json"]
  },
  "receipts": [
    {
      "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000101",
      "spec_version": "0.1",
      "agent": {
        "id": "https://example.org/agents/research-01",
        "name": "Example Research Agent"
      },
      "client": { "id": "did:key:ILLUSTRATIVE-CLIENT-A" },
      "task": {
        "id": "client-a-task-001",
        "type": "research-summary",
        "capabilities": ["web-search", "summarization"],
        "description": "Summarize five recent papers on agent trust frameworks.",
        "started": "2026-11-02",
        "completed": "2026-11-02"
      },
      "outcome": {
        "status": "COMPLETED",
        "tags": ["on-time", "as-specified"],
        "evidence_url": "https://example.org/deliverables/summary-001"
      },
      "issued": "2026-11-02",
      "signature": {
        "algorithm": "Ed25519",
        "public_key": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-KEY",
        "signature": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
      }
    },
    {
      "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000102",
      "spec_version": "0.1",
      "agent": {
        "id": "https://example.org/agents/research-01",
        "name": "Example Research Agent"
      },
      "client": { "id": "did:key:ILLUSTRATIVE-CLIENT-B" },
      "task": {
        "id": "client-b-task-014",
        "type": "research-summary",
        "capabilities": ["web-search", "summarization"],
        "description": "Compare three open agent frameworks for a build decision.",
        "started": "2026-11-09",
        "completed": "2026-11-10"
      },
      "outcome": {
        "status": "COMPLETED_WITH_ISSUES",
        "tags": ["late", "as-specified"],
        "evidence_url": "https://example.org/deliverables/comparison-014"
      },
      "issued": "2026-11-10",
      "signature": {
        "algorithm": "Ed25519",
        "public_key": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-KEY",
        "signature": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
      }
    }
  ],
  "aggregates": {
    "total": 2,
    "counted": 2,
    "distinct_clients": 2,
    "by_task_type": {
      "research-summary": { "COMPLETED": 1, "COMPLETED_WITH_ISSUES": 1, "FAILED": 0, "CANCELLED": 0 }
    },
    "by_outcome": { "COMPLETED": 1, "COMPLETED_WITH_ISSUES": 1, "FAILED": 0, "CANCELLED": 0 },
    "completion_rate": 0.5,
    "first_receipt": "2026-11-02",
    "last_receipt": "2026-11-10",
    "computed_at": "2026-11-19"
  },
  "history": [
    { "date": "2026-11-19", "note": "Illustrative seed record created for spec v0.1." }
  ]
}
```

### A.2 — Illustrative mixed record: what counts and what does not

A record with four receipts, of which two count:

- Receipt 1: COMPLETED, valid signature, distinct client → COUNTS.
- Receipt 2: FAILED, valid signature, distinct client → COUNTS (a failure is
  evidence too; hiding it would be dishonest).
- Receipt 3: a duplicate of receipt 1 (same client id, same task id) → does
  NOT count (rule 5).
- Receipt 4: signed by the agent's own key (self-issued) → does NOT count
  (rule 3).

Aggregates: `total` 4, `counted` 2, `distinct_clients` 2, `completion_rate`
0.5 (1 COMPLETED of 1 COMPLETED + 1 FAILED).

### A.3 — Illustrative standalone receipt (minimal shape)

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000201",
  "spec_version": "0.1",
  "agent": { "id": "https://example.org/agents/coding-02", "name": "Example Coding Agent" },
  "client": { "id": "did:key:ILLUSTRATIVE-CLIENT-C" },
  "task": {
    "id": "client-c-task-007",
    "type": "code-review",
    "capabilities": ["code-review"],
    "description": "Review a 400-line pull request for security issues.",
    "started": "2026-11-15",
    "completed": "2026-11-15"
  },
  "outcome": { "status": "COMPLETED", "tags": ["on-time"] },
  "issued": "2026-11-15",
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-KEY",
    "signature": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
  }
}
```

---

## Appendix B — JSON Schema (v0.1, sketch)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.org/oar/schema/0.1/reputation.json",
  "title": "Open Agent Reputation — Reputation File",
  "type": "object",
  "required": ["id", "spec_version", "agent", "receipts", "aggregates", "history"],
  "properties": {
    "id": { "type": "string", "minLength": 1 },
    "spec_version": { "type": "string", "const": "0.1" },
    "agent": {
      "type": "object",
      "required": ["id", "name"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "name": { "type": "string", "minLength": 1 },
        "identifiers": { "type": "array", "items": { "type": "string" } }
      }
    },
    "receipts": { "type": "array", "items": { "$ref": "#/$defs/receipt" } },
    "aggregates": {
      "type": "object",
      "required": ["total", "counted", "distinct_clients", "by_task_type", "by_outcome", "completion_rate"],
      "properties": {
        "total": { "type": "integer", "minimum": 0 },
        "counted": { "type": "integer", "minimum": 0 },
        "distinct_clients": { "type": "integer", "minimum": 0 },
        "by_task_type": { "type": "object" },
        "by_outcome": { "type": "object" },
        "completion_rate": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "first_receipt": { "type": ["string", "null"], "format": "date" },
        "last_receipt": { "type": ["string", "null"], "format": "date" },
        "computed_at": { "type": "string", "format": "date" }
      }
    },
    "history": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["date", "note"],
        "properties": {
          "date": { "type": "string", "format": "date" },
          "note": { "type": "string" }
        }
      }
    }
  },
  "$defs": {
    "receipt": {
      "type": "object",
      "required": ["id", "spec_version", "agent", "client", "task", "outcome", "issued", "signature"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "spec_version": { "type": "string", "const": "0.1" },
        "agent": {
          "type": "object",
          "required": ["id", "name"],
          "properties": {
            "id": { "type": "string", "minLength": 1 },
            "name": { "type": "string", "minLength": 1 }
          }
        },
        "client": {
          "type": "object",
          "required": ["id"],
          "properties": {
            "id": { "type": "string", "minLength": 1 },
            "name": { "type": "string" }
          }
        },
        "task": {
          "type": "object",
          "required": ["id", "type", "capabilities", "description", "started", "completed"],
          "properties": {
            "id": { "type": "string", "minLength": 1 },
            "type": { "type": "string", "minLength": 1 },
            "capabilities": { "type": "array", "items": { "type": "string" } },
            "description": { "type": "string", "minLength": 1 },
            "started": { "type": "string", "format": "date" },
            "completed": { "type": "string", "format": "date" }
          }
        },
        "outcome": {
          "type": "object",
          "required": ["status"],
          "properties": {
            "status": { "type": "string", "enum": ["COMPLETED", "COMPLETED_WITH_ISSUES", "FAILED", "CANCELLED"] },
            "tags": { "type": "array", "items": { "type": "string" } },
            "evidence_url": { "type": "string", "format": "uri" }
          }
        },
        "payment_ref": { "type": "string" },
        "issued": { "type": "string", "format": "date" },
        "signature": {
          "type": "object",
          "required": ["algorithm", "public_key", "signature"],
          "properties": {
            "algorithm": { "type": "string", "const": "Ed25519" },
            "public_key": { "type": "string", "minLength": 1 },
            "signature": { "type": "string", "minLength": 1 }
          }
        }
      }
    }
  }
}
```
