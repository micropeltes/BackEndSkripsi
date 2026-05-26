from __future__ import annotations

from app.converters.base import BaseGasSensorConverter
from app.utils.sensor_types import RatioMode, SensorName


class NH3MICSConverter(BaseGasSensorConverter):

    @property
    def sensor_name(self) -> SensorName:
        return SensorName.NH3_MICS

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = 10000.0

    ratio_mode = RatioMode.RS_OVER_R0

    # Placeholder curve
    curve_a = 70.0
    curve_b = -1.8
    
class COMICSConverter(BaseGasSensorConverter):

    @property
    def sensor_name(self) -> SensorName:
        return SensorName.CO

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = 10000.0

    ratio_mode = RatioMode.RS_OVER_R0

    curve_a = 50.0
    curve_b = -1.5
    
class NO2MICSConverter(BaseGasSensorConverter):

    @property
    def sensor_name(self) -> SensorName:
        return SensorName.NO2

    rl_ohm = 10000.0
    vcc = 5.0
    default_r0 = 10000.0

    ratio_mode = RatioMode.RS_OVER_R0

    curve_a = 10.0
    curve_b = -1.0