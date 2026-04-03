from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import router
from database import init_db
from mqttsub import start_mqtt

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting backend...")
    db_ready = init_db()

    if db_ready:
        start_mqtt()
    else:
        print("Skipping MQTT startup because the database is unavailable. Check DATABASE_URL in .env.")

    yield
    print("Shutting down backend...")

app = FastAPI(lifespan=lifespan)

app.include_router(router)
