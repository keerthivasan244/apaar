from sqlalchemy import func, select

from app.models import College, Flag, MatchCandidate, Student
from app.seed import EXPECTED_FLAG_COUNTS, flag_counts


def test_exact_open_flag_counts(db):
    assert flag_counts(db) == EXPECTED_FLAG_COUNTS


def test_probable_dup_bands(db):
    severities = sorted(db.scalars(select(Flag.severity).where(Flag.code == "PROBABLE_DUP")))
    assert severities == ["high", "medium"]
    bands = {m.band: m for m in db.scalars(select(MatchCandidate))}
    assert set(bands) == {"probable", "review"}
    assert {bands["probable"].student_a.name, bands["probable"].student_b.name} == {"Sneha Kulkarni", "Snehaa Kulkarni"}
    assert 0.75 <= bands["review"].score < 0.90
    assert bands["review"].student_a.college_id == 3 and bands["review"].student_b.college_id == 4


def test_planted_records(db):
    assert db.scalar(select(func.count()).where(Student.apaar_id == "421900000011")) == 2
    ananya = db.scalar(select(Student).where(Student.apaar_id == "421900000101"))
    assert ananya.name == "Ananya Rao" and ananya.college_id == 1
    c1_flags = db.scalar(select(func.count()).where(Flag.college_id == 1))
    assert c1_flags == 0  # P1: clean college


def test_flag_ages(db):
    from app.models import utcnow

    now = utcnow()
    for f in db.scalars(select(Flag)):
        age = (now - f.created_at).days
        assert (20 <= age <= 35) if f.college_id == 3 else (1 <= age <= 10)


def test_prev_year_enrolment(db):
    for cid, ratio in ((1, 1.0), (2, 0.83), (3, 0.71), (4, 1.0), (7, 1.0)):
        college = db.get(College, cid)
        active = db.scalar(select(func.count()).where(Student.college_id == cid, Student.status == "active"))
        assert college.prev_year_enrolment == round(active * ratio)
