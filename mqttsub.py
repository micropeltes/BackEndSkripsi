import paho.mqtt.client as mqtt
from database import save_data

BROKER = "broker.emqx.io"
TOPIC = "sensor/control"

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print("Received:", payload)
    save_data(payload)

def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, 1883, 60)
    client.loop_start()