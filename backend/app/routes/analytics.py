from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_policy
from ..db import get_db
from ..models import AuditLog, College, Flag, MatchCandidate, Student, User
from ..security import INSTITUTION, OFFICER, assert_college_access, require_roles
from ..services import ledger
from ..services.risk import compute_risk

router = APIRouter(prefix="/analytics", tags=["analytics"])


def audit_out(a: AuditLog) -> dict:
    return {"id": a.id, "ts": a.ts, "actor": a.actor, "actor_role": a.actor_role, "action": a.action,
            "entity_type": a.entity_type, "entity_id": a.entity_id, "hash": a.hash}


def _flags_by_code(db: Session, college_id: int | None = None) -> list[dict]:
    stmt = select(Flag.code, func.count()).where(Flag.status == "open").group_by(Flag.code)
    if college_id:
        stmt = stmt.where(Flag.college_id == college_id)
    return [{"code": c, "count": n} for c, n in sorted(db.execute(stmt).all(), key=lambda x: -x[1])]


def _categories(db: Session, college_id: int | None = None) -> list[dict]:
    year = get_policy()["academic_year"]
    stmt = (select(Student.admission_category, func.count())
            .where(Student.status == "active", Student.year == year).group_by(Student.admission_category))
    if college_id:
        stmt = stmt.where(Student.college_id == college_id)
    return [{"category": c, "count": n} for c, n in sorted(db.execute(stmt).all(), key=lambda x: -x[1])]


@router.get("/overview")
def overview(db: Session = Depends(get_db), _user: User = Depends(require_roles(OFFICER))):
    risk = compute_risk(db)
    over = sorted(risk, key=lambda r: (-r["facts"]["excess"], r["college_id"]))[:10]
    return {
        "totals": {
            "colleges": db.scalar(select(func.count(College.id))),
            "students": db.scalar(select(func.count()).where(Student.status == "active")),
            "open_flags": db.scalar(select(func.count()).where(Flag.status == "open")),
            "pending_matches": db.scalar(select(func.count()).where(MatchCandidate.status == "pending")),
            "high_risk_colleges": sum(1 for r in risk if r["band"] == "high"),
        },
        "flags_by_code": _flags_by_code(db),
        "category_breakdown": _categories(db),
        "top_over_intake": [{"college_id": r["college_id"], "college": r["name"],
                             "approved": r["facts"]["approved_intake"], "admitted": r["facts"]["admitted"],
                             "excess": r["facts"]["excess"]} for r in over],
        "top_risk": [{"college_id": r["college_id"], "name": r["name"], "score": r["score"], "band": r["band"],
                      "top_reason": r["reasons"][0] if r["reasons"] else None} for r in risk[:5]],
        "recent_audit": [audit_out(a) for a in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(5))],
    }


@router.get("/colleges/{college_id}")
def college_analytics(college_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    assert_college_access(user, college_id)
    if db.get(College, college_id) is None:
        raise HTTPException(404, "College not found")
    programmes = ledger.college_ledger(db, college_id)
    return {
        "programmes": programmes,
        "category_breakdown": _categories(db, college_id),
        "flags_by_code": _flags_by_code(db, college_id),
        "totals": {
            "students": db.scalar(select(func.count()).where(Student.college_id == college_id,
                                                              Student.status == "active")),
            "open_flags": db.scalar(select(func.count()).where(Flag.college_id == college_id,
                                                                Flag.status == "open")),
            "programmes": len(programmes),
            "programmes_over_intake": sum(1 for p in programmes if p["over_by"] > 0),
            "approved_intake": sum(p["approved_intake"] for p in programmes),
            "admitted": sum(p["admitted"] for p in programmes),
        },
    }
