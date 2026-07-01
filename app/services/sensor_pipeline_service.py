from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.converters.registry import SensorConverterRegistry
from app.core.config import Settings
from app.models import ErrorLog
from app.schemas.mqtt import MqttErrorPayload, MqttRawPayload
from app.services.calibration_service import CalibrationService
from app.services.conversion_service import ConversionService
from app.services.raw_acquisition_service import RawAcquisitionService
from app.services.sensor_payload_service import build_latest_sensor_payload
from app.services.sensor_reading_service import SensorReadingService
from app.services.websocket_manager import sensor_ws_manager
from app.utils.errors import AppError
from app.utils.filters import RollingAverageFilter
from app.utils.time_utils import now_ms


logger = logging.getLogger(__name__)


class SensorPipelineService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: Callable[[], Session],
        registry: SensorConverterRegistry,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.registry = registry
        self.raw_service = RawAcquisitionService()
        self.rolling_filter = RollingAverageFilter(window_size=settings.filter_window_size)

    def process_payload(self, payload: MqttRawPayload) -> int:
        received_timestamp_ms = now_ms()
        samples = self.raw_service.explode_payload(
            payload=payload,
            received_timestamp_ms=received_timestamp_ms,
        )

        saved_count = 0
        with self.session_factory() as db:
            calibration_service = CalibrationService(db=db, registry=self.registry)
            conversion_service = ConversionService(
                settings=self.settings,
                registry=self.registry,
                calibration_service=calibration_service,
                rolling_filter=self.rolling_filter,
            )
            reading_service = SensorReadingService(db=db)

            for sample in samples:
                try:
                    result = conversion_service.convert_sample(sample)
                    reading_service.persist(sample=sample, result=result)
                    saved_count += 1
                except AppError as exc:
                    logger.warning(
                        "Skipping sample due to known validation/conversion issue | device=%s sensor=%s reason=%s",
                        sample.device_id,
                        sample.sensor.value,
                        exc,
                    )
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception(
                        "Unexpected processing failure | device=%s sensor=%s reason=%s",
                        sample.device_id,
                        sample.sensor.value,
                        exc,
                    )

            db.commit()

            if saved_count > 0:
                latest_payload = build_latest_sensor_payload(
                    limit=1000,
                    device_id=None,
                    settings=self.settings,
                    registry=self.registry,
                    calibration_service=calibration_service,
                    reading_service=reading_service,
                )
                sensor_ws_manager.broadcast_json_threadsafe(
                    {
                        "type": "update",
                        **latest_payload.model_dump(),
                    }
                )

        return saved_count

    def process_error_payload(self, payload: MqttErrorPayload) -> int:
        with self.session_factory() as db:
            db.add(
                ErrorLog(
                    device_id=payload.device_id,
                    error=payload.error,
                    payload_timestamp_ms=payload.timestamp_ms,
                    received_timestamp_ms=now_ms(),
                )
            )
            db.commit()

        return 1
