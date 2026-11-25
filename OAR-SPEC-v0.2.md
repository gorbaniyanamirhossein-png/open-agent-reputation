# Open Agent Reputation (OAR)

**Specification — Version 0.2 (Draft)**
**Date:** 2026-11-19
**Author:** Amirhossein Gorbaniyan
**Status:** Draft — open for comment. Not yet final.
**License:** This specification is licensed under CC BY 4.0. Reference implementations are licensed under Apache 2.0.
**Supersedes:** v0.1 (2026-11-19). See §14 for the changelog and migration notes.

## 0. Abstract

Agents are starting to hire, pay, and delegate to other agents — but there is no
trustworthy way to know which ones are competent and which are fraudulent. The
best-known answer, ERC-8004's on-chain Reputation Registry, was measured
empirically in June 2026 and found wanting: "cannot function as a trust signal:
values are not commensurable, feedback records are rarely grounded in verifiable
interactions, and reputation can be manipulated at minimal cost" (Xiong et al.,
arXiv:2606.26028). Only 0.141% of its feedback rows trace to real paid work.

The Open Agent Reputation (OAR) specification defines a minimal, standalone,
authority-free format for portable agent reputation: client-signed receipts
from real work, a hash chain that makes silent deletion detectable, deterministic
aggregation, and a portable bundle of ordinary files. No blockchain, no wallet,
no token, no service, no score, no one to pay, no one to trust.

OAR does not claim to be the first portable agent reputation format. It claims
to be the minimal, standalone, authority-free, score-free one: a bundle of
files, not a service; evidence, not a score. See §13 for the honest comparison
with adjacent work.

## 1. Trust model

OAR's guarantees, stated plainly before any detail:

**What OAR guarantees**

- **Authenticity of receipts.** A receipt is signed by the client that hired the
  agent (Ed25519). Anyone can verify the signature with the key carried in the
  receipt itself — no lookup, no service.
- **Detectable deletion.** Receipts are linked in a hash chain (§5) and the
  canonical record lives in a public git registry (§3). Removing a published
  receipt breaks the chain or shows up in git history. The agent cannot silently
  drop an unfavorable receipt from a record anyone has already seen.
- **Recomputable aggregates.** Every number in the record is derived from the
  receipts by a public rule (§7). Anyone recomputes them; a mismatch is
  visible.

**What OAR does NOT guarantee**

- **Sybil-proofing.** Distinct keys are cheap. v0.2 adds real mitigations
  (§7.2) but does not claim to solve coordinated fakery. A consumer must weigh
  the evidence, including how many distinct clients it comes from.
- **Truth of the task.** A valid signature proves the client said it, not that
  the task happened as described. Evidence URLs and payment references raise
  confidence; they do not prove facts.
- **Future performance.** A good record is evidence about the past, not
  insurance about the future.

**Incentives (honest note).** A receipt costs the client one signature and one
small file. Clients sign because it helps them re-hire and recommend good
agents, and because platforms and marketplaces can automate issuance. OAR v0.2
does not solve incentives; it lowers the cost to near zero and makes the
receipt portable, so one signature serves every future counterparty.

## 2. Design principles

1. **Spec first, not a service.** OAR is a file format and a set of rules. No
   server, no company, no account, no meter.
2. **Receipts, not scores.** A reputation record shows evidence and counts. There
   is no single trust score: scores hide their inputs, cannot be compared across
   systems, and are exactly what the empirical study found broken.
3. **No authority.** No guild, no seed set, no operator. A receipt is verified
   against the client's own key; aggregates are recomputed by anyone from the
   receipts.
4. **Portable by design.** A reputation bundle is a directory of ordinary files
   (git, zip, folder) that travels with the agent and is verifiable offline,
   with no query to any service. L0/L1 verification never needs the network.
5. **Aggregation by rule, not by model.** No LLM, no EigenTrust, no opaque
   algorithm. Counts and rates from a public rule (§7).
6. **Grounded in real work.** A receipt attests to a specific task the client
   hired the agent for. Praise without a task does not count.
7. **Correctable.** A wrong receipt can be revoked by its issuer; an agent can
   respond. A record that cannot be corrected is a liability machine (§8).
8. **Privacy by design.** No PII in receipts, revocations, or responses; clients
   are pseudonymous keys; task descriptions are short summaries, not
   transcripts.
