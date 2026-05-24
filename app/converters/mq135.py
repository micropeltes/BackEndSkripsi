from __future__ import annotations

from app.converters.base import BaseGasSensorConverter
from app.utils.sensor_types import RatioMode, SensorName


class MQ135Converter(BaseGasSensorConverter):
    @property
    def sensor_name(self) -> SensorName:
        return SensorName.MQ135

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = 10000.0
    ratio_mode = RatioMode.RS_OVER_R0

    # Default curve placeholder (must be tuned with your lab calibration data).
    curve_a = 116.6020682
    curve_b = -2.769034857
