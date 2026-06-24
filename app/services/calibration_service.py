from __future__ import annotations

from sqlalchemy.orm import Session

from app.converters.base import CalibrationProfile
from app.converters.registry import SensorConverterRegistry
from app.database import run_read_with_db_retry
from app.models import SensorCalibration
from app.schemas.calibration import CalibrationUpsertRequest
from app.utils.errors import NotFoundError
from app.utils.sensor_types import RatioMode, SensorName


class CalibrationService:
    def __init__(self, db: Session, registry: SensorConverterRegistry) -> None:
        self.db = db
        self.registry = registry

    def get_effective_profile(self, *, sensor: SensorName, device_id: str) -> CalibrationProfile:
        converter = self.registry.get(sensor)

        def fetch_calibration() -> SensorCalibration | None:
            return (
                self.db.query(SensorCalibration)
                .filter(
                    SensorCalibration.sensor == sensor.value,
                    SensorCalibration.device_id == device_id,
                )
                .first()
            )

        calibration = run_read_with_db_retry(
            self.db,
            fetch_calibration,
            operation_name="fetch effective calibration",
        )

        if calibration is None:
            return CalibrationProfile(
                r0=converter.default_r0,
                rl_ohm=converter.rl_ohm,
                vcc=converter.vcc,
                ratio_mode=converter.ratio_mode,
            )

        ratio_mode = (
            RatioMode(calibration.ratio_mode)
            if calibration.ratio_mode is not None
            else converter.ratio_mode
        )

        return CalibrationProfile(
            r0=calibration.r0,
            rl_ohm=calibration.rl_ohm if calibration.rl_ohm is not None else converter.rl_ohm,
            vcc=calibration.vcc if calibration.vcc is not None else converter.vcc,
            ratio_mode=ratio_mode,
        )

    def upsert(
        self,
        *,
        sensor: SensorName,
        payload: CalibrationUpsertRequest,
    ) -> SensorCalibration:
        calibration = (
            self.db.query(SensorCalibration)
            .filter(
                SensorCalibration.sensor == sensor.value,
                SensorCalibration.device_id == payload.device_id,
            )
            .first()
        )

        ratio_mode = payload.ratio_mode.value if payload.ratio_mode is not None else None

        if calibration is None:
            calibration = SensorCalibration(
                sensor=sensor.value,
                device_id=payload.device_id,
                r0=payload.r0,
                rl_ohm=payload.rl_ohm,
                vcc=payload.vcc,
                ratio_mode=ratio_mode,
            )
            self.db.add(calibration)
        else:
            calibration.r0 = payload.r0
            calibration.rl_ohm = payload.rl_ohm
            calibration.vcc = payload.vcc
            calibration.ratio_mode = ratio_mode

        self.db.commit()
        self.db.refresh(calibration)
        return calibration

    def get_by_sensor_and_device(self, *, sensor: SensorName, device_id: str) -> SensorCalibration:
        def fetch_calibration() -> SensorCalibration | None:
            return (
                self.db.query(SensorCalibration)
                .filter(
                    SensorCalibration.sensor == sensor.value,
                    SensorCalibration.device_id == device_id,
                )
                .first()
            )

        calibration = run_read_with_db_retry(
            self.db,
            fetch_calibration,
            operation_name="fetch calibration by sensor and device",
        )

        if calibration is None:
            raise NotFoundError(
                f"Calibration not found for sensor '{sensor.value}' and device '{device_id}'."
            )
        return calibration
