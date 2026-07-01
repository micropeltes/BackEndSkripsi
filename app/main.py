from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.converters.registry import SensorConverterRegistry
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database import SessionLocal, init_db
from app.routers.calibration import router as calibration_router
from app.routers.health import router as health_router
from app.routers.sensors import router as sensors_router
from app.routers.websocket import router as websocket_router
from app.converters.r0_baselines import format_active_r0_baselines
from app.services.mqtt_ingestion_service import AsyncMqttIngestionService
from app.services.sensor_pipeline_service import SensorPipelineService
from app.services.websocket_manager import sensor_ws_manager
from app.utils.errors import AppError


setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
rate_limit_buckets: dict[str, tuple[float, int]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting backend service")
    sensor_ws_manager.bind_loop(asyncio.get_running_loop())

    db_ready = init_db()
    if not db_ready:
        logger.error("Database initialization failed. Check DATABASE_URL.")

    registry = SensorConverterRegistry()
    logger.info(
        "Active calibrated R0 baselines: %s",
        format_active_r0_baselines(registry.list_supported()),
    )

    mqtt_ingestion: AsyncMqttIngestionService | None = None
    app.state.mqtt_ingestion = None
    app.state.mqtt_startup_error = None

    if db_ready and settings.mqtt_enabled:
        try:
            pipeline = SensorPipelineService(
                settings=settings,
                session_factory=SessionLocal,
                registry=registry,
            )
            mqtt_ingestion = AsyncMqttIngestionService(
                settings=settings,
                pipeline_service=pipeline,
            )
            await mqtt_ingestion.start()
            app.state.mqtt_ingestion = mqtt_ingestion
            logger.info("MQTT ingestion started")
        except Exception as exc:  # pragma: no cover - defensive startup guard
            app.state.mqtt_startup_error = str(exc)
            logger.exception("MQTT startup failed: %s", exc)

    yield

    if mqtt_ingestion is not None:
        await mqtt_ingestion.stop()
        logger.info("MQTT ingestion stopped")

    logger.info("Backend shutdown completed")


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if settings.rate_limit_per_minute <= 0:
        return await call_next(request)

    client_host = request.client.host if request.client else "unknown"
    now = monotonic()
    window_started_at, count = rate_limit_buckets.get(client_host, (now, 0))

    if now - window_started_at >= 60:
        window_started_at = now
        count = 0

    count += 1
    rate_limit_buckets[client_host] = (window_started_at, count)

    if count > settings.rate_limit_per_minute:
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "rate_limited",
                "detail": "Too many requests.",
            },
        )

    if len(rate_limit_buckets) > 10000:
        stale_before = now - 120
        stale_keys = [
            host
            for host, (started_at, _) in rate_limit_buckets.items()
            if started_at < stale_before
        ]
        for host in stale_keys:
            rate_limit_buckets.pop(host, None)

    return await call_next(request)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.message,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database request failed: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "error_code": "database_unavailable",
            "detail": "Database connection is temporarily unavailable.",
        },
    )


app.include_router(health_router)
app.include_router(sensors_router, prefix=settings.api_prefix)
app.include_router(websocket_router, prefix=settings.api_prefix)
app.include_router(calibration_router, prefix=settings.api_prefix)
