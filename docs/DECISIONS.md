# Decisions

Ambiguities in PRD.md resolved during implementation. Simplest option that satisfies the acceptance criteria.

1. **Repo root.** The PRD shows an `apaar-verify/` folder; the git repository root plays that role.
2. **Database path.** `DATABASE_URL` defaults to `sqlite:///<repo>/data/app.db` (absolute, so it works from any working directory). `DATA_DIR` and `KEYS_DIR` env vars override locations (used by tests).
3. **Auto-seed.** On startup, if the database has no users, the app seeds itself so `docker compose up` gives a ready demo.
4. **Students store `level` and `shift`.** They are template columns; keeping them on the record makes the roster and reports complete. Not in the section 7 column list but harmless.
5. **Public config endpoint.** `GET /api/v1/config` exposes `demo_mode`, the demo OTP hint (only when `DEMO_MODE=true`) and the policy so the frontend pre-check uses the same enums and regex as the server.
