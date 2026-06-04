from __future__ import annotations

from app.converters.base import BaseGasSensorConverter
from app.converters.r0_baselines import get_calibrated_r0
from app.utils.sensor_types import RatioMode, SensorName


class NH3MICSConverter(BaseGasSensorConverter):

    @property
    def sensor_name(self) -> SensorName:
        return SensorName.NH3_MICS

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = get_calibrated_r0(SensorName.NH3_MICS)

    ratio_mode = RatioMode.RS_OVER_R0

    # Placeholder curve
    curve_a = 0.75
    curve_b = -1.45

class COMICSConverter(BaseGasSensorConverter):

    @property
    def sensor_name(self) -> SensorName:
        return SensorName.CO

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = get_calibrated_r0(SensorName.CO)

    ratio_mode = RatioMode.RS_OVER_R0

    curve_a = 5.8
    curve_b = -2.25
        
class NO2MICSConverter(BaseGasSensorConverter):

    @property
    def sensor_name(self) -> SensorName:
        return SensorName.NO2

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = get_calibrated_r0(SensorName.NO2)

    ratio_mode = RatioMode.RS_OVER_R0

    curve_a = 0.35
    curve_b = 1.35
