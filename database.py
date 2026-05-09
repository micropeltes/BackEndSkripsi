import os

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from config import load_dotenv
from models import Base, SensorData, SensorDelay

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment.")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully.")
        return True
    except SQLAlchemyError as exc:
        print(f"Database initialization failed: {exc}")
        return False


def save_data(
    device_id,
    nh3_mics,
    nh3_mems,
    h2s,
    no2,
    co,
    mq135,
    received_timestamp_ms=None,
    device_timestamp_ms=None,
    diff_ms=None,
):
    db = SessionLocal()

    try:
        sensor_data = SensorData(
            device_id=device_id,
            nh3_mics=nh3_mics,
            nh3_mems=nh3_mems,
            h2s=h2s,
            no2=no2,
            co=co,
            mq135=mq135,
        )
        db.add(sensor_data)

        # Flush dulu agar sensor_data.id tersedia untuk relasi delay.
        db.flush()

        if (
            received_timestamp_ms is not None
            and device_timestamp_ms is not None
            and diff_ms is not None
        ):
            delay_data = SensorDelay(
                sensor_data_id=sensor_data.id,
                received_timestamp_ms=int(received_timestamp_ms),
                device_timestamp_ms=int(device_timestamp_ms),
                diff_ms=int(diff_ms),
            )
            db.add(delay_data)

        db.commit()
        print("Saved to DB:", sensor_data.id)
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"Failed to save data: {exc}")
    finally:
        db.close()
