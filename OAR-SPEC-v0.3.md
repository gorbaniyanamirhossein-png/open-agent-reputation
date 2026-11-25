# Open Agent Reputation (OAR)

**Specification — Version 0.3 (Draft)**
**Date:** 2026-11-20
**Author:** Amirhossein Gorbaniyan
**Status:** Draft — open for comment. Not yet final.
**License:** This specification is licensed under CC BY 4.0. Reference implementations are licensed under Apache 2.0.
**Supersedes:** v0.2 (2026-11-19). See §17 for the changelog and migration notes.

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
from real work, publisher-signed chain inclusion, optional signed checkpoints,
deterministic aggregation, and a portable bundle of ordinary files. No
blockchain, no wallet, no token, no service, no score, no one to pay, no one to
trust.

OAR does not claim to be the first portable agent reputation format. It claims
to be the minimal, standalone, authority-free, score-free one: a bundle of
files, not a service; evidence, not a score. See §16 for the honest comparison
with adjacent work.

## 1. Trust model

OAR's guarantees, stated plainly before any detail:

**What OAR guarantees**

- **Authenticity of receipts.** A receipt is signed by the client that hired the
  agent (Ed25519). Anyone can verify the signature with the key carried in the
  receipt itself — no lookup, no service.
- **Order-independent signing.** A client signs only the receipt content. Chain
  position is a separate, publisher-signed statement (§6), so concurrent
  clients never conflict over who holds the chain head.
- **Detectable deletion.** Receipts are bound to chain positions by
  publisher-signed inclusion records (§6), and the canonical record lives in a
  public git registry (§4). Removing a published receipt breaks the chain or
  shows up in git history. The agent cannot silently drop an unfavorable
  receipt from a record anyone has already seen.
- **Recomputable aggregates.** Every number in the record is derived from the
  receipts by a public rule (§9). Anyone recomputes them; a mismatch is
  visible.

**What OAR does NOT guarantee**

- **Sybil-proofing.** Distinct keys are cheap. v0.3 adds real mitigations
  (§9.2) but does not claim to solve coordinated fakery. A consumer must weigh
  the evidence, including how many distinct clients it comes from.
- **Truth of the task.** A valid signature proves the client said it, not that
  the task happened as described. Evidence URLs and payment references raise
  confidence; they do not prove facts.
- **Absolute history.** A public git repository is a publication and audit
  mechanism, not an immutability guarantee: history can be rewritten by anyone
  with push access. Internal chain consistency (§6) and externally anchored
  completeness (§7) are different things; only checkpoints and mirrors anchor
  history against rewriting.
- **Future performance.** A good record is evidence about the past, not
  insurance about the future.

**Incentives (honest note).** A receipt costs the client one signature and one
small file. Clients sign because it helps them re-hire and recommend good
agents, and because platforms and marketplaces can automate issuance. OAR v0.3
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
   with no query to any service. Validity verification never needs the network;
   only optional endpoint checks do.
5. **Aggregation by rule, not by model.** No LLM, no EigenTrust, no opaque
   algorithm. Counts and rates from a public rule (§9).
6. **Grounded in real work.** A receipt attests to a specific task the client
   hired the agent for. Praise without a task does not count.
7. **Correctable.** A wrong receipt can be revoked by its issuer and replaced;
   an agent can respond. A record that cannot be corrected is a liability
   machine (§10).
8. **Privacy by design.** No PII in receipts, revocations, or responses; clients
   are pseudonymous keys; task descriptions are short summaries, not
   transcripts (§14).
9. **Forkable and interoperable.** Anyone may extend the format. An OAR record
   may reference an ERC-8004 agentId, an A2A agent card, or an x402 payment
   receipt as supporting evidence.

## 3. Encodings

All encodings are exact. There is one canonical form for each value; verifiers
MUST reject non-canonical forms.

- **Public keys and identifiers — did:key.** Ed25519 public keys are encoded as
  `did:key` URIs (W3C Credentials Community Group, did:key method): the
  multicodec varint `0xed01` (Ed25519 public key) prepended to the 32-byte raw
  public key, encoded as multibase base58btc (prefix `z`). Example:
  `did:key:z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH`. The `client.id`,
  every `public_key` field, and the agent's key are did:key URIs. Verifiers MUST
  decode the multibase string, check the multicodec prefix, require exactly 32
  bytes after the prefix, and reject any string that does not round-trip to its
  canonical encoding. (Base58btc admits non-canonical forms; accepting them
  would let two strings denote the same key.) A did:key has no rotation or
  revocation inside the method itself: rotating a key changes the did:key. OAR
  handles rotation with signed rotation statements (§11).
- **Signatures.** Ed25519 signatures (RFC 8032) are 64 bytes, encoded as
  multibase base64url (prefix `u`). Example: `u<base64url-of-64-bytes>`.
- **Hashes.** SHA-256 digests are lowercase hexadecimal (64 characters).
- **Fingerprints (display only).** A key fingerprint is the SHA-256 hex digest
  of the 32-byte raw public key. Fingerprints are for display and short
  reference only; they are never identifiers.
- **Canonical JSON.** All signatures cover JCS-canonicalized JSON (RFC 8785)
  of the signed object with its `signature` object removed. Chain hashes cover
  the JCS-canonicalized receipt INCLUDING its `signature` object (§6).
- **Dates.** RFC 3339 full-dates (`YYYY-MM-DD`). Verifiers MUST enforce real
  calendar dates (JSON Schema `format` is annotation-only; OAR requires
  enforcement). "Today" means the UTC calendar date at verification time.
- **Identifiers.** All `id` fields are UUIDs (RFC 4122), lowercase recommended.

## 4. The reputation bundle

A reputation bundle is a directory of ordinary JSON files — one bundle per
agent. Receipts, inclusion records, revocations, responses, and checkpoints are
separate files: each unit can be checked, cited, and revoked independently, and
no single file grows without bound.

