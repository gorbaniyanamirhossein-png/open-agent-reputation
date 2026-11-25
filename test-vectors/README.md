# OAR v0.3 — Test Vectors

Five cases with REAL Ed25519 signatures (generated for this specification).
The keypairs are test-only: their private keys were used in memory during
generation and never written to disk. The public keys appear as `did:key`
URIs inside the files. No test vector carries real reputation.

| Case | Directory | Expected validity | Expected history |
|---|---|---|---|
| Valid bundle | `01-valid/` | VALID | UNANCHORED (no checkpoint) |
| Bad receipt signature | `02-bad-signature/` | INVALID | UNANCHORED |
| Broken chain | `03-broken-chain/` | INVALID | UNANCHORED |
| Revoked receipt | `04-revoked/` | VALID | UNANCHORED |
| Duplicate receipt | `05-duplicate/` | VALID | UNANCHORED |

Each case directory contains a complete bundle (`reputation.json`,
`receipts/`, `chain/`, and `revocations/` where applicable) plus
`expected.json` with the expected verification result (spec §12.2).

## How to verify (spec §12)

1. Validate every file against its JSON Schema (`schemas/`).
2. Verify every signature: decode the `did:key` public key, decode the
   multibase base64url signature, verify over the JCS-canonicalized object
   minus its `signature` object (RFC 8785).
3. Recompute the chain: each inclusion record's `receipt_hash` must equal the
   SHA-256 of the JCS-canonicalized receipt (including its signature), each
   `previous_receipt_hash` must equal the previous receipt's hash, and the
   last hash must equal the record's `chain_head`.
4. Apply the revocations and the counting rules (§9.1); recompute the
   aggregates and compare with the stated ones.

## Regeneration

Run `generate-test-vectors.py` in `~/workspace/agent-reputation/`. It
regenerates all five cases and re-validates them (schemas, signatures,
chain links, aggregates). Fresh keypairs are generated on each run, so the
files change; the expected results do not.
