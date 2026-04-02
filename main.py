from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import router
from database import init_db
from mqttsub import start_mqtt

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting backend...")
    init_db()
    start_mqtt()
    yield
    print("Shutting down backend...")

app = FastAPI(lifespan=lifespan)

app.include_router(router)
