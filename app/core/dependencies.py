from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.converters.registry import SensorConverterRegistry
from app.core.config import Settings, get_settings
from app.database import get_db
from app.services.calibration_service import CalibrationService
from app.services.sensor_reading_service import SensorReadingService


_registry = SensorConverterRegistry()


def get_settings_dependency() -> Settings:
    return get_settings()


def get_db_dependency() -> Generator[Session, None, None]:
    yield from get_db()


def get_converter_registry() -> SensorConverterRegistry:
    return _registry


def get_calibration_service(
    db: Session = Depends(get_db_dependency),
    registry: SensorConverterRegistry = Depends(get_converter_registry),
) -> CalibrationService:
    return CalibrationService(db=db, registry=registry)


def get_sensor_reading_service(
    db: Session = Depends(get_db_dependency),
) -> SensorReadingService:
    return SensorReadingService(db=db)
