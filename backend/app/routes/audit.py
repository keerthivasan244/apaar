from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditLog, User
from ..security import OFFICER, require_roles
from ..services.audit import verify_chain
from .common import Page

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(page: Page = Depends(), action: str | None = None, db: Session = Depends(get_db),
               _user: User = Depends(require_roles(OFFICER))):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(page.apply(stmt.order_by(AuditLog.id.desc())))
    return page.wrap([{"id": a.id, "ts": a.ts, "actor": a.actor, "actor_role": a.actor_role, "action": a.action,
                       "entity_type": a.entity_type, "entity_id": a.entity_id, "payload": a.payload,
                       "prev_hash": a.prev_hash, "hash": a.hash} for a in rows], total)


@router.get("/verify")
def verify(db: Session = Depends(get_db), _user: User = Depends(require_roles(OFFICER))):
    return verify_chain(db)
