from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.utils.sensor_types import SensorName


class SensorProcessedResponse(BaseModel):
    sensor: SensorName
    adc: int
    voltage: float
    rs: float
    r0: float
    ratio: float
    ppm: float
    unit: str = "ppm"
    created_at: datetime | None = None


class SensorReadingRecordResponse(SensorProcessedResponse):
    device_id: str
    temperature_c: float | None = None
    humidity_pct: float | None = None
    payload_timestamp_ms: int | None = None
    received_timestamp_ms: int | None = None
    created_at: datetime


class SensorListResponse(BaseModel):
    count: int
    items: list[SensorReadingRecordResponse]


class SensorDataRecordResponse(BaseModel):
    id: int
    device_id: str
    nh3_mics: float | None = None
    nh3_mems: float | None = None
    h2s: float | None = None
    no2: float | None = None
    co: float | None = None
    mq135: float | None = None
    created_at: datetime


class SensorDataListResponse(BaseModel):
    count: int
    items: list[SensorDataRecordResponse]


class SensorConvertRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    sensor: SensorName
    adc: int = Field(ge=0, le=32767)
    temperature_c: float | None = Field(default=None, ge=-40, le=125)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)

class SensorHistoricalProcessedSensorData(BaseModel):
    adc: int
    voltage: float
    rs: float
    r0: float
    ratio: float
    ppm: float
    unit: str

class SensorHistoricalProcessedItem(BaseModel):
    id: int
    device_id: str
    created_at: datetime
    sensors: dict[str, SensorHistoricalProcessedSensorData]


class SensorHistoricalProcessedResponse(BaseModel):
    count: int
    items: list[SensorHistoricalProcessedItem]
