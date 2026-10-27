# Decisions

Ambiguities in PRD.md resolved during implementation. Simplest option that satisfies the acceptance criteria.

1. **Repo root.** The PRD shows an `apaar-verify/` folder; the git repository root plays that role.
2. **Database path.** `DATABASE_URL` defaults to `sqlite:///<repo>/data/app.db` (absolute, so it works from any working directory). `DATA_DIR` and `KEYS_DIR` env vars override locations (used by tests).
3. **Auto-seed.** On startup, if the database has no users, the app seeds itself so `docker compose up` gives a ready demo.
4. **Students store `level` and `shift`.** They are template columns; keeping them on the record makes the roster and reports complete. Not in the section 7 column list but harmless.
5. **Public config endpoint.** `GET /api/v1/config` exposes `demo_mode`, the demo OTP hint (only when `DEMO_MODE=true`) and the policy so the frontend pre-check uses the same enums and regex as the server.
6. **Row numbers** in upload results are spreadsheet line numbers (header is line 1, first data row is 2). The client pre-check uses the same numbering.
7. **Extra blocking error `STUDENT_ID_EXISTS`.** A row whose `student_id` already exists for the college and year is an error, so re-uploading a file never crashes on the unique constraint or silently duplicates records.
8. **Dry-run APAAR conflicts** are reported as `DUP_SAME_COLLEGE` / `DUP_CROSS_COLLEGE` warnings ("another institution", never named). In-file duplicate APAARs are `DUP_SAME_COLLEGE` warnings.
9. **Programme-level flags** use status `resolved_auto` when a reviewed flag's condition clears; open flags whose condition clears are deleted (PRD 6.3).
10. **Single-record `POST /students`** always returns 200 with `{status, issues, student_id}`; `student_id` is null when the row has blocking errors.
