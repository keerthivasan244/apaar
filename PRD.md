# PRD: APAAR Verify (SIH 2026, PS SIH26263) – Working Demo

**Audience:** Claude Code (autonomous implementation) and the 4-person team reviewing its work.
**Status:** v1.0, 27 October 2026. Demo build, not production.

---

## 0. How to use this document (instructions for Claude Code)

1. Read this entire file before writing code. It is the source of truth. If something is ambiguous, choose the simplest option that satisfies the acceptance criteria, record the decision in `docs/DECISIONS.md`, and continue. Do not stop to ask unless something is blocking.
2. Build in the phases in section 13. After each phase: run the tests, run the app, fix failures, then `git commit` with a clear message.
3. Priority is a **reliable demo of the happy path** over breadth. Every feature in sections 6 to 11 marked MUST must work end to end. Features marked STRETCH come last.
4. Never use real personal data. All colleges, students and IDs are synthetic and must be labelled "Synthetic demo data" in the UI footer.
5. No external network calls are needed for the core demo. The only optional external call is the LLM in the STRETCH feature (section 15).
6. Keep dependencies to those listed in section 4. Pin versions in `requirements.txt` and `package.json`.
7. When finished, make sure `docker compose up` (or the documented commands) starts everything and the demo script in section 11 passes.

---

## 1. Product summary

**Problem (SIH26263, AICTE, Regulation Bureau, theme Smart Automation).** AICTE needs a platform where approved institutions submit student data keyed on the APAAR ID (the national academic registry ID), and where AICTE can detect enrolment fraud and verify records. Typical failures: the same student enrolled at two institutions, admissions above sanctioned intake or supernumerary limits, malformed or missing IDs, programmes the institution is not approved to run, and records that employers cannot verify without paperwork.

**Solution.** APAAR Verify: an institution portal (bulk upload with pre-check), a regulator console (dashboard, flag queue, fuzzy duplicate review, explainable risk scores, audit), a student wallet (signed credential QR, consent inbox), and a verifier portal plus a public offline verification page.

**Four differentiators (these are what must look polished):**
1. **Fuzzy identity resolution:** catches duplicate students even when the APAAR ID is missing or different, with a field-by-field explanation.
2. **Explainable institution risk score:** 0 to 100 with the top reasons in plain language.
3. **Properly signed credentials:** Ed25519 signatures; QR verifiable offline in the browser; central revocation.
4. **Tamper-evident audit chain plus consent:** hash-chained log with a Verify button that visibly fails after tampering; verifiers see only consent-scoped fields.

**Mocked by design:** the real APAAR registry, DigiLocker and AICTE systems are not accessible. Access to them goes through adapter interfaces (section 6.9) with mock implementations. The UI must say "Demo mode: external registries are simulated".

---

## 2. Goals, non-goals, success criteria

**Goals**
- A 5-minute demo (section 11) runs smoothly on a laptop with no internet.
- All planted fraud cases in the seed data are detected and explained.
- Code is clean enough for judges to open the repo and understand it.

**Non-goals**
- Real authentication providers, real SMS, real APAAR/DigiLocker integration.
- Multi-tenant scale, background job queues, Kubernetes, blockchain.
- Mobile app. The web UI must be responsive down to tablet width; phone is a bonus.

**Success criteria (all must pass)**
- `pytest` passes (section 12).
- The demo script in section 11 passes manually without errors in a fresh browser profile after `POST /admin/demo/reset`.
- Expected seed flag counts in section 10.3 match exactly.
- Tampering with an audit row makes `/audit/verify` fail; altering one character of a credential token makes signature verification fail.

---

## 3. Users and demo accounts

| Role | Purpose | Username | Password | Bound to |
|---|---|---|---|---|
| `institution_admin` | Uploads and manages own college data | `inst_a` | `demo123` | College 1 (Greenfield) |
| `institution_admin` | Second college for contrast | `inst_b` | `demo123` | College 2 (Lakeview) |
| `aicte_officer` | Regulator console | `officer` | `demo123` | All colleges |
| `student` | Wallet and consent inbox | `student` | `demo123` | Student "Ananya Rao" (College 1) |
| `verifier` | Employer or university verifying records | `verifier` | `demo123` | Organisation "Acme Hiring Pvt Ltd (demo)" |

Login uses `username` (plain string, not email). Demo OTP for consent approval is `123456` (config `DEMO_OTP`) and is shown as a hint in the UI when `DEMO_MODE=true`.

---

## 4. Tech stack (fixed)

**Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite (single file `data/app.db`), uvicorn, PyJWT, PyNaCl (Ed25519), rapidfuzz, pandas, openpyxl, python-multipart, Faker (`en_IN`), pytest, httpx. Password hashing: stdlib `hashlib.pbkdf2_hmac` (no bcrypt dependency).

**Frontend:** React 18, Vite, TypeScript, Tailwind CSS 3.4, React Router 6, TanStack Table v8, Recharts, react-dropzone, papaparse, tweetnacl, qrcode.react, lucide-react. Plain Tailwind components (no UI kit) to avoid setup friction. Use `fetch` (no axios).

**Delivery:** One Docker image. FastAPI serves the built frontend (`frontend/dist`) with SPA fallback; API under `/api/v1`. In dev, Vite proxies `/api` to `localhost:8000`.

**Constraints:** single uvicorn worker (SQLite); CORS open only in dev; JWT HS256, 12-hour expiry; secrets from env with safe demo defaults.

---

## 5. Repository structure and commands

