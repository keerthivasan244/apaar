from datetime import date

from app.services.matching import Candidate, band_for, name_similarity, score_pair
from app.services.normalise import hash_phone, normalise_name


def cand(name, father, dob, gender="M", phone=None, college=1):
    ph, last4 = hash_phone(phone)
    return Candidate(None, college, name, normalise_name(name), father, normalise_name(father), dob, gender,
                     ph, last4)


def test_mohammed_muhammad_probable():
    r = score_pair(cand("Mohammed Aslam", "Abdul Rahman", date(2005, 3, 14)),
                   cand("Muhammad Aslam", "Abdul Rehman", date(2005, 3, 14), college=2))
    assert r["score"] >= 0.90 and band_for(r["score"]) == "probable"
    assert any("spelling variants" in e for e in r["explanations"])
    assert "Date of birth identical" in r["explanations"]


def test_dob_swap_probable():
    r = score_pair(cand("Rohit Sharma", "Suresh Sharma", date(2004, 2, 11)),
                   cand("Rohit Sharma", "Suresh Sharma", date(2004, 11, 2)))
    assert r["score"] >= 0.90
    assert r["components"]["dob"]["similarity"] == 0.7
    assert "Date of birth matches with day and month swapped" in r["explanations"]


def test_unrelated_same_dob_below_review():
    r = score_pair(cand("Rahul Verma", "Sanjay Verma", date(2005, 4, 9)),
                   cand("Arjun Nair", "Krishnan Nair", date(2005, 4, 9)))
    assert r["score"] < 0.75 and band_for(r["score"]) is None


def test_missing_phone_renormalises():
    with_phone = score_pair(cand("Asha Rao", "Ravi Rao", date(2005, 1, 20), "F", "9876543210"),
                            cand("Asha Rao", "Ravi Rao", date(2005, 1, 20), "F", "9876543210"))
    without = score_pair(cand("Asha Rao", "Ravi Rao", date(2005, 1, 20), "F"),
                         cand("Asha Rao", "Ravi Rao", date(2005, 1, 20), "F", "9876543210"))
    assert with_phone["score"] == 1.0 and without["score"] == 1.0
    comps = without["components"]
    assert comps["phone"]["excluded"] and comps["phone"]["weight"] == 0
    assert abs(sum(c["weight"] for c in comps.values()) - 1.0) < 1e-3
    assert abs(comps["name"]["weight"] - 0.40 / 0.90) < 1e-3


def test_differing_phone_lowers_score():
    r = score_pair(cand("Karan Mehta", "Rajesh Mehta", date(2005, 4, 9), phone="9811111111"),
                   cand("Karan Mehata", "Rajesh Mehta", date(2005, 9, 4), phone="9822222222"))
    assert 0.75 <= r["score"] < 0.90 and band_for(r["score"]) == "review"


def test_initial_awareness():
    assert name_similarity("prakash r kulkarni", "prakash ramesh kulkarni") == 1.0
