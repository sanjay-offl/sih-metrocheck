"""MetroCheck API entrypoint.

Run locally with:  uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

import app.models  # noqa: F401 - registers every table on Base.metadata
from app.core.config import BACKEND_DIR, settings
from app.core.database import Base, engine
from app.routes import auth, dashboard, products, reports, scan
from app.services.cache_service import cache_health
from app.services.vision_service import vision_engine

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("metrocheck")


def init_database() -> None:
    """Apply migrations in production, create tables for quick local runs."""
    if settings.run_migrations:
        try:
            from alembic import command
            from alembic.config import Config

            config = Config(str(BACKEND_DIR / "alembic.ini"))
            config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
            logger.info("Applying Alembic migrations")
            command.upgrade(config, "head")
            return
        except Exception:  # noqa: BLE001 - fall back to create_all below
            logger.exception("Alembic upgrade failed; falling back to create_all")

    Base.metadata.create_all(bind=engine)
    logger.info("Database schema ensured via create_all")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.reports_path.mkdir(parents=True, exist_ok=True)
    init_database()
    logger.info(
        "MetroCheck %s ready — extraction engine: %s (%s)",
        settings.app_version,
        vision_engine(),
        settings.gemini_model if vision_engine() == "gemini" else "tesseract",
    )
    if vision_engine() == "ocr":
        logger.warning(
            "GEMINI_API_KEY is not set: MetroCheck will use Tesseract OCR fallback "
            "and cannot measure font sizes for Rule 10."
        )
    yield
    engine.dispose()


app = FastAPI(
    title="MetroCheck API",
    description=(
        "AI-powered compliance checking for packaged commodities under the "
        "Legal Metrology (Packaged Commodities) Rules, 2011."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": type(exc).__name__},
    )


# Static uploads (label images referenced by scans)
app.mount("/uploads", StaticFiles(directory=str(settings.upload_path), check_dir=False), name="uploads")

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(scan.router, prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)


@app.get("/health", tags=["System"])
def health() -> dict:
    database = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        database = f"error: {type(exc).__name__}"

    return {
        "status": "ok" if database == "ok" else "degraded",
        "service": "MetroCheck API",
        "version": settings.app_version,
        "database": database,
        "cache": cache_health(),
        "vision_engine": vision_engine(),
    }


@app.get("/", tags=["System"])
def root() -> dict:
    return {
        "name": settings.app_name,
        "tagline": "Scan. Detect. Enforce.",
        "docs": "/docs",
        "health": "/health",
        "api_prefix": API_PREFIX,
    }
