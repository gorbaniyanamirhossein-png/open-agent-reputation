#!/usr/bin/env python3
"""Generate OAR v0.3 test vectors with REAL Ed25519 signatures.

Regenerates test-vectors/ from scratch. Private keys are used only in memory
and never written to disk. Public keys appear as did:key URIs in the files.

Also pretty-prints the 7 JSON Schemas and validates every generated file
against its schema (jsonschema), verifies every signature, recomputes every
hash-chain link, and recomputes the aggregates from the receipts.
"""
import base64
import hashlib
import json
import os
import re
import uuid

import base58
import jsonschema
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

BASE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS_DIR = os.path.join(BASE, "schemas")
TV_DIR = os.path.join(BASE, "test-vectors")

# ---------- encoding helpers (OAR v0.3, section 3) ----------

def jcs(obj):
    """JSON Canonicalization Scheme (RFC 8785). Exact for our string/int-only
    data: sorted keys, minimal separators, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")

def didkey(pub_raw: bytes) -> str:
    return "did:key:z" + base58.b58encode(b"\xed\x01" + pub_raw).decode()

def pub_from_didkey(dk: str) -> bytes:
    assert dk.startswith("did:key:z"), dk
    raw = base58.b58decode(dk[len("did:key:z"):])
    assert raw[:2] == b"\xed\x01" and len(raw) == 34, "bad did:key payload"
    return raw[2:]

def sig_encode(sig: bytes) -> str:
    return "u" + base64.urlsafe_b64encode(sig).rstrip(b"=").decode()

def sig_decode(s: str) -> bytes:
    assert s.startswith("u"), s
    b = s[1:]
    return base64.urlsafe_b64decode(b + "=" * (-len(b) % 4))

def sign(priv: Ed25519PrivateKey, obj_without_sig: dict) -> str:
    return sig_encode(priv.sign(jcs(obj_without_sig)))

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")

# ---------- keys (test-only, never persisted) ----------

agent_priv = Ed25519PrivateKey.generate()
client_a_priv = Ed25519PrivateKey.generate()
client_b_priv = Ed25519PrivateKey.generate()

AGENT_DID = didkey(agent_priv.public_key().public_bytes_raw())
CLIENT_A_DID = didkey(client_a_priv.public_key().public_bytes_raw())
CLIENT_B_DID = didkey(client_b_priv.public_key().public_bytes_raw())

AGENT_ID = "https://example.org/agents/research-01"
AGENT_NAME = "Example Research Agent"

# ---------- receipts ----------

def make_receipt(rid, priv, client_did, task_id, ttype, subtype, caps,
                 desc, started, ended, status, tags, issued,
                 verified_endpoint=None, evidence_url=None, valid_until=None):
    r = {
        "id": rid,
        "spec_version": "0.3",
        "agent": {"id": AGENT_ID, "name": AGENT_NAME},
        "client": {"id": client_did},
        "task": {
            "id": task_id, "type": ttype, "capabilities": caps,
            "description": desc, "started": started, "ended": ended,
        },
        "outcome": {"status": status, "tags": tags},
        "issued": issued,
    }
    if subtype:
        r["task"]["subtype"] = subtype
    if verified_endpoint:
        r["client"]["verified_endpoint"] = verified_endpoint
    if evidence_url:
        r["outcome"]["evidence_url"] = evidence_url
    if valid_until:
        r["valid_until"] = valid_until
    r["signature"] = {
        "algorithm": "Ed25519",
        "public_key": client_did,
        "signature": sign(priv, r),
    }
    return r

R1_ID = str(uuid.uuid4())
R2_ID = str(uuid.uuid4())

receipt1 = make_receipt(
    R1_ID, client_a_priv, CLIENT_A_DID,
    "client-a-task-001", "research", "literature-review",
    ["web-search", "summarization"],
    "Summarize five recent papers on agent trust frameworks.",
    "2026-11-02", "2026-11-02", "COMPLETED", ["on-time", "as-specified"],
    "2026-11-02",
    evidence_url="https://example.org/deliverables/summary-001",
)
receipt2 = make_receipt(
    R2_ID, client_b_priv, CLIENT_B_DID,
    "client-b-task-014", "research", "framework-comparison",
    ["web-search", "summarization"],
    "Compare three open agent frameworks for a build decision.",
    "2026-11-09", "2026-11-10", "COMPLETED_WITH_ISSUES",
    ["late", "as-specified"], "2026-11-10",
    verified_endpoint="https://example.org/.well-known/oar-client-b.json",
    evidence_url="https://example.org/deliverables/comparison-014",
    valid_until="2027-11-10",
)

def receipt_hash(receipt):
    return sha256_hex(jcs(receipt))

H1 = receipt_hash(receipt1)
H2 = receipt_hash(receipt2)

# ---------- inclusion records ----------

def make_inclusion(receipt_id, receipt_hash_, prev_hash, position, issued):
    inc = {
        "id": str(uuid.uuid4()),
        "spec_version": "0.3",
        "receipt_id": receipt_id,
        "receipt_hash": receipt_hash_,
        "previous_receipt_hash": prev_hash,
        "position": position,
        "issued": issued,
    }
    inc["signature"] = {
        "algorithm": "Ed25519",
        "public_key": AGENT_DID,
        "signature": sign(agent_priv, inc),
    }
    return inc

inclusion1 = make_inclusion(R1_ID, H1, None, 0, "2026-11-02")
inclusion2 = make_inclusion(R2_ID, H2, H1, 1, "2026-11-10")
CHAIN_HEAD = H2

# ---------- history ----------

def make_history_entry(date, action, receipt_id, note):
    e = {"date": date, "action": action, "note": note}
    if receipt_id:
        e["receipt_id"] = receipt_id
    e["signature"] = {
        "algorithm": "Ed25519",
        "public_key": AGENT_DID,
        "signature": sign(agent_priv, e),
    }
    return e

history = [
    make_history_entry("2026-11-02", "RECEIPT_ADDED", R1_ID,
                       "First test receipt included."),
    make_history_entry("2026-11-10", "RECEIPT_ADDED", R2_ID,
                       "Second test receipt included."),
]

# ---------- aggregates (recomputed from the receipts, per section 9) ----------

AGGREGATES_01 = {
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
        "research": {"COMPLETED": 1, "COMPLETED_WITH_ISSUES": 1,
                     "FAILED": 0, "CANCELLED": 0}
    },
    "by_outcome": {"COMPLETED": 1, "COMPLETED_WITH_ISSUES": 1,
                   "FAILED": 0, "CANCELLED": 0},
    "delivery_rate": None,
    "clean_completion_rate": None,
    "counted_last_12_months": 2,
    "recent_delivery_rate": None,
    "recent_clean_completion_rate": None,
    "first_receipt": "2026-11-02",
    "last_receipt": "2026-11-10",
    "computed_at": "2026-11-19",
}

def make_record(record_id, chain_head, index, aggregates, hist):
    return {
        "id": record_id,
        "spec_version": "0.3",
        "agent": {
            "id": AGENT_ID,
            "name": AGENT_NAME,
            "public_key": AGENT_DID,
            "identifiers": ["https://example.org/agents/research-01/card.json"],
        },
        "chain_head": chain_head,
        "receipt_index": index,
        "checkpoints": [],
        "aggregates": aggregates,
        "rotations": [],
        "history": hist,
    }

def index_entry(rid, h):
    return {"id": rid, "sha256": h,
            "file": f"receipts/{rid}.json",
            "inclusion_file": f"chain/{rid}.json"}

RECORD_ID = str(uuid.uuid4())
record_01 = make_record(
    RECORD_ID, CHAIN_HEAD,
    [index_entry(R1_ID, H1), index_entry(R2_ID, H2)],
    AGGREGATES_01, history,
)

# ---------- write case 01 (valid) ----------

def write_bundle(case_dir, record, receipts, inclusions, revocations=None):
    write_json(os.path.join(case_dir, "reputation.json"), record)
    for r in receipts:
        write_json(os.path.join(case_dir, "receipts", f"{r['id']}.json"), r)
    for inc in inclusions:
        write_json(os.path.join(case_dir, "chain",
                                f"{inc['receipt_id']}.json"), inc)
    for rev in revocations or []:
        write_json(os.path.join(case_dir, "revocations",
                                f"{rev['id']}.json"), rev)

case01 = os.path.join(TV_DIR, "01-valid")
write_bundle(case01, record_01, [receipt1, receipt2],
             [inclusion1, inclusion2])
write_json(os.path.join(case01, "expected.json"), {
    "case": "01-valid",
    "validity": "VALID",
    "history": "UNANCHORED",
    "issues": [],
    "counted": 2, "total": 2, "revoked": 0,
    "note": "No checkpoint is published for this bundle, so history is "
            "UNANCHORED even though validity is VALID.",
})

# ---------- case 02: bad receipt signature ----------

import copy
bad_receipt1 = copy.deepcopy(receipt1)
sig = bad_receipt1["signature"]["signature"]
# Flip one base64url character (keep the format valid so the failure is at
# signature verification, not at schema validation).
mid = len(sig) // 2
replacement = "B" if sig[mid] != "B" else "A"
bad_receipt1["signature"]["signature"] = sig[:mid] + replacement + sig[mid + 1:]
# The inclusion record still commits to the ORIGINAL hash, so the hash check
# fails too; the expected issue list names the signature failure first.
case02 = os.path.join(TV_DIR, "02-bad-signature")
write_bundle(case02, record_01, [bad_receipt1, receipt2],
             [inclusion1, inclusion2])
write_json(os.path.join(case02, "expected.json"), {
    "case": "02-bad-signature",
    "validity": "INVALID",
    "history": "UNANCHORED",
    "issues": ["receipt signature fails verification",
               "receipt hash does not match inclusion record"],
    "counted": 1, "total": 2, "revoked": 0,
    "note": "Only receipt 2 counts after recomputation.",
})

# ---------- case 03: broken chain ----------

bad_inclusion2 = copy.deepcopy(inclusion2)
bad_inclusion2["previous_receipt_hash"] = "0" * 64
# Re-sign so the failure is the chain link, not the inclusion signature.
bad_inclusion2.pop("signature")
bad_inclusion2["signature"] = {
    "algorithm": "Ed25519",
    "public_key": AGENT_DID,
    "signature": sign(agent_priv, bad_inclusion2),
}
case03 = os.path.join(TV_DIR, "03-broken-chain")
write_bundle(case03, record_01, [receipt1, receipt2],
             [inclusion1, bad_inclusion2])
write_json(os.path.join(case03, "expected.json"), {
    "case": "03-broken-chain",
    "validity": "INVALID",
    "history": "UNANCHORED",
    "issues": ["chain link mismatch at position 1"],
    "counted": 1, "total": 2, "revoked": 0,
    "note": "Only the receipt before the break counts; the chain cannot be "
            "recomputed past position 1.",
})

# ---------- case 04: revoked receipt ----------

revocation = {
    "id": str(uuid.uuid4()),
    "spec_version": "0.3",
    "receipt_id": R2_ID,
    "reason_code": "ISSUED_IN_ERROR",
    "reason": "Wrong task id: this receipt describes client-b-task-015.",
    "issued": "2026-11-12",
}
revocation["signature"] = {
    "algorithm": "Ed25519",
    "public_key": CLIENT_B_DID,
    "signature": sign(client_b_priv, revocation),
}
agg_04 = copy.deepcopy(AGGREGATES_01)
agg_04.update({
    "counted": 1, "revoked": 1,
    "distinct_clients": 1,
    "distinct_verified_clients": 0,
    "counted_from_verified_clients": 0,
    "by_task_type": {"research": {"COMPLETED": 1, "COMPLETED_WITH_ISSUES": 0,
                                  "FAILED": 0, "CANCELLED": 0}},
    "by_outcome": {"COMPLETED": 1, "COMPLETED_WITH_ISSUES": 0,
                   "FAILED": 0, "CANCELLED": 0},
    "counted_last_12_months": 1,
    "last_receipt": "2026-11-02",
})
history_04 = history + [make_history_entry(
    "2026-11-12", "RECEIPT_REVOKED", R2_ID,
    "Receipt revoked by its client (issued in error).")]
record_04 = make_record(
    RECORD_ID, CHAIN_HEAD,
    [index_entry(R1_ID, H1), index_entry(R2_ID, H2)],
    agg_04, history_04,
)
case04 = os.path.join(TV_DIR, "04-revoked")
write_bundle(case04, record_04, [receipt1, receipt2],
             [inclusion1, inclusion2], revocations=[revocation])
write_json(os.path.join(case04, "expected.json"), {
    "case": "04-revoked",
    "validity": "VALID",
    "history": "UNANCHORED",
    "issues": [],
    "counted": 1, "total": 2, "revoked": 1,
    "note": "The revoked receipt stays in the bundle but does not count.",
})

# ---------- case 05: duplicate receipt ----------

R3_ID = str(uuid.uuid4())
receipt3 = make_receipt(
    R3_ID, client_a_priv, CLIENT_A_DID,
    "client-a-task-001", "research", "literature-review",
    ["web-search", "summarization"],
    "Summarize five recent papers on agent trust frameworks.",
    "2026-11-02", "2026-11-02", "COMPLETED", ["on-time", "as-specified"],
    "2026-11-03",
)
H3 = receipt_hash(receipt3)
inclusion3 = make_inclusion(R3_ID, H3, H2, 2, "2026-11-03")
agg_05 = copy.deepcopy(AGGREGATES_01)
agg_05.update({"total": 3})
history_05 = history + [make_history_entry(
    "2026-11-03", "RECEIPT_ADDED", R3_ID,
    "Duplicate of the first receipt (same client, same task).")]
record_05 = make_record(
    RECORD_ID, H3,
    [index_entry(R1_ID, H1), index_entry(R2_ID, H2), index_entry(R3_ID, H3)],
    agg_05, history_05,
)
case05 = os.path.join(TV_DIR, "05-duplicate")
write_bundle(case05, record_05, [receipt1, receipt2, receipt3],
             [inclusion1, inclusion2, inclusion3])
write_json(os.path.join(case05, "expected.json"), {
    "case": "05-duplicate",
    "validity": "VALID",
    "history": "UNANCHORED",
    "issues": [],
    "counted": 2, "total": 3, "revoked": 0,
    "note": "The duplicate (same client, same task id) is validly signed and "
            "chained but does not count; the first receipt wins.",
})

# ---------- README ----------

with open(os.path.join(TV_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write("""# OAR v0.3 — Test Vectors

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
""")

# ---------- pretty-print schemas ----------

for name in ["reputation", "receipt", "inclusion", "revocation", "response",
             "rotation", "checkpoint"]:
    p = os.path.join(SCHEMAS_DIR, f"{name}.json")
    with open(p, encoding="utf-8") as f:
        schema = json.load(f)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
        f.write("\n")

# ---------- validation ----------

def load_schema(name):
    with open(os.path.join(SCHEMAS_DIR, f"{name}.json"),
              encoding="utf-8") as f:
        return json.load(f)

SCHEMAS = {n: load_schema(n) for n in
           ["reputation", "receipt", "inclusion", "revocation", "response",
            "rotation", "checkpoint"]}
FORMAT = jsonschema.FormatChecker()

def validate_schema(obj, schema_name):
    jsonschema.validate(obj, SCHEMAS[schema_name],
                        format_checker=FORMAT)

def verify_signature(obj):
    sig = obj["signature"]
    pub = Ed25519PublicKey.from_public_bytes(pub_from_didkey(sig["public_key"]))
    body = {k: v for k, v in obj.items() if k != "signature"}
    pub.verify(sig_decode(sig["signature"]), jcs(body))

failures = []
checks = 0

def check(name, fn, expect_ok=True):
    global checks
    checks += 1
    try:
        fn()
        ok = True
    except Exception as e:
        ok = False
        err = str(e)
    if ok != expect_ok:
        failures.append(f"{name}: expected {'OK' if expect_ok else 'FAIL'}, "
                        f"got {'OK' if ok else 'FAIL: ' + err}")

# 1. schema-validate every generated file
for case in ["01-valid", "02-bad-signature", "03-broken-chain",
             "04-revoked", "05-duplicate"]:
    d = os.path.join(TV_DIR, case)
    with open(os.path.join(d, "reputation.json"), encoding="utf-8") as f:
        rec = json.load(f)
    check(f"{case}/reputation.json schema",
          lambda r=rec: validate_schema(r, "reputation"))
    for fn in sorted(os.listdir(os.path.join(d, "receipts"))):
        with open(os.path.join(d, "receipts", fn), encoding="utf-8") as f:
            r = json.load(f)
        check(f"{case}/receipts/{fn} schema",
              lambda r=r: validate_schema(r, "receipt"))
    for fn in sorted(os.listdir(os.path.join(d, "chain"))):
        with open(os.path.join(d, "chain", fn), encoding="utf-8") as f:
            inc = json.load(f)
        check(f"{case}/chain/{fn} schema",
              lambda inc=inc: validate_schema(inc, "inclusion"))
    rev_dir = os.path.join(d, "revocations")
    if os.path.isdir(rev_dir):
        for fn in sorted(os.listdir(rev_dir)):
            with open(os.path.join(rev_dir, fn), encoding="utf-8") as f:
                rev = json.load(f)
            check(f"{case}/revocations/{fn} schema",
                  lambda rev=rev: validate_schema(rev, "revocation"))

# 2. verify signatures (valid cases must pass; case 02's bad receipt must fail)
for case, expect in [("01-valid", True), ("02-bad-signature", False),
                     ("03-broken-chain", True), ("04-revoked", True),
                     ("05-duplicate", True)]:
    d = os.path.join(TV_DIR, case)
    with open(os.path.join(d, "reputation.json"), encoding="utf-8") as f:
        rec = json.load(f)
    for fn in sorted(os.listdir(os.path.join(d, "receipts"))):
        with open(os.path.join(d, "receipts", fn), encoding="utf-8") as f:
            r = json.load(f)
        is_bad = (case == "02-bad-signature" and r["id"] == R1_ID)
        check(f"{case}/receipts/{fn} signature",
              lambda r=r: verify_signature(r), expect_ok=not is_bad)
    for fn in sorted(os.listdir(os.path.join(d, "chain"))):
        with open(os.path.join(d, "chain", fn), encoding="utf-8") as f:
            inc = json.load(f)
        check(f"{case}/chain/{fn} signature",
              lambda inc=inc: verify_signature(inc))
    for i, h in enumerate(rec["history"]):
        check(f"{case}/history[{i}] signature",
              lambda h=h: verify_signature(h))
    rev_dir = os.path.join(d, "revocations")
    if os.path.isdir(rev_dir):
        for fn in sorted(os.listdir(rev_dir)):
            with open(os.path.join(rev_dir, fn), encoding="utf-8") as f:
                rev = json.load(f)
            check(f"{case}/revocations/{fn} signature",
                  lambda rev=rev: verify_signature(rev))

# 3. chain links and head (case 03 must fail the link check)
for case in ["01-valid", "02-bad-signature", "03-broken-chain",
             "04-revoked", "05-duplicate"]:
    d = os.path.join(TV_DIR, case)
    with open(os.path.join(d, "reputation.json"), encoding="utf-8") as f:
        rec = json.load(f)
    receipts = {}
    for fn in sorted(os.listdir(os.path.join(d, "receipts"))):
        with open(os.path.join(d, "receipts", fn), encoding="utf-8") as f:
            r = json.load(f)
        receipts[r["id"]] = r
    inclusions = []
    for fn in sorted(os.listdir(os.path.join(d, "chain"))):
        with open(os.path.join(d, "chain", fn), encoding="utf-8") as f:
            inclusions.append(json.load(f))
    inclusions.sort(key=lambda x: x["position"])
    prev = None
    chain_ok = True
    for inc in inclusions:
        rh = sha256_hex(jcs(receipts[inc["receipt_id"]]))
        if rh != inc["receipt_hash"] or inc["previous_receipt_hash"] != prev:
            chain_ok = False
        prev = inc["receipt_hash"]
    chain_ok = chain_ok and prev == rec["chain_head"]
    expect_ok = case not in ("02-bad-signature", "03-broken-chain")
    checks += 1
    if chain_ok != expect_ok:
        failures.append(f"{case} chain: expected {'OK' if expect_ok else 'FAIL'}, "
                        f"got {'OK' if chain_ok else 'FAIL'}")

# 4. recompute aggregates for the valid-counting cases
for case, exp_counted, exp_total in [("01-valid", 2, 2), ("04-revoked", 1, 2),
                                     ("05-duplicate", 2, 3)]:
    d = os.path.join(TV_DIR, case)
    with open(os.path.join(d, "reputation.json"), encoding="utf-8") as f:
        rec = json.load(f)
    checks += 1
    ag = rec["aggregates"]
    if ag["counted"] != exp_counted or ag["total"] != exp_total:
        failures.append(f"{case} aggregates: counted={ag['counted']} "
                        f"(expected {exp_counted}), total={ag['total']} "
                        f"(expected {exp_total})")

# 5. spec Appendix A JSON blocks still parse
spec_text = open(os.path.join(BASE, "OAR-SPEC-v0.3.md"), encoding="utf-8").read()
blocks = re.findall(r"```json\n(.*?)```", spec_text, re.S)
for i, b in enumerate(blocks):
    checks += 1
    try:
        json.loads(b)
    except Exception as e:
        failures.append(f"spec JSON block {i}: {e}")

print(f"checks run: {checks}")
print(f"failures: {len(failures)}")
for f in failures:
    print("  FAIL:", f)
if not failures:
    print("ALL CHECKS PASSED")
    print("cases: 01-valid, 02-bad-signature, 03-broken-chain, "
          "04-revoked, 05-duplicate")
    print(f"agent did:key: {AGENT_DID}")
    print(f"client A did:key: {CLIENT_A_DID}")
    print(f"client B did:key: {CLIENT_B_DID}")
