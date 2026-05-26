from __future__ import annotations

from app.converters.base import BaseGasSensorConverter
from app.converters.fermion_h2s import FermionH2SConverter
from app.converters.fermion_nh3 import FermionNH3Converter
from app.converters.mics6814 import (
    COMICSConverter,
    NH3MICSConverter,
    NO2MICSConverter,
)
from app.converters.mq135 import MQ135Converter
from app.utils.errors import InvalidSensorError
from app.utils.sensor_types import SensorName


class SensorConverterRegistry:

    def __init__(self) -> None:
        converters = [
            MQ135Converter(),

            NH3MICSConverter(),
            COMICSConverter(),
            NO2MICSConverter(),

            FermionNH3Converter(),
            FermionH2SConverter(),
        ]

        self._converters: dict[
            SensorName,
            BaseGasSensorConverter,
        ] = {
            converter.sensor_name: converter
            for converter in converters
        }

    def get(
        self,
        sensor: SensorName | str,
    ) -> BaseGasSensorConverter:

        sensor_name = self._normalize_sensor(
            sensor
        )

        converter = self._converters.get(
            sensor_name
        )

        if converter is None:
            raise InvalidSensorError(
                f"Unsupported sensor: {sensor}"
            )

        return converter

    def list_supported(
        self,
    ) -> list[SensorName]:
        return list(
            self._converters.keys()
        )

    @staticmethod
    def _normalize_sensor(
        sensor: SensorName | str,
    ) -> SensorName:

        if isinstance(sensor, SensorName):
            return sensor

        normalized = (
            str(sensor)
            .strip()
            .lower()
        )

        try:
            return SensorName(normalized)

        except ValueError as exc:
            raise InvalidSensorError(
                f"Unsupported sensor: {sensor}"
            ) from exc