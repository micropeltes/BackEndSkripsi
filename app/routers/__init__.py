from app.routers.calibration import router as calibration_router
from app.routers.health import router as health_router
from app.routers.sensors import router as sensors_router

__all__ = [
    "health_router",
    "sensors_router",
    "calibration_router",
]