9. **Forkable and interoperable.** Anyone may extend the format. An OAR record
   may reference an ERC-8004 agentId, an A2A agent card, or an x402 payment
   receipt as supporting evidence.

## 3. The reputation bundle

A reputation bundle is a directory of ordinary JSON files — one bundle per
agent. Receipts are separate files: a busy agent's history grows without making
any single file enormous, and each receipt can be checked, cited, and revoked
independently.

A registry — for git hosting — is a public repository with this layout:

```
/
├── README.md                 # what this registry covers, who maintains it
├── agents/
│   └── <agent-id>/
│       ├── reputation.json   # the record: identity, chain head, receipt index, aggregates
│       ├── receipts/
│       │   ├── <receipt-id>.json
│       │   └── ...
│       ├── revocations/      # client-signed revocations (§8)
│       │   └── <revocation-id>.json
│       └── responses/        # agent-signed responses (§8)
│           └── <response-id>.json
├── SCHEMA.json               # JSON Schema for OAR files (Appendix B)
└── LICENSE                   # CC BY 4.0 (recommended for the data)
```

The canonical record is the public git registry. Git history is the audit trail:
every receipt ever published remains in history even if removed from HEAD, and
the verifier flags receipts present in history but absent from the current index
(§10). A bundle may also be carried elsewhere (the agent's own site, a zip, an
A2A card link) — but a bundle that was never published in a public registry has
no public history, and a consumer should weigh that.

## 4. The receipt

The receipt is the core unit. It is issued by the CLIENT — the party that hired
the agent for a specific task — never by the agent itself and never by a
platform. One file per receipt: `receipts/<receipt-id>.json`.

### 4.1 Required fields

| Field | Type | Rule |
|---|---|---|
| `id` | string | UUID (v4 recommended). Unique across all receipts. The file name is `<id>.json`. |
| `spec_version` | string | `"0.2"` |
| `agent` | object | `{ "id": string (stable identifier, §9), "name": string }` |
| `client` | object | `{ "id": string (public-key fingerprint or did:key), "name": string (optional, pseudonymous), "verified_endpoint": string (optional, did:web or URL publishing this key — see §7.2) }` |
| `task` | object | `{ "id": string (client-assigned, unique per client — used for de-duplication), "type": string (from the vocabulary in §4.4), "subtype": string (optional, free-form), "capabilities": string[], "description": string (short summary), "started": "YYYY-MM-DD", "completed": "YYYY-MM-DD" }` |
| `outcome` | object | `{ "status": "COMPLETED" \| "COMPLETED_WITH_ISSUES" \| "FAILED" \| "CANCELLED", "tags": string[] (e.g. "on-time", "as-specified"), "evidence_url": string (optional, link to the deliverable or proof) }` |
| `issued` | string | `YYYY-MM-DD` — when the client issued the receipt. |
| `previous_receipt_hash` | string \| null | SHA-256 (hex) of the previous receipt in the chain (§5); `null` for the first receipt. |
| `signature` | object | `{ "algorithm": "Ed25519", "public_key": string, "signature": string }` |

### 4.2 Optional fields

- `valid_until` (string, `YYYY-MM-DD`) — the client may set an expiry. An
  expired receipt does not count (§7). Default: no expiry.
- `payment_ref` (string — e.g. an x402 receipt id, as supporting evidence;
  payment is NOT required — many agent tasks are unpaid or test work).

### 4.3 Signature

- Algorithm: Ed25519.
- The signature covers the JCS-canonicalized (RFC 8785) JSON of the receipt
  with the `signature` object removed. (The chain hash in §5 is computed over
  the receipt WITH the signature object — the two canonicalizations serve
  different purposes and must not be confused.)
- `public_key` is the client's Ed25519 public key, as a hex-encoded SPKI DER
  string or a `did:key` identifier. The key travels in the receipt: verification
  needs no lookup.
- A receipt whose signature does not verify is ignored by aggregation (§7). It
  may remain in the bundle, marked by its failed check — the failure itself is
  information.

### 4.4 Outcome statuses and task types

Outcome statuses:

- `COMPLETED` — the task was delivered as agreed.
- `COMPLETED_WITH_ISSUES` — delivered, with problems the response or history
  note should name (late, partial, needed rework).
- `FAILED` — the agent did not deliver.
- `CANCELLED` — the task was cancelled before completion. Shown in the counts,
  excluded from the completion rate (§7): a cancellation is not, by itself,
  evidence about the agent.

