import pytest

USERS = {
    "inst_a": "institution_admin",
    "inst_b": "institution_admin",
    "officer": "aicte_officer",
    "student": "student",
    "verifier": "verifier",
}


def test_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


@pytest.mark.parametrize("username,role", USERS.items())
def test_login_all_demo_users(client, username, role):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": "demo123"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == role
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["username"] == username


def test_bad_password(client):
    r = client.post("/api/v1/auth/login", json={"username": "officer", "password": "nope"})
    assert r.status_code == 401
    assert "detail" in r.json()


def test_unauthenticated_is_401(client):
    assert client.get("/api/v1/colleges").status_code == 401
    assert client.get("/api/v1/colleges", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_role_guards(client, auth):
    assert client.get("/api/v1/colleges", headers=auth("officer")).status_code == 200
    for user in ("inst_a", "student", "verifier"):
        assert client.get("/api/v1/colleges", headers=auth(user)).status_code == 403
    # institution admins only see their own college
    assert client.get("/api/v1/colleges/1", headers=auth("inst_a")).status_code == 200
    assert client.get("/api/v1/colleges/2", headers=auth("inst_a")).status_code == 403
    assert client.get("/api/v1/colleges/2", headers=auth("inst_b")).status_code == 200
