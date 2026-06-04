from __future__ import annotations

from app.converters.base import BaseGasSensorConverter
from app.converters.r0_baselines import get_calibrated_r0
from app.utils.sensor_types import RatioMode, SensorName


class FermionNH3Converter(BaseGasSensorConverter):
    @property
    def sensor_name(self) -> SensorName:
        return SensorName.FERMION_NH3

    rl_ohm = 10000.0
    vcc = 3.3
    default_r0 = get_calibrated_r0(SensorName.FERMION_NH3)
    ratio_mode = RatioMode.R0_OVER_RS

    # Placeholder curve; tune using clean-air and known-ppm calibration gas.
    curve_a = 12.5
    curve_b = -1.65