```
apaar-verify/
├─ PRD.md
├─ CLAUDE.md                 # see Appendix A
├─ README.md                 # setup, demo accounts, demo script
├─ docs/DECISIONS.md
├─ docker-compose.yml
├─ Dockerfile
├─ Makefile                  # make dev, make test, make seed, make build
├─ data/                     # runtime: app.db, keys/ (gitignored)
├─ backend/
│  ├─ requirements.txt
│  ├─ app/
│  │  ├─ main.py             # app factory, static serving, router mounting
│  │  ├─ config.py           # env + policy.json loading
│  │  ├─ policy.json
│  │  ├─ db.py               # engine, session, Base
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  ├─ security.py         # password hashing, JWT, role deps
│  │  ├─ services/
│  │  │  ├─ ingest.py        # parse CSV/XLSX, normalise rows
│  │  │  ├─ validation.py    # row rules + flag generation
│  │  │  ├─ normalise.py     # name/phone normalisation
│  │  │  ├─ matching.py      # fuzzy identity resolution
│  │  │  ├─ ledger.py        # intake and supernumerary computation
│  │  │  ├─ risk.py
│  │  │  ├─ credentials.py   # Ed25519 sign/verify, key mgmt
│  │  │  ├─ consent.py
│  │  │  ├─ audit.py         # hash chain
│  │  │  ├─ reports.py
│  │  │  └─ adapters.py      # mock APAAR/DigiLocker/SMS
│  │  ├─ routes/             # auth, colleges, students, flags, matches,
│  │  │                      # analytics, risk, credentials, consents,
│  │  │                      # verify, audit, reports, admin_demo, nlq
│  │  └─ seed.py             # deterministic seed + CSV generator
│  ├─ seed_data/             # generated sample CSVs (committed)
│  └─ tests/
└─ frontend/
   ├─ package.json, vite.config.ts, tailwind.config.js, index.html
   └─ src/
      ├─ main.tsx, App.tsx, routes.tsx
      ├─ api/                # client.ts + typed endpoint wrappers
      ├─ auth/               # AuthContext, ProtectedRoute
      ├─ components/         # Layout, Sidebar, KpiTile, Badge, DataTable, ...
      └─ pages/              # per role, see section 9
```

**Commands (must exist):** `make dev` (backend on 8000 with reload and frontend on 5173), `make test`, `make seed` (reset DB and seed), `make build` (frontend build), `docker compose up` (production-style on port 8000).

---

## 6. Domain rules (MUST)

### 6.1 Policy configuration (`backend/app/policy.json`)

All numeric rules live here, not in code. **Values are illustrative placeholders and must be checked against the current AICTE Approval Process Handbook before being quoted publicly.** The UI footer on the compliance pages shows "Policy values illustrative".

```json
{
  "academic_year": 2026,
  "apaar_regex": "^\\d{12}$",
  "intake_categories": ["Regular", "EWS", "Sports"],
  "supernumerary_cap_pct": { "TFW": 5, "PMSSS": 5, "NRI": 15, "OCI": 15, "FN": 15 },
  "levels": ["UG", "PG", "DIPLOMA"],
  "shifts": ["Day", "Evening"],
  "genders": ["M", "F", "O"],
  "social_categories": ["General", "SC", "ST", "OBC", "EWS", "NA"],
  "age_range_on_1_july": { "UG": [16, 30], "PG": [20, 45], "DIPLOMA": [14, 30] },
  "match_thresholds": { "probable": 0.90, "review": 0.75 },
  "match_weights": { "name": 0.40, "father_name": 0.25, "dob": 0.20, "gender": 0.05, "phone": 0.10 },
  "risk_weights": { "over_intake": 35, "duplicates": 25, "data_quality": 15, "flag_ageing": 10, "anomaly": 15 },
  "risk_bands": { "low_max": 30, "medium_max": 60 },
  "consent_ttl_hours": 24
}
```

Supernumerary cap in seats for a programme and category = `ceil(cap_pct / 100 * approved_intake)`.

### 6.2 CSV/XLSX template

Header names are case-insensitive and trimmed. Provide the template at `GET /api/v1/templates/students.csv`.

| Column | Required | Notes |
|---|---|---|
| `student_id` | yes | Institution's own ID; unique within file and college |
| `apaar_id` | no | Stored as given; validated against regex |
| `name` | yes | |
| `father_name` | yes | |
| `dob` | yes | `YYYY-MM-DD`, or `DD/MM/YYYY` or `DD-MM-YYYY` (day first). Anything else is a row error |
| `gender` | yes | `M`, `F`, `O` |
| `phone` | no | Stored only as normalised hash plus last 4 digits |
| `programme` | yes | Free text; matched to the college's approved programmes (case and whitespace insensitive) |
| `level` | yes | `UG`, `PG`, `DIPLOMA` |
| `shift` | yes | `Day`, `Evening` |
| `admission_category` | yes | `Regular`, `EWS`, `Sports`, `TFW`, `PMSSS`, `NRI`, `OCI`, `FN` |
| `social_category` | yes | `General`, `SC`, `ST`, `OBC`, `EWS`, `NA` |
| `year` | yes | Must equal `academic_year` |

### 6.3 Validation: blocking errors versus saved flags

**Blocking row errors (row is not saved):** `MISSING_REQUIRED_FIELD`, `INVALID_DOB_FORMAT`, `INVALID_GENDER`, `INVALID_LEVEL`, `INVALID_SHIFT`, `INVALID_ADMISSION_CATEGORY`, `INVALID_SOCIAL_CATEGORY`, `YEAR_MISMATCH`, `DUP_STUDENT_ID_IN_FILE`.

**Flags (row is saved, flag created):**

| Code | Severity | Level | Trigger |
|---|---|---|---|
| `MISSING_APAAR` | medium | student | `apaar_id` blank |
| `INVALID_APAAR_FORMAT` | high | student | present but fails regex |
| `DUP_SAME_COLLEGE` | high | student | same valid APAAR on 2+ active records in the same college and year (flag every record) |
| `DUP_CROSS_COLLEGE` | critical | student | same valid APAAR active at 2+ different colleges in the same year (flag every record) |
| `PROBABLE_DUP` | high if score >= probable, medium if >= review | student | fuzzy match (6.5); links to a `match_candidates` row |
| `INTAKE_EXCEEDED` | high | programme | admitted (intake categories, active, current year) > approved_intake |
| `SUPERNUMERARY_EXCEEDED` | high | programme | count of a supernumerary category > cap seats |
| `UNAPPROVED_PROGRAMME` | high | student | programme text does not match any approved programme of the college (`programme_id` null, raw text kept) |
| `CATEGORY_INCONSISTENT` | medium | student | `admission_category == FN` and `social_category` not in (`NA`) |
| `DOB_IMPLAUSIBLE` | medium | student | age on 1 July of academic year outside the range for the level |

**Idempotency:** programme-level flags (`INTAKE_EXCEEDED`, `SUPERNUMERARY_EXCEEDED`) are recomputed after every commit and are unique per `(programme_id, code[, category])`; if the condition clears, the flag is removed (unless reviewed, in which case it is marked `resolved_auto`). Student-level flags are created once per `(student_id, code, counterpart)`.

**Flag status:** `open`, `confirmed` (officer agrees it is real), `dismissed` (false positive). Reviewing writes an audit entry.

### 6.4 Seat ledger

