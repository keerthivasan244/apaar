"""Fuzzy identity resolution across institutions (PRD 6.5)."""
from dataclasses import dataclass
from datetime import date

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler, Levenshtein
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import get_policy
from ..models import MatchCandidate, Student


@dataclass
class Candidate:
    """The fields the matcher needs; built from a Student or from not-yet-saved seed rows."""
    id: int | None
    college_id: int
    name: str
    name_norm: str
    father_name: str
    father_name_norm: str
    dob: date
    gender: str
    phone_hash: str | None = None
    phone_last4: str | None = None
    apaar_id: str | None = None

    @classmethod
    def of(cls, s: Student) -> "Candidate":
        return cls(s.id, s.college_id, s.name, s.name_norm, s.father_name, s.father_name_norm, s.dob,
                   s.gender, s.phone_hash, s.phone_last4, s.apaar_id)


# ------------------------------------------------------------------ similarity primitives

def _expand_initials(tokens: list[str], other: list[str]) -> list[str]:
    """A single-letter token is treated as equal to a token in `other` starting with that letter."""
    out = []
    for t in tokens:
        if len(t) == 1:
            full = next((o for o in other if len(o) > 1 and o.startswith(t)), None)
            out.append(full or t)
        else:
            out.append(t)
    return out


def name_similarity(a: str, b: str) -> float | None:
    if not a or not b:
        return None
    ta, tb = a.split(), b.split()
    ta, tb = _expand_initials(ta, tb), _expand_initials(tb, ta)
    sa, sb = " ".join(ta), " ".join(tb)
    return max(JaroWinkler.similarity(sa, sb), fuzz.token_sort_ratio(sa, sb) / 100)


def swapped_dob(d: date) -> date | None:
    if d.day <= 12 and d.month <= 12 and d.day != d.month:
        return date(d.year, d.day, d.month)
    return None


def dob_similarity(a: date, b: date) -> float:
    if a == b:
        return 1.0
    if swapped_dob(a) == b:
        return 0.7
    return 0.0


# ------------------------------------------------------------------ scoring and explanations

def _name_sentence(label: str, raw_a: str, raw_b: str, norm_a: str, norm_b: str, sim: float) -> str:
    if norm_a == norm_b:
        if raw_a.strip().lower() == raw_b.strip().lower():
            return f"{label} identical ({norm_a})"
        return f"{label} normalise to the same string ({norm_a}), spelling variants treated as equal"
    tokens_a = [t for t in norm_a.split() if len(t) > 1]
    tokens_b = [t for t in norm_b.split() if len(t) > 1]
    if tokens_a == tokens_b:
        return f"{label} match apart from an initial (similarity {sim:.2f})"
    dist = Levenshtein.distance(norm_a, norm_b)
    if dist == 1:
        return f"{label} differ by one letter (similarity {sim:.2f})"
    if sim >= 0.85:
        return f"{label} are very similar, {dist} letters apart (similarity {sim:.2f})"
    return f"{label} differ (similarity {sim:.2f})"


def score_pair(a: Candidate, b: Candidate) -> dict:
    weights = get_policy()["match_weights"]
    raw: dict[str, tuple] = {  # field -> (value_a, value_b, similarity or None if excluded)
        "name": (a.name, b.name, name_similarity(a.name_norm, b.name_norm)),
        "father_name": (a.father_name, b.father_name, name_similarity(a.father_name_norm, b.father_name_norm)),
        "dob": (a.dob.isoformat(), b.dob.isoformat(), dob_similarity(a.dob, b.dob)),
        "gender": (a.gender, b.gender, 1.0 if a.gender == b.gender else 0.0),
        "phone": (f"…{a.phone_last4}" if a.phone_last4 else None, f"…{b.phone_last4}" if b.phone_last4 else None,
                  (1.0 if a.phone_hash == b.phone_hash else 0.0) if a.phone_hash and b.phone_hash else None),
    }
    available = sum(weights[f] for f, (_, _, sim) in raw.items() if sim is not None)
    components, score = {}, 0.0
    for f, (va, vb, sim) in raw.items():
        eff = weights[f] / available if sim is not None else 0.0
        contribution = (sim or 0.0) * eff
        score += contribution
        components[f] = {"value_a": va, "value_b": vb, "similarity": None if sim is None else round(sim, 4),
                         "base_weight": weights[f], "weight": round(eff, 4),
                         "contribution": round(contribution, 4), "excluded": sim is None}

    explanations = [
        _name_sentence("Names", a.name, b.name, a.name_norm, b.name_norm, raw["name"][2] or 0),
        _name_sentence("Father's names", a.father_name, b.father_name, a.father_name_norm, b.father_name_norm,
                       raw["father_name"][2] or 0),
    ]
    dob_sim = raw["dob"][2]
    explanations.append("Date of birth identical" if dob_sim == 1.0 else
                        "Date of birth matches with day and month swapped" if dob_sim == 0.7 else
                        "Dates of birth differ")
    explanations.append("Gender matches" if a.gender == b.gender else "Gender differs")
    phone_sim = raw["phone"][2]
    if phone_sim is None:
        explanations.append("Phone missing on one or both records, so its weight is shared across the other fields")
    else:
        explanations.append(f"Phone numbers match (ending {a.phone_last4})" if phone_sim == 1.0
                            else "Phone numbers differ")
    return {"score": round(score, 4), "components": components, "explanations": explanations}