A registry — for git hosting — is a public repository with this layout:

```
/
├── README.md                 # what this registry covers, who maintains it
├── agents/
│   └── <agent-id>/
│       ├── reputation.json   # the record: identity, chain head, receipt index, aggregates
│       ├── receipts/
│       │   └── <receipt-id>.json
│       ├── chain/
│       │   └── <receipt-id>.json        # inclusion records (§6)
│       ├── revocations/
│       │   └── <revocation-id>.json
│       ├── responses/
│       │   └── <response-id>.json
│       └── checkpoints/
│           └── <checkpoint-id>.json     # optional (§7)
├── schemas/                  # JSON Schemas (Appendix B)
└── LICENSE                   # CC BY 4.0 (recommended for the data)
```

The canonical record is the public git registry. Git history is a publication
and audit mechanism: it shows what was published and when. It is NOT an
immutability guarantee — history can be rewritten by anyone with push access
(§1). External anchoring against rewriting comes from checkpoints (§7) and
mirrors: publishing the bundle in two or more independent locations lets a
consumer compare chain heads across mirrors. A bundle that was never published
in a public registry has no public history, and a consumer should weigh that.

## 5. The receipt

The receipt is the core unit. It is issued by the CLIENT — the party that hired
the agent for a specific task — never by the agent itself and never by a
platform. One file per receipt: `receipts/<receipt-id>.json`.

The client signs ONLY the receipt content. The receipt carries no chain fields:
its position in the chain is fixed later, by the publisher, in a separate
signed inclusion record (§6). Two clients issuing receipts at the same time
never conflict.

### 5.1 Required fields

| Field | Type | Rule |
|---|---|---|
| `id` | string | UUID. Unique across all receipts. The file name is `<id>.json`. |
| `spec_version` | string | `"0.3"` |
| `agent` | object | `{ "id": string (stable identifier, §11), "name": string }` |
| `client` | object | `{ "id": string (did:key, §3), "name": string (optional, pseudonymous), "verified_endpoint": string (optional, did:web or URL publishing this key — see §9.2) }` |
| `task` | object | `{ "id": string (client-assigned, unique per client — used for de-duplication), "type": string (from the vocabulary in §5.4), "subtype": string (optional, free-form), "capabilities": string[], "description": string (short summary, ≤ 280 characters), "started": "YYYY-MM-DD", "ended": "YYYY-MM-DD" }` |
| `outcome` | object | `{ "status": "COMPLETED" \| "COMPLETED_WITH_ISSUES" \| "FAILED" \| "CANCELLED", "tags": string[] (e.g. "on-time", "as-specified"), "evidence_url": string (optional, link to the deliverable or proof) }` |
| `issued` | string | `YYYY-MM-DD` — when the client issued the receipt. |
| `signature` | object | `{ "algorithm": "Ed25519", "public_key": string (did:key), "signature": string (multibase base64url) }` |

### 5.2 Optional fields

- `replaces` (string — the id of a revoked receipt this receipt replaces; see
  §10.1).
- `valid_until` (string, `YYYY-MM-DD`) — the client may set an expiry. An
  expired receipt does not count (§9). Default: no expiry.
- `payment_ref` (string — e.g. an x402 receipt id, as supporting evidence;
  payment is NOT required — many agent tasks are unpaid or test work).

### 5.3 Signature

- Algorithm: Ed25519 (RFC 8032).
- The signature covers the JCS-canonicalized (RFC 8785) JSON of the receipt
  with the `signature` object removed.
- `public_key` is the client's did:key (§3). The key travels in the receipt:
  verification needs no lookup.
- A receipt whose signature does not verify is ignored by aggregation (§9). It
  may remain in the bundle, marked by its failed check — the failure itself is
  information.

### 5.4 Outcome statuses and task types

Outcome statuses:

- `COMPLETED` — the task was delivered as agreed.
- `COMPLETED_WITH_ISSUES` — delivered, with problems the response or history
  note should name (late, partial, needed rework).
- `FAILED` — the agent did not deliver.
- `CANCELLED` — the task was cancelled before completion. Shown in the counts,
  excluded from the delivery and clean-completion rates (§9): a cancellation is
  not, by itself, evidence about the agent.

`task.ended` is the outcome-independent end date of the engagement: when the
work (or the attempt) ended, whatever the outcome. A FAILED or CANCELLED task
has an end date but no completion date; one field serves all outcomes.

Task types (controlled vocabulary — aggregates by type only work with a shared
vocabulary):

`research`, `coding`, `data-analysis`, `writing`, `customer-support`, `design`,
`automation`, `other`.

`subtype` is free-form (e.g. type `research`, subtype `literature-review`). A
receipt whose `type` is not in the vocabulary is still valid, but its type
counts as `other` for aggregation — a label mistake must not invalidate a
receipt.

## 6. Chain inclusion

Chain position is a publisher-signed statement, separate from the receipt. The
model follows Certificate Transparency (RFC 9162): the content issuer signs the
content, and the log (here, the publisher) signs a separate inclusion statement.
OAR's inclusion record is the analogue of CT's Signed Certificate Timestamp; its
checkpoint (§7) is the analogue of the Signed Tree Head. OAR uses a hash chain
rather than a Merkle tree, for simplicity at this scale.

An inclusion record is one file per receipt: `chain/<receipt-id>.json`.

| Field | Type | Rule |
|---|---|---|
| `id` | string | UUID. |
| `spec_version` | string | `"0.3"` |
| `receipt_id` | string | The receipt this record includes. The file name is `<receipt_id>.json`. |
| `receipt_hash` | string | SHA-256 (hex) of the JCS-canonicalized receipt INCLUDING its `signature` object. |
| `previous_receipt_hash` | string \| null | SHA-256 (hex) of the previous receipt in the chain; `null` for the first receipt (position 0). |
| `position` | integer | 0-based place in the chain. Positions are consecutive from 0 with no gaps. |
| `issued` | string | `YYYY-MM-DD` — when the publisher included the receipt. |
| `signature` | object | The AGENT's signature (§3) over the JCS-canonicalized record minus the `signature` object. |

