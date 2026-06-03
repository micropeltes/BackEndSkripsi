from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.config import get_settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/mqtt")
def mqtt_health_check(request: Request) -> dict[str, object]:
    settings = get_settings()
    mqtt_ingestion = getattr(request.app.state, "mqtt_ingestion", None)
    startup_error = getattr(request.app.state, "mqtt_startup_error", None)

    if mqtt_ingestion is None:
        return {
            "enabled": settings.mqtt_enabled,
            "started": False,
            "connected": False,
            "broker": settings.mqtt_broker,
            "port": settings.mqtt_port,
            "topic": settings.mqtt_sensor_topic,
            "ca_cert": settings.mqtt_ca_cert,
            "auth_configured": bool(settings.mqtt_username and settings.mqtt_password),
            "startup_error": startup_error,
        }

    return {
        "started": True,
        **mqtt_ingestion.status(),
    }
