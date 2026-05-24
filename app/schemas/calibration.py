from __future__ import annotations

from pydantic import BaseModel, Field

from app.utils.sensor_types import RatioMode, SensorName


class CalibrationUpsertRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    r0: float = Field(gt=0)
    rl_ohm: float | None = Field(default=None, gt=0)
    vcc: float | None = Field(default=None, gt=0)
    ratio_mode: RatioMode | None = None


class CalibrationResponse(BaseModel):
    sensor: SensorName
    device_id: str
    r0: float
    rl_ohm: float | None = None
    vcc: float | None = None
    ratio_mode: RatioMode | None = None
