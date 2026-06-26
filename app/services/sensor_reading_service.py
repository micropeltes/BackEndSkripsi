from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.converters.base import ConversionResult
from app.database import run_read_with_db_retry
from app.models import SensorReading
from app.schemas.mqtt import RawSensorSample
from app.utils.errors import NotFoundError
from app.utils.sensor_types import SensorName


@dataclass
class SensorSnapshot:
    id: int
    device_id: str
    created_at: datetime
    received_timestamp_ms: int
    payload_timestamp_ms: int | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    nh3_mics: float | None = None
    nh3_mems: float | None = None
    h2s: float | None = None
    no2: float | None = None
    co: float | None = None
    mq135: float | None = None


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

    def get_latest_row(self, *, device_id: str | None = None) -> SensorSnapshot:
        rows = self.get_latest_rows(limit=1, device_id=device_id)
        return rows[0]

    def get_latest_rows(
        self,
        *,
        limit: int,
        device_id: str | None = None,
    ) -> list[SensorSnapshot]:
        return self._get_grouped_rows(
            limit=limit,
            device_id=device_id,
            operation_name="fetch latest sensor readings",
        )

    def get_rows_by_created_at_range(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        limit: int,
        device_id: str | None = None,
    ) -> list[SensorSnapshot]:
        return self._get_grouped_rows(
            limit=limit,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            operation_name="fetch sensor readings by created_at range",
        )

    def _get_grouped_rows(
        self,
        *,
        limit: int,
        device_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        operation_name: str,
    ) -> list[SensorSnapshot]:
        recent_groups_query = self.db.query(
            SensorReading.device_id.label("device_id"),
            SensorReading.received_timestamp_ms.label("received_timestamp_ms"),
            func.max(SensorReading.id).label("max_id"),
        )
        if device_id:
            recent_groups_query = recent_groups_query.filter(
                SensorReading.device_id == device_id
            )
        if start_time is not None:
            recent_groups_query = recent_groups_query.filter(
                SensorReading.created_at >= start_time
            )
        if end_time is not None:
            recent_groups_query = recent_groups_query.filter(
                SensorReading.created_at <= end_time
            )

        recent_groups = (
            recent_groups_query.group_by(
                SensorReading.device_id,
                SensorReading.received_timestamp_ms,
            )
            .order_by(
                SensorReading.received_timestamp_ms.desc(),
                func.max(SensorReading.id).desc(),
            )
            .limit(limit)
            .subquery()
        )

        def fetch_rows() -> list[SensorReading]:
            return (
                self.db.query(SensorReading)
                .join(
                    recent_groups,
                    and_(
                        SensorReading.device_id == recent_groups.c.device_id,
                        SensorReading.received_timestamp_ms
                        == recent_groups.c.received_timestamp_ms,
                    ),
                )
                .order_by(
                    SensorReading.received_timestamp_ms.desc(),
                    SensorReading.id.desc(),
                )
                .all()
            )

        rows = run_read_with_db_retry(
            self.db,
            fetch_rows,
            operation_name=operation_name,
        )

        snapshots = self._build_snapshots(rows=rows, limit=limit)
        if not snapshots:
            if device_id:
                raise NotFoundError(f"No readings found for device '{device_id}'.")
            raise NotFoundError("No readings found.")

        return snapshots

    def get_adc_by_sensor(
        self,
        *,
        row: SensorSnapshot,
        sensor: SensorName,
    ) -> int:
        sensor_map: dict[SensorName, float | None] = {
            SensorName.MQ135: row.mq135,
            # MICS6814 has multiple channels in wide schema. We use NH3 channel
            # as the primary value for generic "mics6814" endpoint.
            SensorName.NH3_MICS: row.nh3_mics,
            SensorName.CO: row.co,
            SensorName.NO2: row.no2,            
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

    def get_all_sensor_adc(self, *, row: SensorSnapshot) -> dict[SensorName, int]:
        return {
            sensor: self.get_adc_by_sensor(row=row, sensor=sensor)
            for sensor in SensorName
        }

    def _build_snapshots(
        self,
        *,
        rows: list[SensorReading],
        limit: int,
    ) -> list[SensorSnapshot]:
        snapshots: list[SensorSnapshot] = []
        grouped: dict[tuple[str, int], SensorSnapshot] = {}
        sensor_field_map: dict[str, str] = {
            SensorName.MQ135.value: "mq135",
            SensorName.NH3_MICS.value: "nh3_mics",
            SensorName.CO.value: "co",
            SensorName.NO2.value: "no2",
            SensorName.FERMION_NH3.value: "nh3_mems",
            SensorName.FERMION_H2S.value: "h2s",
        }

        for reading in rows:
            group_key = (
                reading.device_id,
                reading.received_timestamp_ms,
            )
            snapshot = grouped.get(group_key)
            if snapshot is None:
                if len(snapshots) >= limit:
                    continue

                snapshot = SensorSnapshot(
                    id=reading.id,
                    device_id=reading.device_id,
                    created_at=reading.created_at,
                    received_timestamp_ms=reading.received_timestamp_ms,
                    payload_timestamp_ms=reading.payload_timestamp_ms,
                    temperature_c=reading.temperature_c,
                    humidity_pct=reading.humidity_pct,
                )
                grouped[group_key] = snapshot
                snapshots.append(snapshot)
            else:
                if reading.id > snapshot.id:
                    snapshot.id = reading.id
                if reading.created_at > snapshot.created_at:
                    snapshot.created_at = reading.created_at
                if snapshot.payload_timestamp_ms is None and reading.payload_timestamp_ms is not None:
                    snapshot.payload_timestamp_ms = reading.payload_timestamp_ms
                if snapshot.temperature_c is None and reading.temperature_c is not None:
                    snapshot.temperature_c = reading.temperature_c
                if snapshot.humidity_pct is None and reading.humidity_pct is not None:
                    snapshot.humidity_pct = reading.humidity_pct

            target_field = sensor_field_map.get(reading.sensor)
            if target_field is not None:
                setattr(snapshot, target_field, float(reading.adc_raw))

        return snapshots
