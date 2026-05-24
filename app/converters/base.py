from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.utils.errors import ConversionError, InvalidADCError
from app.utils.sensor_types import RatioMode, SensorName


@dataclass(frozen=True)
class CalibrationProfile:
    r0: float
    rl_ohm: float | None = None
    vcc: float | None = None
    ratio_mode: RatioMode | None = None


@dataclass(frozen=True)
class ConversionResult:
    sensor: SensorName
    adc: int
    adc_filtered: float
    voltage: float
    rs: float
    r0: float
    ratio: float
    ppm: float
    unit: str


class BaseGasSensorConverter(ABC):
    rl_ohm: float
    vcc: float
    default_r0: float
    ratio_mode: RatioMode
    curve_a: float
    curve_b: float
    unit: str = "ppm"

    @property
    @abstractmethod
    def sensor_name(self) -> SensorName:
        raise NotImplementedError

    def convert(
        self,
        adc: int,
        adc_filtered: float,
        calibration: CalibrationProfile,
        *,
        ads1115_lsb: float,
        adc_min: int,
        adc_max: int,
        temperature_c: float | None = None,
        humidity_pct: float | None = None,
    ) -> ConversionResult:
        self._validate_adc(adc=adc, adc_min=adc_min, adc_max=adc_max)

        rl_ohm = calibration.rl_ohm if calibration.rl_ohm is not None else self.rl_ohm
        vcc = calibration.vcc if calibration.vcc is not None else self.vcc
        r0 = calibration.r0
        ratio_mode = calibration.ratio_mode or self.ratio_mode

        if r0 <= 0:
            raise ConversionError("R0 must be greater than 0.")
        if rl_ohm <= 0:
            raise ConversionError("RL must be greater than 0.")
        if vcc <= 0:
            raise ConversionError("VCC must be greater than 0.")

        # ADS1115 gain=1 => LSB is 125uV (0.000125V)
        voltage = self._adc_to_voltage(adc_filtered, ads1115_lsb)

        if voltage <= 0:
            raise ConversionError("Voltage is 0V or negative; cannot compute Rs.")
        if voltage >= vcc:
            raise ConversionError("Voltage is equal/above VCC; cannot compute Rs reliably.")

        # Rs = RL * ((VCC - Vout) / Vout)
        rs = rl_ohm * ((vcc - voltage) / voltage)
        if rs <= 0:
            raise ConversionError("Computed Rs is non-positive.")

        ratio = self._compute_ratio(rs=rs, r0=r0, mode=ratio_mode)
        if ratio <= 0:
            raise ConversionError("Computed ratio is non-positive.")

        ppm_raw = self.estimate_ppm(ratio)
        ppm = self.apply_environment_compensation(
            ppm=ppm_raw,
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
        )

        return ConversionResult(
            sensor=self.sensor_name,
            adc=adc,
            adc_filtered=adc_filtered,
            voltage=voltage,
            rs=rs,
            r0=r0,
            ratio=ratio,
            ppm=ppm,
            unit=self.unit,
        )

    def estimate_ppm(self, ratio: float) -> float:
        if ratio <= 0:
            raise ConversionError("Ratio must be greater than 0 for ppm estimation.")
        return float(self.curve_a * math.pow(ratio, self.curve_b))

    def apply_environment_compensation(
        self,
        ppm: float,
        *,
        temperature_c: float | None,
        humidity_pct: float | None,
    ) -> float:
        # Placeholder hooks for future compensation formulas.
        temp_factor = self.temperature_compensation_factor(temperature_c)
        humidity_factor = self.humidity_compensation_factor(humidity_pct)
        return ppm * temp_factor * humidity_factor

    def temperature_compensation_factor(self, temperature_c: float | None) -> float:
        _ = temperature_c
        return 1.0

    def humidity_compensation_factor(self, humidity_pct: float | None) -> float:
        _ = humidity_pct
        return 1.0

    @staticmethod
    def _adc_to_voltage(adc_value: float, ads1115_lsb: float) -> float:
        return float(adc_value * ads1115_lsb)

    @staticmethod
    def _compute_ratio(*, rs: float, r0: float, mode: RatioMode) -> float:
        if mode == RatioMode.RS_OVER_R0:
            return rs / r0
        return r0 / rs

    @staticmethod
    def _validate_adc(*, adc: int, adc_min: int, adc_max: int) -> None:
        if adc < adc_min or adc > adc_max:
            raise InvalidADCError(
                f"ADC value {adc} is outside valid ADS1115 range ({adc_min}..{adc_max})."
            )
