"""Deterministic demo seed (PRD section 10). Run with `python -m app.seed`.

Students are inserted through the same validation, flagging and matching services as uploads, so
flags and matches arise naturally. The seed asserts the exact flag counts from PRD 10.3.
"""
import csv
import random
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_policy
from .models import College, Flag, Programme, Student, User, utcnow
from .security import hash_password
from .services import validation
from .services.audit import record
from .services.ingest import COLUMNS
from .services.matching import BlockIndex, Candidate
from .services.normalise import hash_phone, normalise_name

SEED_DATA_DIR = Path(__file__).resolve().parents[1] / "seed_data"

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
            progs = [(p, rng.choice([60, 60, 90])) for p in POLY_PROGRAMMES]
        else:
            count = rng.choice([3, 3, 3, 3, 4, 5])
            names = [CSE] + rng.sample(ENGG_PROGRAMMES[1:], count - 1)
            progs = [(p, rng.choice([60, 60, 60, 90, 120] if p == CSE else [60, 60, 60, 90])) for p in names]
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



EXPECTED_FLAG_COUNTS = {
    "DUP_CROSS_COLLEGE": 2, "DUP_SAME_COLLEGE": 4, "PROBABLE_DUP": 2, "INTAKE_EXCEEDED": 3,
    "SUPERNUMERARY_EXCEEDED": 1, "UNAPPROVED_PROGRAMME": 4, "CATEGORY_INCONSISTENT": 1,
    "INVALID_APAAR_FORMAT": 10, "MISSING_APAAR": 2, "DOB_IMPLAUSIBLE": 2,
}

# Exact admission-category counts (including planted rows) for the planted programmes.
FIXED_PLANS = {
    (1, CSE): {"Regular": 90, "EWS": 7, "Sports": 3},           # admitted 100 of 180
    (1, ECE): {"Regular": 63, "EWS": 5, "Sports": 2},           # admitted 70 of 120
    (2, CSE): {"Regular": 130, "Sports": 4},                    # P2: 134 of 120
    (2, ECE): {"Regular": 50, "TFW": 5},                        # P3: TFW cap 3
    (3, CSE): {"Regular": 125, "EWS": 10, "Sports": 3},         # P14: 138 of 120
    (3, ME): {"Regular": 90, "EWS": 7, "Sports": 2},            # P14: 99 of 90
    (3, CE): {"Regular": 72, "EWS": 6, "Sports": 2},            # P14: 80 of 90
}
PREV_YEAR_RATIO = {2: 0.83, 3: 0.71}  # everyone else: equal to current enrolment
ROBOTICS = "B.Tech Robotics and AI"
INVALID_APAARS = ["12345", "ABCD12345678", "4219 0000 0031", "42190000003", "4219000000321",
                  "4219-0000-0033", "42190000003X", "APAAR0000034", "4219O0000036", "421900000037 8"]


