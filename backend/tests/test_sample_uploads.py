from pathlib import Path

SEED_DATA = Path(__file__).resolve().parents[1] / "seed_data"


def _post(client, auth, name, dry_run):
    content = (SEED_DATA / name).read_bytes()
    r = client.post(f"/api/v1/students/bulk?dry_run={str(dry_run).lower()}", files={"file": (name, content)},
                    headers=auth("inst_a"))
    assert r.status_code == 200, r.text
    return r.json()


def test_sample_files_flow(client, auth, restore_seed):
    dry = _post(client, auth, "c1_clean.csv", True)
    assert dry["summary"] == {"total": 40, "ok": 40, "warnings": 0, "errors": 0}
    out = _post(client, auth, "c1_clean.csv", False)
    assert out["rows_saved"] == 40 and out["new_flags"] == 0 and out["new_matches"] == 0

    dry = _post(client, auth, "c1_with_issues.csv", True)
    assert dry["summary"] == {"total": 40, "ok": 36, "warnings": 3, "errors": 1}
    warn_codes = sorted(i["code"] for r in dry["rows"] if r["status"] == "warning" for i in r["issues"])
    assert warn_codes == ["DUP_CROSS_COLLEGE", "INVALID_APAAR_FORMAT", "MISSING_APAAR"]
    assert "Lakeview" not in str(dry)
    error = next(r for r in dry["rows"] if r["status"] == "error")
    assert error["issues"][0]["code"] == "INVALID_DOB_FORMAT"

    out = _post(client, auth, "c1_with_issues.csv", False)
    assert out["rows_saved"] == 39 and out["rows_skipped"] == 1
    assert out["new_matches"] >= 2

    matches = client.get("/api/v1/matches?status=pending", headers=auth("officer")).json()["items"]
    by_name = {m["student_b"]["name"]: m for m in matches}
    assert by_name["Muhammad Aslam"]["score"] >= 0.90 and by_name["Muhammad Aslam"]["band"] == "probable"
    assert by_name["Rohit Sharma"]["score"] >= 0.90
    cross = client.get("/api/v1/flags?code=DUP_CROSS_COLLEGE", headers=auth("officer")).json()
    assert cross["total"] == 4  # 2 seeded + the new pair (both records)
