from __future__ import annotations

from secure_vector_db.crypto.merkle_audit import JsonlMerkleAuditLog, append_merkle_audit_event, build_merkle_audit_event


def test_merkle_audit_event_is_safe_dict() -> None:
    event = build_merkle_audit_event("verify", "valid", "abc", 2, 3, "integridad Merkle valida")
    payload = event.to_dict()
    assert payload["action"] == "verify"
    assert payload["status"] == "valid"
    assert "vector" not in str(payload).lower()


def test_jsonl_merkle_audit_log_persists_events(tmp_path) -> None:
    log = JsonlMerkleAuditLog(tmp_path / "audit" / "merkle.jsonl")
    append_merkle_audit_event(log, "root", "valid", "abc", 1, 1, "integridad Merkle valida")
    events = log.read_events()
    assert len(events) == 1
    assert events[0].action == "root"