Task types (controlled vocabulary — aggregates by type only work with a shared
vocabulary):

`research`, `coding`, `data-analysis`, `writing`, `customer-support`, `design`,
`automation`, `other`.

`subtype` is free-form (e.g. type `research`, subtype `literature-review`). A
receipt whose `type` is not in the vocabulary is still valid, but its type
counts as `other` for aggregation — a label mistake must not invalidate a
receipt.

## 5. The receipt chain

Receipts are linked in a hash chain so that silent deletion is detectable.

- Each receipt carries `previous_receipt_hash`: the SHA-256 (hex) of the
  JCS-canonicalized JSON of the previous receipt, INCLUDING its `signature`
  object. The first receipt in a chain has `previous_receipt_hash: null`.
- Chain order is deterministic: by `issued` date, then by receipt `id` as a
  tiebreak.
- The reputation record commits to `chain_head`: the SHA-256 (hex) of the
  JCS-canonicalized JSON of the latest receipt, including its signature object.
  An empty record has `chain_head: null`.
- The verifier recomputes the chain from the receipt files (§10). A missing
  receipt breaks the chain: the next receipt's `previous_receipt_hash` will not
  match any receipt in the bundle.

Honest limits: an agent can rebuild a chain from scratch after deleting a
receipt — the rebuilt chain is internally consistent. What the chain prevents
is SILENT deletion from a record anyone has already seen: the rebuilt chain has
a different head, and anyone who recorded the old head (the public registry's
git history, a client, a consumer) detects the rewrite. The chain plus the
public registry is the mechanism; neither alone is enough. A fresh agent with no
published history can start clean — which is visible as "no history," not as a
good record.

The chain is a linked list of hashes inside ordinary files. It is not a
blockchain: no consensus, no mining, no token, no network.

## 6. The reputation record

`reputation.json` — the record is an index plus derived values. It does NOT
embed receipts.

| Field | Type | Rule |
|---|---|---|
| `id` | string | UUID of this reputation file. |
| `spec_version` | string | `"0.2"` |
| `agent` | object | `{ "id": string, "name": string, "identifiers": string[] }` — identifiers optional (website, A2A card URL, ERC-8004 agentId, did:web). |
| `chain_head` | string \| null | SHA-256 (hex) of the latest receipt (§5); `null` when the record has no receipts. |
| `receipt_index` | array | Entries `{ "id": string, "sha256": string, "file": string (relative path, e.g. "receipts/<id>.json") }`, one per receipt file in the bundle. |
| `aggregates` | object | Derived values (§7), recomputed from the receipt files. |
| `rotations` | array | Key-rotation statements (§9). May be empty. |
| `history` | array | Signed history entries (§6.1). |

Aggregates are DERIVED, not asserted. Anyone recomputes them from the receipt
files using §7. If the stated aggregates do not match recomputation, the
aggregates are untrusted — but each receipt remains individually verifiable.

### 6.1 History

History entries are structured and signed by the agent (the publisher):

`{ "date": "YYYY-MM-DD", "action": string, "receipt_id": string (optional), "note": string, "signature": { "algorithm": "Ed25519", "public_key": string, "signature": string } }`

Actions: `RECEIPT_ADDED`, `RECEIPT_REVOKED`, `RESPONSE_ADDED`, `KEY_ROTATED`,
`CORRECTION`. The signature covers the JCS-canonicalized entry minus the
`signature` object.

History is informational. The authoritative audit trail is the registry's git
log (§3).

## 7. Aggregation rules

### 7.1 What counts

A receipt COUNTS if and only if ALL of the following hold:

1. Its signature verifies against the stated public key (§4.3).
2. Its `agent.id` matches the record's `agent.id`.
3. Its client key is not the agent's key (self-issued receipts never count).
4. Its dates are sane: `completed` ≥ `started`, `completed` ≤ today,
   `issued` ≥ `completed`.
5. It is not a duplicate: no earlier counted receipt shares the same client id
   and task id. The first one counts; later copies are ignored.
6. It is not expired: if `valid_until` is set, `valid_until` ≥ today.
7. It is not revoked: no valid revocation (§8) references its id.
8. It respects the rate limit (§7.2, rule R1).
9. It is a member of the chain: its hash appears in the chain recomputed from
   the bundle, ending at the record's `chain_head` (§5).
10. Its outcome status is one of the four in §4.4.

### 7.2 Sybil mitigations (real rules, honestly bounded)

