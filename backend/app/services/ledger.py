"""Seat ledger: intake and supernumerary usage per programme (PRD 6.4)."""
import math
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_policy
from ..models import Programme, Student


def cap_seats(cap_pct: float, approved_intake: int) -> int:
    return math.ceil(cap_pct / 100 * approved_intake)


def category_counts(db: Session, college_ids: list[int] | None, year: int) -> dict[int, dict[str, int]]:
    """programme_id -> {admission_category: active count} in a single grouped query."""
    stmt = (
        select(Student.programme_id, Student.admission_category, func.count())
        .where(Student.status == "active", Student.year == year, Student.programme_id.is_not(None))
        .group_by(Student.programme_id, Student.admission_category)
    )
    if college_ids is not None:
        stmt = stmt.where(Student.college_id.in_(college_ids))
    counts: dict[int, dict[str, int]] = defaultdict(dict)
    for pid, cat, n in db.execute(stmt):
        counts[pid][cat] = n
    return counts


def programme_entry(prog: Programme, counts: dict[str, int], policy: dict) -> dict:
    admitted = sum(counts.get(c, 0) for c in policy["intake_categories"])
    supernumerary = {}
    for cat, pct in policy["supernumerary_cap_pct"].items():
        count = counts.get(cat, 0)
        cap = cap_seats(pct, prog.approved_intake)
        supernumerary[cat] = {"count": count, "cap": cap, "over_by": max(0, count - cap)}
    return {
        "id": prog.id, "college_id": prog.college_id, "name": prog.name, "level": prog.level,
        "shift": prog.shift, "approved_intake": prog.approved_intake, "admitted": admitted,
        "over_by": max(0, admitted - prog.approved_intake), "supernumerary": supernumerary,
        "total_enrolled": sum(counts.values()),
    }


def ledger_for_colleges(db: Session, college_ids: list[int] | None = None, year: int | None = None) -> dict[int, list[dict]]:
    """college_id -> list of programme ledger entries."""
    policy = get_policy()
    year = year or policy["academic_year"]
    counts = category_counts(db, college_ids, year)
    stmt = select(Programme).order_by(Programme.college_id, Programme.id)
    if college_ids is not None:
        stmt = stmt.where(Programme.college_id.in_(college_ids))
    out: dict[int, list[dict]] = defaultdict(list)
    for prog in db.scalars(stmt):
        out[prog.college_id].append(programme_entry(prog, counts.get(prog.id, {}), policy))
    return out


def college_ledger(db: Session, college_id: int, year: int | None = None) -> list[dict]:
    return ledger_for_colleges(db, [college_id], year).get(college_id, [])
