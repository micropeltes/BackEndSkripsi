from __future__ import annotations

import re

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.utils.sensor_types import SensorName


LEGACY_SENSOR_MAP: dict[str, SensorName] = {
    "mq135": SensorName.MQ135,
    "mq_135": SensorName.MQ135,
    "mq-135": SensorName.MQ135,
    "air_quality": SensorName.MQ135,
    "airquality": SensorName.MQ135,

    "nh3_mics": SensorName.NH3_MICS,
    "mics6814": SensorName.NH3_MICS,
    "mics_6814": SensorName.NH3_MICS,
    "mics6814_nh3": SensorName.NH3_MICS,
    "mics_nh3": SensorName.NH3_MICS,
    "nh3": SensorName.NH3_MICS,
    "co": SensorName.CO,
    "mics6814_co": SensorName.CO,
    "mics_co": SensorName.CO,
    "no2": SensorName.NO2,
    "no_2": SensorName.NO2,
    "mics6814_no2": SensorName.NO2,
    "mics_no2": SensorName.NO2,

    "fermion_nh3": SensorName.FERMION_NH3,
    "nh3_mems": SensorName.FERMION_NH3,

    "fermion_h2s": SensorName.FERMION_H2S,
    "h2s": SensorName.FERMION_H2S,
}


SENSOR_NAME_KEYS = ("sensor", "sensor_name", "sensorName", "name", "type", "channel")
SENSOR_VALUE_KEYS = ("adc", "adc_raw", "adcRaw", "adc_value", "adcValue", "value", "raw")
NESTED_SENSOR_MAP_KEYS = ("adc", "sensors", "sensor_data", "sensorData", "values", "readings", "data")
MICS6814_GROUP_KEYS = {"mics6814", "mics_6814", "mics", "mics6814_channels"}
MICS6814_CHANNEL_MAP = {
    "nh3": SensorName.NH3_MICS,
    "nh3_mics": SensorName.NH3_MICS,
    "co": SensorName.CO,
    "no2": SensorName.NO2,
    "no_2": SensorName.NO2,
}
DEVICE_ID_KEYS = ("device_id", "devid", "deviceId", "deviceID", "device")


def _normalize_key(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())
    return normalized.strip("_")


def _resolve_sensor(raw_key: object) -> SensorName | None:
    if isinstance(raw_key, SensorName):
        return raw_key

    normalized = _normalize_key(raw_key)
    sensor = LEGACY_SENSOR_MAP.get(normalized)
    if sensor is not None:
        return sensor

    try:
        return SensorName(normalized)
    except ValueError:
        return None


def _coerce_adc_value(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _merge_sensor_map(adc_map: dict[str, int], source: object) -> None:
    if not isinstance(source, dict):
        return

    for key, value in source.items():
        normalized_key = _normalize_key(key)
        if normalized_key in MICS6814_GROUP_KEYS and isinstance(value, dict):
            for channel_key, channel_value in value.items():
                channel = MICS6814_CHANNEL_MAP.get(_normalize_key(channel_key))
                adc_value = _coerce_adc_value(channel_value)
                if channel is not None and adc_value is not None:
                    adc_map.setdefault(channel.value, adc_value)
            continue

        sensor = _resolve_sensor(key)
        adc_value = _coerce_adc_value(value)
        if sensor is not None and adc_value is not None:
            adc_map.setdefault(sensor.value, adc_value)


def _infer_sensor_from_payload(raw: dict[str, object]) -> SensorName | None:
    for key in SENSOR_NAME_KEYS:
        sensor_value = raw.get(key)
        if sensor_value is not None:
            sensor = _resolve_sensor(sensor_value)
            if sensor is not None:
                return sensor

    topic = raw.get("_mqtt_topic")
    if isinstance(topic, str):
        for segment in reversed([part for part in re.split(r"[/.\s]+", topic) if part]):
            sensor = _resolve_sensor(segment)
            if sensor is not None:
                return sensor

    return None


class EnvironmentPayload(BaseModel):
    temperature_c: float | None = None
    humidity_pct: float | None = None


def _normalize_timestamp_ms(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        parsed_timestamp = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None

    # Device payloads may send Unix seconds or milliseconds.
    if parsed_timestamp < 1_000_000_000_000:
        parsed_timestamp *= 1000

    return parsed_timestamp


class MqttRawPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    device_id: str = Field(
        validation_alias=AliasChoices(
            "device_id",
            "devid",
            "deviceId",
            "deviceID",
            "device",
        ),
        min_length=1,
    )
    timestamp_ms: int | None = Field(
        default=None,
        validation_alias=AliasChoices("timestamp_ms", "timestamp"),
    )
    adc: dict[SensorName, int] = Field(default_factory=dict)
    environment: EnvironmentPayload | None = None

    @model_validator(mode="before")
    @classmethod
    def merge_legacy_sensor_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        raw = dict(data)
        adc_map: dict[str, int] = {}

        if "device_id" not in raw:
            for device_key in DEVICE_ID_KEYS:
                device_id = raw.get(device_key)
                if device_id is not None:
                    raw["device_id"] = device_id
                    break

        for map_key in NESTED_SENSOR_MAP_KEYS:
            _merge_sensor_map(adc_map, raw.get(map_key))

        _merge_sensor_map(adc_map, raw)

        single_sensor = _infer_sensor_from_payload(raw)
        if single_sensor is not None:
            for value_key in SENSOR_VALUE_KEYS:
                adc_value = _coerce_adc_value(raw.get(value_key))
                if adc_value is not None:
                    adc_map.setdefault(single_sensor.value, adc_value)
                    break

        raw["adc"] = adc_map
        return raw

    @field_validator("adc")
    @classmethod
    def validate_adc_not_empty(cls, value: dict[SensorName, int]) -> dict[SensorName, int]:
        if not value:
            raise ValueError("ADC payload is empty.")
        return value

    @field_validator("timestamp_ms", mode="before")
    @classmethod
    def normalize_payload_timestamp(cls, value: object) -> int | None:
        return _normalize_timestamp_ms(value)


class MqttErrorPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    device_id: str = Field(
        validation_alias=AliasChoices(
            "device_id",
            "devid",
            "deviceId",
            "deviceID",
            "device",
        ),
        min_length=1,
    )
    timestamp_ms: int | None = Field(
        default=None,
        validation_alias=AliasChoices("timestamp_ms", "timestamp"),
    )
    error: str = Field(min_length=1)

    @field_validator("timestamp_ms", mode="before")
    @classmethod
    def normalize_payload_timestamp(cls, value: object) -> int | None:
        return _normalize_timestamp_ms(value)


class RawSensorSample(BaseModel):
    device_id: str
    sensor: SensorName
    adc: int
    payload_timestamp_ms: int | None = None
    received_timestamp_ms: int
    temperature_c: float | None = None
    humidity_pct: float | None = None
