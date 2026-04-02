from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base
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
