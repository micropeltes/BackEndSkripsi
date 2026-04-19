from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import SensorData

router = APIRouter()


@router.get("/data")
def get_data(
    limit: int = Query(default=10, ge=1, le=100),
    device_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(SensorData)

    if device_id:
        query = query.filter(SensorData.device_id == device_id)

    records = (
        query.order_by(SensorData.created_at.desc(), SensorData.id.desc())
        .limit(limit)
        .all()
    )

    return {
        "message": "Query data berhasil",
        "count": len(records),
        "items": [
            {
                "id": record.id,
                "device_id": record.device_id,
                "nh3_mics": record.nh3_mics,
                "nh3_mems": record.nh3_mems,
                "h2s": record.h2s,
                "no2": record.no2,
                "co": record.co,
                "mq135": record.mq135,
                "created_at": record.created_at,
            }
            for record in records
        ],
    }
