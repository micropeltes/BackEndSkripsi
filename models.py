from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func


Base = declarative_base()


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50))
    nh3_mics = Column(Float)
    nh3_mems = Column(Float)
    h2s = Column(Float)
    no2 = Column(Float)
    co = Column(Float)
    mq135 = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delay = relationship("SensorDelay", back_populates="sensor_data", uselist=False)


class SensorDelay(Base):
    __tablename__ = "sensor_delay"

    id = Column(Integer, primary_key=True, index=True)
    sensor_data_id = Column(Integer, ForeignKey("sensor_data.id"), unique=True, nullable=False)
    received_timestamp_ms = Column(BigInteger, nullable=False)
    device_timestamp_ms = Column(BigInteger, nullable=False)
    diff_ms = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sensor_data = relationship("SensorData", back_populates="delay")
