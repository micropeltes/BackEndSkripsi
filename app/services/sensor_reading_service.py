from __future__ import annotations

from sqlalchemy.orm import Session

from app.converters.base import ConversionResult
from app.models import SensorReading
from app.schemas.mqtt import RawSensorSample
from app.utils.errors import NotFoundError
from app.utils.sensor_types import SensorName


class SensorReadingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def persist(self, *, sample: RawSensorSample, result: ConversionResult) -> SensorReading:
        reading = SensorReading(
            device_id=sample.device_id,
            sensor=sample.sensor.value,
            adc_raw=result.adc,
            adc_filtered=result.adc_filtered,
            voltage=result.voltage,
            rs=result.rs,
            r0=result.r0,
            ratio=result.ratio,
            ppm=result.ppm,
            unit=result.unit,
            temperature_c=sample.temperature_c,
            humidity_pct=sample.humidity_pct,
            payload_timestamp_ms=sample.payload_timestamp_ms,
            received_timestamp_ms=sample.received_timestamp_ms,
        )
        self.db.add(reading)
        return reading

    def get_latest(self, *, sensor: SensorName, device_id: str | None = None) -> SensorReading:
        query = self.db.query(SensorReading).filter(SensorReading.sensor == sensor.value)
        if device_id:
            query = query.filter(SensorReading.device_id == device_id)

        reading = (
            query.order_by(SensorReading.created_at.desc(), SensorReading.id.desc())
            .limit(1)
            .first()
        )
        if reading is None:
            if device_id:
                raise NotFoundError(
                    f"No reading found for sensor '{sensor.value}' and device '{device_id}'."
                )
            raise NotFoundError(f"No reading found for sensor '{sensor.value}'.")
        return reading

    def list_latest(
        self,
        *,
        limit: int,
        device_id: str | None = None,
        sensor: SensorName | None = None,
    ) -> list[SensorReading]:
        query = self.db.query(SensorReading)
        if device_id:
            query = query.filter(SensorReading.device_id == device_id)
        if sensor:
            query = query.filter(SensorReading.sensor == sensor.value)

        return (
            query.order_by(SensorReading.created_at.desc(), SensorReading.id.desc())
            .limit(limit)
            .all()
        )
