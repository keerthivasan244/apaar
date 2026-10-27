"""Deterministic demo seed (PRD section 10). Run with `python -m app.seed`."""
import random

from sqlalchemy.orm import Session

from .models import College, Programme, User
from .security import hash_password

COLLEGES = [
    ("Greenfield Institute of Technology", "Pune", "Maharashtra"),
    ("Lakeview College of Engineering", "Chennai", "Tamil Nadu"),
    ("Riverstone Technical Campus", "Jaipur", "Rajasthan"),
    ("Summit Polytechnic", "Bhopal", "Madhya Pradesh"),
    ("Coastal Institute of Engineering", "Visakhapatnam", "Andhra Pradesh"),
    ("Himalaya School of Technology", "Dehradun", "Uttarakhand"),
    ("Deccan College of Engineering", "Hyderabad", "Telangana"),
    ("Sundarbans Institute of Technology", "Kolkata", "West Bengal"),
    ("Narmada Engineering College", "Indore", "Madhya Pradesh"),
    ("Malabar Institute of Technology", "Kochi", "Kerala"),
    ("Thar Polytechnic", "Jodhpur", "Rajasthan"),
    ("Western Ghats College of Engineering", "Kolhapur", "Maharashtra"),
    ("Brahmaputra Technical Institute", "Guwahati", "Assam"),
    ("Kaveri Institute of Technology", "Mysuru", "Karnataka"),
    ("Satpura Engineering College", "Nagpur", "Maharashtra"),
    ("Konkan Polytechnic", "Mangaluru", "Karnataka"),
    ("Ganga Plains Institute", "Lucknow", "Uttar Pradesh"),
    ("Vindhya School of Engineering", "Raipur", "Chhattisgarh"),
    ("Eastern Hills College of Technology", "Bhubaneswar", "Odisha"),
    ("Punjab Valley Institute of Engineering", "Ludhiana", "Punjab"),
]

CSE = "B.Tech Computer Science and Engineering"
ECE = "B.Tech Electronics and Communication Engineering"
ME = "B.Tech Mechanical Engineering"
CE = "B.Tech Civil Engineering"
MTECH = "M.Tech Computer Science"
DME = "Diploma in Mechanical Engineering"
DCE = "Diploma in Civil Engineering"
DCO = "Diploma in Computer Engineering"
ENGG_PROGRAMMES = [CSE, ECE, ME, CE, MTECH]
POLY_PROGRAMMES = [DME, DCE, DCO]

# (name, approved_intake) for the planted colleges; others are drawn randomly.
FIXED_PROGRAMMES = {
    1: [(CSE, 180), (ECE, 120), (ME, 60)],
    2: [(CSE, 120), (ECE, 60), (ME, 90)],
    3: [(CSE, 120), (ME, 90), (CE, 90)],
    4: [(DME, 120), (DCE, 60), (DCO, 60)],
}

DEMO_PASSWORD = "demo123"


def level_for(programme: str) -> str:
    if programme.startswith("M.Tech"):
        return "PG"
    if programme.startswith("Diploma"):
        return "DIPLOMA"
    return "UG"


def seed_institutions(db: Session, rng: random.Random) -> list[College]:
    colleges = []
    for idx, (name, city, state) in enumerate(COLLEGES, start=1):
        ctype = "Polytechnic" if "Polytechnic" in name else "Engineering"
        college = College(aicte_id=f"SYN-{idx:04d}", name=name, city=city, state=state, type=ctype)
        if idx in FIXED_PROGRAMMES:
            progs = FIXED_PROGRAMMES[idx]
        elif ctype == "Polytechnic":
            progs = [(p, rng.choice([60, 90, 120])) for p in POLY_PROGRAMMES]
        else:
            count = rng.choice([3, 3, 3, 4, 5])
            names = [CSE] + rng.sample(ENGG_PROGRAMMES[1:], count - 1)
            progs = [(p, rng.choice([60, 60, 90, 90, 120, 180])) for p in names]
        college.programmes = [
            Programme(name=p, level=level_for(p), shift="Day", approved_intake=intake) for p, intake in progs
        ]
        db.add(college)
        colleges.append(college)
    db.flush()
    return colleges


def seed_users(db: Session, colleges: list[College], student_id: int | None = None) -> None:
    pw = hash_password(DEMO_PASSWORD)  # one hash reused: demo accounts share a password
    db.add_all([
        User(username="inst_a", password_hash=pw, role="institution_admin",
             display_name="Greenfield Admin", college_id=colleges[0].id),
        User(username="inst_b", password_hash=pw, role="institution_admin",
             display_name="Lakeview Admin", college_id=colleges[1].id),
        User(username="officer", password_hash=pw, role="aicte_officer", display_name="AICTE Officer"),
        User(username="student", password_hash=pw, role="student", display_name="Ananya Rao",
             college_id=colleges[0].id, student_id=student_id),
        User(username="verifier", password_hash=pw, role="verifier", display_name="Acme Verifier",
             organisation="Acme Hiring Pvt Ltd (demo)"),
    ])


def seed(db: Session) -> dict:
    rng = random.Random(2026)
    colleges = seed_institutions(db, rng)
    seed_users(db, colleges)
    db.commit()
    return {"colleges": len(colleges)}


def reset_and_seed() -> dict:
    from .db import SessionLocal, create_all, drop_all

    drop_all()
    create_all()
    with SessionLocal() as db:
        return seed(db)


if __name__ == "__main__":
    print(reset_and_seed())