For each programme and the current academic year: `admitted` = active students whose `admission_category` is in `intake_categories`; `supernumerary[cat]` = active students in that category; `approved_intake` from the programme. Expose `over_by = max(0, admitted - approved_intake)` and per-category `{count, cap, over_by}`.

### 6.5 Fuzzy identity resolution (differentiator 1)

**When it runs:** after each committed upload (and during seeding) for every newly inserted student, against students at **other colleges** in the same year. Skip pairs that are already an exact valid-APAAR duplicate.

**Normalisation (`normalise.py`)**
- Names: lowercase; strip punctuation and extra spaces; remove honorifics (`mr mrs ms dr shri smt kumari sri`); map variants to canonical (`mohd md muhammad mohamed mohammad muhammed -> mohammed`; `kumar kumaar -> kumar`; `singh sing -> singh`; extendable dict in `normalise.py`); collapse repeated letters (`aa -> a`, `ee -> e`, `oo -> o`).
- Phone: digits only, last 10; store `phone_hash = sha256(salt + digits)` and `phone_last4`.

**Blocking:** candidate pairs share gender and either the same DOB or a day/month-swapped DOB (only when both day and month are 12 or below).

**Name similarity:** `max(JaroWinkler(a, b), token_sort_ratio(a, b)/100)` using rapidfuzz on normalised strings, with initial awareness: a single-letter token matches any token starting with that letter (treated as equal) before scoring.

**Pair score:** weighted sum over available components; components where either side is missing are excluded and the remaining weights renormalised.
- name (0.40): name similarity
- father_name (0.25): same similarity function
- dob (0.20): 1.0 exact, 0.7 day/month swap, else 0
- gender (0.05): 1.0 equal else 0
- phone (0.10): 1.0 if hashes equal else 0 (excluded if either missing)

**Thresholds:** score >= 0.90 gives a `PROBABLE_DUP` flag (high); 0.75 to 0.90 gives a flag (medium, "review"); below 0.75 is ignored.

**Output per match:** `match_candidates` row with `score`, `components` (per field: value_a, value_b, similarity, weight, contribution) and `explanations` (human sentences, e.g. "Names normalise to the same string (mohammed aslam)", "Father's names differ by one letter (similarity 0.93)", "Date of birth identical", "Date of birth matches with day and month swapped"). Never auto-reject; an officer confirms or dismisses.

**Privacy:** institution admins can see that one of their records is flagged as a probable duplicate but never the other college's name or record. Only `aicte_officer` sees both sides.

### 6.6 Risk score (differentiator 2)

Per college, current year. Each component is a value in 0..1; score = `round(sum(weight_i * component_i))` (weights from policy, total 100).

| Component | Weight | Definition |
|---|---|---|
| `over_intake` | 35 | `excess = sum(programme over_by) + sum(supernumerary over_by)`; `min(1, (excess / total_approved_intake) / 0.10)` |
| `duplicates` | 25 | students involved in open `DUP_*` flags or pending/confirmed matches, divided by active students; `min(1, rate / 0.05)` |
| `data_quality` | 15 | students with open `MISSING_APAAR`, `INVALID_APAAR_FORMAT`, `DOB_IMPLAUSIBLE`, `CATEGORY_INCONSISTENT`, `UNAPPROVED_PROGRAMME` over active students; `min(1, rate / 0.10)` |
| `flag_ageing` | 10 | mean age in days of open flags; `min(1, mean_days / 30)` |
| `anomaly` | 15 | `growth = (active_now - prev_year_enrolment) / prev_year_enrolment`; `min(1, max(0, growth) / 0.25)` |

**Bands:** `score < 30` low (green), `30..60` medium (amber), `> 60` high (red).
**Reasons:** for each component with contribution > 0, generate a sentence from a template, sort by contribution descending, return the top three. Examples: "Admitted 317 against 300 approved seats (excess 27, 9.0%)", "3.1% of students are in suspected duplicate records", "8 unresolved flags averaging 28 days old", "Enrolment up 40% on last year".
**Disclaimer text (UI):** "Risk score prioritises inspections; it is not a penalty decision."

### 6.7 Signed credentials (differentiator 3)

- **Keys:** Ed25519 keypair generated on first start, stored in `data/keys/ed25519_private.key` and `ed25519_public.key` (gitignored). `kid = "k1"`.
- **Payload (JSON):** `{"v":1,"cid":"<uuid4>","sid":"<student_code>","apaar":"XXXXXXXX1234" or null,"inst":"<aicte_id>","inst_name":"...","prog":"...","yr":2026,"status":"active","iat":<unix>,"kid":"k1"}`. The APAAR is masked to the last 4 digits.
- **Token:** `payload_b64 + "." + sig_b64` where `payload_b64 = base64url(canonical_json(payload))` (no padding) and `sig_b64 = base64url(Ed25519 signature over the ASCII bytes of payload_b64)`.
- **Verification:** (a) server `POST /credentials/verify`; (b) browser-only using `tweetnacl` and the public key from `GET /keys/public` (cached in localStorage so it works offline). Signature validity is independent of revocation; revocation status needs the server (`GET /credentials/status/{cid}`).
- **QR content:** `<origin>/verify?token=<token>`. Use `qrcode.react` with error correction level `L`.

### 6.8 Consent and verification

- **Public lookup (no auth):** `GET /verify/apaar/{apaar_id}` returns only `{found, enrolment_status, institution_name, programme, year}`, never name, DOB or contact. Rate limit 30 requests per minute per IP (in-memory).
- **Consent flow (verifier role):** verifier creates a request with `apaar_id`, requested `fields` (subset of `name`, `dob`, `programme`, `admission_category`, `student_code`) and `purpose` text. The student sees it in the inbox, approves with the OTP (or denies). Approved consents expire after `consent_ttl_hours`. The student can revoke at any time. The verifier can read `GET /consents/{id}/result` only while status is `approved` and unexpired; the response contains only the approved fields.
- All consent events are audited.

### 6.9 Adapters (mocked externals)

`adapters.py` defines interfaces `ApaarRegistry.lookup(apaar_id)`, `DigiLocker.fetch(doc_id)`, `OtpSender.send(phone, otp)`, each with a `Mock*` implementation reading from the local DB or returning the fixed demo OTP. Business code depends on the interface only. The registry mock simply checks that the APAAR exists in the seeded `students` table. This is where the real services would plug in.

### 6.10 Audit chain (differentiator 4)

