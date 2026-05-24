from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.sensor_types import SensorName


LEGACY_SENSOR_MAP: dict[str, SensorName] = {
    "mq135": SensorName.MQ135,
    "mics6814": SensorName.MICS6814,
    "nh3_mics": SensorName.MICS6814,
    "fermion_nh3": SensorName.FERMION_NH3,
    "nh3_mems": SensorName.FERMION_NH3,
    "fermion_h2s": SensorName.FERMION_H2S,
    "h2s": SensorName.FERMION_H2S,
}


class EnvironmentPayload(BaseModel):
    temperature_c: float | None = None
    humidity_pct: float | None = None


class MqttRawPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    device_id: str = Field(validation_alias=AliasChoices("device_id", "devid"), min_length=1)
    timestamp_ms: int | None = Field(default=None, validation_alias=AliasChoices("timestamp_ms", "timestamp"))
    adc: dict[SensorName, int] = Field(default_factory=dict)
    environment: EnvironmentPayload | None = None

    @model_validator(mode="before")
    @classmethod
    def merge_legacy_sensor_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        raw = dict(data)
        adc_raw = raw.get("adc", {})
        adc_map: dict[str, int] = {}

        if isinstance(adc_raw, dict):
            for key, value in adc_raw.items():
                adc_map[str(key).lower()] = value

        for raw_key, sensor in LEGACY_SENSOR_MAP.items():
            if raw_key in raw:
                adc_map.setdefault(sensor.value, raw[raw_key])

            upper_key = raw_key.upper()
            if upper_key in raw:
                adc_map.setdefault(sensor.value, raw[upper_key])

        raw["adc"] = adc_map
        return raw

    @field_validator("adc")
    @classmethod
    def validate_adc_not_empty(cls, value: dict[SensorName, int]) -> dict[SensorName, int]:
        if not value:
            raise ValueError("ADC payload is empty.")
        return value


class RawSensorSample(BaseModel):
    device_id: str
    sensor: SensorName
    adc: int
    payload_timestamp_ms: int | None = None
    received_timestamp_ms: int
    temperature_c: float | None = None
    humidity_pct: float | None = None
