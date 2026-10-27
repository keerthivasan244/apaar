from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Flag, MatchCandidate, Student, User, utcnow
from ..schemas import ReviewIn
from ..security import OFFICER, require_roles
from ..services.audit import record_for
from .common import Page

router = APIRouter(prefix="/matches", tags=["matches"])


def side(s: Student, full: bool = False) -> dict:
    out = {"id": s.id, "name": s.name, "student_code": s.student_code, "college_id": s.college_id,
           "college_name": s.college.name}
    if full:
        out.update({"father_name": s.father_name, "dob": s.dob.isoformat(), "gender": s.gender,
                    "apaar_id": s.apaar_id, "phone_last4": s.phone_last4,
                    "programme": s.programme.name if s.programme else s.programme_raw,
                    "college_aicte_id": s.college.aicte_id})
    return out


def match_out(m: MatchCandidate, full: bool = False) -> dict:
    out = {"id": m.id, "score": m.score, "band": m.band, "status": m.status,
           "student_a": side(m.student_a, full), "student_b": side(m.student_b, full),
           "created_at": m.created_at.isoformat(), "reviewed_by": m.reviewed_by,
           "reviewed_at": m.reviewed_at.isoformat() if m.reviewed_at else None, "note": m.note}
    if full:
        out.update({"components": m.components, "explanations": m.explanations})
    else:
        out["top_explanation"] = m.explanations[0] if m.explanations else None
    return out


@router.get("")
def list_matches(page: Page = Depends(), status: str | None = None, band: str | None = None,
                 db: Session = Depends(get_db), _user: User = Depends(require_roles(OFFICER))):
    stmt = select(MatchCandidate)
    if status:
        stmt = stmt.where(MatchCandidate.status == status)
    if band:
        stmt = stmt.where(MatchCandidate.band == band)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(page.apply(stmt.order_by(MatchCandidate.score.desc(), MatchCandidate.id)))
    return page.wrap([match_out(m) for m in rows], total)


def _get(db: Session, match_id: int) -> MatchCandidate:
    m = db.get(MatchCandidate, match_id)
    if m is None:
        raise HTTPException(404, "Match not found")
    return m


@router.get("/{match_id}")
def get_match(match_id: int, db: Session = Depends(get_db), _user: User = Depends(require_roles(OFFICER))):
    return match_out(_get(db, match_id), full=True)


@router.patch("/{match_id}")
def review_match(match_id: int, body: ReviewIn, db: Session = Depends(get_db),
                 user: User = Depends(require_roles(OFFICER))):
    m = _get(db, match_id)
    now = utcnow()
    m.status, m.note, m.reviewed_by, m.reviewed_at = body.status, body.note, user.username, now
    linked = list(db.scalars(select(Flag).where(Flag.match_id == m.id)))
    for f in linked:
        f.status, f.note, f.reviewed_by, f.reviewed_at = body.status, body.note, user.username, now
    record_for(db, user, "MATCH_REVIEW", "match", m.id,
               {"status": body.status, "score": m.score, "note": body.note or "",
                "flag_ids": [f.id for f in linked]})
    db.commit()
    return match_out(m, full=True)