- Table `audit_log` is append-only in application code.
- Entry fields: `id` (autoincrement), `ts` (UTC ISO), `actor` (username or `system`), `actor_role`, `action`, `entity_type`, `entity_id`, `payload` (JSON), `prev_hash`, `hash`.
- Hash: `hash = sha256_hex(prev_hash + canonical_json(entry_without_hash))` where `canonical_json = json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False)`; genesis `prev_hash = "0" * 64`.
- Audited actions: `UPLOAD_COMMIT`, `FLAG_REVIEW`, `MATCH_REVIEW`, `CREDENTIAL_ISSUE`, `CREDENTIAL_REVOKE`, `CONSENT_REQUEST`, `CONSENT_APPROVE`, `CONSENT_DENY`, `CONSENT_REVOKE`, `DEMO_RESET`, `SEED`.
- `GET /audit/verify` recomputes the chain from entry 1 and returns `{intact, entries_checked, first_broken_id}`.
- Demo-only `POST /admin/demo/tamper-audit` changes the `payload` of a chosen (or random middle) entry directly in the database without rehashing. `POST /admin/demo/reset` re-seeds everything, which restores integrity.

---

## 7. Data model (SQLAlchemy; SQLite)

Use integer primary keys unless stated. All timestamps are UTC. Add indexes on the columns marked (idx).

**users**: `id`, `username` (unique), `password_hash`, `role`, `display_name`, `college_id` (nullable), `student_id` (nullable), `organisation` (nullable)

**colleges**: `id`, `aicte_id` (unique, e.g. `SYN-0001`), `name`, `city`, `state`, `type` (Engineering / Polytechnic), `prev_year_enrolment`

**programmes**: `id`, `college_id` (idx), `name`, `level`, `shift`, `approved_intake`

**students** (one row per enrolment): `id`, `college_id` (idx), `programme_id` (nullable), `programme_raw`, `year` (idx), `student_code`, `apaar_id` (idx, nullable, stored as given), `name`, `name_norm`, `father_name`, `father_name_norm`, `dob` (idx), `gender`, `phone_hash` (nullable), `phone_last4` (nullable), `admission_category`, `social_category`, `status` (`active`/`withdrawn`), `batch_id` (nullable), `created_at`. Unique on `(college_id, student_code, year)`.

**upload_batches**: `id`, `college_id`, `uploaded_by`, `filename`, `rows_total`, `rows_saved`, `rows_error`, `created_at`

**flags**: `id`, `student_id` (nullable, idx), `college_id` (idx), `programme_id` (nullable), `code` (idx), `severity`, `message`, `evidence` (JSON), `status` (idx, default `open`), `reviewed_by`, `reviewed_at`, `note`, `match_id` (nullable), `created_at`

**match_candidates**: `id`, `student_a_id`, `student_b_id`, `score`, `band` (`probable`/`review`), `components` (JSON), `explanations` (JSON list), `status` (`pending`/`confirmed`/`dismissed`), `reviewed_by`, `reviewed_at`, `note`, `created_at`. `student_a` is the older record.

**consents**: `id`, `student_id`, `verifier_user_id`, `purpose`, `fields` (JSON list), `status` (`requested`/`approved`/`denied`/`revoked`/`expired`), `created_at`, `approved_at`, `expires_at`

**credentials**: `id` (uuid string), `student_id`, `token`, `kid`, `issued_at`, `revoked_at`, `revoked_reason`

**audit_log**: as in 6.10.

---

## 8. API specification (`/api/v1`, JSON)

**Conventions:** `Authorization: Bearer <jwt>`. Errors: `{"detail": "..."}` with proper status codes (401, 403, 404, 422). List endpoints accept `page` (default 1) and `page_size` (default 25, max 200) and return `{items, total, page, page_size}`. Institution admins are always scoped to their own `college_id` (ignore any other `college_id` they pass).

### Auth
| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/auth/login` | public | `{username, password}` returns `{access_token, token_type, user:{id, username, role, display_name, college_id, student_id}}` |
| GET | `/auth/me` | any | current user |

### Colleges and programmes
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/colleges` | officer | list with `{id, aicte_id, name, city, state, students, open_flags, risk_score, risk_band}` |
| GET | `/colleges/{id}` | officer, own admin | detail |
| GET | `/colleges/{id}/programmes` | officer, own admin | each with `approved_intake, admitted, over_by, supernumerary:{CAT:{count,cap,over_by}}` |

### Students and upload
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/templates/students.csv` | any authed | CSV template with one example row |
| POST | `/students/bulk?dry_run=true\|false` | institution | multipart `file` (csv or xlsx, max 5 MB, max 5,000 rows). Response below |
| POST | `/students` | institution | single record (same fields as template); same validation; returns `{status, issues, student_id}` |
| GET | `/students` | officer, institution | filters `college_id, programme_id, q (name/code/apaar), has_flag`; APAAR shown in full to officers, masked for others |
| GET | `/students/{id}` | officer, own admin | detail with flags |

`POST /students/bulk` response:
```json
{
  "dry_run": true,
  "summary": {"total": 40, "ok": 36, "warnings": 3, "errors": 1},
  "rows": [
    {"row": 7, "status": "warning|ok|error",
     "issues": [{"code": "INVALID_APAAR_FORMAT", "severity": "high", "field": "apaar_id",
                 "message": "APAAR must be exactly 12 digits", "hint": "Remove spaces or letters"}],
     "data": {"student_code": "...", "name": "..."}}
  ],
  "batch_id": null,
  "new_flags": null,
  "new_matches": null
}
```
With `dry_run=false`: rows with status `error` are skipped, others are saved, then flags, ledger flags and fuzzy matches are generated; response includes `batch_id`, `new_flags`, `new_matches` (counts) and an audit entry `UPLOAD_COMMIT` is written. Dry-run must never write to the database. Dry-run cannot detect fuzzy cross-college duplicates; it may report in-database exact APAAR conflicts as warnings without naming the other college.

### Flags and matches
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/flags` | officer, institution | filters `status, code, severity, college_id`; institution view redacts counterpart details to `"another institution"` |
| PATCH | `/flags/{id}` | officer (any), institution (own, `dismissed` not allowed) | `{status: "confirmed"\|"dismissed", note}`; audited |
| GET | `/matches` | officer | filters `status, band` |
| GET | `/matches/{id}` | officer | both student records, `score`, `components`, `explanations` |
| PATCH | `/matches/{id}` | officer | `{status: "confirmed"\|"dismissed", note}`; also updates the linked flag; audited |

