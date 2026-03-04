from fastapi import FastAPI
from contextlib import asynccontextmanager
from api import router
from mqttsub import start_mqtt

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_mqtt()
    yield
    # Shutdown (kalau perlu cleanup bisa taruh di sini)

app = FastAPI(lifespan=lifespan)

app.include_router(router)