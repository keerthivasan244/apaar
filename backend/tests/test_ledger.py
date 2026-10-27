def _prog(client, auth, college_id, name_part):
    ledger = client.get(f"/api/v1/colleges/{college_id}/programmes", headers=auth("officer")).json()
    return next(p for p in ledger if name_part in p["name"])


def test_p2_over_intake(client, auth):
    cse = _prog(client, auth, 2, "Computer Science")
    assert (cse["approved_intake"], cse["admitted"], cse["over_by"]) == (120, 134, 14)


def test_p3_supernumerary(client, auth):
    ece = _prog(client, auth, 2, "Electronics")
    assert ece["admitted"] == 50 and ece["over_by"] == 0
    assert ece["supernumerary"]["TFW"] == {"count": 5, "cap": 3, "over_by": 2}
    assert ece["supernumerary"]["NRI"]["cap"] == 9  # ceil(15% of 60)


def test_p14_and_p1(client, auth):
    assert _prog(client, auth, 3, "Computer Science")["admitted"] == 138
    assert _prog(client, auth, 3, "Mechanical")["over_by"] == 9
    assert _prog(client, auth, 3, "Civil")["over_by"] == 0
    assert _prog(client, auth, 1, "Computer Science")["admitted"] == 100
    assert _prog(client, auth, 1, "Electronics")["admitted"] == 70


def test_ledger_scoping(client, auth):
    assert client.get("/api/v1/colleges/2/programmes", headers=auth("inst_a")).status_code == 403
