from fastapi import FastAPI
from api import router
from mqttsub import start_mqtt
from database import save_data

app = FastAPI()

app.include_router(router)


@app.on_event("startup")
def startup():

    print("Starting backend...")

    # cek database
    save_data()

    # start MQTT subscriber
    start_mqtt()