### Analytics and risk
| Method | Path | Role | Response |
|---|---|---|---|
| GET | `/analytics/overview` | officer | `{totals:{colleges, students, open_flags, pending_matches, high_risk_colleges}, flags_by_code:[{code,count}], category_breakdown:[{category,count}], top_over_intake:[{college, approved, admitted}], recent_audit:[...5]}` |
| GET | `/analytics/colleges/{id}` | officer, own admin | `{programmes:[...], category_breakdown, flags_by_code, totals}` |
| GET | `/risk/colleges` | officer | `[{college_id, name, state, score, band, components:{name:{value, weight, contribution}}, reasons:[str,str,str]}]` sorted by score desc |
| GET | `/risk/colleges/{id}` | officer, own admin | single |

### Credentials and keys
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/keys/public` | public | `{kid, algorithm:"Ed25519", public_key_b64}` |
| POST | `/credentials/issue/{student_id}` | institution (own), officer | issues a new credential; audited |
| GET | `/credentials/mine` | student | list with token and status |
| POST | `/credentials/{id}/revoke` | institution (own), officer | `{reason}`; audited |
| GET | `/credentials/status/{cid}` | public | `{cid, status:"valid"\|"revoked"\|"unknown", revoked_at, reason}` |
| POST | `/credentials/verify` | public | `{token}` returns `{signature_valid, status, payload}`; invalid tokens return `signature_valid:false` with no payload |

### Verification and consent
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/verify/apaar/{apaar_id}` | public | masked result, rate limited |
| POST | `/consents` | verifier | `{apaar_id, fields, purpose}` |
| GET | `/consents/mine` | student, verifier | role-scoped list |
| POST | `/consents/{id}/approve` | student | `{otp}`; wrong OTP gives 400 |
| POST | `/consents/{id}/deny` | student | |
| POST | `/consents/{id}/revoke` | student | |
| GET | `/consents/{id}/result` | verifier | only approved fields; 403 if not approved or expired |

### Audit, reports, admin
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/audit` | officer | paginated, newest first |
| GET | `/audit/verify` | officer | `{intact, entries_checked, first_broken_id}` |
| GET | `/reports/roster?college_id=&format=csv\|xlsx` | officer, own admin | roster download |
| GET | `/reports/compliance?format=csv\|xlsx` | officer | per college: approved, admitted, over_by, open flags, duplicates, risk score and band |
| POST | `/admin/demo/reset` | officer, only if `DEMO_MODE` | full reseed |
| POST | `/admin/demo/tamper-audit` | officer, only if `DEMO_MODE` | alters one audit row without rehashing, returns the entry id |
| POST | `/nlq` | officer | STRETCH, section 15 |

---

## 9. Frontend specification

**Design tokens:** navy `#1F3A5F` (primary), teal `#0F6E56` (accent), background `#F6F7F9`, severity colours: low grey, medium amber `#B7791F`, high red `#C0392B`, critical dark red `#7B1E1E`. Risk bands: low green, medium amber, high red. Font: system UI stack. Footer on every page: "Synthetic demo data. External registries are simulated."

**Global:** sidebar per role, top bar (user name, role chip, logout), toast notifications, consistent loading skeletons, empty states with an explanation, error banners that show `detail`. All tables sortable and paginated (TanStack Table). Auth token kept in memory plus `sessionStorage`. `ProtectedRoute` redirects by role. Login page lists the demo accounts when `DEMO_MODE` is true (one-click fill).

### Routes
| Route | Role | Page |
|---|---|---|
| `/login` | public | Login with demo account chips |
| `/institution` | institution | KPI tiles (students, open flags, programmes over intake), programme table with approved vs admitted bars, supernumerary usage |
| `/institution/upload` | institution | Upload wizard (below) |
| `/institution/students` | institution | Searchable roster with flag badges |
| `/institution/flags` | institution | Own flags; counterpart redacted |
| `/institution/credentials` | institution | Issue and revoke credentials for students |
| `/aicte` | officer | Dashboard (below) |
| `/aicte/colleges`, `/aicte/colleges/:id` | officer | College list with risk chips; college detail (programmes, flags, risk) |
| `/aicte/flags` | officer | Flag queue with filters (code, severity, status, college) and bulk-free review dialog |
| `/aicte/matches`, `/aicte/matches/:id` | officer | Fuzzy match queue and review page (below) |
| `/aicte/risk` | officer | Risk table with expandable component bars and reasons |
| `/aicte/audit` | officer | Audit table, Verify chain, demo tamper button |
| `/aicte/reports` | officer | Download compliance and roster reports |
| `/aicte/ask` | officer | STRETCH natural-language query |
| `/student` | student | Profile, credential QR card, consent inbox and active grants |
| `/verifier` | verifier | Lookup, request consent, my requests and results |
| `/verify` | public | Offline credential verification page |

### Upload wizard (`/institution/upload`) MUST
1. **Choose file:** drag-and-drop (csv or xlsx) plus "Download template" link.
2. **Client-side pre-check (browser only, papaparse):** required columns present, each row's APAAR 12 digits, DOB parseable, enumerations valid. Show a table "Row / Field / Problem / Suggested fix" with a count banner. Hints: APAAR → "Must be exactly 12 digits, remove spaces or letters"; DOB → "Use YYYY-MM-DD or DD/MM/YYYY"; gender → "Use M, F or O"; category → "Use one of: Regular, EWS, Sports, TFW, PMSSS, NRI, OCI, FN".
3. **Server dry-run:** calls the bulk endpoint with `dry_run=true`; shows summary tiles (total, ok, warnings, errors) and a filterable row table with issue chips.
4. **Confirm and submit:** button disabled if zero savable rows; calls with `dry_run=false`; success panel shows rows saved, rows skipped, new flags, new probable duplicates (count only), and a link to the flags page.

### AICTE dashboard (`/aicte`) MUST
KPI tiles (colleges, students, open flags, pending matches, high-risk colleges); bar chart "Approved intake vs admitted" for the 10 colleges with the largest excess; pie or donut "Admission categories"; bar chart "Open flags by code"; list "Highest-risk institutions" (top 5, score chip, top reason); "Recent audit activity" (last 5). Each KPI tile and chart item links to the filtered page.

### Match review page (`/aicte/matches/:id`) MUST
Header: score badge (colour by band) and band label. Two record cards side by side (college, programme, name, father, DOB, gender, APAAR or "missing", phone last 4). Centre table: field, value A, value B, similarity (progress bar), weight, contribution to score. Below: bulleted `explanations`. Note textarea and two buttons: **Confirm duplicate** and **Dismiss (different people)**. Confirm and dismiss update the linked flag and show a toast; list view reflects the change.

