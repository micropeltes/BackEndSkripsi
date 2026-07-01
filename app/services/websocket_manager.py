from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketState


logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.discard(websocket)

    async def send_json(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        if websocket.application_state != WebSocketState.CONNECTED:
            await self.disconnect(websocket)
            return

        await websocket.send_json(jsonable_encoder(payload))

    async def broadcast_json(self, payload: dict[str, Any]) -> None:
        encoded = jsonable_encoder(payload)
        async with self._lock:
            connections = list(self.active_connections)

        stale_connections: list[WebSocket] = []
        for websocket in connections:
            try:
                if websocket.application_state == WebSocketState.CONNECTED:
                    await websocket.send_json(encoded)
                else:
                    stale_connections.append(websocket)
            except Exception as exc:  # pragma: no cover - defensive websocket guard
                logger.warning("WebSocket broadcast failed: %s", exc)
                stale_connections.append(websocket)

        for websocket in stale_connections:
            await self.disconnect(websocket)

    def broadcast_json_threadsafe(self, payload: dict[str, Any]) -> None:
        if self._loop is None or self._loop.is_closed():
            return

        future = asyncio.run_coroutine_threadsafe(self.broadcast_json(payload), self._loop)
        future.add_done_callback(self._log_future_error)

    @staticmethod
    def health_payload() -> dict[str, str]:
        return {
            "type": "health",
            "status": "connected",
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _log_future_error(future: asyncio.Future) -> None:
        try:
            future.result()
        except Exception as exc:  # pragma: no cover - defensive callback guard
            logger.warning("WebSocket background broadcast failed: %s", exc)


sensor_ws_manager = WebSocketConnectionManager()
