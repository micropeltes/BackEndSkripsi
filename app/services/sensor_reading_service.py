from __future__ import annotations

from sqlalchemy.orm import Session

from app.converters.base import ConversionResult
from app.models import SensorData, SensorReading
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

    def get_latest_row(self, *, device_id: str | None = None) -> SensorData:
        query = self.db.query(SensorData)
        if device_id:
            query = query.filter(SensorData.device_id == device_id)

        row = (
            query.order_by(SensorData.created_at.desc(), SensorData.id.desc())
            .limit(1)
            .first()
        )
        if row is None:
            if device_id:
                raise NotFoundError(f"No reading found for device '{device_id}'.")
            raise NotFoundError("No reading found.")
        return row

    def get_latest_rows(
        self,
        *,
        limit: int,
        device_id: str | None = None,
    ) -> list[SensorData]:
        query = self.db.query(SensorData)
        if device_id:
            query = query.filter(SensorData.device_id == device_id)

        rows = (
            query.order_by(SensorData.created_at.desc(), SensorData.id.desc())
            .limit(limit)
            .all()
        )

        if not rows:
            if device_id:
                raise NotFoundError(f"No readings found for device '{device_id}'.")
            raise NotFoundError("No readings found.")

        return rows

    def get_adc_by_sensor(
        self,
        *,
        row: SensorData,
        sensor: SensorName,
    ) -> int:
        sensor_map: dict[SensorName, float | None] = {
            SensorName.MQ135: row.mq135,
            # MICS6814 has multiple channels in wide schema. We use NH3 channel
            # as the primary value for generic "mics6814" endpoint.
            SensorName.MICS6814: row.nh3_mics,
            SensorName.FERMION_NH3: row.nh3_mems,
            SensorName.FERMION_H2S: row.h2s,
        }

        adc_value = sensor_map[sensor]
        if adc_value is None:
            raise NotFoundError(
                f"ADC value for sensor '{sensor.value}' is null in latest row "
                f"(device '{row.device_id}')."
            )

        return int(round(adc_value))

    def get_all_sensor_adc(self, *, row: SensorData) -> dict[SensorName, int]:
        return {
            sensor: self.get_adc_by_sensor(row=row, sensor=sensor)
            for sensor in SensorName
        }
