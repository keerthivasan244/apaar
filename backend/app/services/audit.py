"""Tamper-evident, hash-chained audit log (PRD 6.10)."""
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditLog

GENESIS = "0" * 64


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def entry_body(row: AuditLog) -> dict:
    return {
        "id": row.id, "ts": row.ts, "actor": row.actor, "actor_role": row.actor_role,
        "action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id,
        "payload": row.payload, "prev_hash": row.prev_hash,
    }


def compute_hash(body: dict) -> str:
    return hashlib.sha256((body["prev_hash"] + canonical_json(body)).encode("utf-8")).hexdigest()


def record(db: Session, *, actor: str, actor_role: str, action: str, entity_type: str,
           entity_id, payload: dict | None = None, ts: datetime | None = None) -> AuditLog:
    """Append an entry. The caller commits. Single writer (one uvicorn worker) keeps ids sequential."""
    db.flush()
    last = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).first()
    # Round-trip the payload through JSON so the hashed form equals what SQLite returns later.
    payload = json.loads(canonical_json(payload or {}))
    row = AuditLog(
        id=(last.id + 1) if last else 1,
        ts=(ts or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        actor=actor, actor_role=actor_role, action=action, entity_type=entity_type,
        entity_id=str(entity_id), payload=payload, prev_hash=last.hash if last else GENESIS,
    )
    row.hash = compute_hash(entry_body(row))
    db.add(row)
    db.flush()
    return row


def record_for(db: Session, user, action: str, entity_type: str, entity_id, payload: dict | None = None):
    return record(db, actor=user.username, actor_role=user.role, action=action,
                  entity_type=entity_type, entity_id=entity_id, payload=payload)


def verify_chain(db: Session) -> dict:
    prev = GENESIS
    checked = 0
    for row in db.scalars(select(AuditLog).order_by(AuditLog.id)):
        checked += 1
        body = entry_body(row)
        if row.prev_hash != prev or compute_hash(body) != row.hash:
            return {"intact": False, "entries_checked": checked, "first_broken_id": row.id}
        prev = row.hash
    return {"intact": True, "entries_checked": checked, "first_broken_id": None}
