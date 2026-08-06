import logging
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.access_middleware import AccessLogMiddleware
from app.config import get_settings
from app.dependencies import get_current_user
from app.logging_config import setup_logging
from app.routers import auth, chart, orders, query

settings = get_settings()

# ── Logging ── must be set up before any module creates a logger
setup_logging(debug=settings.debug)

_sys_log = logging.getLogger("system")

# ── Directory layout ──
# main.py lives at backend/app/main.py → .parent.parent.parent = project root
ROOT_DIR     = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

# ── Middleware ── order matters: CORS first, then access log
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AccessLogMiddleware)


# ── Startup / shutdown lifecycle ────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    _sys_log.info("Application starting up — %s (debug=%s)", settings.app_name, settings.debug)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    _sys_log.info("Application shutting down")


# ── Frontend files ── registered BEFORE API routers
@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    """Serve the SPA entry point."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/frontend/{path:path}", include_in_schema=False)
async def serve_frontend(path: str) -> FileResponse:
    """Serve all frontend assets: CSS, JS, images, favicon, etc."""
    file_path = FRONTEND_DIR / path
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path))


# ── API routers ── after static routes
app.include_router(auth.router)
app.include_router(chart.router, dependencies=[Depends(get_current_user)])
app.include_router(query.router, dependencies=[Depends(get_current_user)])
# Orders router: auth is enforced inside each endpoint via require_admin
app.include_router(orders.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