### Risk page MUST
Table sorted by score; each row shows college, state, score chip with band colour, top reason. Expanding a row shows five horizontal bars (one per component with value, weight, contribution) and the three reason sentences. Disclaimer text from 6.6 is shown.

### Audit page MUST
Table (id, time, actor, action, entity, short hash first 10 chars). **Verify chain** button calls `/audit/verify`: green banner "Chain intact: N entries verified" or red banner "Chain broken at entry #K". When `DEMO_MODE`, a secondary button "Tamper entry (demo)" calls the tamper endpoint. A "Reset demo data" button (demo mode only, with confirm dialog) calls the reset endpoint.

### Student page MUST
Profile card (name, institution, programme, year, APAAR masked). **Credential card:** QR (qrcode.react), status chip (valid or revoked, from the status endpoint), buttons "Copy token", "Open verification page". **Consent inbox:** pending requests showing verifier organisation, purpose and requested fields; Approve (OTP input with demo hint) or Deny; active grants list with expiry and Revoke.

### Verifier page MUST
APAAR lookup form leading to a masked result card (status, institution, programme, year). Button "Request detailed verification" opens a form: field checkboxes and purpose. "My requests" table with status chips; when approved, a "View result" panel shows exactly the approved fields; when denied, revoked or expired, shows the reason.

### Public verify page (`/verify`) MUST
Reads `?token=` or accepts pasted token. On load it fetches `/keys/public` and caches `{kid, public_key_b64}` in `localStorage`; if the fetch fails it uses the cache and shows an "Offline mode" badge. "Verify signature" runs entirely in the browser with `tweetnacl` and shows: green "Signature valid" with payload fields, or red "Signature invalid, record may be tampered". Separate button "Check revocation (needs connection)" calls `/credentials/status/{cid}` and shows valid, revoked (with reason) or "could not check". A note explains that signature validity and revocation are independent.

---

## 10. Seed data specification (MUST; `seed.py`, deterministic with `random.seed(2026)` and `Faker.seed(2026)`)

### 10.1 General
- 20 synthetic colleges (list in 10.2), each 3 to 5 programmes from: B.Tech Computer Science and Engineering, B.Tech Electronics and Communication Engineering, B.Tech Mechanical Engineering, B.Tech Civil Engineering, M.Tech Computer Science (PG), Diploma in Mechanical Engineering (Polytechnics). `approved_intake` from {60, 90, 120, 180}.
- Normal programmes: admitted = 80% to 97% of approved intake, all valid, no flags. Roughly 3,000 students total. Generated normal records must be fully valid (12-digit unique APAAR starting `4219`, plausible DOB, valid enums) and must not accidentally match any other student above 0.75 (the seeder runs the matcher and re-draws names on collision).
- Students already in the DB are created without going through the HTTP API but through the same validation and matching services so flags and matches are produced naturally.
- Flag `created_at` back-dated: College 3 flags 20 to 35 days old; others 1 to 10 days.
- Users from section 3 are created. Credentials: Ananya Rao (College 1, CSE, APAAR `421900000101`) has one valid credential; Dev Malhotra (College 1, ECE) has one credential that is revoked with reason "Withdrawn from programme".
- `prev_year_enrolment`: College 1 and 5 to 20 equal to current; College 2 about 83% of current (growth about 20%); College 3 about 71% (growth about 40%); College 4 equal to current.

### 10.2 Colleges
1 Greenfield Institute of Technology (Pune, Maharashtra) · 2 Lakeview College of Engineering (Chennai, Tamil Nadu) · 3 Riverstone Technical Campus (Jaipur, Rajasthan) · 4 Summit Polytechnic (Bhopal, Madhya Pradesh) · 5 Coastal Institute of Engineering (Visakhapatnam, Andhra Pradesh) · 6 Himalaya School of Technology (Dehradun, Uttarakhand) · 7 Deccan College of Engineering (Hyderabad, Telangana) · 8 Sundarbans Institute of Technology (Kolkata, West Bengal) · 9 Narmada Engineering College (Indore, Madhya Pradesh) · 10 Malabar Institute of Technology (Kochi, Kerala) · 11 Thar Polytechnic (Jodhpur, Rajasthan) · 12 Western Ghats College of Engineering (Kolhapur, Maharashtra) · 13 Brahmaputra Technical Institute (Guwahati, Assam) · 14 Kaveri Institute of Technology (Mysuru, Karnataka) · 15 Satpura Engineering College (Nagpur, Maharashtra) · 16 Konkan Polytechnic (Mangaluru, Karnataka) · 17 Ganga Plains Institute (Lucknow, Uttar Pradesh) · 18 Vindhya School of Engineering (Raipur, Chhattisgarh) · 19 Eastern Hills College of Technology (Bhubaneswar, Odisha) · 20 Punjab Valley Institute of Engineering (Ludhiana, Punjab). `aicte_id` = `SYN-0001` to `SYN-0020`.

### 10.3 Planted cases (exact)

| # | Case | Where | Detail |
|---|---|---|---|
| P1 | Clean college | College 1 | CSE approved 180 (admitted 100 seeded), ECE approved 120 (admitted 70 seeded). No flags. Live-demo upload target |
| P2 | Over-intake | College 2 | CSE approved 120, admitted 134 (130 Regular + 4 Sports) |
| P3 | Supernumerary breach | College 2 | ECE approved 60: 50 Regular plus 5 TFW (cap 3) |
| P4 | Exact cross-college duplicate | Colleges 2 and 3 | One student at each, same valid APAAR `421900000011` (different names are fine) |
| P5 | Same-college duplicates | College 3 | Two pairs sharing an APAAR within College 3 |
| P6 | Fuzzy duplicate, high | Colleges 2 and 4 | "Sneha Kulkarni" (C2, APAAR present) vs "Snehaa Kulkarni" (C4, APAAR missing); same DOB, gender F; fathers "Prakash Kulkarni" and "Prakash R Kulkarni" |
| P7 | Fuzzy duplicate, review band | Colleges 3 and 4 | "Karan Mehta" (C3) vs "Karan Mehata" (C4, APAAR missing); DOB day/month swapped; fathers similar; expected score in 0.75 to 0.90 |
| P8 | Live fuzzy target 1 | College 3 | Existing "Mohammed Aslam", APAAR `421900000021`, DOB 2005-03-14, gender M, father "Abdul Rahman" |
| P9 | Live fuzzy target 2 | College 4 | Existing "Rohit Sharma", DOB 2004-02-11, gender M, father "Suresh Sharma" |
| P10 | Unapproved programme | College 4 | 4 students in "B.Tech Robotics and AI" (not an approved programme) |
| P11 | Category inconsistency | College 4 | 1 student `FN` with social category `OBC` |
| P12 | Malformed APAAR | College 3 | 10 students with invalid APAARs (for example `12345`, `ABCD12345678`, `4219 0000 0031`) |
| P13 | Implausible DOB | College 3 | 2 students with age far outside range |
| P14 | High-risk college | College 3 | CSE approved 120 admitted 138; ME approved 90 admitted 99; CE approved 90 admitted 80 (no excess); prev year about 71% of current |
| P15 | Revoked credential | College 1 | Dev Malhotra (see 10.1) |

