# CLAUDE.md
- Source of truth: PRD.md. Follow the phases in section 13; commit after each phase.
- Backend: Python 3.11, FastAPI, SQLAlchemy 2, SQLite. Run tests with `make test`. Keep business logic in app/services, routes thin.
- Frontend: React 18 + Vite + TypeScript + Tailwind 3.4. No UI kit. Typed API wrappers in src/api.
- All demo data is synthetic. Never add real personal data.
- Numbers like thresholds and caps live in backend/app/policy.json, not in code.
- Never write SQL from model output; the NLQ feature uses validated JSON filters only.
- After finishing a phase, run the app and the relevant tests, then summarise results.
- Record any ambiguity resolution in docs/DECISIONS.md.
