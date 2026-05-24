from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.converters.registry import SensorConverterRegistry
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database import SessionLocal, init_db
from app.routers.calibration import router as calibration_router
from app.routers.health import router as health_router
from app.routers.sensors import router as sensors_router
from app.services.mqtt_ingestion_service import AsyncMqttIngestionService
from app.services.sensor_pipeline_service import SensorPipelineService
from app.utils.errors import AppError


setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting backend service")

    db_ready = init_db()
    if not db_ready:
        logger.error("Database initialization failed. Check DATABASE_URL.")

    mqtt_ingestion: AsyncMqttIngestionService | None = None

    if db_ready and settings.mqtt_enabled:
        try:
            pipeline = SensorPipelineService(
                settings=settings,
                session_factory=SessionLocal,
                registry=SensorConverterRegistry(),
            )
            mqtt_ingestion = AsyncMqttIngestionService(
                settings=settings,
                pipeline_service=pipeline,
            )
            await mqtt_ingestion.start()
            app.state.mqtt_ingestion = mqtt_ingestion
            logger.info("MQTT ingestion started")
        except Exception as exc:  # pragma: no cover - defensive startup guard
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.message,
        },
    )


app.include_router(health_router)
app.include_router(sensors_router, prefix=settings.api_prefix)
app.include_router(calibration_router, prefix=settings.api_prefix)
