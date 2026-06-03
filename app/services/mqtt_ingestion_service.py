from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import queue
import threading

import paho.mqtt.client as mqtt

from app.core.config import Settings
from app.schemas.mqtt import MqttRawPayload
from app.services.sensor_pipeline_service import SensorPipelineService


logger = logging.getLogger(__name__)


class AsyncMqttIngestionService:
    def __init__(
        self,
        *,
        settings: Settings,
        pipeline_service: SensorPipelineService,
    ) -> None:
        self.settings = settings
        self.pipeline_service = pipeline_service

        self._queue: queue.Queue[MqttRawPayload | None] = queue.Queue(maxsize=settings.mqtt_queue_size)
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        self._device_timestamp_cache: dict[str, int] = {}
        self._connected = False
        self._subscribed_topics: list[str] = []
        self._last_error: str | None = None
        self._last_message_at: str | None = None
        self._last_processed_at: str | None = None
        self._received_messages = 0
        self._queued_payloads = 0
        self._processed_payloads = 0
        self._saved_readings = 0
        self._dropped_payloads = 0

        self.client = mqtt.Client(client_id=settings.mqtt_client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        if settings.mqtt_ca_cert:
            ca_cert_path = Path(settings.mqtt_ca_cert)
            if not ca_cert_path.exists():
                raise FileNotFoundError(f"MQTT_CA_CERT does not exist: {settings.mqtt_ca_cert}")
            self.client.tls_set(ca_certs=settings.mqtt_ca_cert)
            self.client.tls_insecure_set(True)

        if settings.mqtt_username and settings.mqtt_password:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.settings.mqtt_enabled,
            "connected": self._connected,
            "broker": self.settings.mqtt_broker,
            "port": self.settings.mqtt_port,
            "client_id": self.settings.mqtt_client_id,
            "auth_configured": bool(self.settings.mqtt_username and self.settings.mqtt_password),
            "ca_cert": self.settings.mqtt_ca_cert,
            "subscribed_topics": self._subscribed_topics,
            "queue_size": self._queue.qsize(),
            "queue_max_size": self.settings.mqtt_queue_size,
            "received_messages": self._received_messages,
            "queued_payloads": self._queued_payloads,
            "processed_payloads": self._processed_payloads,
            "saved_readings": self._saved_readings,
            "dropped_payloads": self._dropped_payloads,
            "last_message_at": self._last_message_at,
            "last_processed_at": self._last_processed_at,
            "last_error": self._last_error,
        }

    async def start(self) -> None:
        if not self.settings.mqtt_enabled:
            logger.info("MQTT ingestion disabled by MQTT_ENABLED=false")
            return

        logger.info(
            "Connecting MQTT broker %s:%s topic=%s auth=%s ca_cert=%s",
            self.settings.mqtt_broker,
            self.settings.mqtt_port,
            self.settings.mqtt_sensor_topic,
            bool(self.settings.mqtt_username and self.settings.mqtt_password),
            self.settings.mqtt_ca_cert,
        )

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker,
            name="mqtt-db-worker",
            daemon=True,
        )
        self._worker_thread.start()

        self.client.connect_async(
            host=self.settings.mqtt_broker,
            port=self.settings.mqtt_port,
            keepalive=self.settings.mqtt_keepalive,
        )
        self.client.loop_start()

    async def stop(self) -> None:
        self._stop_event.set()

        self.client.disconnect()
        self.client.loop_stop()

        if self._worker_thread is not None:
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass
            await asyncio.to_thread(self._worker_thread.join, 5)
            self._worker_thread = None

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: dict,
        rc: int,
        properties: object | None = None,
    ) -> None:
        _ = (client, userdata, flags, properties)

        rc_value = self._reason_code_value(rc)
        if rc_value != 0:
            self._connected = False
            self._last_error = f"MQTT connection failed with code {rc_value}"
            logger.error("%s", self._last_error)
            return

        self._connected = True
        self._last_error = None

        topics: list[tuple[str, int]] = [
            (self.settings.mqtt_sensor_topic, self.settings.mqtt_qos),
            (self.settings.mqtt_timestamp_topic, self.settings.mqtt_qos),
        ]
        if self.settings.mqtt_timestamp_topic_legacy:
            topics.append((self.settings.mqtt_timestamp_topic_legacy, self.settings.mqtt_qos))
        if self.settings.mqtt_legacy_topic:
            topics.append((self.settings.mqtt_legacy_topic, self.settings.mqtt_qos))

        self.client.subscribe(topics)
        self._subscribed_topics = [topic for topic, _ in topics]
        logger.info("Subscribed MQTT topics: %s", ", ".join(self._subscribed_topics))

    def _on_message(self, client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        _ = (client, userdata)

        try:
            self._received_messages += 1
            self._last_message_at = self._utc_now()
            payload_text = msg.payload.decode("utf-8")
            raw_payload = json.loads(payload_text)

            if not isinstance(raw_payload, dict):
                self._last_error = "Skipping MQTT message: payload is not a JSON object"
                logger.warning("%s", self._last_error)
                return

            topic = msg.topic
            is_timestamp_topic = topic == self.settings.mqtt_timestamp_topic
            if self.settings.mqtt_timestamp_topic_legacy:
                is_timestamp_topic = is_timestamp_topic or topic == self.settings.mqtt_timestamp_topic_legacy

            if is_timestamp_topic:
                self._cache_device_timestamp(raw_payload)
                return

            self._merge_cached_timestamp(raw_payload)
            parsed = MqttRawPayload.model_validate(raw_payload)
            self._enqueue_payload_threadsafe(parsed)
        except json.JSONDecodeError:
            self._last_error = "Skipping MQTT message: invalid JSON"
            logger.warning("%s", self._last_error)
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception("Failed to parse MQTT message: %s", exc)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        rc: int,
        properties: object | None = None,
    ) -> None:
        _ = (client, userdata, properties)
        self._connected = False
        rc_value = self._reason_code_value(rc)
        if rc_value != 0:
            self._last_error = f"MQTT disconnected unexpectedly with code {rc_value}"
            logger.warning("%s", self._last_error)
        else:
            logger.info("MQTT disconnected cleanly")

    def _cache_device_timestamp(self, raw_payload: dict[str, object]) -> None:
        device_id = raw_payload.get("device_id") or raw_payload.get("devid")
        timestamp = raw_payload.get("timestamp_ms", raw_payload.get("timestamp"))
        if device_id is None or timestamp is None:
            return

        try:
            parsed_timestamp = int(float(str(timestamp)))
            # Accept both unix seconds and milliseconds from devices.
            if parsed_timestamp < 1_000_000_000_000:
                parsed_timestamp *= 1000
            self._device_timestamp_cache[str(device_id)] = parsed_timestamp
        except ValueError:
            logger.warning("Invalid cached timestamp for device=%s", device_id)

    def _merge_cached_timestamp(self, raw_payload: dict[str, object]) -> None:
        if "timestamp_ms" in raw_payload or "timestamp" in raw_payload:
            return

        device_id = raw_payload.get("device_id") or raw_payload.get("devid")
        if device_id is None:
            return

        cached = self._device_timestamp_cache.get(str(device_id))
        if cached is not None:
            raw_payload["timestamp_ms"] = cached

    def _enqueue_payload_threadsafe(self, payload: MqttRawPayload) -> None:
        if self._stop_event.is_set():
            return

        try:
            self._queue.put_nowait(payload)
            self._queued_payloads += 1
        except queue.Full:
            self._dropped_payloads += 1
            self._last_error = "Dropping MQTT payload because queue is full"
            logger.warning("Dropping MQTT payload because queue is full")

    def _worker(self) -> None:
        logger.info("MQTT DB worker thread started")
        while not self._stop_event.is_set():
            try:
                payload = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            if payload is None:
                self._queue.task_done()
                break

            try:
                saved = self.pipeline_service.process_payload(payload)
                self._processed_payloads += 1
                self._saved_readings += saved
                self._last_processed_at = self._utc_now()
                logger.info(
                    "Processed MQTT payload | device=%s saved=%s sensors=%s",
                    payload.device_id,
                    saved,
                    len(payload.adc),
                )
            except Exception as exc:
                self._last_error = str(exc)
                logger.exception("MQTT payload processing failed: %s", exc)
            finally:
                self._queue.task_done()

        logger.info("MQTT DB worker thread stopped")

    @staticmethod
    def _reason_code_value(reason_code: object) -> int | object:
        try:
            return int(reason_code)
        except (TypeError, ValueError):
            return reason_code

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
