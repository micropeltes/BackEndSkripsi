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


class SensorReadingRecordResponse(SensorProcessedResponse):
    device_id: str
    temperature_c: float | None = None
    humidity_pct: float | None = None
    payload_timestamp_ms: int | None = None
    received_timestamp_ms: int
    created_at: datetime


class SensorListResponse(BaseModel):
    count: int
    items: list[SensorReadingRecordResponse]


class SensorConvertRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    sensor: SensorName
    adc: int
    temperature_c: float | None = None
    humidity_pct: float | None = None
