from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ErrorLog(Base):
    __tablename__ = "errorlog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    error: Mapped[str] = mapped_column(Text)
    payload_timestamp_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    received_timestamp_ms: Mapped[int] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


Index(
    "ix_errorlog_device_received_id",
    ErrorLog.device_id,
    ErrorLog.received_timestamp_ms.desc(),
    ErrorLog.id.desc(),
)
