import json
import paho.mqtt.client as mqtt
from database import save_data

BROKER = "45.126.43.35"
PORT = 8883
TOPIC = "test/topic"

CA_CERT = r"C:\mqtt\ca.crt"

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with code:", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print("Raw:", payload)

        data = json.loads(payload)  # 🔥 parsing JSON

        # Ambil field
        devid = data.get("DevID")
        nh3_mics = data.get("NH3_MICS")
        nh3_mems = data.get("NH3_MEMS")
        h2s = data.get("H2S")
        no2 = data.get("NO2")
        co = data.get("CO")
        mq135 = data.get("MQ135")

        print("Parsed:", data)

        # Simpan ke DB
        save_data(devid, nh3_mics, nh3_mems, h2s, no2, co, mq135)

    except Exception as e:
        print("Error parsing message:", e)

def start_mqtt():
    client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    client.tls_set(ca_certs=CA_CERT)
    client.tls_insecure_set(True)

    client.connect(BROKER, PORT, 60)
    client.loop_start()