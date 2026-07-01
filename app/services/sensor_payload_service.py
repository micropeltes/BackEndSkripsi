from __future__ import annotations

from datetime import datetime

from app.converters.registry import SensorConverterRegistry
from app.core.config import Settings
from app.schemas.sensor import (
    SensorHistoricalProcessedItem,
    SensorHistoricalProcessedResponse,
    SensorHistoricalProcessedSensorData,
    SensorProcessedResponse,
    SensorReadingRecordResponse,
)
from app.services.calibration_service import CalibrationService
from app.services.sensor_reading_service import SensorReadingService
from app.utils.errors import NotFoundError
from app.utils.sensor_types import SensorName


def round_sensor_value(value: float) -> float:
    return round(value, 6)


def convert_adc_to_processed(
    *,
    sensor: SensorName,
    adc: int,
    device_id: str,
    created_at: datetime,
    settings: Settings,
    registry: SensorConverterRegistry,
    calibration_service: CalibrationService,
) -> SensorProcessedResponse:
    converter = registry.get(sensor)
    calibration = calibration_service.get_effective_profile(
        sensor=sensor,
        device_id=device_id,
    )
    result = converter.convert(
        adc=adc,
        adc_filtered=float(adc),
        calibration=calibration,
        ads1115_lsb=settings.ads1115_lsb,
        adc_min=settings.ads1115_min_adc,
        adc_max=settings.ads1115_max_adc,
    )

    return SensorProcessedResponse(
        sensor=result.sensor,
        adc=result.adc,
        voltage=round_sensor_value(result.voltage),
        rs=round_sensor_value(result.rs),
        r0=round_sensor_value(result.r0),
        ratio=round_sensor_value(result.ratio),
        ppm=round_sensor_value(result.ppm),
        unit=result.unit,
        created_at=created_at,
    )


def processed_to_record(
    *,
    processed: SensorProcessedResponse,
    row: object,
) -> SensorReadingRecordResponse:
    return SensorReadingRecordResponse(
        sensor=processed.sensor,
        adc=processed.adc,
        voltage=processed.voltage,
        rs=processed.rs,
        r0=processed.r0,
        ratio=processed.ratio,
        ppm=processed.ppm,
        unit=processed.unit,
        created_at=processed.created_at,
        device_id=getattr(row, "device_id"),
        temperature_c=getattr(row, "temperature_c", None),
        humidity_pct=getattr(row, "humidity_pct", None),
        payload_timestamp_ms=getattr(row, "payload_timestamp_ms", None),
        received_timestamp_ms=getattr(row, "received_timestamp_ms", None),
    )


def build_historical_processed_response(
    *,
    rows: list[object],
    settings: Settings,
    registry: SensorConverterRegistry,
    calibration_service: CalibrationService,
    reading_service: SensorReadingService,
) -> SensorHistoricalProcessedResponse:
    items: list[SensorHistoricalProcessedItem] = []
    supported_sensors = registry.list_supported()

    for row in rows:
        sensors_data: dict[str, SensorHistoricalProcessedSensorData] = {}

        for sensor_name in supported_sensors:
            try:
                adc = reading_service.get_adc_by_sensor(
                    row=row,
                    sensor=sensor_name,
                )
                processed = convert_adc_to_processed(
                    sensor=sensor_name,
                    adc=adc,
                    device_id=row.device_id,
                    created_at=row.created_at,
                    settings=settings,
                    registry=registry,
                    calibration_service=calibration_service,
                )
                sensors_data[sensor_name.value] = SensorHistoricalProcessedSensorData(
                    adc=processed.adc,
                    voltage=processed.voltage,
                    rs=processed.rs,
                    r0=processed.r0,
                    ratio=processed.ratio,
                    ppm=processed.ppm,
                    unit=processed.unit,
                )
            except Exception:
                continue

        items.append(
            SensorHistoricalProcessedItem(
                id=row.id,
                device_id=row.device_id,
                created_at=row.created_at,
                sensors=sensors_data,
            )
        )

    return SensorHistoricalProcessedResponse(count=len(items), items=items)


def build_latest_sensor_payload(
    *,
    limit: int,
    device_id: str | None,
    settings: Settings,
    registry: SensorConverterRegistry,
    calibration_service: CalibrationService,
    reading_service: SensorReadingService,
) -> SensorHistoricalProcessedResponse:
    try:
        rows = reading_service.get_latest_rows(
            limit=limit,
            device_id=device_id,
        )
    except NotFoundError:
        return SensorHistoricalProcessedResponse(count=0, items=[])

    return build_historical_processed_response(
        rows=rows,
        settings=settings,
        registry=registry,
        calibration_service=calibration_service,
        reading_service=reading_service,
    )
