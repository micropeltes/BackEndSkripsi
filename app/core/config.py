from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
TRUE_ALIAS_VALUES = {"debug", "dev", "development"}
FALSE_ALIAS_VALUES = {"release", "prod", "production"}


def load_dotenv(dotenv_path: str = ".env") -> None:
    env_file = Path(dotenv_path)
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _parse_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    if normalized in TRUE_ALIAS_VALUES:
        return True
    if normalized in FALSE_ALIAS_VALUES:
        return False

    return default


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set in the environment.")
    return value


class Settings(BaseModel):
    app_name: str = "Electronic Nose Backend"
    api_prefix: str = "/api/v1"
    debug: bool = False

    database_url: str

    mqtt_enabled: bool = True
    mqtt_broker: str | None = None
    mqtt_port: int = 8883
    mqtt_sensor_topic: str = "test/topic"
    mqtt_timestamp_topic: str = "device/timestamp"
    mqtt_timestamp_topic_legacy: str | None = "device/timestmap"
    mqtt_legacy_topic: str | None = None
    mqtt_ca_cert: str | None = None
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_client_id: str = "e-nose-backend"
    mqtt_qos: int = 0
    mqtt_keepalive: int = 60
    mqtt_queue_size: int = 1000

    ads1115_lsb: float = Field(default=0.000125, gt=0)
    ads1115_min_adc: int = 0
    ads1115_max_adc: int = 32767
    filter_window_size: int = Field(default=5, ge=1, le=100)

    @field_validator("mqtt_qos")
    @classmethod
    def validate_qos(cls, value: int) -> int:
        if value not in (0, 1, 2):
            raise ValueError("MQTT QoS must be 0, 1, or 2")
        return value

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        mqtt_enabled = _parse_bool("MQTT_ENABLED", True)

        broker = os.getenv("MQTT_BROKER")
        ca_cert = os.getenv("MQTT_CA_CERT")
        if mqtt_enabled:
            broker = broker or _required_env("MQTT_BROKER")
            ca_cert = ca_cert or _required_env("MQTT_CA_CERT")

        return cls(
            debug=_parse_bool("DEBUG", False),
            database_url=_required_env("DATABASE_URL"),
            mqtt_enabled=mqtt_enabled,
            mqtt_broker=broker,
            mqtt_port=int(os.getenv("MQTT_PORT", "8883")),
            mqtt_sensor_topic=os.getenv("MQTT_SENSOR_TOPIC", os.getenv("MQTT_TOPIC", "test/topic")),
            mqtt_timestamp_topic=os.getenv("MQTT_TIMESTAMP_TOPIC", "device/timestamp"),
            mqtt_timestamp_topic_legacy=os.getenv("MQTT_TIMESTAMP_TOPIC_LEGACY", "device/timestmap"),
            mqtt_legacy_topic=os.getenv("MQTT_LEGACY_TOPIC"),
            mqtt_ca_cert=ca_cert,
            mqtt_username=os.getenv("MQTT_USERNAME"),
            mqtt_password=os.getenv("MQTT_PASSWORD"),
            mqtt_client_id=os.getenv("MQTT_CLIENT_ID", "e-nose-backend"),
            mqtt_qos=int(os.getenv("MQTT_QOS", "0")),
            mqtt_keepalive=int(os.getenv("MQTT_KEEPALIVE", "60")),
            mqtt_queue_size=int(os.getenv("MQTT_QUEUE_SIZE", "1000")),
            ads1115_lsb=float(os.getenv("ADS1115_LSB", "0.000125")),
            ads1115_min_adc=int(os.getenv("ADS1115_MIN_ADC", "0")),
            ads1115_max_adc=int(os.getenv("ADS1115_MAX_ADC", "32767")),
            filter_window_size=int(os.getenv("FILTER_WINDOW_SIZE", "5")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