Rules:

- The chain is ordered by `position`. Each record's `previous_receipt_hash`
  MUST equal the previous record's `receipt_hash`.
- `chain_head` (in the reputation record, §8) is the `receipt_hash` of the
  highest-position inclusion record, or `null` when the record has no receipts.
- The verifier recomputes the chain from the inclusion records and the receipt
  files (§12). A missing receipt breaks the chain; a receipt file with no
  inclusion record is flagged "published but not chained"; an inclusion record
  with no receipt file is an error.
- The publisher (the agent) chooses inclusion order. Order is by inclusion
  date, not by task date; the chain orders publication, not work.

Honest limits: a publisher can rebuild a chain from scratch after dropping a
receipt — the rebuilt chain is internally consistent. What the chain prevents
is SILENT deletion from a record anyone has already seen: the rebuilt chain has
a different head, and anyone who recorded the old head (a checkpoint, a mirror,
a client, a consumer) detects the rewrite. The chain plus public checkpoints is
the mechanism; neither alone is enough. A fresh agent with no published history
can start clean — which is visible as "no history," not as a good record.

The chain is a linked list of hashes inside ordinary files. It is not a
blockchain: no consensus, no mining, no token, no network.

## 7. Checkpoints

A checkpoint is an optional, signed, externally published statement about a
chain head. It is how history gets anchored against rewriting. Anyone may
publish one: the agent, a client, a third-party monitor, or a mirror operator.

A checkpoint file (`checkpoints/<checkpoint-id>.json`, or published anywhere
public and timestamped):

| Field | Type | Rule |
|---|---|---|
| `id` | string | UUID. |
| `spec_version` | string | `"0.3"` |
| `agent_id` | string | The agent whose chain this anchors. |
| `chain_head` | string | SHA-256 (hex) of the chain head at the checkpoint date. |
| `receipt_count` | integer | Number of receipts in the chain at the checkpoint date. |
| `date` | string | `YYYY-MM-DD` — when the checkpoint was taken. |
| `publisher` | string | did:key or URL identifying who attests. |
| `signature` | object | The publisher's signature (§3) over the JCS-canonicalized checkpoint minus the `signature` object. |

Rules:

- A checkpoint attests: "as of `date`, this agent's chain had `receipt_count`
  receipts and head `chain_head`."
- The reputation record lists known checkpoints in its `checkpoints` array
  (§8) as `{ "id", "url" }` references. Checkpoint files in the bundle's
  `checkpoints/` directory are verifiable offline; external checkpoints need a
  fetch, at the consumer's choice.
- The verifier compares each known checkpoint against the current chain (§12):
  a checkpoint matches if the chain at `receipt_count` receipts has head
  `chain_head`. A checkpoint that does not match any prefix of the current chain
  means the chain was rewritten after that checkpoint — flagged, not hidden.
- Mirrors: publishing the same bundle in two or more independent locations is
  recommended. A consumer that finds different heads across mirrors knows at
  least one was rewritten.

Checkpoints are OPTIONAL. A record without checkpoints is unanchored, not
invalid (§12). No checkpoint service is required or defined: a checkpoint is a
file, and it can be published anywhere public — a second git repository, a
personal site, a signed social post carrying the head.

## 8. The reputation record

`reputation.json` — the record is an index plus derived values. It does NOT
embed receipts.

| Field | Type | Rule |
|---|---|---|
| `id` | string | UUID of this reputation file. |
| `spec_version` | string | `"0.3"` |
| `agent` | object | `{ "id": string, "name": string, "public_key": string (did:key — the agent's signing key, §11), "identifiers": string[] }` — identifiers optional (website, A2A card URL, ERC-8004 agentId, did:web). |
| `chain_head` | string \| null | SHA-256 (hex) of the latest receipt (§6); `null` when the record has no receipts. |
| `receipt_index` | array | Entries `{ "id": string, "sha256": string, "file": string (relative path, e.g. "receipts/<id>.json"), "inclusion_file": string (relative path, e.g. "chain/<id>.json") }`, one per receipt file in the bundle. |
| `checkpoints` | array | Entries `{ "id": string, "url": string }` — known checkpoints (§7). May be empty. |
| `aggregates` | object | Derived values (§9), recomputed from the receipt files. |
| `rotations` | array | Key-rotation statements (§11). May be empty. |
| `history` | array | Signed history entries (§8.1). |

Aggregates are DERIVED, not asserted. Anyone recomputes them from the receipt
files using §9. If the stated aggregates do not match recomputation, the
aggregates are untrusted — but each receipt remains individually verifiable.

### 8.1 History

History entries are structured and signed by the agent (the publisher):

`{ "date": "YYYY-MM-DD", "action": string, "receipt_id": string (optional), "note": string (≤ 280 characters), "signature": { "algorithm": "Ed25519", "public_key": string (did:key), "signature": string } }`

Actions: `RECEIPT_ADDED`, `RECEIPT_REVOKED`, `RESPONSE_ADDED`, `KEY_ROTATED`,
`CORRECTION`. The signature covers the JCS-canonicalized entry minus the
`signature` object.

Roles, stated precisely:

- **Git history** is the audit trail for PUBLICATION: what was published, when,
  and what changed. It cannot say why.
- **Signed internal history** is the publisher's annotated log: why something
  happened ("migrated from v0.2", "receipt revoked at the client's request").
  It attests to the publisher's claims, not to the receipts' truth.
- **Consistency.** Every `RECEIPT_ADDED` entry should correspond to a receipt
  file in the bundle, and every receipt file should have a history entry. The
  verifier checks this and flags mismatches as WARNINGS, not errors — history
  is annotation, and a missing annotation must not invalidate a valid receipt.

## 9. Aggregation rules

### 9.1 What counts

A receipt COUNTS if and only if ALL of the following hold:

