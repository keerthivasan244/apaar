"""Explainable institution risk score (PRD 6.6). One pass over grouped queries; no per-college queries."""
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from ..config import get_policy
from ..models import College, Flag, MatchCandidate, Student, utcnow
from . import ledger

DUP_FLAG_CODES = ("DUP_SAME_COLLEGE", "DUP_CROSS_COLLEGE")
QUALITY_CODES = ("MISSING_APAAR", "INVALID_APAAR_FORMAT", "DOB_IMPLAUSIBLE", "CATEGORY_INCONSISTENT",
                 "UNAPPROVED_PROGRAMME")
DISCLAIMER = "Risk score prioritises inspections; it is not a penalty decision."


def short_programme(name: str) -> str:
    """'B.Tech Computer Science and Engineering' -> 'CSE'; 'M.Tech Computer Science' -> 'M.Tech CS'."""
    prefix, _, rest = name.partition(" ")
    if prefix == "Diploma":
        prefix, rest = "Diploma", rest.removeprefix("in ")
    initials = "".join(w[0] for w in rest.split() if w[0].isupper())
    return initials if prefix == "B.Tech" else f"{prefix} {initials}"


def over_intake_sentence(progs: list[dict], approved: int, admitted: int, excess: int, rate: float) -> str:
    if admitted > approved:
        return f"Admitted {admitted} against {approved} approved seats (excess {excess}, {rate * 100:.1f}%)"
    parts = [f"{short_programme(p['name'])} intake +{p['over_by']}" for p in progs if p["over_by"]]
    parts += [f"{short_programme(p['name'])} {cat} quota +{s['over_by']}"
              for p in progs for cat, s in p["supernumerary"].items() if s["over_by"]]
    return f"{excess} admissions above approved limits ({rate * 100:.1f}% of {approved} seats): {', '.join(parts)}"


def band_for(score: int) -> str:
    bands = get_policy()["risk_bands"]
    if score < bands["low_max"]:
        return "low"
    if score <= bands["medium_max"]:
        return "medium"
    return "high"


def _student_sets(db: Session, year: int) -> tuple[dict, dict]:
    dup: dict[int, set[int]] = defaultdict(set)
    quality: dict[int, set[int]] = defaultdict(set)
    for cid, sid, code in db.execute(select(Flag.college_id, Flag.student_id, Flag.code).where(
            Flag.status == "open", Flag.student_id.is_not(None),
            Flag.code.in_(DUP_FLAG_CODES + QUALITY_CODES))):
        (dup if code in DUP_FLAG_CODES else quality)[cid].add(sid)
    for col in (MatchCandidate.student_a_id, MatchCandidate.student_b_id):
        s = aliased(Student)
        for cid, sid in db.execute(select(s.college_id, s.id).join(MatchCandidate, col == s.id).where(
                MatchCandidate.status.in_(("pending", "confirmed")), s.year == year)):
            dup[cid].add(sid)
    return dup, quality


def compute_risk(db: Session, college_ids: list[int] | None = None) -> list[dict]:
    policy = get_policy()
    year = policy["academic_year"]
    weights = policy["risk_weights"]
    colleges = list(db.scalars(select(College).where(College.id.in_(college_ids)) if college_ids
                               else select(College)))
    ledgers = ledger.ledger_for_colleges(db, [c.id for c in colleges] if college_ids else None, year)
    active = dict(db.execute(select(Student.college_id, func.count()).where(
        Student.status == "active", Student.year == year).group_by(Student.college_id)).all())
    dup, quality = _student_sets(db, year)
    now = utcnow()
    ages: dict[int, list[float]] = defaultdict(list)
    for cid, created in db.execute(select(Flag.college_id, Flag.created_at).where(Flag.status == "open")):
        ages[cid].append((now - created).total_seconds() / 86400)

    out = []
    for c in colleges:
        progs = ledgers.get(c.id, [])
        n_active = active.get(c.id, 0)
        approved = sum(p["approved_intake"] for p in progs)
        admitted = sum(p["admitted"] for p in progs)
        excess = (sum(p["over_by"] for p in progs)
                  + sum(s["over_by"] for p in progs for s in p["supernumerary"].values()))
        excess_rate = excess / approved if approved else 0.0
        dup_n, qual_n = len(dup.get(c.id, ())), len(quality.get(c.id, ()))
        dup_rate = dup_n / n_active if n_active else 0.0
        qual_rate = qual_n / n_active if n_active else 0.0
        flag_ages = ages.get(c.id, [])
        mean_age = sum(flag_ages) / len(flag_ages) if flag_ages else 0.0
        growth = (n_active - c.prev_year_enrolment) / c.prev_year_enrolment if c.prev_year_enrolment else 0.0

        values = {
            "over_intake": min(1.0, excess_rate / 0.10),
            "duplicates": min(1.0, dup_rate / 0.05),
            "data_quality": min(1.0, qual_rate / 0.10),
            "flag_ageing": min(1.0, mean_age / 30),
            "anomaly": min(1.0, max(0.0, growth) / 0.25),
        }
        sentences = {
            "over_intake": over_intake_sentence(progs, approved, admitted, excess, excess_rate),
            "duplicates": f"{dup_rate * 100:.1f}% of students are in suspected duplicate records ({dup_n} students)",
            "data_quality": f"{qual_n} students ({qual_rate * 100:.1f}%) have data-quality issues such as "
                            f"missing or invalid APAAR IDs",
            "flag_ageing": f"{len(flag_ages)} unresolved flags averaging {mean_age:.0f} days old",
            "anomaly": f"Enrolment up {growth * 100:.0f}% on last year ({c.prev_year_enrolment} to {n_active})",
        }
        components = {k: {"value": round(v, 4), "weight": weights[k], "contribution": round(weights[k] * v, 2)}
                      for k, v in values.items()}
        score = round(sum(weights[k] * v for k, v in values.items()))
        ranked = sorted((k for k in values if weights[k] * values[k] > 0),
                        key=lambda k: weights[k] * values[k], reverse=True)
        out.append({
            "college_id": c.id, "aicte_id": c.aicte_id, "name": c.name, "state": c.state, "score": score,
            "band": band_for(score), "components": components, "reasons": [sentences[k] for k in ranked[:3]],
            "facts": {"active_students": n_active, "approved_intake": approved, "admitted": admitted,
                      "excess": excess, "duplicate_students": dup_n, "quality_students": qual_n,
                      "open_flags": len(flag_ages), "prev_year_enrolment": c.prev_year_enrolment},
        })
    out.sort(key=lambda r: (-r["score"], r["college_id"]))
    return out
