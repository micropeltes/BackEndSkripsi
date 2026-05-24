from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.converters.registry import SensorConverterRegistry
from app.core.config import Settings
from app.core.dependencies import (
    get_calibration_service,
    get_converter_registry,
    get_settings_dependency,
    get_sensor_reading_service,
)
from app.schemas.sensor import (
    SensorConvertRequest,
    SensorListResponse,
    SensorProcessedResponse,
    SensorReadingRecordResponse,
)
from app.services.calibration_service import CalibrationService
from app.services.sensor_reading_service import SensorReadingService
from app.utils.sensor_types import SensorName


router = APIRouter(prefix="/sensors", tags=["sensors"])


def _round(value: float) -> float:
    return round(value, 6)


def _record_to_processed(record) -> SensorProcessedResponse:
    return SensorProcessedResponse(
        sensor=SensorName(record.sensor),
        adc=record.adc_raw,
        voltage=_round(record.voltage),
        rs=_round(record.rs),
        r0=_round(record.r0),
        ratio=_round(record.ratio),
        ppm=_round(record.ppm),
        unit=record.unit,
    )


def _record_to_full(record) -> SensorReadingRecordResponse:
    return SensorReadingRecordResponse(
        sensor=SensorName(record.sensor),
        adc=record.adc_raw,
        voltage=_round(record.voltage),
        rs=_round(record.rs),
        r0=_round(record.r0),
        ratio=_round(record.ratio),
        ppm=_round(record.ppm),
        unit=record.unit,
        device_id=record.device_id,
        temperature_c=record.temperature_c,
        humidity_pct=record.humidity_pct,
        payload_timestamp_ms=record.payload_timestamp_ms,
        received_timestamp_ms=record.received_timestamp_ms,
        created_at=record.created_at,
    )


@router.get("/supported")
def get_supported_sensors(
    registry: SensorConverterRegistry = Depends(get_converter_registry),
) -> dict[str, list[str]]:
    return {"sensors": [sensor.value for sensor in registry.list_supported()]}


@router.get("/{sensor}/latest", response_model=SensorProcessedResponse)
def get_latest_sensor_data(
    sensor: SensorName,
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    reading_service: SensorReadingService = Depends(get_sensor_reading_service),
) -> SensorProcessedResponse:
    record = reading_service.get_latest(sensor=sensor, device_id=device_id)
    return _record_to_processed(record)


@router.get("/latest", response_model=SensorListResponse)
def list_latest_sensor_data(
    limit: int = Query(default=20, ge=1, le=500),
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    sensor: SensorName | None = None,
    reading_service: SensorReadingService = Depends(get_sensor_reading_service),
) -> SensorListResponse:
    records = reading_service.list_latest(limit=limit, device_id=device_id, sensor=sensor)
    items = [_record_to_full(record) for record in records]
    return SensorListResponse(count=len(items), items=items)


@router.post("/convert", response_model=SensorProcessedResponse)
def convert_on_demand(
    payload: SensorConvertRequest,
    settings: Settings = Depends(get_settings_dependency),
    registry: SensorConverterRegistry = Depends(get_converter_registry),
    calibration_service: CalibrationService = Depends(get_calibration_service),
) -> SensorProcessedResponse:
    converter = registry.get(payload.sensor)
    calibration = calibration_service.get_effective_profile(
        sensor=payload.sensor,
        device_id=payload.device_id,
    )

    result = converter.convert(
        adc=payload.adc,
        adc_filtered=float(payload.adc),
        calibration=calibration,
        ads1115_lsb=settings.ads1115_lsb,
        adc_min=settings.ads1115_min_adc,
        adc_max=settings.ads1115_max_adc,
        temperature_c=payload.temperature_c,
        humidity_pct=payload.humidity_pct,
    )

    return SensorProcessedResponse(
        sensor=result.sensor,
        adc=result.adc,
        voltage=_round(result.voltage),
        rs=_round(result.rs),
        r0=_round(result.r0),
        ratio=_round(result.ratio),
        ppm=_round(result.ppm),
        unit=result.unit,
    )