1. Its signature verifies against the stated public key (§5.3).
2. Its `agent.id` matches the record's `agent.id`.
3. Its client key is not the agent's key (self-issued receipts never count).
4. Its dates are sane: `started` ≤ `ended` ≤ today; `issued` ≥ `ended`;
   `issued` ≤ today; and `valid_until`, if present, is ≥ `issued` (a receipt
   born expired is malformed and fails validation). See §3 for date rules.
5. It is not a duplicate: no earlier counted receipt shares the same client id
   and task id. Revoked receipts are ignored for de-duplication, so a
   replacement receipt (§10.1) can count. The first counted receipt wins;
   later copies are ignored.
6. It is not expired: if `valid_until` is set, `valid_until` ≥ today.
7. It is not revoked: no valid revocation (§10) references its id.
8. It is included in the chain: a valid inclusion record (§6) exists for it,
   its `receipt_hash` matches the receipt file, and the chain is intact up to
   the record's `chain_head`.
9. Its outcome status is one of the four in §5.4.

### 9.2 Sybil mitigations (real rules, honestly bounded)

- **R1 — Verified clients.** A client MAY publish its public key at a
  `verified_endpoint` (did:web or URL) named in the receipt. The record reports
  `counted_from_verified_clients` and `distinct_verified_clients` separately, so
  a consumer can choose to trust only receipts from clients whose keys are
  published at endpoints it recognizes. Verification of an endpoint is the
  consumer's choice; the format only carries the link. (An endpoint proves the
  key is published at a domain the consumer recognizes; it does not prove who
  operates that domain — see §11.)
- **R2 — Burst reporting (not a cap).** v0.2 capped counted receipts at one per
  client per agent per day; that punished legitimate high-frequency use (a
  client hiring the same agent for many small tasks in a day). v0.3 counts all
  valid receipts and reports concentration instead: `burst_receipts` (counted
  receipts beyond the first per client-agent-day, by `ended` date) and
  `max_receipts_per_client_day` (the largest single-day count from one client).
  Consumers judge concentration from visible data; the format does not judge
  for them.
- **R3 — Transparency.** The record always shows `distinct_clients` and the full
  receipt list, so a consumer can see whether fifty receipts come from fifty
  clients or from two.

These raise the cost of fabrication. They do not eliminate coordinated fakery —
see §1. Distinct public keys are NOT proof of distinct real-world clients; the
format reports keys, and consumers must not read more into them than that.

### 9.3 Derived values

All computed over counted receipts only, unless noted:

- `total` — receipt files in the bundle; `counted` — receipts passing §9.1;
  `revoked` — receipts with a valid revocation; `replaced` — counted receipts
  that replace a revoked one (§10.1).
- `distinct_clients` — distinct client ids among counted receipts (keys linked
  by a valid rotation, §11, count as one client).
- `distinct_verified_clients`, `counted_from_verified_clients` — the R1 subset.
- `burst_receipts`, `max_receipts_per_client_day` — the R2 measures.
- `by_task_type` — counts per task type (vocabulary, §5.4) and outcome.
- `by_outcome` — counts per outcome status.
- `delivery_rate` — (COMPLETED + COMPLETED_WITH_ISSUES) /
  (COMPLETED + COMPLETED_WITH_ISSUES + FAILED). Did the agent deliver at all?
  Shown ONLY when the denominator is ≥ 5; otherwise `null` (insufficient data).
- `clean_completion_rate` — COMPLETED /
  (COMPLETED + COMPLETED_WITH_ISSUES + FAILED). Did the agent deliver without
  issues? Same ≥ 5 threshold; otherwise `null`.
- `counted_last_12_months` — counted receipts whose `ended` date falls in the
  365 days before `computed_at`.
- `recent_delivery_rate`, `recent_clean_completion_rate` — the same two rates
  over the last-12-months subset, each with the same ≥ 5 threshold; otherwise
  `null`.
- `first_receipt`, `last_receipt` — date range of counted receipts (by `ended`).
- `computed_at` — when the aggregates were computed.

CANCELLED is excluded from all four rates (see §5.4). There is no recency
weighting. Consumers filter by date from the receipts themselves.

## 10. Revocation & agent response

### 10.1 Revocation and replacement

A client may revoke its own receipt — issued in error, fraudulent, or disputed.
A revocation is a separate file, `revocations/<revocation-id>.json`:

`{ "id", "spec_version": "0.3", "receipt_id", "reason_code": "ISSUED_IN_ERROR" | "FRAUDULENT" | "TASK_DISPUTED" | "OTHER", "reason": string (short, ≤ 280 characters), "issued": "YYYY-MM-DD", "signature": { "algorithm": "Ed25519", "public_key": string (did:key), "signature": string } }`

- The signature is the CLIENT's, over the JCS-canonicalized revocation minus
  the `signature` object, and the key MUST match the receipt's client key.
- A revoked receipt remains in the bundle but does not count (§9.1, rule 7).
  The aggregates report it under `revoked`.
- Revocation is permanent in v0.3: there is no un-revoke.
- **Replacement.** A client that revokes a receipt may issue a replacement: a
  NEW receipt (new id, new signature) for the same task, carrying `replaces`
  with the revoked receipt's id. Rules: (a) the replacement's client key MUST
  match the revoked receipt's client key; (b) a `replaces` reference to a
  receipt that is not revoked (or not by the same client) is ignored, with a
  warning; (c) de-duplication (§9.1, rule 5) ignores revoked receipts, so the
  replacement counts; (d) the aggregates report counted replacements under
  `replaced`. The revoked original stays in the bundle, marked revoked — the
  correction is visible, not hidden.

### 10.2 Agent response

An agent may attach one signed response to a receipt — its side of the story.
A response is a separate file, `responses/<response-id>.json`:

