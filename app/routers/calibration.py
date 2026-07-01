from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_calibration_service
from app.core.security import require_api_key
from app.schemas.calibration import CalibrationResponse, CalibrationUpsertRequest
from app.services.calibration_service import CalibrationService
from app.utils.sensor_types import RatioMode, SensorName


router = APIRouter(prefix="/calibrations", tags=["calibrations"])


@router.put("/{sensor}", response_model=CalibrationResponse)
def upsert_calibration(
    sensor: SensorName,
    payload: CalibrationUpsertRequest,
    _: None = Depends(require_api_key),
    service: CalibrationService = Depends(get_calibration_service),
) -> CalibrationResponse:
    calibration = service.upsert(sensor=sensor, payload=payload)
    ratio_mode = RatioMode(calibration.ratio_mode) if calibration.ratio_mode else None

    return CalibrationResponse(
        sensor=sensor,
        device_id=calibration.device_id,
        r0=calibration.r0,
        rl_ohm=calibration.rl_ohm,
        vcc=calibration.vcc,
        ratio_mode=ratio_mode,
    )


@router.get("/{sensor}", response_model=CalibrationResponse)
def get_calibration(
    sensor: SensorName,
    device_id: str = Query(min_length=1, max_length=64),
    service: CalibrationService = Depends(get_calibration_service),
) -> CalibrationResponse:
    calibration = service.get_by_sensor_and_device(sensor=sensor, device_id=device_id)
    ratio_mode = RatioMode(calibration.ratio_mode) if calibration.ratio_mode else None

    return CalibrationResponse(
        sensor=sensor,
        device_id=calibration.device_id,
        r0=calibration.r0,
        rl_ohm=calibration.rl_ohm,
        vcc=calibration.vcc,
        ratio_mode=ratio_mode,
    )