**Expected open flag counts after a fresh seed (the seed script asserts these and fails loudly):**

| Code | Count |
|---|---|
| `DUP_CROSS_COLLEGE` | 2 |
| `DUP_SAME_COLLEGE` | 4 |
| `PROBABLE_DUP` | 2 (one high, one medium) |
| `INTAKE_EXCEEDED` | 3 (C2 CSE, C3 CSE, C3 ME) |
| `SUPERNUMERARY_EXCEEDED` | 1 |
| `UNAPPROVED_PROGRAMME` | 4 |
| `CATEGORY_INCONSISTENT` | 1 |
| `INVALID_APAAR_FORMAT` | 10 |
| `MISSING_APAAR` | 2 |
| `DOB_IMPLAUSIBLE` | 2 |

**Expected risk results:** College 3 band high with score at least 65; College 2 band medium (30 to 60); College 1 band low (below 30); all other colleges low. If a band is off, tune only seed levers (prev-year enrolment, back-dated flag ages), not the formula.

### 10.4 Sample upload files (generated into `backend/seed_data/`, committed)

- `c1_clean.csv`: 40 rows for College 1 (25 CSE, 15 ECE), all valid, unique APAAR IDs not present elsewhere. Expected dry-run: 40 ok, 0 warnings, 0 errors. After commit: no new flags.
- `c1_with_issues.csv`: 40 rows for College 1 (spread across CSE and ECE so no programme exceeds intake):
  - 1 row with a malformed APAAR (warning, `INVALID_APAAR_FORMAT`)
  - 1 row with unparseable DOB `31/02/2005` (error, row skipped)
  - 1 row reusing the exact APAAR of an existing College 2 student (dry-run warning without naming the other college; `DUP_CROSS_COLLEGE` flag on commit)
  - 1 row "Muhammad Aslam", APAAR blank (warning, `MISSING_APAAR`), DOB 2005-03-14, gender M, father "Abdul Rehman" (fuzzy match against P8, score at least 0.90 on commit)
  - 1 row "Rohit Sharma", valid new APAAR, DOB 2004-11-02, gender M, father "Suresh Sharma" (ok on dry-run; day/month swap match against P9, score at least 0.90 on commit)
  - 35 clean rows
  Expected dry-run: **36 ok, 3 warnings, 1 error**. After commit: 39 rows saved, at least 2 new `PROBABLE_DUP` matches, 1 new `DUP_CROSS_COLLEGE` flag (on both records), and 2 new `MISSING_APAAR`/`INVALID_APAAR_FORMAT` flags.

---

## 11. Demo script and acceptance walkthrough (must pass)

Pre-step: `POST /admin/demo/reset` (or `make seed`). Use a fresh browser profile.

| Step | Actor | Action | Expected result |
|---|---|---|---|
| 1 | `inst_a` | Upload `c1_clean.csv` through the wizard | Pre-check shows 0 problems; dry-run 40 ok; commit saves 40; no new flags |
| 2 | `inst_a` | Upload `c1_with_issues.csv` | Pre-check lists the malformed APAAR and the bad DOB with hints; dry-run shows 36 ok, 3 warnings, 1 error; commit saves 39 rows and skips 1; success panel shows new flags and at least 2 new probable duplicates |
| 3 | `officer` | Open `/aicte` | KPIs updated; over-intake chart shows C3 and C2; risk list shows C3 high |
| 4 | `officer` | Open `/aicte/matches` and the Muhammad Aslam match | Score at least 0.90, explanations mention the spelling variant and identical DOB, both colleges visible; click Confirm duplicate; linked flag becomes confirmed |
| 5 | `officer` | Open `/aicte/risk` and expand College 3 | Score at least 65, bars and three plain-language reasons |
| 6 | `student` | Open `/student`; show QR card | Status valid |
| 7 | `verifier` | Lookup `421900000101`, request consent for `name, programme` with a purpose | Request shows as requested |
| 8 | `student` | Approve with OTP `123456` | Status approved |
| 9 | `verifier` | View result | Exactly name and programme shown; no DOB |
| 10 | public | Open `/verify` with the student's token, disconnect network, click Verify | Signature valid works offline |
| 11 | public | Change one character of the token and verify | Signature invalid |
| 12 | public | Open Dev Malhotra's seeded token on `/verify` and click Check revocation | Signature valid but status revoked with reason "Withdrawn from programme" |
| 13 | `officer` | `/aicte/audit` → Verify chain | Green, N entries |
| 14 | `officer` | Tamper entry (demo), then Verify chain | Red, broken at the tampered entry id |
| 15 | `officer` | Reset demo data | Chain intact again |

---

## 12. Testing (MUST)

Backend `pytest` (use a temporary SQLite DB per test session; seed once):

- `test_normalise.py`: "Mohd Aslam" and "Muhammad Aslam" normalise equal; honorifics stripped; repeated vowels collapsed.
- `test_matching.py`: Mohammed/Muhammad pair scores at least 0.90; DOB-swap pair scores at least 0.90 and flags `components.dob = 0.7`; unrelated pair with the same DOB scores below 0.75; missing phone renormalises weights.
- `test_validation.py`: each rule code triggers on a crafted row and not on a clean row; blocking errors skip rows; regex edge cases (`12345`, `ABCD12345678`, 12 digits with spaces).
- `test_ledger.py`: over-intake and supernumerary computations against P2 and P3.
- `test_risk.py`: bands for C1, C2, C3 as in 10.3; reasons list has at most 3 items and names real numbers.
- `test_credentials.py`: sign and verify round trip; one altered character fails; revoked credential reports `revoked` while signature is still valid.
- `test_audit.py`: chain intact after seed; tamper endpoint breaks verification at the right entry; reset restores it.
- `test_consent.py`: wrong OTP rejected; only approved fields returned; expired or revoked consent returns 403.
- `test_api_flow.py`: scripted version of demo steps 1 to 15 using `httpx` against the app, including role-permission checks (institution cannot read another college; verifier cannot read results without consent; student cannot access officer routes).
- `test_seed_counts.py`: exact flag counts from 10.3.