def band_for(score: float) -> str | None:
    t = get_policy()["match_thresholds"]
    if score >= t["probable"]:
        return "probable"
    if score >= t["review"]:
        return "review"
    return None


# ------------------------------------------------------------------ blocking

def block_keys(c: Candidate) -> list[tuple[str, date]]:
    keys = [(c.gender, c.dob)]
    if (s := swapped_dob(c.dob)) is not None:
        keys.append((c.gender, s))
    return keys


class BlockIndex:
    """In-memory (gender, dob) index, used by the seeder to avoid accidental collisions."""

    def __init__(self):
        self._by_key: dict[tuple[str, date], list[Candidate]] = {}

    def add(self, c: Candidate) -> None:
        self._by_key.setdefault((c.gender, c.dob), []).append(c)

    def candidates(self, c: Candidate) -> list[Candidate]:
        out = []
        for key in block_keys(c):
            out.extend(self._by_key.get(key, []))
        return out

    def best_score(self, c: Candidate) -> float:
        return max((score_pair(c, o)["score"] for o in self.candidates(c) if o is not c), default=0.0)


def _exact_apaar_dup(a: Candidate, b: Candidate) -> bool:
    from .validation import apaar_valid

    return bool(a.apaar_id) and a.apaar_id == b.apaar_id and apaar_valid(a.apaar_id)


def match_new_students(db: Session, students: list[Student]) -> tuple[int, int]:
    """Match newly inserted students against active students at other colleges. Returns (matches, flags)."""
    from .validation import add_student_flag

    if not students:
        return 0, 0
    year = students[0].year
    dobs = set()
    for s in students:
        dobs.update(d for _, d in block_keys(Candidate.of(s)))
    index = BlockIndex()
    pool = {}
    for s in db.scalars(select(Student).where(Student.year == year, Student.status == "active",
                                              Student.dob.in_(dobs))):
        pool[s.id] = s
        index.add(Candidate.of(s))

    new_ids = {s.id for s in students}
    existing_pairs = set()
    for a_id, b_id in db.execute(select(MatchCandidate.student_a_id, MatchCandidate.student_b_id).where(
            or_(MatchCandidate.student_a_id.in_(new_ids), MatchCandidate.student_b_id.in_(new_ids)))):
        existing_pairs.add(frozenset((a_id, b_id)))

    matches = flags = 0
    for s in students:
        me = Candidate.of(s)
        for other in index.candidates(me):
            if other.college_id == me.college_id or other.id == me.id or _exact_apaar_dup(me, other):
                continue
            pair = frozenset((me.id, other.id))
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)
            older, newer = sorted((pool[other.id], s), key=lambda x: (x.created_at, x.id))
            result = score_pair(Candidate.of(older), Candidate.of(newer))  # A is the older record
            band = band_for(result["score"])
            if band is None:
                continue
            match = MatchCandidate(student_a_id=older.id, student_b_id=newer.id, score=result["score"],
                                   band=band, components=result["components"],
                                   explanations=result["explanations"], status="pending")
            db.add(match)
            db.flush()
            matches += 1
            severity = "high" if band == "probable" else "medium"
            label = "Probable duplicate" if band == "probable" else "Possible duplicate (review)"
            flag = add_student_flag(
                db, newer, "PROBABLE_DUP",
                f"{label} of a student at another institution (score {result['score']:.2f})",
                evidence={"score": result["score"], "band": band, "counterpart_student_id": older.id,
                          "counterpart_college_id": older.college_id},
                severity=severity, match_id=match.id)
            flags += 1 if flag else 0
    return matches, flags
