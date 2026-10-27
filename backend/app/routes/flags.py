from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Flag, MatchCandidate, Student, User, utcnow
from ..schemas import ReviewIn
from ..security import INSTITUTION, OFFICER, require_roles, scoped_college_id
from ..services.audit import record_for
from .common import Page

router = APIRouter(prefix="/flags", tags=["flags"])

REDACTED = "another institution"


def age_days(created: datetime) -> int:
    return max(0, (utcnow() - created).days)


def flag_out(db: Session, f: Flag, user: User, counterparts: dict[int, Student] | None = None) -> dict:
    evidence = dict(f.evidence or {})
    cp_id = evidence.get("counterpart_student_id")
    counterpart = None
    if cp_id is not None:
        if user.role == OFFICER:
            cp = (counterparts or {}).get(cp_id) or db.get(Student, cp_id)
            if cp is not None:
                counterpart = {"student_id": cp.id, "name": cp.name, "student_code": cp.student_code,
                               "college_id": cp.college_id, "college_name": cp.college.name}
        else:
            counterpart = REDACTED
            evidence = {k: v for k, v in evidence.items() if not k.startswith("counterpart")}
    return {
        "id": f.id, "code": f.code, "severity": f.severity, "message": f.message, "status": f.status,
        "evidence": evidence, "counterpart": counterpart,
        "student": ({"id": f.student.id, "name": f.student.name, "student_code": f.student.student_code}
                    if f.student else None),
        "college_id": f.college_id, "college_name": f.college.name,
        "programme": f.programme.name if f.programme else (f.student.programme_raw if f.student else None),
        "match_id": f.match_id if user.role == OFFICER else None,
        "created_at": f.created_at.isoformat(), "age_days": age_days(f.created_at),
        "reviewed_by": f.reviewed_by, "reviewed_at": f.reviewed_at.isoformat() if f.reviewed_at else None,
        "note": f.note,
    }


@router.get("")
def list_flags(page: Page = Depends(), status: str | None = None, code: str | None = None,
               severity: str | None = None, college_id: int | None = None, db: Session = Depends(get_db),
               user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    college_id = scoped_college_id(user, college_id)
    stmt = select(Flag)
    if college_id:
        stmt = stmt.where(Flag.college_id == college_id)
    if status:
        stmt = stmt.where(Flag.status == status)
    if code:
        stmt = stmt.where(Flag.code == code)
    if severity:
        stmt = stmt.where(Flag.severity == severity)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(db.scalars(page.apply(stmt.order_by(Flag.id.desc()))))
    cp_ids = {f.evidence.get("counterpart_student_id") for f in rows} - {None}
    counterparts = {s.id: s for s in db.scalars(select(Student).where(Student.id.in_(cp_ids)))} if cp_ids else {}
    return page.wrap([flag_out(db, f, user, counterparts) for f in rows], total)


@router.patch("/{flag_id}")
def review_flag(flag_id: int, body: ReviewIn, db: Session = Depends(get_db),
                user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    flag = db.get(Flag, flag_id)
    if flag is None:
        raise HTTPException(404, "Flag not found")
    if user.role == INSTITUTION:
        if flag.college_id != user.college_id:
            raise HTTPException(403, "You cannot review another institution's flag")
        if body.status == "dismissed":
            raise HTTPException(403, "Only AICTE officers can dismiss flags")
    flag.status, flag.note = body.status, body.note
    flag.reviewed_by, flag.reviewed_at = user.username, utcnow()
    if flag.match_id and user.role == OFFICER:
        match = db.get(MatchCandidate, flag.match_id)
        if match and match.status == "pending":
            match.status, match.note = body.status, body.note
            match.reviewed_by, match.reviewed_at = user.username, flag.reviewed_at
    record_for(db, user, "FLAG_REVIEW", "flag", flag.id,
               {"code": flag.code, "status": body.status, "note": body.note or ""})
    db.commit()
    return flag_out(db, flag, user)
