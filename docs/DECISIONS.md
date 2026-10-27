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
11. **Seed size.** Planted programme sizes are fixed by PRD 10.3 (C3 alone has 317 students), and every college needs 3 to 5 programmes at 60+ seats filled 80 to 97%, so the seed has about 5,200 students rather than "roughly 3,000". Seeding still takes about 3 seconds.
12. **Polytechnic programmes.** The PRD list has a single diploma programme; polytechnics need 3, so `Diploma in Civil Engineering` and `Diploma in Computer Engineering` were added.
13. **`PROBABLE_DUP` flag placement.** One flag per match, on the newer record (`student_b`), linked by `match_id`. This gives the expected count of 2 and puts the flag on the uploading institution's record during a live upload.
14. **Normal seed identities** are drawn until their best fuzzy score against everyone already generated is below the review threshold; names and DOB are redrawn together.
15. **P7 (review band)**: both Karan records carry different phone numbers, which pulls the score to about 0.83 (a matching name, father and swapped DOB alone would score above 0.90).
16. **Spelling variants**: `rehman` is deliberately not mapped to `rahman`, so the Aslam match shows a father's-name difference of one letter as in the PRD example.
