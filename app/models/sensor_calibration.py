from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SensorCalibration(Base):
    __tablename__ = "sensor_calibrations"
    __table_args__ = (
        UniqueConstraint("device_id", "sensor", name="uq_sensor_calibration_device_sensor"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    sensor: Mapped[str] = mapped_column(String(32), index=True)

    r0: Mapped[float] = mapped_column(Float)
    rl_ohm: Mapped[float | None] = mapped_column(Float, nullable=True)
    vcc: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratio_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


Index("ix_sensor_calibration_device_sensor", SensorCalibration.device_id, SensorCalibration.sensor)