class Generator:
    """Synthetic people with deterministic randomness and collision-free fuzzy identities."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        Faker.seed(2026)
        self.fake = Faker("en_IN")
        self.fake.seed_instance(2026)
        self.index = BlockIndex()
        self.threshold = get_policy()["match_thresholds"]["review"]
        self._apaar_pool = iter(rng.sample(range(10_000_000, 99_999_999), 9000))
        self._phones: set[str] = set()

    def apaar(self) -> str:
        return f"4219{next(self._apaar_pool):08d}"

    def phone(self) -> str:
        while True:
            p = self.rng.choice("6789") + "".join(self.rng.choice("0123456789") for _ in range(9))
            if p not in self._phones:
                self._phones.add(p)
                return p

    def dob(self, level: str) -> date:
        start, end = {"UG": (date(2005, 1, 1), date(2008, 6, 30)), "PG": (date(1998, 1, 1), date(2003, 6, 30)),
                      "DIPLOMA": (date(2007, 7, 1), date(2010, 12, 31))}[level]
        return start + timedelta(days=self.rng.randrange((end - start).days))

    def register(self, row: dict, college_id: int) -> None:
        self.index.add(self._candidate(row, college_id))

    def _candidate(self, row: dict, college_id: int) -> Candidate:
        ph, last4 = hash_phone(row.get("phone"))
        return Candidate(None, college_id, row["name"], normalise_name(row["name"]), row["father_name"],
                         normalise_name(row["father_name"]), date.fromisoformat(row["dob"]), row["gender"], ph,
                         last4, row.get("apaar_id") or None)

    def person(self, college_id: int, level: str) -> dict:
        """A normal student who does not resemble anyone already generated (score < review threshold)."""
        for _ in range(100):
            gender = self.rng.choice("MF")
            first = self.fake.first_name_male() if gender == "M" else self.fake.first_name_female()
            last = self.fake.last_name()
            row = {"name": f"{first} {last}", "father_name": f"{self.fake.first_name_male()} {last}",
                   "gender": gender, "dob": self.dob(level).isoformat(), "phone": self.phone(),
                   "apaar_id": self.apaar()}
            cand = self._candidate(row, college_id)
            if self.index.best_score(cand) < self.threshold:
                self.index.add(cand)
                return row
        raise RuntimeError("Could not draw a non-colliding synthetic identity")


def make_row(code: str, programme: str, level: str, category: str, person: dict, **overrides) -> dict:
    row = {"student_id": code, "apaar_id": person.get("apaar_id", ""), "name": person["name"],
           "father_name": person["father_name"], "dob": person["dob"], "gender": person["gender"],
           "phone": person.get("phone", ""), "programme": programme, "level": level, "shift": "Day",
           "admission_category": category, "social_category": "General", "year": str(get_policy()["academic_year"])}
    row.update(overrides)
    return row


def planted_rows(gen: Generator) -> dict[int, list[dict]]:
    """Rows for planted cases P1 to P13, keyed by college number. `student_id` is assigned later."""
    p = {}

    def add(cid, programme, person, category="Regular", **kw):
        gen.register(person, cid)
        p.setdefault(cid, []).append(make_row("", programme, level_for(programme), category, person, **kw))

    # P1 / P15: Greenfield
    add(1, CSE, {"name": "Ananya Rao", "father_name": "Venkatesh Rao", "dob": "2006-01-15", "gender": "F",
                 "apaar_id": "421900000101", "phone": gen.phone()}, social_category="General")
    add(1, ECE, {"name": "Dev Malhotra", "father_name": "Rajiv Malhotra", "dob": "2005-10-03", "gender": "M",
                 "apaar_id": gen.apaar(), "phone": gen.phone()})
    # P4: exact cross-college duplicate (C2 and C3)
    add(2, CSE, {"name": "Nikhil Joshi", "father_name": "Mahesh Joshi", "dob": "2005-07-19", "gender": "M",
                 "apaar_id": "421900000011", "phone": gen.phone()})
    add(3, CSE, {"name": "Vikram Chauhan", "father_name": "Ajay Chauhan", "dob": "2006-02-27", "gender": "M",
                 "apaar_id": "421900000011", "phone": gen.phone()})
    # P5: two same-college APAAR pairs at C3
    for apaar, prog_a, prog_b in (("421900000041", CSE, ME), ("421900000042", CE, CE)):
        add(3, prog_a, gen.person(3, "UG") | {"apaar_id": apaar})
        add(3, prog_b, gen.person(3, "UG") | {"apaar_id": apaar})
    # P6: fuzzy duplicate, high band (C2 vs C4)
    add(2, CSE, {"name": "Sneha Kulkarni", "father_name": "Prakash Kulkarni", "dob": "2005-06-01", "gender": "F",
                 "apaar_id": gen.apaar()})
    add(4, DME, {"name": "Snehaa Kulkarni", "father_name": "Prakash R Kulkarni", "dob": "2005-06-01",
                 "gender": "F", "apaar_id": ""})
    # P7: fuzzy duplicate, review band (C3 vs C4): swapped DOB, different phones
    add(3, ME, {"name": "Karan Mehta", "father_name": "Rajesh Mehta", "dob": "2005-04-09", "gender": "M",
                "apaar_id": gen.apaar(), "phone": gen.phone()})
    add(4, DME, {"name": "Karan Mehata", "father_name": "Rajesh Mehta", "dob": "2005-09-04", "gender": "M",
                 "apaar_id": "", "phone": gen.phone()})
    # P8 / P9: live fuzzy targets
    add(3, CSE, {"name": "Mohammed Aslam", "father_name": "Abdul Rahman", "dob": "2005-03-14", "gender": "M",
                 "apaar_id": "421900000021"})
    add(4, DCO, {"name": "Rohit Sharma", "father_name": "Suresh Sharma", "dob": "2004-02-11", "gender": "M",
                 "apaar_id": gen.apaar()})
    # P10: unapproved programme at C4
    for _ in range(4):
        add(4, ROBOTICS, gen.person(4, "UG"))
    # P11: FN admission with a social category
    add(4, DCO, gen.person(4, "DIPLOMA"), category="FN", social_category="OBC")
    # P12: malformed APAAR IDs at C3, spread over programmes
    for i, bad in enumerate(INVALID_APAARS):
        add(3, (CSE, ME, CE)[i % 3], gen.person(3, "UG") | {"apaar_id": bad})
    # P13: implausible DOBs at C3
    add(3, CE, gen.person(3, "UG") | {"dob": "1965-02-10"})
    add(3, CSE, gen.person(3, "UG") | {"dob": "2016-05-20"})
    return p


def random_plan(rng: random.Random, approved: int) -> dict[str, int]:
    """Normal programme: 80-97% of intake, all within caps."""
    policy = get_policy()
    admitted = round(approved * rng.uniform(0.80, 0.97))
    ews = round(admitted * rng.uniform(0.05, 0.10))
    sports = rng.randint(0, 3)
    plan = {"Regular": admitted - ews - sports, "EWS": ews, "Sports": sports}
    for cat in ("TFW", "PMSSS", "NRI"):
        if rng.random() < 0.4:
            cap = validation.ledger.cap_seats(policy["supernumerary_cap_pct"][cat], approved)
            plan[cat] = rng.randint(1, max(1, cap - 1))
    return plan


SOCIAL = (["General"] * 45) + (["OBC"] * 30) + (["SC"] * 15) + (["ST"] * 7) + (["EWS"] * 3)


def college_rows(gen: Generator, college: College, idx: int, planted: list[dict]) -> list[dict]:
    rng = gen.rng
    rows = list(planted)
    for prog in college.programmes:
        plan = FIXED_PLANS.get((idx, prog.name)) or random_plan(rng, prog.approved_intake)
        already = Counter(r["admission_category"] for r in planted if r["programme"] == prog.name)
        for cat, count in plan.items():
            for _ in range(max(0, count - already.get(cat, 0))):
                person = gen.person(college.id, prog.level)
                social = "NA" if cat in ("NRI", "OCI", "FN") else rng.choice(SOCIAL)
                rows.append(make_row("", prog.name, prog.level, cat, person, social_category=social))
    rng.shuffle(rows)
    prefix = "".join(w[0] for w in college.name.split() if w[0].isupper())
    for n, row in enumerate(rows, start=1):
        row["student_id"] = f"{prefix}26-{n:04d}"
    return rows


def backdate_flags(db: Session, rng: random.Random) -> None:
    now = utcnow()
    for flag in db.scalars(select(Flag).order_by(Flag.id)):
        days = rng.uniform(20, 35) if flag.college_id == 3 else rng.uniform(1, 10)
        flag.created_at = now - timedelta(days=days)


def flag_counts(db: Session) -> dict[str, int]:
    return dict(db.execute(select(Flag.code, func.count()).where(Flag.status == "open").group_by(Flag.code)).all())


def seed(db: Session, *, write_samples: bool = False) -> dict:
    started = time.perf_counter()
    random.seed(2026)
    rng = random.Random(2026)
    colleges = seed_institutions(db, rng)
    gen = Generator(rng)
    planted = planted_rows(gen)

    for idx, college in enumerate(colleges, start=1):
        ctx = validation.CollegeContext(db, college)
        results = validation.validate_rows(db, college_rows(gen, college, idx, planted.get(idx, [])), ctx)
        errors = [r for r in results if r.status == "error"]
        if errors:
            raise RuntimeError(f"Seed rows rejected for {college.name}: {errors[0].as_dict()}")
        students = validation.save_students(db, ctx, results, batch_id=None)
        validation.post_insert(db, ctx, students)

    for idx, college in enumerate(colleges, start=1):
        active = db.scalar(select(func.count()).where(Student.college_id == college.id, Student.status == "active"))
        college.prev_year_enrolment = round(active * PREV_YEAR_RATIO.get(idx, 1.0))
    backdate_flags(db, rng)

    ananya = db.scalar(select(Student).where(Student.apaar_id == "421900000101"))
    seed_users(db, colleges, student_id=ananya.id)
    db.flush()
    seed_credentials(db, ananya)

    counts = flag_counts(db)
    if counts != EXPECTED_FLAG_COUNTS:
        raise RuntimeError(f"Seed flag counts {counts} differ from expected {EXPECTED_FLAG_COUNTS}")
    total_students = db.scalar(select(func.count(Student.id)))
    record(db, actor="system", actor_role="system", action="SEED", entity_type="database", entity_id="all",
           payload={"colleges": len(colleges), "students": total_students, "flags": counts})
    db.commit()
    if write_samples:
        write_sample_csvs(db, gen)
    return {"colleges": len(colleges), "students": total_students, "flags": counts,
            "seconds": round(time.perf_counter() - started, 1)}


def seed_credentials(db: Session, ananya: Student) -> None:
    """Hook for Phase 6 (signed credentials)."""


# ------------------------------------------------------------------ sample upload files (PRD 10.4)

def _c1_people(gen: Generator, n: int) -> list[dict]:
    return [gen.person(1, "UG") for _ in range(n)]


def build_sample_rows(db: Session, gen: Generator) -> tuple[list[dict], list[dict]]:
    clean = []
    for i, person in enumerate(_c1_people(gen, 40)):
        prog = CSE if i < 25 else ECE
        clean.append(make_row(f"GIT26-1{i + 1:03d}", prog, "UG", "Regular", person,
                              social_category=gen.rng.choice(SOCIAL)))

    issues = []
    people = _c1_people(gen, 38)
    for i, person in enumerate(people[:35]):
        prog = CSE if i < 20 else ECE
        issues.append(make_row(f"GIT26-2{i + 1:03d}", prog, "UG", "Regular", person,
                               social_category=gen.rng.choice(SOCIAL)))
    bad_apaar, bad_dob, cross = people[35:38]
    issues.append(make_row("GIT26-2036", CSE, "UG", "Regular", bad_apaar | {"apaar_id": "4219 1234 567"}))
    issues.append(make_row("GIT26-2037", ECE, "UG", "Regular", bad_dob | {"dob": "31/02/2005"}))
    c2_apaar = db.scalar(select(Student.apaar_id).where(Student.college_id == 2, Student.programme_id.is_not(None),
                                                        Student.name != "Sneha Kulkarni",
                                                        Student.apaar_id != "421900000011")
                         .order_by(Student.id).limit(1))
    issues.append(make_row("GIT26-2038", ECE, "UG", "Regular", cross | {"apaar_id": c2_apaar}))
    issues.append(make_row("GIT26-2039", CSE, "UG", "Regular",
                           {"name": "Muhammad Aslam", "father_name": "Abdul Rehman", "dob": "2005-03-14",
                            "gender": "M", "apaar_id": "", "phone": ""}))
    issues.append(make_row("GIT26-2040", CSE, "UG", "Regular",
                           {"name": "Rohit Sharma", "father_name": "Suresh Sharma", "dob": "2004-11-02",
                            "gender": "M", "apaar_id": gen.apaar(), "phone": ""}))
    gen.rng.shuffle(issues)
    return clean, issues


def write_sample_csvs(db: Session, gen: Generator, out_dir: Path = SEED_DATA_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    clean, issues = build_sample_rows(db, gen)
    for name, rows in (("c1_clean.csv", clean), ("c1_with_issues.csv", issues)):
        with open(out_dir / name, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)


def reset_and_seed(*, write_samples: bool = False) -> dict:
    from .db import SessionLocal, create_all, drop_all

    drop_all()
    create_all()
    with SessionLocal() as db:
        return seed(db, write_samples=write_samples)


if __name__ == "__main__":
    print(reset_and_seed(write_samples=True))