`{ "id", "spec_version": "0.3", "receipt_id", "agent": { "id", "name" }, "text": string (short, ≤ 500 characters), "issued": "YYYY-MM-DD", "signature": { "algorithm": "Ed25519", "public_key": string (did:key), "signature": string } }`

- The signature is the AGENT's, over the JCS-canonicalized response minus the
  `signature` object. The key MUST match the record's `agent.public_key` (or a
  key linked to it by a valid rotation, §11).
- A response is informational ONLY. It never changes the outcome, the counts,
  or the rates.
- At most one response per receipt per agent is recognized; if several exist,
  the earliest-issued is the response and the rest are ignored.

## 11. Identity, keys & rotation

- An agent is identified by a stable identifier: a URL, a `did:web`, a `did:key`,
  or an ERC-8004 agentId. OAR does not create identity; it references it. The
  agent's SIGNING key is separate from its identifier and is carried in the
  record as `agent.public_key` (did:key, §8) — the key that signs inclusion
  records, history entries, and responses.
- A client is identified by its Ed25519 public key, as a did:key (§3). Clients
  are pseudonymous by default. **Cryptographic validity and organizational
  identity are separate things**: a valid signature proves control of a key,
  not that the key belongs to a named person or organization. A
  `verified_endpoint` links a key to a domain the consumer may recognize; it
  does not prove who operates that domain, and a compromised endpoint can
  publish a false key. Consumers decide what an endpoint is worth.
- **Rotation.** A subject (agent or client) that changes keys publishes a
  rotation statement:

  `{ "subject": "agent" | "client", "old_key": string (did:key), "new_key": string (did:key), "date": "YYYY-MM-DD", "signature": { "algorithm": "Ed25519", "public_key": string (= old_key), "signature": string } }`

  The signature is by the OLD key, over the JCS-canonicalized statement minus
  the `signature` object. Rotation is necessary because did:key has no
  rotation inside the method: a new key is a new did:key.
- **Publication.** Rotation statements live in each affected record's
  `rotations` array. A client SHOULD also publish its key history at its
  `verified_endpoint` (a JSON file: `{ "client": <current did:key>,
  "rotations": [ ...statements... ] }`), so that any record the client appears
  in can follow the rotation. The verifier follows in-record rotations always;
  it follows endpoint rotations only if it can fetch the endpoint (optional
  network), and notes "rotation data may be incomplete" when it cannot. Keys
  linked by valid rotations count as one client for `distinct_clients`, and an
  agent's signatures under a rotated key remain attributable.
- Interoperability: an OAR record MAY list an ERC-8004 agentId among its
  identifiers; a receipt MAY reference an x402 payment receipt (`payment_ref`);
  a receipt MAY be linked from an A2A agent card.

## 12. Verification

Anyone may verify a reputation bundle, with no service and no account.
Verification reports two independent dimensions — data validity and history —
plus the verified-client counts. No single level or score merges them: a record
can be internally valid and still have an unanchored history, and the report
must say so.

### 12.1 Checks

1. Parse `reputation.json`; check required fields against the schema
   (Appendix B). Unknown fields are IGNORED (forward compatibility, §12.3).
2. For each `receipt_index` entry: load the receipt file and the inclusion
   file; check the receipt's SHA-256 matches the index; check ids match;
   verify the receipt signature (§5.3) and the inclusion signature (§6).
   Flag receipt files present in `receipts/` but missing from the index
   ("present but not indexed"), index entries whose files are missing (error),
   and receipts with no inclusion record ("published but not chained").
3. Recompute the chain (§6) from the inclusion records and compare with
   `chain_head`. A break means a receipt is missing or the chain was rebuilt —
   report it.
4. Apply the revocations (§10.1) and the aggregation rules (§9); compare the
   recomputed aggregates with the stated ones.
5. Check history entries' signatures (§8.1) and rotation statements (§11);
   check history/bundle consistency (§8.1).
6. For each known checkpoint (§7): verify its signature and compare its
   (`chain_head`, `receipt_count`) against the chain. A checkpoint that matches
   the chain at its count anchors history at its date; one that matches no
   prefix means the chain was rewritten after that checkpoint.

### 12.2 Verification result

The verifier reports:

```
{
  "validity": "VALID" | "INVALID",
  "issues": [ ... ],              // each failed check, named
  "history": "UNANCHORED" | "ANCHORED" | "REWRITTEN" | "UNCHECKABLE",
  "history_detail": "...",        // which checkpoints matched, if any
  "verified_clients": {
    "counted_from_verified_clients": 0,
    "distinct_verified_clients": 0
  },
  "warnings": [ ... ]             // non-fatal notes (unindexed files, history mismatches, ...)
}
```

- `validity` covers checks 1–5: schema, signatures, chain integrity,
  revocations, aggregates, history, rotations. One failed check makes the
  record INVALID; the `issues` list names every failure.
- `history` is independent of validity: `UNANCHORED` (no checkpoints known),
  `ANCHORED` (at least one checkpoint matches the chain), `REWRITTEN` (a
  checkpoint contradicts the current chain), `UNCHECKABLE` (checkpoints are
  referenced but cannot be fetched or verified).
- A record can be VALID and UNANCHORED: its data checks out, but nothing
  external anchors its history. That is the normal state of a young record,
  and the report says so plainly instead of implying completeness.

A static, serverless verifier page is the planned reference tool. Verification
itself needs no service.

### 12.3 Unknown fields and versions

- Verifiers MUST ignore unknown fields in any OAR file. Unknown fields are
  part of the signed content (signatures cover the full canonical JSON), so
  they cannot be stripped without breaking the signature — but a verifier that
  does not understand them must not fail on them. This is what makes future
  versions readable by today's verifiers.
- A file whose `spec_version` the verifier does not support is SKIPPED with a
  warning, not an error: the rest of the bundle is still verified.

## 13. Conformance & interoperability

**Conformance classes.** An implementation claims conformance per role:

- **Conformant verifier** — MUST implement all checks in §12, MUST report the
  result in the §12.2 shape, MUST ignore unknown fields (§12.3), and MUST
  enforce the date rules in §3 (not merely accept `format: date`).