Frontend: `npm run build` and `tsc --noEmit` must pass. Optional STRETCH: Playwright smoke test covering demo steps 1 to 4.

---

## 13. Build phases for Claude Code

Work through these in order. Commit at the end of each. State "Phase N complete" with a one-paragraph summary and test results.

| Phase | Scope | Done when |
|---|---|---|
| 0 Scaffold | Repo structure, config, DB, Makefile, Dockerfile, health endpoint, frontend shell with Tailwind and router | `make dev` serves both; `/api/v1/health` returns ok |
| 1 Core data | Models, policy loading, security (JWT, roles), auth routes, seed for colleges, programmes, users | Login works for all five demo users; role guards return 403 correctly |
| 2 Ingest and validation | Parser, validation, flag generation, ledger, bulk and single endpoints, template endpoint | Dry-run and commit work on sample CSVs; ledger flags correct |
| 3 Matching | Normaliser, matcher, match endpoints, flag linkage | Matching tests pass; planted pairs detected |
| 4 Seed completion | Full seed with all planted cases, back-dated flags, sample CSV generation, exact count assertions | `test_seed_counts.py` passes |
| 5 Analytics and risk | Analytics endpoints, risk service, reports | Risk bands match 10.3 |
| 6 Credentials, consent, audit | Key management, credentials, public verify, consent flow, audit chain, demo admin endpoints | Their tests pass |
| 7 Frontend: shell and institution | Auth, layouts, institution pages, upload wizard | Demo steps 1 and 2 work in the browser |
| 8 Frontend: AICTE | Dashboard, colleges, flags, matches, risk, audit, reports | Demo steps 3 to 5, 13 to 15 work |
| 9 Frontend: student, verifier, public | Wallet, consent, verifier, offline verify page | Demo steps 6 to 12 work, including offline |
| 10 Hardening | Docker image, README with demo script, empty and error states, responsive pass, full `test_api_flow.py`, run the demo script end to end | Everything in section 2 success criteria passes |
| 11 STRETCH | Natural-language query (section 15) | Works with and without API key |

---

## 14. Non-functional, security and privacy

- Passwords hashed with PBKDF2-HMAC-SHA256 (at least 200,000 iterations, random salt). JWT secret from `JWT_SECRET` (demo default allowed, logged warning).
- Role checks implemented once as FastAPI dependencies; every route declares its roles. Institution scoping enforced in the query layer.
- Validate and sanitise all inputs with Pydantic; reject files over 5 MB or 5,000 rows; treat uploaded content as untrusted (no formula evaluation: prefix cell values starting with `=`, `+`, `-`, `@` with a single quote on XLSX/CSV export).
- Data minimisation: public endpoints never return personal data; APAAR masked for non-officers; phone stored as salted hash plus last 4 digits only.
- Cross-institution privacy: institutions never see the counterpart college or record in duplicate flags.
- Performance: dashboard and risk endpoints respond within 1 second on the seed data; add indexes noted in section 7; compute risk in a single pass per college, no N+1 queries.
- Reliability: the app must start with no internet; seed runs in under 30 seconds.
- Logging: structured request logs; never log passwords, tokens or OTPs.
- Env vars: `DEMO_MODE` (default `true`), `JWT_SECRET`, `DEMO_OTP` (default `123456`), `DATABASE_URL` (default `sqlite:///data/app.db`), `ANTHROPIC_API_KEY` (optional, STRETCH only).

---

## 15. STRETCH: natural-language officer query (`/aicte/ask`, `POST /nlq`)

Input: `{question: "Which colleges in Tamil Nadu exceeded CSE intake?"}`. The server converts it into a **validated JSON filter**, never SQL:

```json
{"metric": "over_intake|duplicates|risk_score|open_flags|enrolment",
 "filters": {"state": "Tamil Nadu", "programme_contains": "Computer Science", "min_value": 1},
 "sort": "desc", "limit": 10}
```

- If `ANTHROPIC_API_KEY` is set, ask an LLM to output only this JSON (Pydantic validates against an allow-list of metrics and filter keys; reject anything else). If not set, use a simple keyword parser covering the same shapes.
- Execute the filter with existing service functions and return `{interpretation: <filter>, columns, rows}`. The UI shows the interpretation ("Understood as: ...") above a table, plus a bar chart when the metric is numeric.
- Suggested example chips: "Which colleges exceeded intake?", "Top 5 risk scores", "Colleges in Rajasthan with duplicates".

---

## 16. Assumptions and open questions

- The verbatim official PS text was not available when this was written; requirements are reconstructed from public prototypes. Before final submission, compare section 1 and 6 with the official Background, Description and Expected Outcomes on the SIH portal and note any difference in `docs/DECISIONS.md`.
- APAAR is assumed to be a 12-digit numeric ID. Confirm against official APAAR documentation; the regex is in `policy.json` for easy change.
- Supernumerary caps, age ranges and thresholds are illustrative.
- Risk score weights are heuristic and for inspection prioritisation only.
- Nothing here is production-ready or legally compliant; do not describe it as such in the UI or documents.

---

## Appendix A: suggested `CLAUDE.md` (create at repo root)

```markdown
# CLAUDE.md
- Source of truth: PRD.md. Follow the phases in section 13; commit after each phase.
- Backend: Python 3.11, FastAPI, SQLAlchemy 2, SQLite. Run tests with `make test`. Keep business logic in app/services, routes thin.
- Frontend: React 18 + Vite + TypeScript + Tailwind 3.4. No UI kit. Typed API wrappers in src/api.
- All demo data is synthetic. Never add real personal data.
- Numbers like thresholds and caps live in backend/app/policy.json, not in code.
- Never write SQL from model output; the NLQ feature uses validated JSON filters only.
- After finishing a phase, run the app and the relevant tests, then summarise results.
- Record any ambiguity resolution in docs/DECISIONS.md.
```

## Appendix B: first prompt to give Claude Code

> Read PRD.md completely and CLAUDE.md. Create a short implementation plan, then execute Phase 0 and Phase 1. Run the tests and the app, fix any failures, commit, and report. Then continue phase by phase until Phase 10, stopping only for blocking issues.
