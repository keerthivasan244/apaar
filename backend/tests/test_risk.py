import re


def _risk(client, auth):
    return {r["college_id"]: r for r in client.get("/api/v1/risk/colleges", headers=auth("officer")).json()}


def test_bands(client, auth):
    risk = _risk(client, auth)
    assert risk[3]["band"] == "high" and risk[3]["score"] >= 65
    assert risk[2]["band"] == "medium" and 30 <= risk[2]["score"] <= 60
    assert risk[1]["band"] == "low" and risk[1]["score"] < 30
    assert all(r["band"] == "low" for cid, r in risk.items() if cid not in (2, 3))


def test_sorted_and_components(client, auth):
    rows = client.get("/api/v1/risk/colleges", headers=auth("officer")).json()
    assert [r["score"] for r in rows] == sorted((r["score"] for r in rows), reverse=True)
    c3 = rows[0]
    assert set(c3["components"]) == {"over_intake", "duplicates", "data_quality", "flag_ageing", "anomaly"}
    assert round(sum(c["contribution"] for c in c3["components"].values())) == c3["score"]


def test_reasons_are_short_and_numeric(client, auth):
    for r in _risk(client, auth).values():
        assert len(r["reasons"]) <= 3
        for reason in r["reasons"]:
            assert re.search(r"\d", reason)
    c3 = _risk(client, auth)[3]
    assert c3["reasons"][0] == "Admitted 317 against 300 approved seats (excess 27, 9.0%)"
    assert "CSE intake +14" in _risk(client, auth)[2]["reasons"][0]


def test_risk_scoping(client, auth):
    assert client.get("/api/v1/risk/colleges/1", headers=auth("inst_a")).status_code == 200
    assert client.get("/api/v1/risk/colleges/3", headers=auth("inst_a")).status_code == 403
    assert client.get("/api/v1/risk/colleges", headers=auth("inst_a")).status_code == 403
    assert "disclaimer" in client.get("/api/v1/risk/colleges/1", headers=auth("inst_a")).json()


def test_overview_and_reports(client, auth):
    ov = client.get("/api/v1/analytics/overview", headers=auth("officer")).json()
    assert ov["totals"]["colleges"] == 20 and ov["totals"]["high_risk_colleges"] == 1
    assert ov["totals"]["pending_matches"] == 2
    assert [x["college_id"] for x in ov["top_over_intake"][:2]] == [3, 2]
    assert ov["top_risk"][0]["college_id"] == 3
    colleges = client.get("/api/v1/colleges", headers=auth("officer")).json()
    assert colleges[2]["risk_band"] == "high" and colleges[2]["open_flags"] > 0
    ca = client.get("/api/v1/analytics/colleges/2", headers=auth("inst_b")).json()
    assert ca["totals"]["programmes_over_intake"] == 1

    r = client.get("/api/v1/reports/compliance?format=csv", headers=auth("officer"))
    assert r.status_code == 200 and "risk_score" in r.text.splitlines()[0]
    assert len(r.text.strip().splitlines()) == 21
    r = client.get("/api/v1/reports/compliance?format=xlsx", headers=auth("officer"))
    assert r.content[:2] == b"PK"
    r = client.get("/api/v1/reports/roster?college_id=2&format=csv", headers=auth("inst_a"))
    assert r.status_code == 200 and "GIT26-" in r.text  # scoped to own college regardless of the parameter
    assert "XXXXXXXX" in r.text
    assert client.get("/api/v1/reports/compliance", headers=auth("inst_a")).status_code == 403


def test_formula_injection_escaped():
    from app.services.reports import safe_cell

    assert safe_cell("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert safe_cell("@x") == "'@x" and safe_cell("normal") == "normal" and safe_cell(5) == 5