- **Conformant issuer** (client) — MUST produce schema-valid receipts with
  valid Ed25519 signatures over JCS-canonicalized content, using the §3
  encodings.
- **Conformant publisher** (agent/registry) — MUST maintain chain and index
  consistency (§6, §8), MUST sign inclusion records with the record's agent
  key, and MUST NOT silently remove published receipts: removals go through
  revocation (§10.1) or remain visible in git history.

**Test vectors.** The `test-vectors/` directory (Appendix C) provides a valid
bundle with real Ed25519 signatures and four negative cases (bad signature,
broken chain, revoked receipt, duplicate receipt), each with its expected
verification result. A conformant verifier MUST reproduce every expected
result. Vectors use the §3 encodings and JCS canonicalization; they are the
authoritative check that two independent implementations agree.

**Interoperability notes.** OAR files are plain JSON over UTF-8. Implementers
in any language need only: JSON parsing, SHA-256, Ed25519 (RFC 8032), JCS
(RFC 8785), base58btc/base64url decoding, and UUID parsing. No library beyond
a standard crypto library is required.

## 14. Privacy

- Issuers MUST NOT include PII or confidential information in free-text fields
  (`description`, `reason`, `text`, `note`) or in `evidence_url`. Free-text
  fields are length-limited (§5, §8, §10) to reduce the PII surface and keep
  files small; the limits do not by themselves prevent PII, and issuers remain
  responsible for what they write.
- `evidence_url` SHOULD point to public, redacted artifacts. A URL is public
  forever once published in a git registry; issuers MUST NOT use URLs carrying
  credentials, tokens, or private identifiers in query parameters.
- Task descriptions are short summaries, never full transcripts.
- A client may use a fresh key per agent (pseudonymity) — at the cost of its
  receipts counting as distinct clients. That trade-off is the client's choice,
  and the record makes it visible.
- Redaction: if PII is discovered in a published receipt, the issuer revokes it
  and issues a redacted replacement (§10.1). Honest limit: revocation does not
  erase git history — the original remains in history, marked revoked. OAR is
  a record, not a forgetfulness machine. Issuers should treat every published
  field as permanent.

## 15. What OAR is not

- **Not a blockchain:** no chain network, no token, no wallet, no gas, no
  consensus. The hash chain (§6) is a linked list inside ordinary files.
- **Not a score:** no trust number, no ranking. Evidence and counts only.
- **Not a marketplace:** OAR records reputation; it does not match, hire, or pay.
- **Not an identity system:** it references identifiers; it does not issue them.
  A did:key proves control of a key, not a real-world identity (§11).
- **Not a guarantee:** a good record is evidence about the past, not insurance
  about the future.

## 16. Relation to prior art

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

