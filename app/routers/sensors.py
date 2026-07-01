from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query

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
    SensorHistoricalProcessedItem,
    SensorHistoricalProcessedResponse,
    SensorHistoricalProcessedSensorData,
    SensorListResponse,
    SensorProcessedResponse,
    SensorReadingRecordResponse,
)
from app.services.calibration_service import CalibrationService
from app.services.sensor_payload_service import build_latest_sensor_payload
from app.services.sensor_reading_service import SensorReadingService, SensorSnapshot
from app.utils.errors import NotFoundError, ValidationError
from app.utils.sensor_types import SensorName


router = APIRouter(prefix="/sensors", tags=["sensors"])


def _round(value: float) -> float:
    return round(value, 6)


def _normalize_device_id(device_id: str | None) -> str | None:
    if device_id is None:
        return None

    normalized = device_id.strip()
    return normalized or None


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


def _build_historical_processed_response(
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
        sensors_data: dict[
            str,
            SensorHistoricalProcessedSensorData,
        ] = {}

        for sensor_name in supported_sensors:
            try:
                adc = reading_service.get_adc_by_sensor(
                    row=row,
                    sensor=sensor_name,
                )

                processed = _convert_adc_to_processed(
                    sensor=sensor_name,
                    adc=adc,
                    device_id=row.device_id,
                    created_at=row.created_at,
                    settings=settings,
                    registry=registry,
                    calibration_service=calibration_service,
                )

                sensors_data[sensor_name.value] = (
                    SensorHistoricalProcessedSensorData(
                        adc=processed.adc,
                        voltage=processed.voltage,
                        rs=processed.rs,
                        r0=processed.r0,
                        ratio=processed.ratio,
                        ppm=processed.ppm,
                        unit=processed.unit,
                    )
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

    return SensorHistoricalProcessedResponse(
        count=len(items),
        items=items,
    )


@router.get("/supported")
def get_supported_sensors(
    registry: SensorConverterRegistry = Depends(get_converter_registry),
) -> dict[str, list[str]]:
    return {
        "sensors": [
            sensor.value for sensor in registry.list_supported()
        ]
    }


@router.get(
    "/{sensor}/latest",
    response_model=SensorProcessedResponse,
)
def get_latest_sensor_data(
    sensor: SensorName,
    device_id: str | None = Query(
        default=None,
        max_length=64,
    ),
    reading_service: SensorReadingService = Depends(
        get_sensor_reading_service
    ),
    settings: Settings = Depends(
        get_settings_dependency
    ),
    registry: SensorConverterRegistry = Depends(
        get_converter_registry
    ),
    calibration_service: CalibrationService = Depends(
        get_calibration_service
    ),
) -> SensorProcessedResponse:
    device_id = _normalize_device_id(device_id)
    row = reading_service.get_latest_row(
        device_id=device_id
    )

    adc = reading_service.get_adc_by_sensor(
        row=row,
        sensor=sensor,
    )

    return _convert_adc_to_processed(
        sensor=sensor,
        adc=adc,
        device_id=row.device_id,
        created_at=row.created_at,
        settings=settings,
        registry=registry,
        calibration_service=calibration_service,
    )


@router.get(
    "/latest",
    response_model=SensorListResponse,
)
def list_latest_sensor_data(
    device_id: str | None = Query(
        default=None,
        max_length=64,
    ),
    sensor: SensorName | None = None,
    reading_service: SensorReadingService = Depends(
        get_sensor_reading_service
    ),
    settings: Settings = Depends(
        get_settings_dependency
    ),
    registry: SensorConverterRegistry = Depends(
        get_converter_registry
    ),
    calibration_service: CalibrationService = Depends(
        get_calibration_service
    ),
) -> SensorListResponse:
    device_id = _normalize_device_id(device_id)
    row = reading_service.get_latest_row(
        device_id=device_id
    )

    sensors = (
        [sensor]
        if sensor is not None
        else registry.list_supported()
    )

    items: list[SensorReadingRecordResponse] = []

    for sensor_name in sensors:
        try:
            adc = reading_service.get_adc_by_sensor(
                row=row,
                sensor=sensor_name,
            )
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

        items.append(
            _processed_to_record(
                processed=processed,
                row=row,
            )
        )

    if not items:
        raise NotFoundError(
            f"No sensor values found in latest row "
            f"for device '{row.device_id}'."
        )

    return SensorListResponse(
        count=len(items),
        items=items,
    )


@router.get(
    "/latest/{limit}",
    response_model=SensorHistoricalProcessedResponse,
)
def list_latest_sensor_rows(
    limit: int = Path(
        ge=1,
        le=1000,
    ),
    device_id: str | None = Query(
        default=None,
        max_length=64,
    ),
    reading_service: SensorReadingService = Depends(
        get_sensor_reading_service
    ),
    settings: Settings = Depends(
        get_settings_dependency
    ),
    registry: SensorConverterRegistry = Depends(
        get_converter_registry
    ),
    calibration_service: CalibrationService = Depends(
        get_calibration_service
    ),
) -> SensorHistoricalProcessedResponse:
    device_id = _normalize_device_id(device_id)
    return build_latest_sensor_payload(
        limit=limit,
        device_id=device_id,
        settings=settings,
        registry=registry,
        calibration_service=calibration_service,
        reading_service=reading_service,
    )


@router.get(
    "/history",
    response_model=SensorHistoricalProcessedResponse,
)
def list_sensor_history_by_time(
    start_time: datetime = Query(
        description="Inclusive start timestamp in ISO 8601 format.",
    ),
    end_time: datetime = Query(
        description="Inclusive end timestamp in ISO 8601 format.",
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=1000,
    ),
    device_id: str | None = Query(
        default=None,
        max_length=64,
    ),
    reading_service: SensorReadingService = Depends(
        get_sensor_reading_service
    ),
    settings: Settings = Depends(
        get_settings_dependency
    ),
    registry: SensorConverterRegistry = Depends(
        get_converter_registry
    ),
    calibration_service: CalibrationService = Depends(
        get_calibration_service
    ),
) -> SensorHistoricalProcessedResponse:
    device_id = _normalize_device_id(device_id)
    if end_time < start_time:
        raise HTTPException(
            status_code=422,
            detail="end_time must be greater than or equal to start_time.",
        )

    try:
        rows = reading_service.get_rows_by_created_at_range(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            device_id=device_id,
        )
    except NotFoundError:
        return SensorHistoricalProcessedResponse(count=0, items=[])

    return _build_historical_processed_response(
        rows=rows,
        settings=settings,
        registry=registry,
        calibration_service=calibration_service,
        reading_service=reading_service,
    )


@router.get(
    "/latest/{limit}/unprocessed",
    response_model=SensorDataListResponse,
)
def list_latest_sensor_rows_unprocessed(
    limit: int = Path(
        ge=1,
        le=1000,
    ),
    device_id: str | None = Query(
        default=None,
        max_length=64,
    ),
    reading_service: SensorReadingService = Depends(
        get_sensor_reading_service
    ),
) -> SensorDataListResponse:
    device_id = _normalize_device_id(device_id)
    try:
        rows = reading_service.get_latest_rows(
            limit=limit,
            device_id=device_id,
        )
    except NotFoundError:
        return SensorDataListResponse(count=0, items=[])

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

    return SensorDataListResponse(
        count=len(items),
        items=items,
    )


@router.post(
    "/convert",
    response_model=SensorProcessedResponse,
)
def convert_on_demand(
    payload: SensorConvertRequest,
    settings: Settings = Depends(
        get_settings_dependency
    ),
    registry: SensorConverterRegistry = Depends(
        get_converter_registry
    ),
    calibration_service: CalibrationService = Depends(
        get_calibration_service
    ),
) -> SensorProcessedResponse:
    converter = registry.get(
        payload.sensor
    )

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
