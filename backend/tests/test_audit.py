def test_chain_intact_after_seed(client, auth):
    r = client.get("/api/v1/audit/verify", headers=auth("officer")).json()
    assert r["intact"] is True and r["entries_checked"] >= 4 and r["first_broken_id"] is None
    actions = [a["action"] for a in client.get("/api/v1/audit", headers=auth("officer")).json()["items"]]
    assert "SEED" in actions and "CREDENTIAL_REVOKE" in actions


def test_tamper_then_reset(client, auth, restore_seed):
    officer = auth("officer")
    # Add a few entries so there is a middle to tamper with.
    flags = client.get("/api/v1/flags?status=open", headers=officer).json()["items"][:3]
    for f in flags:
        client.patch(f"/api/v1/flags/{f['id']}", json={"status": "confirmed"}, headers=officer)
    total = client.get("/api/v1/audit/verify", headers=officer).json()["entries_checked"]

    r = client.post("/api/v1/admin/demo/tamper-audit", json={"entry_id": 3}, headers=officer)
    assert r.json() == {"entry_id": 3}
    v = client.get("/api/v1/audit/verify", headers=officer).json()
    assert v == {"intact": False, "entries_checked": 3, "first_broken_id": 3}

    r = client.post("/api/v1/admin/demo/tamper-audit", headers=officer)
    assert 2 <= r.json()["entry_id"] < total

    assert client.post("/api/v1/admin/demo/reset", headers=auth("inst_a")).status_code == 403
    r = client.post("/api/v1/admin/demo/reset", headers=officer)
    assert r.status_code == 200
    v = client.get("/api/v1/audit/verify", headers=officer).json()
    assert v["intact"] is True
    last = client.get("/api/v1/audit?page_size=1", headers=officer).json()["items"][0]
    assert last["action"] == "DEMO_RESET"


def test_audit_requires_officer(client, auth):
    assert client.get("/api/v1/audit", headers=auth("inst_a")).status_code == 403
    assert client.get("/api/v1/audit/verify", headers=auth("verifier")).status_code == 403
