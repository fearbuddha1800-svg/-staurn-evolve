---
slug: audit_ledger.schema
type: note
graph: gitnexus
---

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:signal-relay:audit-ledger:entry:v1",
  "title": "Hash-chained audit ledger entry",
  "description": "One JSON document per audit_entries SQLite row. The hash covers every field except hash using audit_ledger.entry_hash. Cross-record integrity, sequence continuity, stale-base checks and approval transitions must be checked with AuditLedger.verify; JSON Schema alone does not verify cryptography or authorization. Ledger reverts never execute broker actions. Unknown metrics are null, not fabricated zeroes. Keep consistent units within one scope/database.",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "seq", "timestamp", "scope", "kind", "actor", "reason", "state", "payload", "prev_hash", "hash"],
  "properties": {
    "version": {"const": 1},
    "seq": {"$ref": "#/$defs/sequence"},
    "timestamp": {"type": "string", "format": "date-time", "pattern": "Z$"},
    "scope": {"$ref": "#/$defs/text"},
    "kind": {"enum": ["snapshot", "revert_proposed", "revert_approved", "revert_rejected", "revert_committed"]},
    "actor": {"$ref": "#/$defs/text"},
    "reason": {"$ref": "#/$defs/text"},
    "state": {"$ref": "#/$defs/state"},
    "payload": {"type": "object"},
    "prev_hash": {"$ref": "#/$defs/hash"},
    "hash": {"$ref": "#/$defs/hash"}
  },
  "allOf": [
    {
      "if": {"properties": {"kind": {"const": "snapshot"}}},
      "then": {"properties": {"payload": {
        "type": "object", "additionalProperties": false,
        "required": ["metadata"], "properties": {"metadata": {"type": "object"}}
      }}}
    },
    {
      "if": {"properties": {"kind": {"const": "revert_proposed"}}},
      "then": {"properties": {"payload": {
        "type": "object", "additionalProperties": false,
        "required": ["target_seq", "target_hash", "base_seq", "base_hash"],
        "properties": {
          "target_seq": {"$ref": "#/$defs/sequence"},
          "target_hash": {"$ref": "#/$defs/hash"},
          "base_seq": {"$ref": "#/$defs/sequence"},
          "base_hash": {"$ref": "#/$defs/hash"}
        }
      }}}
    },
    {
      "if": {"properties": {"kind": {"enum": ["revert_approved", "revert_rejected"]}}},
      "then": {"properties": {"payload": {
        "type": "object", "additionalProperties": false,
        "required": ["proposal_seq"],
        "properties": {"proposal_seq": {"$ref": "#/$defs/sequence"}}
      }}}
    },
    {
      "if": {"properties": {"kind": {"const": "revert_committed"}}},
      "then": {"properties": {"payload": {
        "type": "object", "additionalProperties": false,
        "required": ["proposal_seq", "approval_seq", "target_seq", "target_hash"],
        "properties": {
          "proposal_seq": {"$ref": "#/$defs/sequence"},
          "approval_seq": {"$ref": "#/$defs/sequence"},
          "target_seq": {"$ref": "#/$defs/sequence"},
          "target_hash": {"$ref": "#/$defs/hash"}
        }
      }}}
    }
  ],
  "$defs": {
    "sequence": {"type": "integer", "minimum": 1},
    "hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "text": {"type": "string", "minLength": 1, "maxLength": 4096, "pattern": "\\S"},
    "state": {
      "type": "object", "additionalProperties": false,
      "required": ["position_size", "netprofit", "equity", "max_drawdown"],
      "properties": {
        "position_size": {"type": ["number", "null"], "description": "Signed position size in the caller-declared units; null means unknown."},
        "netprofit": {"type": ["number", "null"], "description": "Observed net profit in caller-declared units."},
        "equity": {"type": ["number", "null"], "description": "Observed equity; not recomputed from netprofit."},
        "max_drawdown": {"type": ["number", "null"], "minimum": 0, "description": "Nonnegative drawdown magnitude on a caller-declared basis."}
      }
    }
  }
}

## Links from
- [[test_audit_ledger]]
