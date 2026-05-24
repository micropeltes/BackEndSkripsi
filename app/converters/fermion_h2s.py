from __future__ import annotations

from app.converters.base import BaseGasSensorConverter
from app.utils.sensor_types import RatioMode, SensorName


class FermionH2SConverter(BaseGasSensorConverter):
    @property
    def sensor_name(self) -> SensorName:
        return SensorName.FERMION_H2S

    rl_ohm = 10000.0
    vcc = 3.3
    default_r0 = 10000.0
    ratio_mode = RatioMode.R0_OVER_RS

    # Placeholder curve; tune using clean-air and known-ppm calibration gas.
    curve_a = 7.5
    curve_b = 1.3
