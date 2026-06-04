from __future__ import annotations

import logging
from collections.abc import Iterable

from app.utils.sensor_types import SensorName


logger = logging.getLogger(__name__)

SAFE_FALLBACK_R0 = 10000.0

CALIBRATED_R0_BY_SENSOR = {
    SensorName.MQ135: 100000.0,

    SensorName.NH3_MICS: 300000.0,
    SensorName.CO: 500000.0,
    SensorName.NO2: 10000.0,

    SensorName.FERMION_NH3: 30000.0,
    SensorName.FERMION_H2S: 30000.0,
}


def get_calibrated_r0(sensor: SensorName) -> float:
    r0 = CALIBRATED_R0_BY_SENSOR.get(sensor)
    if r0 is None:
        logger.warning(
            "No calibrated R0 baseline found for sensor=%s; using safe fallback R0=%s",
            sensor.value,
            SAFE_FALLBACK_R0,
        )
        return SAFE_FALLBACK_R0

    return r0


def format_active_r0_baselines(sensors: Iterable[SensorName]) -> str:
    return ", ".join(
        f"{sensor.value}={get_calibrated_r0(sensor)}"
        for sensor in sensors
    )
