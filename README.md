# APAAR Verify (SIH 2026, PS SIH26263) – working demo

Synthetic demo data only. External registries (APAAR, DigiLocker, SMS) are simulated.

See PRD.md for the full specification. Setup and demo script are documented below (completed in Phase 10).

## Quick start (dev)

```bash
python3 -m venv .venv && make install
make seed      # reset DB and seed demo data
make dev       # backend :8000, frontend :5173
make test
```
