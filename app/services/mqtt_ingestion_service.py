from __future__ import annotations

import asyncio
import json
import logging

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

        self._queue: asyncio.Queue[MqttRawPayload] = asyncio.Queue(maxsize=settings.mqtt_queue_size)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._worker_task: asyncio.Task[None] | None = None

        self._device_timestamp_cache: dict[str, int] = {}

        self.client = mqtt.Client(client_id=settings.mqtt_client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        if settings.mqtt_ca_cert:
            self.client.tls_set(ca_certs=settings.mqtt_ca_cert)
            self.client.tls_insecure_set(True)

        if settings.mqtt_username and settings.mqtt_password:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    async def start(self) -> None:
        if not self.settings.mqtt_enabled:
            logger.info("MQTT ingestion disabled by MQTT_ENABLED=false")
            return

        self._loop = asyncio.get_running_loop()

        logger.info(
            "Connecting MQTT broker %s:%s topic=%s",
            self.settings.mqtt_broker,
            self.settings.mqtt_port,
            self.settings.mqtt_sensor_topic,
        )

        self.client.connect(
            host=self.settings.mqtt_broker,
            port=self.settings.mqtt_port,
            keepalive=self.settings.mqtt_keepalive,
        )
        self.client.loop_start()

        self._worker_task = asyncio.create_task(self._worker(), name="mqtt-ingestion-worker")

    async def stop(self) -> None:
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: dict,
        rc: int,
        properties: object | None = None,
    ) -> None:
        _ = (client, userdata, flags, properties)

        rc_value = int(rc) if isinstance(rc, int) else rc
        if rc_value != 0:
            logger.error("MQTT connection failed with code %s", rc_value)
            return

        topics: list[tuple[str, int]] = [
            (self.settings.mqtt_sensor_topic, self.settings.mqtt_qos),
            (self.settings.mqtt_timestamp_topic, self.settings.mqtt_qos),
        ]
        if self.settings.mqtt_timestamp_topic_legacy:
            topics.append((self.settings.mqtt_timestamp_topic_legacy, self.settings.mqtt_qos))
        if self.settings.mqtt_legacy_topic:
            topics.append((self.settings.mqtt_legacy_topic, self.settings.mqtt_qos))

        self.client.subscribe(topics)
        logger.info("Subscribed MQTT topics: %s", ", ".join(topic for topic, _ in topics))

    def _on_message(self, client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        _ = (client, userdata)

        try:
            payload_text = msg.payload.decode("utf-8")
            raw_payload = json.loads(payload_text)

            if not isinstance(raw_payload, dict):
                logger.warning("Skipping MQTT message: payload is not a JSON object")
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
            logger.warning("Skipping MQTT message: invalid JSON")
        except Exception as exc:
            logger.exception("Failed to parse MQTT message: %s", exc)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        rc: int,
        properties: object | None = None,
    ) -> None:
        _ = (client, userdata, properties)
        rc_value = int(rc) if isinstance(rc, int) else rc
        if rc_value != 0:
            logger.warning("MQTT disconnected unexpectedly with code %s", rc_value)
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
        if self._loop is None:
            logger.warning("Ignoring MQTT payload because event loop is not ready")
            return

        def _enqueue() -> None:
            if self._queue.full():
                logger.warning("Dropping MQTT payload because queue is full")
                return
            self._queue.put_nowait(payload)

        self._loop.call_soon_threadsafe(_enqueue)

    async def _worker(self) -> None:
        while True:
            payload = await self._queue.get()
            try:
                saved = await self.pipeline_service.process_payload(payload)
                logger.info(
                    "Processed MQTT payload | device=%s saved=%s sensors=%s",
                    payload.device_id,
                    saved,
                    len(payload.adc),
                )
            except Exception as exc:
                logger.exception("MQTT payload processing failed: %s", exc)
            finally:
                self._queue.task_done()
