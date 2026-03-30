from contextlib import asynccontextmanager
from fastapi import FastAPI
from api import router
from mqttsub import start_mqtt
from database import save_data

app = FastAPI()

app.include_router(router)


@app.on_event("startup")
def startup():
    print("Starting backend...")
    start_mqtt()
    # cek databasefrom contextlib import asynccontextmanager
from fastapi import FastAPI
from api import router
from mqttsub import start_mqtt

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting backend...")
    start_mqtt()  # jalankan MQTT saat startup
    yield
    print("Shutting down backend...")

app = FastAPI(lifespan=lifespan)

app.include_router(router)
    # save_data(value)
    # start MQTT subscriber
