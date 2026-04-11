import json
import os

import paho.mqtt.client as mqtt
from database import save_data
from config import get_required_env

BROKER = get_required_env("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", "8883"))
TOPIC = os.getenv("MQTT_TOPIC", "test/topic")

CA_CERT = get_required_env("MQTT_CA_CERT")

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with code:", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print("Raw:", payload)

        data = json.loads(payload)

        devid = data.get("devid")
        nh3_mics = data.get("nh3_mics", data.get("NH3_MICS"))
        nh3_mems = data.get("nh3_mems", data.get("NH3_MEMS"))
        h2s = data.get("h2s", data.get("H2S"))
        no2 = data.get("no2", data.get("NO2"))
        co = data.get("co", data.get("CO"))
        mq135 = data.get("mq135", data.get("MQ135"))

        # VALIDASI PENTING
        if devid is None:
            print("Invalid data: devid missing")
            return

        print("Parsed:", data)

        save_data(
            devid,
            nh3_mics,
            nh3_mems,
            h2s,
            no2,
            co,
            mq135
        )

    except json.JSONDecodeError:
        print("Invalid JSON format")
    except Exception as e:
        print("Error:", e)

def start_mqtt():
    client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    client.tls_set(ca_certs=CA_CERT)
    client.tls_insecure_set(True)

    client.connect(BROKER, PORT, 60)
    client.loop_start()
