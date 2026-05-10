import json
import os
import socket
import struct
import time

import paho.mqtt.client as mqtt
from database import save_data
from config import get_required_env

BROKER = get_required_env("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", "8883"))
SENSOR_TOPIC = os.getenv("MQTT_SENSOR_TOPIC", "test/topic")
TIMESTAMP_TOPIC = os.getenv("MQTT_TIMESTAMP_TOPIC", "device/timestmap")
LEGACY_TOPIC = os.getenv("MQTT_TOPIC")

CA_CERT = get_required_env("MQTT_CA_CERT")

NTP_SERVER = os.getenv("NTP_SERVER", "time.google")
NTP_PORT = 123
NTP_TIMEOUT = float(os.getenv("NTP_TIMEOUT", "2"))
NTP_DELTA = 2208988800  # NTP epoch (1900) to Unix epoch (1970)

# Menyimpan timestamp per device dari topic timestamp terpisah.
DEVICE_TIMESTAMP_CACHE = {}


def get_ntp_unix_time() -> float:
    packet = b"\x1b" + 47 * b"\0"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(NTP_TIMEOUT)
        sock.sendto(packet, (NTP_SERVER, NTP_PORT))
        data, _ = sock.recvfrom(48)

    if len(data) < 48:
        raise RuntimeError("Invalid NTP response")

    seconds, fraction = struct.unpack("!II", data[40:48])
    return seconds - NTP_DELTA + (fraction / 2**32)


def to_seconds(timestamp_value) -> float:
    value = float(timestamp_value)
    # Heuristik: >= 10^12 dianggap milidetik Unix.
    if value >= 1_000_000_000_000:
        return value / 1000.0
    return value

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with code:", rc)
    topics = [(SENSOR_TOPIC, 0), (TIMESTAMP_TOPIC, 0)]
    if LEGACY_TOPIC:
        topics.append((LEGACY_TOPIC, 0))
    client.subscribe(topics)
    print("Subscribed topics:", ", ".join(topic for topic, _ in topics))

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"Raw [{msg.topic}]:", payload)

        data = json.loads(payload)
        devid = data.get("devid")

        if devid is None:
            print("Invalid data: devid missing")
            return

        if msg.topic == TIMESTAMP_TOPIC:
            msg_ts = data.get("timestamp")
            if msg_ts is None:
                print("Timestamp topic payload missing timestamp")
                return
            DEVICE_TIMESTAMP_CACHE[devid] = msg_ts
            print(f"Cached timestamp for {devid}: {msg_ts}")
            return

        msg_ts = data.get("timestamp", DEVICE_TIMESTAMP_CACHE.get(devid))

        received_ts_ms = None
        device_ts_ms = None
        diff_ms = None

        if msg_ts is not None:
            try:
                now_ntp = get_ntp_unix_time()
            except Exception as ntp_err:
                print(f"Failed to get NTP time from {NTP_SERVER}: {ntp_err}. Fallback to local time.")
                now_ntp = time.time()

            device_ts_seconds = to_seconds(msg_ts)
            delay_seconds = now_ntp - device_ts_seconds
            received_ts_ms = int(now_ntp * 1000)
            device_ts_ms = int(device_ts_seconds * 1000)
            diff_ms = int(delay_seconds * 1000)
            print(
                f"Delay device {data.get('devid', '-')}: {delay_seconds:.3f}s / {diff_ms}ms "
                f"(receive={now_ntp:.3f}, device_ts={device_ts_seconds:.3f})"
            )

        nh3_mics = data.get("nh3_mics", data.get("NH3_MICS"))
        nh3_mems = data.get("nh3_mems", data.get("NH3_MEMS"))
        h2s = data.get("h2s", data.get("H2S"))
        no2 = data.get("no2", data.get("NO2"))
        co = data.get("co", data.get("CO"))
        mq135 = data.get("mq135", data.get("MQ135"))

        if msg_ts is None:
            print("Timestamp missing; delay calculation skipped.")

        print("Parsed:", data)

        save_data(
            devid,
            nh3_mics,
            nh3_mems,
            h2s,
            no2,
            co,
            mq135,
            received_ts_ms,
            device_ts_ms,
            diff_ms,
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
