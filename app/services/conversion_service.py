from __future__ import annotations

from app.converters.base import ConversionResult
from app.converters.registry import SensorConverterRegistry
from app.core.config import Settings
from app.schemas.mqtt import RawSensorSample
from app.services.calibration_service import CalibrationService
from app.utils.filters import RollingAverageFilter


class ConversionService:
    def __init__(
        self,
        *,
        settings: Settings,
        registry: SensorConverterRegistry,
        calibration_service: CalibrationService,
        rolling_filter: RollingAverageFilter,
    ) -> None:
        self.settings = settings
        self.registry = registry
        self.calibration_service = calibration_service
        self.rolling_filter = rolling_filter

    def convert_sample(self, sample: RawSensorSample) -> ConversionResult:
        converter = self.registry.get(sample.sensor)
        calibration = self.calibration_service.get_effective_profile(
            sensor=sample.sensor,
            device_id=sample.device_id,
        )

        filter_key = f"{sample.device_id}:{sample.sensor.value}"
        adc_filtered = self.rolling_filter.push(filter_key, sample.adc)

        return converter.convert(
            adc=sample.adc,
            adc_filtered=adc_filtered,
            calibration=calibration,
            ads1115_lsb=self.settings.ads1115_lsb,
            adc_min=self.settings.ads1115_min_adc,
            adc_max=self.settings.ads1115_max_adc,
            temperature_c=sample.temperature_c,
            humidity_pct=sample.humidity_pct,
        )
