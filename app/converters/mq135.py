from __future__ import annotations

from app.converters.base import BaseGasSensorConverter
from app.converters.r0_baselines import get_calibrated_r0
from app.utils.sensor_types import RatioMode, SensorName


class MQ135Converter(BaseGasSensorConverter):
    @property
    def sensor_name(self) -> SensorName:
        return SensorName.MQ135

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = get_calibrated_r0(SensorName.MQ135)
    ratio_mode = RatioMode.RS_OVER_R0

    # Default curve placeholder (must be tuned with your lab calibration data).
    curve_a = 102
    curve_b = -2.48
