from fastapi import APIRouter

from app.core.config import get_settings
from app.routers.calibration import router as calibration_router
from app.routers.health import router as health_router
from app.routers.sensors import router as sensors_router
from app.routers.websocket import router as websocket_router

settings = get_settings()

router = APIRouter()
router.include_router(health_router)
router.include_router(sensors_router, prefix=settings.api_prefix)
router.include_router(websocket_router, prefix=settings.api_prefix)
router.include_router(calibration_router, prefix=settings.api_prefix)
