from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import SensorData

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # cleanup koneksi mati
        for conn in dead_connections:
            self.disconnect(conn)


manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            # menjaga koneksi tetap hidup
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.get("/data")
def get_data(
    limit: int = Query(default=10, ge=1),
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
    
@router.post("/data")
async def create_data(payload: dict, db: Session = Depends(get_db)):
    new_data = SensorData(**payload)

    db.add(new_data)
    db.commit()
    db.refresh(new_data)

    await manager.broadcast({
        "type": "NEW_DATA",
        "data": {
            "id": new_data.id,
            "device_id": new_data.device_id,
            "nh3_mics": new_data.nh3_mics,
            "nh3_mems": new_data.nh3_mems,
            "h2s": new_data.h2s,
            "no2": new_data.no2,
            "co": new_data.co,
            "mq135": new_data.mq135,
            "created_at": str(new_data.created_at),
        }
    })

    return {
        "message": "Data berhasil disimpan",
        "id": new_data.id
    }