- **R1 — Rate limit.** At most one counted receipt per (client id, agent id)
  per calendar day, by `completed` date. If several qualify, the
  earliest-issued counts. This slows farming: each fake receipt needs a
  distinct day or a distinct key.
- **R2 — Verified clients.** A client MAY publish its public key at a
  `verified_endpoint` (did:web or URL) named in the receipt. The record reports
  `counted_from_verified_clients` and `distinct_verified_clients` separately, so
  a consumer can choose to trust only receipts from clients whose keys are
  published at endpoints it recognizes. Verification of an endpoint is the
  consumer's choice; the format only carries the link.
- **R3 — Transparency.** The record always shows `distinct_clients` and the full
  receipt list, so a consumer can see whether fifty receipts come from fifty
  clients or from two.

These raise the cost of fabrication. They do not eliminate coordinated fakery —
see §1.

### 7.3 Derived values

All computed over counted receipts only, unless noted:

- `total` — receipt files in the bundle; `counted` — receipts passing §7.1;
  `revoked` — receipts with a valid revocation.
- `distinct_clients` — distinct client ids among counted receipts (keys linked
  by a valid rotation, §9, count as one client).
- `distinct_verified_clients`, `counted_from_verified_clients` — the R2 subset.
- `by_task_type` — counts per task type (vocabulary, §4.4) and outcome.
- `by_outcome` — counts per outcome status.
- `completion_rate` — COMPLETED / (COMPLETED + COMPLETED_WITH_ISSUES + FAILED).
  CANCELLED is excluded (see §4.4). Shown ONLY when the denominator is ≥ 5;
  otherwise `null` (insufficient data — a 1/1 record must not look perfect).
- `counted_last_12_months` — counted receipts completed in the 12 months before
  `computed_at`.
- `recent_completion_rate` — the same rate over the last-12-months subset, with
  the same ≥ 5 threshold; otherwise `null`.
- `first_receipt`, `last_receipt` — date range of counted receipts.
- `computed_at` — when the aggregates were computed.

There is no recency weighting. Consumers filter by date from the receipts
themselves.

## 8. Revocation & agent response

### 8.1 Revocation

A client may revoke its own receipt — issued in error, fraudulent, or disputed.
A revocation is a separate file, `revocations/<revocation-id>.json`:

`{ "id", "spec_version": "0.2", "receipt_id", "reason_code": "ISSUED_IN_ERROR" | "FRAUDULENT" | "TASK_DISPUTED" | "OTHER", "reason": string (short, free text), "issued": "YYYY-MM-DD", "signature": { "algorithm": "Ed25519", "public_key": string, "signature": string } }`

- The signature is the CLIENT's, over the JCS-canonicalized revocation minus
  the `signature` object, and the key MUST match the receipt's client key.
- A revoked receipt remains in the bundle but does not count (§7.1, rule 7).
  The aggregates report it under `revoked`.
- Revocation is permanent in v0.2: there is no un-revoke. A client that
  changes its mind issues a new receipt for the same task (same task id — the
  de-duplication rule counts the first receipt, so the new receipt is the one
  that counts only if the revoked one is excluded, which it is).

### 8.2 Agent response

An agent may attach one signed response to a receipt — its side of the story.
A response is a separate file, `responses/<response-id>.json`:

`{ "id", "spec_version": "0.2", "receipt_id", "agent": { "id", "name" }, "text": string (short), "issued": "YYYY-MM-DD", "signature": { "algorithm": "Ed25519", "public_key": string, "signature": string } }`

- The signature is the AGENT's, over the JCS-canonicalized response minus the
  `signature` object.
- A response is informational ONLY. It never changes the outcome, the counts,
  or the rates.
- At most one response per receipt per agent is recognized; if several exist,
  the earliest-issued is the response and the rest are ignored.

## 9. Identity, keys & rotation

- An agent is identified by a stable identifier: a URL, a `did:web`, a `did:key`,
  or an ERC-8004 agentId. OAR does not create identity; it references it.
- A client is identified by its Ed25519 public key (fingerprint or `did:key`).
  Clients are pseudonymous by default.
- **Rotation.** A subject (agent or client) that changes keys publishes a
  rotation statement in the record's `rotations` array:

  `{ "subject": "agent" | "client", "old_key": string, "new_key": string, "date": "YYYY-MM-DD", "signature": { "algorithm": "Ed25519", "public_key": string (= old_key), "signature": string } }`

  The signature is by the OLD key, over the JCS-canonicalized statement minus
  the `signature` object. The verifier follows valid rotation chains: keys
  linked by rotations count as one client for `distinct_clients`, and an agent's
  responses and history signed under a rotated key remain attributable.
