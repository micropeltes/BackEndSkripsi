from __future__ import annotations

from app.converters.base import BaseGasSensorConverter
from app.utils.sensor_types import RatioMode, SensorName


class MICS6814Converter(BaseGasSensorConverter):
    @property
    def sensor_name(self) -> SensorName:
        return SensorName.MICS6814

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = 10000.0
    ratio_mode = RatioMode.RS_OVER_R0

    # Placeholder curve for NH3-like channel; tune from calibration dataset.
    curve_a = 70.0
    curve_b = -1.8
