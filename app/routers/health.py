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
        if not settings.mqtt_enabled:
            status = "disabled"
        elif startup_error:
            status = "startup_error"
        else:
            status = "stopped"

        return {
            "status": status,
            "enabled": settings.mqtt_enabled,
            "started": False,
            "connected": False,
            "auth_configured": bool(settings.mqtt_username and settings.mqtt_password),
            "startup_error": bool(startup_error),
        }

    mqtt_status = mqtt_ingestion.status()
    return {
        "status": "connected" if mqtt_status.get("connected") else "disconnected",
        "started": True,
        "enabled": settings.mqtt_enabled,
        "connected": bool(mqtt_status.get("connected")),
        "auth_configured": bool(mqtt_status.get("auth_configured")),
    }
