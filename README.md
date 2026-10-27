# APAAR Verify (SIH 2026, PS SIH26263) – working demo

A platform where AICTE-approved institutions submit student data keyed on the APAAR ID, and where AICTE detects enrolment fraud and verifies records.

> **Synthetic demo data only. External registries (APAAR, DigiLocker, SMS) are simulated.** Policy values in `backend/app/policy.json` are illustrative. Nothing here is production-ready.

**Differentiators**

1. **Fuzzy identity resolution**: catches the same student at two institutions even when the APAAR ID is missing or different, with a field-by-field explanation.
2. **Explainable institution risk score**: 0 to 100 with the top three reasons in plain language.
3. **Signed credentials**: Ed25519 signatures; the QR code is verifiable offline in the browser; revocation is central.
4. **Tamper-evident audit chain plus consent**: hash-chained log whose Verify button visibly fails after tampering; verifiers see only consent-scoped fields.

## Run it

### Docker (production style, port 8000)

```bash
docker compose up --build
# open http://localhost:8000
```

The container seeds the database on first start. Data lives in the `apaar-data` volume.

### Local development

Requirements: Python 3.11+, Node 20+.

```bash
python3 -m venv .venv
make install     # pip install + npm ci
make seed        # reset the SQLite DB (data/app.db) and seed; regenerates backend/seed_data/*.csv
make dev         # backend on :8000 (reload) + Vite on :5173 (proxies /api)
make test        # pytest (83 tests)
make build       # production frontend build into frontend/dist (served by FastAPI on :8000)
```

API docs: http://localhost:8000/api/v1/docs

### Configuration (env vars)

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `true` | Enables demo accounts on the login page, OTP hint, reset/tamper endpoints |
| `JWT_SECRET` | insecure demo value (warning logged) | HS256 signing secret, 12-hour tokens |
| `DEMO_OTP` | `123456` | OTP for consent approval |
| `DATABASE_URL` | `sqlite:///<repo>/data/app.db` | SQLite file |
| `DATA_DIR` | `<repo>/data` | DB and `keys/` (Ed25519 keypair, generated on first start) |
| `ANTHROPIC_API_KEY` | unset | Reserved for the STRETCH natural-language query (not built) |

## Demo accounts (password `demo123`)

| Username | Role | Bound to |
|---|---|---|
| `inst_a` | Institution admin | Greenfield Institute of Technology (College 1) |
| `inst_b` | Institution admin | Lakeview College of Engineering (College 2) |
| `officer` | AICTE officer | All institutions |
| `student` | Student | Ananya Rao (College 1, APAAR 421900000101) |
| `verifier` | Verifier | Acme Hiring Pvt Ltd (demo) |

The login page has one-click chips for each account.

## Five-minute demo script

Before starting: `make seed` (or *Reset demo data* on the audit page), and use a fresh browser profile.

| # | Who | Do | Expect |
|---|---|---|---|
| 1 | `inst_a` | Upload students → drop `backend/seed_data/c1_clean.csv` → Run server dry-run → Confirm | Pre-check 0 problems; dry-run 40 OK; 40 saved, 0 new flags |
| 2 | `inst_a` | Upload `c1_with_issues.csv` | Pre-check lists the malformed APAAR and the bad DOB with hints; dry-run 36 OK, 3 warnings, 1 error; commit saves 39, skips 1, shows new flags and 2 probable duplicates |
| 3 | `officer` | Dashboard | KPIs updated; Riverstone (C3) and Lakeview (C2) lead the over-intake chart; C3 is high risk |
| 4 | `officer` | Duplicate review → Muhammad Aslam | Score 0.99, spelling variant and identical DOB explained, both institutions visible; **Confirm duplicate** → linked flag confirmed |
| 5 | `officer` | Risk scores → expand Riverstone | Score ≥ 65 with five component bars and three reasons |
| 6 | `student` | My wallet | QR credential card, status *Valid* |
| 7 | `verifier` | Look up `421900000101` → Request detailed verification (Name, Programme + purpose) | Request shows *Requested* |
| 8 | `student` | Approve with OTP `123456` | Approved; appears under active grants |
| 9 | `verifier` | View result | Only name and programme; no DOB |
| 10 | public | *Open verification page* from the wallet, disconnect the network, click **Verify signature** | Signature valid (browser-only check with cached key) |
| 11 | public | Change one character of the token, verify | Signature invalid |
| 12 | public | `/verify` → *Dev Malhotra (revoked)* demo token → Verify → Check revocation | Signature valid, status revoked: “Withdrawn from programme” |
| 13 | `officer` | Audit chain → Verify chain | Green: chain intact, N entries |
| 14 | `officer` | Tamper entry (demo) → Verify chain | Red: broken at the tampered entry |
| 15 | `officer` | Reset demo data | Verify chain is intact again |

`backend/tests/test_api_flow.py` runs the same script against the API.

## Repository layout

```
backend/app/
  main.py            app factory, /api/v1 routers, SPA static serving
  config.py          env settings + policy.json
  models.py          SQLAlchemy models        schemas.py   Pydantic I/O
  security.py        PBKDF2 hashing, JWT, role dependencies
  services/          ingest, validation (+flags), normalise, matching, ledger, risk,
                     credentials, consent, audit (hash chain), reports, adapters (mocks)
  routes/            thin HTTP layer, one module per area
  seed.py            deterministic seed with planted fraud cases; asserts flag counts
backend/seed_data/   sample upload CSVs (generated by the seeder, committed)
backend/tests/       pytest suite
frontend/src/        React + Vite + Tailwind: api/, auth/, components/, pages/
docs/DECISIONS.md    how ambiguities in PRD.md were resolved
```

## Seed data and planted cases

20 synthetic colleges (`SYN-0001` to `SYN-0020`), about 5,200 students. Planted cases P1 to P15 (PRD 10.3) produce exactly: 2 cross-college duplicates, 4 same-college duplicates, 2 probable duplicates (one high, one review band), 3 intake breaches, 1 supernumerary breach, 4 unapproved programme, 1 category inconsistency, 10 malformed APAAR, 2 missing APAAR and 2 implausible DOB flags. Riverstone (C3) scores high risk, Lakeview (C2) medium, all others low. The seeder fails loudly if any count drifts.

## Not built

The STRETCH natural-language officer query (PRD section 15, `/aicte/ask`, `POST /nlq`) is not implemented in this build.
