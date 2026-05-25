from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query

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
    SensorDataListResponse,
    SensorDataRecordResponse,
    SensorListResponse,
    SensorProcessedResponse,
    SensorReadingRecordResponse,
)
from app.services.calibration_service import CalibrationService
from app.services.sensor_reading_service import SensorReadingService
from app.utils.errors import NotFoundError
from app.utils.sensor_types import SensorName


router = APIRouter(prefix="/sensors", tags=["sensors"])


def _round(value: float) -> float:
    return round(value, 6)


def _convert_adc_to_processed(
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
        voltage=_round(result.voltage),
        rs=_round(result.rs),
        r0=_round(result.r0),
        ratio=_round(result.ratio),
        ppm=_round(result.ppm),
        unit=result.unit,
        created_at=created_at,
    )


def _processed_to_record(
    *,
    processed: SensorProcessedResponse,
    device_id: str,
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
        device_id=device_id,
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
    settings: Settings = Depends(get_settings_dependency),
    registry: SensorConverterRegistry = Depends(get_converter_registry),
    calibration_service: CalibrationService = Depends(get_calibration_service),
) -> SensorProcessedResponse:
    row = reading_service.get_latest_row(device_id=device_id)
    adc = reading_service.get_adc_by_sensor(row=row, sensor=sensor)
    return _convert_adc_to_processed(
        sensor=sensor,
        adc=adc,
        device_id=row.device_id,
        created_at=row.created_at,
        settings=settings,
        registry=registry,
        calibration_service=calibration_service,
    )


@router.get("/latest", response_model=SensorListResponse)
def list_latest_sensor_data(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    sensor: SensorName | None = None,
    reading_service: SensorReadingService = Depends(get_sensor_reading_service),
    settings: Settings = Depends(get_settings_dependency),
    registry: SensorConverterRegistry = Depends(get_converter_registry),
    calibration_service: CalibrationService = Depends(get_calibration_service),
) -> SensorListResponse:
    row = reading_service.get_latest_row(device_id=device_id)

    sensors = [sensor] if sensor is not None else registry.list_supported()
    items: list[SensorReadingRecordResponse] = []

    for sensor_name in sensors:
        try:
            adc = reading_service.get_adc_by_sensor(row=row, sensor=sensor_name)
        except NotFoundError:
            continue

        processed = _convert_adc_to_processed(
            sensor=sensor_name,
            adc=adc,
            device_id=row.device_id,
            created_at=row.created_at,
            settings=settings,
            registry=registry,
            calibration_service=calibration_service,
        )
        items.append(_processed_to_record(processed=processed, device_id=row.device_id))

    if not items:
        raise NotFoundError(
            f"No sensor values found in latest row for device '{row.device_id}'."
        )

    return SensorListResponse(count=len(items), items=items)


@router.get("/latest/{limit}", response_model=SensorDataListResponse)
def list_latest_sensor_rows(
    limit: int = Path(ge=1, le=1000),
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    reading_service: SensorReadingService = Depends(get_sensor_reading_service),
) -> SensorDataListResponse:
    rows = reading_service.get_latest_rows(limit=limit, device_id=device_id)
    items = [
        SensorDataRecordResponse(
            id=row.id,
            device_id=row.device_id,
            nh3_mics=row.nh3_mics,
            nh3_mems=row.nh3_mems,
            h2s=row.h2s,
            no2=row.no2,
            co=row.co,
            mq135=row.mq135,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return SensorDataListResponse(count=len(items), items=items)


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
