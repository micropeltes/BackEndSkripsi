from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import SensorData

router = APIRouter()


@router.get("/data")
def get_data(
    limit: int | None = Query(default=None, ge=1, le=100),
    jumlah: int | None = Query(default=None, ge=1, le=100),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # `jumlah` disediakan agar fleksibel jika frontend memakai nama ini.
    effective_limit = jumlah if jumlah is not None else (limit if limit is not None else 10)

    query = db.query(SensorData)

    if device_id:
        query = query.filter(SensorData.device_id == device_id)

    records = (
        query.order_by(SensorData.created_at.desc(), SensorData.id.desc())
        .limit(effective_limit)
        .all()
    )

    return {
        "message": "Query data berhasil",
        "requested_limit": effective_limit,
        "device_id_filter": device_id,
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
