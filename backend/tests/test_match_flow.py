import io

ROW = {
    "student_id": "", "apaar_id": "", "name": "", "father_name": "", "dob": "", "gender": "M", "phone": "",
    "programme": "B.Tech Mechanical Engineering", "level": "UG", "shift": "Day",
    "admission_category": "Regular", "social_category": "General", "year": "2026",
}


def upload(client, headers, rows):
    cols = list(ROW)
    text = ",".join(cols) + "\n" + "\n".join(",".join({**ROW, **r}[c] for c in cols) for r in rows) + "\n"
    r = client.post("/api/v1/students/bulk?dry_run=false", files={"file": ("m.csv", io.BytesIO(text.encode()))},
                    headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_cross_college_fuzzy_match_review(client, auth, restore_seed):
    upload(client, auth("inst_b"), [{"student_id": "LV-X1", "apaar_id": "421955550001", "name": "Imran Qureshi",
                                    "father_name": "Salim Qureshi", "dob": "2005-08-21"}])
    out = upload(client, auth("inst_a"), [{"student_id": "GF-X1", "name": "Imraan Qureshi",
                                          "father_name": "Saleem Qureshi", "dob": "2005-08-21"}])
    assert out["new_matches"] == 1

    # Institution sees its flag but never the other college.
    flags = client.get("/api/v1/flags?code=PROBABLE_DUP", headers=auth("inst_a")).json()["items"]
    mine = [f for f in flags if f["student"]["student_code"] == "GF-X1"]
    assert len(mine) == 1 and mine[0]["counterpart"] == "another institution"
    assert "Lakeview" not in str(mine[0]) and mine[0]["match_id"] is None
    assert client.get("/api/v1/matches", headers=auth("inst_a")).status_code == 403

    matches = client.get("/api/v1/matches?status=pending", headers=auth("officer")).json()["items"]
    m = next(x for x in matches if x["student_b"]["student_code"] == "GF-X1")
    detail = client.get(f"/api/v1/matches/{m['id']}", headers=auth("officer")).json()
    assert detail["student_a"]["college_name"].startswith("Lakeview")
    assert set(detail["components"]) == {"name", "father_name", "dob", "gender", "phone"}

    r = client.patch(f"/api/v1/matches/{m['id']}", json={"status": "confirmed", "note": "same person"},
                     headers=auth("officer"))
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    flag = client.get(f"/api/v1/flags?code=PROBABLE_DUP&college_id=1", headers=auth("officer")).json()["items"]
    assert [f["status"] for f in flag if f["match_id"] == m["id"]] == ["confirmed"]


def test_institution_cannot_dismiss(client, auth, restore_seed):
    upload(client, auth("inst_a"), [{"student_id": "GF-Y1", "name": "Some One", "father_name": "Some Parent",
                                    "dob": "2005-08-22"}])
    flag = client.get("/api/v1/flags?code=MISSING_APAAR", headers=auth("inst_a")).json()["items"][0]
    assert client.patch(f"/api/v1/flags/{flag['id']}", json={"status": "dismissed"},
                        headers=auth("inst_a")).status_code == 403
    assert client.patch(f"/api/v1/flags/{flag['id']}", json={"status": "confirmed"},
                        headers=auth("inst_b")).status_code == 403
    assert client.patch(f"/api/v1/flags/{flag['id']}", json={"status": "confirmed"},
                        headers=auth("inst_a")).status_code == 200