- Interoperability: an OAR record MAY list an ERC-8004 agentId among its
  identifiers; a receipt MAY reference an x402 payment receipt (`payment_ref`);
  a receipt MAY be linked from an A2A agent card.

## 10. Verification

Anyone may verify a reputation bundle, with no service and no account:

1. Parse `reputation.json`; check required fields against the schema
   (Appendix B).
2. For each `receipt_index` entry: load the file, check its SHA-256 matches the
   index, check the receipt's `id` matches, verify the signature (§4.3).
   Flag receipt files present in `receipts/` but missing from the index
   (present but not indexed), and index entries whose files are missing (error).
3. Recompute the chain (§5) from the receipt files and compare with
   `chain_head`. A break means a receipt is missing or the chain was rebuilt —
   report it.
4. Apply the revocations (§8.1) and the aggregation rules (§7); compare the
   recomputed aggregates with the stated ones.
5. Check history entries' signatures (§6.1) and rotation statements (§9).
6. If the bundle lives in a git registry, check git history for receipt files
   that were published and later removed from HEAD; report them as
   "published, then removed."

Verification levels, for consumers:

- **L0** — the record parses and receipt files are present. No signatures
  checked. Not trusted.
- **L1** — all counted receipts' signatures verify, the chain is intact, and the
  aggregates recompute. Fully offline. The v0.2 bar.
- **L2** — L1, plus every counted receipt's client has a `verified_endpoint`
  that resolves and publishes the same public key. L2 is the only level that
  may need a network fetch; a consumer that cannot fetch treats L2 as
  "uncheckable," not as failed.

A static, serverless verifier page is the planned reference tool. Verification
itself needs no service.

## 11. Privacy

- No PII in receipts, revocations, or responses: no names, emails, or wallet
  addresses, unless the issuer chooses to identify itself.
- Task descriptions are short summaries, never full transcripts.
- Evidence URLs are optional and the issuer's responsibility.
- A client may use a fresh key per agent (pseudonymity) — at the cost of its
  receipts counting as distinct clients. That trade-off is the client's choice,
  and the record makes it visible.
- Revocation does not erase history: a revoked receipt remains in the bundle and
  in git history, marked revoked. OAR is a record, not a forgetfulness machine.

## 12. What OAR is not

- **Not a blockchain:** no chain network, no token, no wallet, no gas, no
  consensus. The hash chain (§5) is a linked list inside ordinary files.
- **Not a score:** no trust number, no ranking. Evidence and counts only.
- **Not a marketplace:** OAR records reputation; it does not match, hire, or pay.
- **Not an identity system:** it references identifiers; it does not issue them.
- **Not a guarantee:** a good record is evidence about the past, not insurance
  about the future.

## 13. Relation to prior art

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
  no EigenTrust, no ranking; (c) no service and no meter — a bundle of files,
  free, verifiable offline; (d) reputation only — no discovery, routing, or
  escrow.
- **Kredo:** an open protocol (Scoping, v0.2.0) for skill attestations between
  agents, Ed25519-signed, no chain. OAR differs: receipts are issued by the
  client for specific hired work, not by agents about each other's skills, and
  OAR adds a hash chain, revocation, and aggregation rules.
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
  client-issued receipts, a chain, and revocation.
- **x402:** payment receipts — the closest building block for grounding a
  receipt in a payment. OAR receipts MAY reference x402 receipts but do not
  require payment.
- **SENTINEL, VeriSwarm, Vorn:** adjacent products (attestations, incident
  registries, proprietary scoring) — not open formats.

The narrowed claim, stated plainly: OAR is not the first portable agent
reputation format. It is the minimal, standalone, authority-free, score-free
one — a bundle of files, not a service; evidence, not a score; no one to pay,
no one to trust.

## 14. Versioning, changelog & migration