**Design references (not competitors).** OAR's inclusion and checkpoint model
is adapted from Certificate Transparency (RFC 9162): the inclusion record is
OAR's analogue of the Signed Certificate Timestamp (a signed inclusion
statement by the publisher), and the checkpoint is the analogue of the Signed
Tree Head (a signed statement of the log's state). OAR uses a hash chain rather
than a Merkle tree, for simplicity at this scale. Identity encoding follows the
did:key method (W3C Credentials Community Group); canonicalization follows JCS
(RFC 8785); signatures follow Ed25519 (RFC 8032).

The narrowed claim, stated plainly: OAR is not the first portable agent
reputation format. It is the minimal, standalone, authority-free, score-free
one — a bundle of files, not a service; evidence, not a score; no one to pay,
no one to trust.

## 17. Versioning, changelog & migration

The specification follows Semantic Versioning. v0.3 is a draft.
Backward-incompatible changes bump the major version; new optional fields bump
the minor version. (In the 0.x series, minor versions may break compatibility;
each version's changelog states exactly what broke.)

### Changelog — v0.2 → v0.3

Breaking changes are marked **[B]**.

1. **[B] Chain inclusion separated from receipt signing (§6).** v0.2 made the
   client sign `previous_receipt_hash`, which concurrent clients cannot know
   reliably. v0.3 removes chain fields from receipts; the publisher signs a
   separate inclusion record per receipt. Cryptographic binding is preserved
   (the inclusion record commits to the receipt hash and its chain position).
2. **Checkpoints (new §7).** v0.2 treated git history as the audit trail
   without stating its limits. v0.3 states plainly that git history is
   rewritable, distinguishes internal chain consistency from externally
   anchored completeness, and adds optional signed checkpoints (plus mirrors).
3. **[B] Exact encodings (new §3).** v0.2 allowed hex SPKI DER or did:key for
   public keys and left signature encoding unspecified. v0.3 requires did:key
   for all public keys and identifiers, multibase base64url for signatures,
   lowercase hex for hashes, and defines fingerprints as display-only.
4. **[B] `task.completed` → `task.ended` (§5).** A FAILED or CANCELLED task has
   no completion date. One outcome-independent end date serves all outcomes.
5. **Verification redesigned (§12).** v0.2's L0/L1/L2 levels conflated data
   validity, client verification, and history completeness — and L1 implied a
   completeness it could not guarantee. v0.3 reports validity and history as
   independent dimensions and drops the levels.
6. **Rate limit replaced by burst reporting (§9.2).** v0.2's one-receipt-per-day
   cap punished legitimate high-frequency use. v0.3 counts all valid receipts
   and reports concentration (`burst_receipts`, `max_receipts_per_client_day`).
7. **[B] Two rates replace `completion_rate` (§9.3).** `delivery_rate` (did it
   deliver?) and `clean_completion_rate` (did it deliver without issues?),
   each with recent variants. The old single rate conflated the two.
8. **Replacement receipts defined (§10.1).** The `replaces` field, its rules,
   and the `replaced` aggregate are now specified; v0.2's note was ambiguous.
9. **Rotation publication specified (§11).** Rotations live in-record and SHOULD
   be published at the client's verified endpoint, so any record can follow
   them. Verifier behavior when the endpoint is unreachable is defined.
10. **Privacy strengthened (§14).** Length limits on free-text fields; explicit
    MUST NOT rules for PII in text and URLs; redaction guidance via
    revoke-and-replace, with the honest limit that git history preserves the
    original.
11. **History roles clarified (§8.1).** Git history (publication audit) vs
    signed internal history (publisher's annotated log), with a defined
    consistency check.
12. **Unknown-field and version handling defined (§12.3).** Verifiers MUST
    ignore unknown fields; unsupported versions are skipped with a warning.
13. **Date validation made deterministic (§3, §9.1).** Real calendar dates
    enforced; "today" defined as the UTC date at verification; the 12-month
    window defined as 365 days before `computed_at`; `valid_until` before
    `issued` is a validation failure.
14. **Schemas split into seven files (Appendix B).** One independently
    addressable schema per file type (reputation, receipt, inclusion,
    revocation, response, rotation, checkpoint), each self-contained.
15. **Conformance & test vectors (new §13, Appendix C).** Conformance classes
    for verifiers, issuers, and publishers; a test-vectors directory with real
    Ed25519 signatures and expected results.
16. **Agent signing key in the record (§8).** The record now carries
    `agent.public_key` (did:key), the anchor for inclusion, history, and
    response signatures. v0.2 had no such anchor.

### Migration — v0.2 → v0.3

1. Receipts are client-signed, so they cannot be upgraded in place: each client
   re-issues its receipts in v0.3 format (same task id, new receipt id, new
   signature; `ended` instead of `completed`; did:key and multibase encodings;
   no chain fields). Old v0.2 bundles remain valid v0.2 records.
2. The publisher builds inclusion records (§6) from the old chain order (by
   `issued` date, then receipt id) and signs them with the agent key.
3. The record gains `agent.public_key`, `checkpoints`, and the new aggregates;
   the `receipt_index` gains `inclusion_file`.
4. Recompute the aggregates under §9 and record the migration in history
   (`CORRECTION`, "migrated from v0.2; chain re-anchored as inclusion
   records").
5. Checkpoints are optional and new: a migrating publisher SHOULD publish one
   checkpoint for the migrated head, so the migration itself is anchored.

## 18. Quickstart

Create a reputation bundle in ten minutes:

1. Generate an Ed25519 keypair for the agent's identity (any standard tool);
   encode the public key as did:key (§3) and put it in the record as
   `agent.public_key`.
2. Create the bundle directory with `reputation.json`: agent identity, empty
   receipt index, `chain_head: null`, zero aggregates.
3. After a client hires the agent for a task, the client issues a signed receipt
   (§5) — one small JSON file — and sends it to the agent.
4. The agent places the receipt in `receipts/`, writes and signs an inclusion
   record in `chain/` (§6), adds both to the `receipt_index`, recomputes the
   aggregates (§9), and publishes the bundle in a public git registry (§4).
5. Anyone verifies the bundle with the rules in §12 — no service required.
6. Optionally, publish a signed checkpoint (§7) so the chain head is anchored
   outside the registry.

---

## Appendix A — Seed examples (ILLUSTRATIVE)

The examples below show the shape of a v0.3 bundle. They are ILLUSTRATIVE —
invented to demonstrate the format, NOT real interactions. Keys, signatures,
and hashes are placeholders, not real cryptographic values. (Real cryptographic
examples live in the test vectors, Appendix C.) Real seed examples from public
agent interactions are to be added after verification.

### A.1 — Illustrative bundle layout

```
agents/research-01/
├── reputation.json
├── receipts/
│   ├── ILLUSTRATIVE-...-0101.json
│   └── ILLUSTRATIVE-...-0102.json
├── chain/
│   ├── ILLUSTRATIVE-...-0101.json
│   └── ILLUSTRATIVE-...-0102.json
├── revocations/
├── responses/
└── checkpoints/
```

### A.2 — Illustrative v0.3 receipt (no chain fields)

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000102",
  "spec_version": "0.3",
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
    "ended": "2026-11-10"
  },
  "outcome": {
    "status": "COMPLETED_WITH_ISSUES",
    "tags": ["late", "as-specified"],
    "evidence_url": "https://example.org/deliverables/comparison-014"
  },
  "issued": "2026-11-10",
  "valid_until": "2027-11-10",
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "did:key:ILLUSTRATIVE-CLIENT-B",
    "signature": "uILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
  }
}
```

### A.3 — Illustrative inclusion record (for the receipt in A.2)

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000402",
  "spec_version": "0.3",
  "receipt_id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000102",
  "receipt_hash": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0102",
  "previous_receipt_hash": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0101",
  "position": 1,
  "issued": "2026-11-10",
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "did:key:ILLUSTRATIVE-AGENT-KEY",
    "signature": "uILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
  }
}
```

### A.4 — Illustrative checkpoint

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000501",
  "spec_version": "0.3",
  "agent_id": "https://example.org/agents/research-01",
  "chain_head": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0102",
  "receipt_count": 2,
  "date": "2026-11-19",
  "publisher": "did:key:ILLUSTRATIVE-AGENT-KEY",
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "did:key:ILLUSTRATIVE-AGENT-KEY",
    "signature": "uILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
  }
}
```

### A.5 — Illustrative reputation record (two receipts, rates withheld)

```json
{
  "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000001",
  "spec_version": "0.3",
  "agent": {
    "id": "https://example.org/agents/research-01",
    "name": "Example Research Agent",
    "public_key": "did:key:ILLUSTRATIVE-AGENT-KEY",
    "identifiers": ["https://example.org/agents/research-01/card.json"]
  },
  "chain_head": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0102",
  "receipt_index": [
    {
      "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000101",
      "sha256": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0101",
      "file": "receipts/ILLUSTRATIVE-00000000-0000-4000-8000-000000000101.json",
      "inclusion_file": "chain/ILLUSTRATIVE-00000000-0000-4000-8000-000000000101.json"
    },
    {
      "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000102",
      "sha256": "ILLUSTRATIVE-PLACEHOLDER-SHA256-OF-RECEIPT-0102",
      "file": "receipts/ILLUSTRATIVE-00000000-0000-4000-8000-000000000102.json",
      "inclusion_file": "chain/ILLUSTRATIVE-00000000-0000-4000-8000-000000000102.json"
    }
  ],
  "checkpoints": [
    {
      "id": "ILLUSTRATIVE-00000000-0000-4000-8000-000000000501",
      "url": "checkpoints/ILLUSTRATIVE-00000000-0000-4000-8000-000000000501.json"
    }
  ],
  "aggregates": {
    "total": 2,
    "counted": 2,
    "revoked": 0,
    "replaced": 0,
    "distinct_clients": 2,
    "distinct_verified_clients": 1,
    "counted_from_verified_clients": 1,
    "burst_receipts": 0,
    "max_receipts_per_client_day": 1,
    "by_task_type": {
      "research": { "COMPLETED": 1, "COMPLETED_WITH_ISSUES": 1, "FAILED": 0, "CANCELLED": 0 }
    },
    "by_outcome": { "COMPLETED": 1, "COMPLETED_WITH_ISSUES": 1, "FAILED": 0, "CANCELLED": 0 },
    "delivery_rate": null,
    "clean_completion_rate": null,
    "counted_last_12_months": 2,
    "recent_delivery_rate": null,
    "recent_clean_completion_rate": null,
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
      "note": "Illustrative seed record created for spec v0.3.",
      "signature": {
        "algorithm": "Ed25519",
        "public_key": "did:key:ILLUSTRATIVE-AGENT-KEY",
        "signature": "uILLUSTRATIVE-PLACEHOLDER-NOT-A-REAL-SIGNATURE"
      }
    }
  ]
}
```

Note: the rates are `null` here on purpose — the denominator (2) is below the
≥ 5 threshold (§9.3). A two-receipt record must not look like a verdict.

### A.6 — Illustrative mixed record: what counts and what does not

A record with nine receipts, of which four count:

- Receipt 1: COMPLETED, valid signature, distinct client, included in the
  chain → COUNTS.
- Receipt 2: FAILED, valid signature, distinct client, in the chain → COUNTS
  (a failure is evidence too; hiding it would be dishonest).
- Receipt 3: COMPLETED, valid signature, distinct verified client → COUNTS
  (and counts toward `counted_from_verified_clients`).
- Receipt 4: a duplicate of receipt 1 (same client id, same task id) → does
  NOT count (rule 5).
- Receipt 5: signed by the agent's own key (self-issued) → does NOT count
  (rule 3).
- Receipt 6: `valid_until` has passed → does NOT count (rule 6).
- Receipt 7: revoked by its client, then replaced by receipt 8 → does NOT
  count itself (rule 7); receipt 8 (the replacement, same task, `replaces`
  set) → COUNTS as the replacement.
- Receipt 9 (not in the bundle's chain): a receipt file with no inclusion
  record → does NOT count (rule 8) and is flagged "published but not chained".

Aggregates: `total` 9, `counted` 4, `revoked` 1, `replaced` 1,
`distinct_clients` 4, `counted_from_verified_clients` 1, `delivery_rate` null
(denominator 4 < 5).

---

## Appendix B — JSON Schemas

The schemas are separate files, one per file type, each self-contained and
independently addressable. They live in `schemas/` alongside this specification.

| File type | Schema file | $id |
|---|---|---|
| Reputation record | `schemas/reputation.json` | `https://example.org/oar/schema/0.3/reputation.json` |
| Receipt | `schemas/receipt.json` | `https://example.org/oar/schema/0.3/receipt.json` |
| Inclusion record | `schemas/inclusion.json` | `https://example.org/oar/schema/0.3/inclusion.json` |
| Revocation | `schemas/revocation.json` | `https://example.org/oar/schema/0.3/revocation.json` |
| Response | `schemas/response.json` | `https://example.org/oar/schema/0.3/response.json` |
| Rotation | `schemas/rotation.json` | `https://example.org/oar/schema/0.3/rotation.json` |
| Checkpoint | `schemas/checkpoint.json` | `https://example.org/oar/schema/0.3/checkpoint.json` |

