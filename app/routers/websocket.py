from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.converters.registry import SensorConverterRegistry
from app.core.config import get_settings
from app.database import SessionLocal
from app.services.calibration_service import CalibrationService
from app.services.sensor_payload_service import build_latest_sensor_payload
from app.services.sensor_reading_service import SensorReadingService
from app.services.websocket_manager import sensor_ws_manager


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


def _normalize_device_id(device_id: str | None) -> str | None:
    if device_id is None:
        return None
    normalized = device_id.strip()
    return normalized or None


@router.websocket("/sensors/latest")
async def stream_latest_sensors(
    websocket: WebSocket,
    limit: int = Query(default=1000, ge=1, le=1000),
    device_id: str | None = Query(default=None, max_length=64),
) -> None:
    await sensor_ws_manager.connect(websocket)
    client_host = websocket.client.host if websocket.client else "unknown"
    normalized_device_id = _normalize_device_id(device_id)
    logger.info(
        "WS connected path=/api/v1/ws/sensors/latest client=%s limit=%s device_id=%s",
        client_host,
        limit,
        normalized_device_id or "",
    )

    try:
        await sensor_ws_manager.send_json(websocket, sensor_ws_manager.health_payload())
        logger.info("WS sent health")

        settings = get_settings()
        registry = SensorConverterRegistry()
        snapshot_payload = {
            "type": "snapshot",
            "count": 0,
            "items": [],
        }

        try:
            with SessionLocal() as db:
                reading_service = SensorReadingService(db=db)
                calibration_service = CalibrationService(db=db, registry=registry)
                snapshot = build_latest_sensor_payload(
                    limit=limit,
                    device_id=normalized_device_id,
                    settings=settings,
                    registry=registry,
                    calibration_service=calibration_service,
                    reading_service=reading_service,
                )
                snapshot_payload = {
                    "type": "snapshot",
                    **snapshot.model_dump(),
                }
        except Exception as exc:
            logger.warning(
                "WS snapshot build failed path=/api/v1/ws/sensors/latest client=%s error=%s",
                client_host,
                exc,
            )

        await sensor_ws_manager.send_json(websocket, snapshot_payload)
        logger.info("WS sent snapshot count=%s", snapshot_payload["count"])

        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=30)
            except asyncio.TimeoutError:
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                await sensor_ws_manager.send_json(websocket, sensor_ws_manager.health_payload())
                logger.info("WS sent health")
                continue

            if isinstance(message, dict) and message.get("type") == "ping":
                await sensor_ws_manager.send_json(
                    websocket,
                    {
                        "type": "pong",
                        "client_time": message.get("client_time"),
                        "server_time": sensor_ws_manager.health_payload()["server_time"],
                    },
                )
    except WebSocketDisconnect as exc:
        logger.warning(
            "WS disconnected path=/api/v1/ws/sensors/latest client=%s code=%s reason=%s",
            client_host,
            getattr(exc, "code", None),
            getattr(exc, "reason", ""),
        )
    except Exception as exc:  # pragma: no cover - defensive websocket guard
        logger.warning(
            "WS error path=/api/v1/ws/sensors/latest client=%s error=%s",
            client_host,
            exc,
        )
    finally:
        await sensor_ws_manager.disconnect(websocket)