The specification follows Semantic Versioning. v0.2 is a draft.
Backward-incompatible changes bump the major version; new optional fields bump
the minor version. (In the 0.x series, minor versions may break compatibility;
each version's changelog states exactly what broke.)

### Changelog — v0.1 → v0.2

1. **Trust model stated up front (new §1).** v0.1 scattered its assumptions;
   v0.2 states what OAR guarantees and what it does not, including the
   incentives gap.
2. **Receipts are separate files (breaking).** v0.1 embedded all receipts in one
   file, which grows without bound. v0.2 stores one file per receipt and turns
   the record into an index (§3, §6). The unit of portability is now the
   bundle, not a single file.
3. **Receipt hash chain (new §5).** v0.1 had no way to detect a silently deleted
   receipt — the agent publishes its own record. v0.2 links receipts in a hash
   chain and anchors completeness in the public git registry.
4. **Revocation and agent response (new §8).** v0.1 had no correction mechanism.
   Clients may now revoke their receipts; agents may respond.
5. **Receipt expiry (new).** Receipts may carry `valid_until`; expired receipts
   do not count. Aggregates add last-12-months counts (§7.3).
6. **Sybil mitigations in the rules (new §7.2).** v0.1 admitted the problem and
   offered only transparency. v0.2 adds a per-client daily rate limit and a
   verified-client extension.
7. **Controlled task-type vocabulary (new §4.4).** v0.1's free-form types made
   by-type aggregates meaningless.
8. **Completion-rate threshold (new §7.3).** Rates are shown only when the
   denominator is ≥ 5; a 1/1 record no longer looks perfect.
9. **Structured, signed history (revised §6.1).** v0.1's history was vague and
   unsigned.
10. **Key rotation (new §9).** v0.1 treated a new key as a new identity.
11. **Verification level L2 defined (revised §10).** v0.1 listed L2 as "future
    work"; v0.2 defines it through the verified-client extension.
12. **Schema completed (revised Appendix B).** v0.1's schema was a sketch; v0.2's
    covers the record, the receipt, the revocation, and the response.

### Migration — v0.1 → v0.2

1. Move each receipt from the v0.1 file into its own file under `receipts/`.
2. Receipts are client-signed, so they cannot be upgraded in place: each client
   re-issues its receipts in v0.2 format (same task id, new receipt id, new
   signature, chain fields included). Old v0.1 files remain valid v0.1 records.
3. Build the chain in `issued`-date order (§5) and set `chain_head`.
4. Recompute the aggregates under §7 and write the `receipt_index`.
5. Record the migration in history (`CORRECTION`, "migrated from v0.1; chain
   restarts").

## 15. Quickstart

Create a reputation bundle in ten minutes:

1. Generate an Ed25519 keypair for the agent's identity (any standard tool).
2. Create the bundle directory with `reputation.json`: agent identity, empty
   receipt index, `chain_head: null`, zero aggregates.
3. After a client hires the agent for a task, the client issues a signed receipt
   (§4) — one small JSON file — and sends it to the agent.
4. The agent places the receipt in `receipts/`, links it into the chain (§5),
   adds it to the `receipt_index`, recomputes the aggregates (§7), and publishes
   the bundle in a public git registry (§3).
5. Anyone verifies the bundle with the rules in §10 — no service required.

---

## Appendix A — Seed examples (ILLUSTRATIVE)

The examples below show the shape of a v0.2 bundle. They are ILLUSTRATIVE —
invented to demonstrate the format, NOT real interactions. Keys, signatures,
and hashes are placeholders, not real cryptographic values. Real seed examples
from public agent interactions are to be added after verification.

### A.1 — Illustrative bundle layout

```
agents/research-01/
├── reputation.json
├── receipts/
│   ├── ILLUSTRATIVE-...-0101.json
│   └── ILLUSTRATIVE-...-0102.json
├── revocations/
└── responses/
```

### A.2 — Illustrative v0.2 receipt (second in its chain)

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000102",
  "spec_version": "0.2",
  "agent": {
    "id": "https://example.org/agents/research-01",
    "name": "Example Research Agent"
  },
  "client": {
    "id": "did:key:ILLUSTRATIVE-CLIENT-B",
    "verified_endpoint": "https://example.org/.well-known/oar-client-b.json"
  },
  "task": {
    "id": "client-b-task-014",
    "type": "research",
    "subtype": "framework-comparison",
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
  "valid_until": "2027-11-10",
  "previous_receipt_hash": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0101",
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-KEY",
    "signature": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
  }
}
```

### A.3 — Illustrative revocation

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000301",
  "spec_version": "0.2",
  "receipt_id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000102",
  "reason_code": "ISSUED_IN_ERROR",
  "reason": "Wrong task id: this receipt describes client-b-task-015, not 014.",
  "issued": "2026-11-12",
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-KEY",
    "signature": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
  }
}
```

### A.4 — Illustrative reputation record (two receipts, rates withheld)

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000001",
  "spec_version": "0.2",
  "agent": {
    "id": "https://example.org/agents/research-01",
    "name": "Example Research Agent",
    "identifiers": ["https://example.org/agents/research-01/card.json"]
  },
  "chain_head": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0102",
  "receipt_index": [
    {
      "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000101",
      "sha256": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0101",
      "file": "receipts/ILLUSTRATIVE-00000000-0000-4000-8000-000000000101.json"
    },
    {
      "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000102",
      "sha256": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0102",
      "file": "receipts/ILLUSTRATIVE-00000000-0000-4000-8000-000000000102.json"
    }
  ],
  "aggregates": {
    "total": 2,
    "counted": 2,
    "revoked": 0,
    "distinct_clients": 2,
    "distinct_verified_clients": 1,
    "counted_from_verified_clients": 1,
    "by_task_type": {
      "research": { "COMPLETED": 1, "COMPLETED_WITH_ISSUES": 1, "FAILED": 0, "CANCELLED": 0 }
    },
    "by_outcome": { "COMPLETED": 1, "COMPLETED_WITH_ISSUES": 1, "FAILED": 0, "CANCELLED": 0 },
    "completion_rate": null,
    "counted_last_12_months": 2,
    "recent_completion_rate": null,
    "first_receipt": "2026-11-02",
    "last_receipt": "2026-11-10",
    "computed_at": "2026-11-19"
  },
  "rotations": [],
  "history": [
    {
      "date": "2026-11-19",
      "action": "RECEIPT_ADDED",
      "receipt_id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000102",
      "note": "Illustrative seed record created for spec v0.2.",
      "signature": {
        "algorithm": "Ed25519",
        "public_key": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-KEY",
        "signature": "ILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
      }
    }
  ]
}
```

Note: `completion_rate` and `recent_completion_rate` are `null` here on purpose
— the denominator (2) is below the ≥ 5 threshold (§7.3). A two-receipt record
must not look like a verdict.

### A.5 — Illustrative mixed record: what counts and what does not

A record with seven receipts, of which three count:

- Receipt 1: COMPLETED, valid signature, distinct client, in the chain → COUNTS.
- Receipt 2: FAILED, valid signature, distinct client, in the chain → COUNTS
  (a failure is evidence too; hiding it would be dishonest).
- Receipt 3: COMPLETED, valid signature, distinct verified client → COUNTS
  (and counts toward `counted_from_verified_clients`).
- Receipt 4: a duplicate of receipt 1 (same client id, same task id) → does
  NOT count (rule 5).
- Receipt 5: signed by the agent's own key (self-issued) → does NOT count
  (rule 3).
- Receipt 6: `valid_until` has passed → does NOT count (rule 6).
- Receipt 7: a second receipt from receipt 1's client for the same agent on the
  same day → does NOT count (rule 8, rate limit).

Aggregates: `total` 7, `counted` 3, `distinct_clients` 3,
`counted_from_verified_clients` 1, `completion_rate` null (denominator 3 < 5).

---

## Appendix B — JSON Schema (v0.2)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.org/oar/schema/0.2/reputation.json",
  "title": "Open Agent Reputation — Reputation File (v0.2)",
  "type": "object",
  "required": ["id", "spec_version", "agent", "chain_head", "receipt_index", "aggregates", "rotations", "history"],
  "properties": {
    "id": { "type": "string", "minLength": 1 },
    "spec_version": { "type": "string", "const": "0.2" },
    "agent": {
      "type": "object",
      "required": ["id", "name"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "name": { "type": "string", "minLength": 1 },
        "identifiers": { "type": "array", "items": { "type": "string" } }
      }
    },
    "chain_head": { "type": ["string", "null"], "minLength": 1 },
    "receipt_index": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "sha256", "file"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "sha256": { "type": "string", "minLength": 1 },
          "file": { "type": "string", "minLength": 1 }
        }
      }
    },
    "aggregates": {
      "type": "object",
      "required": ["total", "counted", "revoked", "distinct_clients", "distinct_verified_clients", "counted_from_verified_clients", "by_task_type", "by_outcome", "completion_rate", "counted_last_12_months", "recent_completion_rate"],
      "properties": {
        "total": { "type": "integer", "minimum": 0 },
        "counted": { "type": "integer", "minimum": 0 },
        "revoked": { "type": "integer", "minimum": 0 },
        "distinct_clients": { "type": "integer", "minimum": 0 },
        "distinct_verified_clients": { "type": "integer", "minimum": 0 },
        "counted_from_verified_clients": { "type": "integer", "minimum": 0 },
        "by_task_type": { "type": "object" },
        "by_outcome": { "type": "object" },
        "completion_rate": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "counted_last_12_months": { "type": "integer", "minimum": 0 },
        "recent_completion_rate": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "first_receipt": { "type": ["string", "null"], "format": "date" },
        "last_receipt": { "type": ["string", "null"], "format": "date" },
        "computed_at": { "type": "string", "format": "date" }
      }
    },
    "rotations": {
      "type": "array",
      "items": { "$ref": "#/$defs/rotation" }
    },
    "history": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["date", "action", "note", "signature"],
        "properties": {
          "date": { "type": "string", "format": "date" },
          "action": { "type": "string", "enum": ["RECEIPT_ADDED", "RECEIPT_REVOKED", "RESPONSE_ADDED", "KEY_ROTATED", "CORRECTION"] },
          "receipt_id": { "type": "string" },
          "note": { "type": "string" },
          "signature": { "$ref": "#/$defs/signature" }
        }
      }
    }
  },
  "$defs": {
    "signature": {
      "type": "object",
      "required": ["algorithm", "public_key", "signature"],
      "properties": {
        "algorithm": { "type": "string", "const": "Ed25519" },
        "public_key": { "type": "string", "minLength": 1 },
        "signature": { "type": "string", "minLength": 1 }
      }
    },
    "receipt": {
      "type": "object",
      "required": ["id", "spec_version", "agent", "client", "task", "outcome", "issued", "previous_receipt_hash", "signature"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "spec_version": { "type": "string", "const": "0.2" },
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
            "name": { "type": "string" },
            "verified_endpoint": { "type": "string", "format": "uri" }
          }
        },
        "task": {
          "type": "object",
          "required": ["id", "type", "capabilities", "description", "started", "completed"],
          "properties": {
            "id": { "type": "string", "minLength": 1 },
            "type": { "type": "string", "enum": ["research", "coding", "data-analysis", "writing", "customer-support", "design", "automation", "other"] },
            "subtype": { "type": "string" },
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
        "valid_until": { "type": "string", "format": "date" },
        "payment_ref": { "type": "string" },
        "issued": { "type": "string", "format": "date" },
        "previous_receipt_hash": { "type": ["string", "null"], "minLength": 1 },
        "signature": { "$ref": "#/$defs/signature" }
      }
    },
    "revocation": {
      "type": "object",
      "required": ["id", "spec_version", "receipt_id", "reason_code", "reason", "issued", "signature"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "spec_version": { "type": "string", "const": "0.2" },
        "receipt_id": { "type": "string", "minLength": 1 },
        "reason_code": { "type": "string", "enum": ["ISSUED_IN_ERROR", "FRAUDULENT", "TASK_DISPUTED", "OTHER"] },
        "reason": { "type": "string", "minLength": 1 },
        "issued": { "type": "string", "format": "date" },
        "signature": { "$ref": "#/$defs/signature" }
      }
    },
    "response": {
      "type": "object",
      "required": ["id", "spec_version", "receipt_id", "agent", "text", "issued", "signature"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "spec_version": { "type": "string", "const": "0.2" },
        "receipt_id": { "type": "string", "minLength": 1 },
        "agent": {
          "type": "object",
          "required": ["id", "name"],
          "properties": {
            "id": { "type": "string", "minLength": 1 },
            "name": { "type": "string", "minLength": 1 }
          }
        },
        "text": { "type": "string", "minLength": 1 },
        "issued": { "type": "string", "format": "date" },
        "signature": { "$ref": "#/$defs/signature" }
      }
    },
    "rotation": {
      "type": "object",
      "required": ["subject", "old_key", "new_key", "date", "signature"],
      "properties": {
        "subject": { "type": "string", "enum": ["agent", "client"] },
        "old_key": { "type": "string", "minLength": 1 },
        "new_key": { "type": "string", "minLength": 1 },
        "date": { "type": "string", "format": "date" },
        "signature": { "$ref": "#/$defs/signature" }
      }
    }
  }
}
```