Each schema is JSON Schema draft 2020-12. Shared definitions (the `signature`
object) are repeated in each file so every schema stands alone. All schemas
allow unknown fields (`additionalProperties` is not set to `false`): verifiers
MUST ignore unknown fields (§12.3). The schemas enforce structure and types;
the specification's rules (§5–§12) enforce the rest (signature validity, chain
integrity, date sanity, counting).

---

## Appendix C — Test vectors

The `test-vectors/` directory contains a valid bundle with REAL Ed25519
signatures (generated for this specification; keys are test-only and carry no
reputation) and four negative cases. Each case states its expected verification
result (§12.2). A conformant verifier MUST reproduce every expected result.

| Case | Directory | Expected result |
|---|---|---|
| Valid bundle | `test-vectors/01-valid/` | validity VALID; history UNANCHORED (no checkpoint); 2 counted receipts, 2 distinct clients |
| Bad receipt signature | `test-vectors/02-bad-signature/` | validity INVALID (issue: receipt signature fails); the bad receipt does not count |
| Broken chain | `test-vectors/03-broken-chain/` | validity INVALID (issue: chain link mismatch); aggregates do not recompute |
| Revoked receipt | `test-vectors/04-revoked/` | validity VALID; the revoked receipt does not count; `revoked` = 1 |
| Duplicate receipt | `test-vectors/05-duplicate/` | validity VALID; the duplicate does not count; `counted` = 2 of `total` 3 |

See `test-vectors/README.md` for the key material (test-only), the exact
verification steps, and the expected aggregate values per case.
```
