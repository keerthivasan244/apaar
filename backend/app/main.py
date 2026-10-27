"""Application factory: API routers, static frontend serving with SPA fallback."""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select

from . import routes
from .config import get_policy, get_settings
from .db import SessionLocal, create_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("apaar.request")

API_PREFIX = "/api/v1"


def _ensure_seeded() -> None:
    from .models import User
    from .seed import seed

    create_all()
    with SessionLocal() as db:
        if db.scalar(select(func.count(User.id))) == 0:
            logging.getLogger("apaar").info("Empty database, seeding demo data")
            seed(db)


def create_app(*, auto_seed: bool = True) -> FastAPI:
    settings = get_settings()
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        _ensure_seeded() if auto_seed else create_all()
        yield

    app = FastAPI(title="APAAR Verify", version="1.0.0", docs_url=f"{API_PREFIX}/docs",
                  openapi_url=f"{API_PREFIX}/openapi.json", lifespan=lifespan)

    if settings.dev_cors:
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        # Path only: never log query strings (tokens) or bodies (passwords, OTPs).
        log.info('method=%s path=%s status=%s ms=%.1f', request.method, request.url.path,
                 response.status_code, (time.perf_counter() - start) * 1000)
        return response

    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", tags=["meta"])
    def health():
        return {"status": "ok"}

    @api.get("/config", tags=["meta"])
    def public_config():
        policy = get_policy()
        return {
            "demo_mode": settings.demo_mode,
            "demo_otp_hint": settings.demo_otp if settings.demo_mode else None,
            "academic_year": policy["academic_year"],
            "policy": policy,
        }

    for router in routes.all_routers():
        api.include_router(router)
    app.include_router(api)

    dist = settings.frontend_dist

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        index = dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "Frontend not built. Run `make build` or use the Vite dev server."},
                            status_code=404)

    return app


app = create_app()
