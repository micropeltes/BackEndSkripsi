from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    sensor: Mapped[str] = mapped_column(String(32), index=True)

    adc_raw: Mapped[int] = mapped_column(Integer)
    adc_filtered: Mapped[float] = mapped_column(Float)
    voltage: Mapped[float] = mapped_column(Float)
    rs: Mapped[float] = mapped_column(Float)
    r0: Mapped[float] = mapped_column(Float)
    ratio: Mapped[float] = mapped_column(Float)
    ppm: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16), default="ppm")

    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    payload_timestamp_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    received_timestamp_ms: Mapped[int] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


Index("ix_sensor_readings_device_sensor_created", SensorReading.device_id, SensorReading.sensor, SensorReading.created_at.desc())
Index("ix_sensor_readings_received_id", SensorReading.received_timestamp_ms.desc(), SensorReading.id.desc())
Index("ix_sensor_readings_device_received_id", SensorReading.device_id, SensorReading.received_timestamp_ms.desc(), SensorReading.id.desc())
