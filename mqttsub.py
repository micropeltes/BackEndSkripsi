import json
import os
import math

import paho.mqtt.client as mqtt
from database import save_data
from config import get_required_env

BROKER = get_required_env("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", "8883"))
TOPIC = os.getenv("MQTT_TOPIC", "test/topic")

CA_CERT = get_required_env("MQTT_CA_CERT")

# =========================
# KONFIGURASI SENSOR
# =========================

VREF = 4.096       # ADS1115 reference voltage
ADC_MAX = 32767.0
RL = 10000.0       # 10k ohm

# R0 (HARUS dikalibrasi nanti!)
R0 = {
    "nh3_mics": 10000,
    "nh3_mems": 10000,
    "h2s": 10000,
    "no2": 10000,
    "co": 10000,
    "mq135": 10000,
}

# Konstanta dari datasheet (approx)
GAS_CURVE = {
    "nh3_mics": (102.2, -2.473),
    "nh3_mems": (102.2, -2.473),
    "h2s": (44.947, -1.375),
    "no2": (0.72, -1.6),
    "co": (605.18, -3.937),
    "mq135": (116.602, -2.769),
}

# =========================
# FUNCTION CONVERTER
# =========================

def adc_to_voltage(adc):
    return (adc / ADC_MAX) * VREF

def voltage_to_rs(voltage):
    if voltage <= 0:
        return None
    return RL * (VREF - voltage) / voltage

def rs_to_ppm(rs, gas_name):
    if rs is None:
        return None

    r0 = R0[gas_name]
    ratio = rs / r0

    A, B = GAS_CURVE[gas_name]
    ppm = A * (ratio ** B)

    return round(ppm, 2)

def convert_adc_to_ppm(adc, gas_name):
    voltage = adc_to_voltage(adc)
    rs = voltage_to_rs(voltage)
    ppm = rs_to_ppm(rs, gas_name)
    return ppm

# =========================
# MQTT CALLBACK
# =========================

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with code:", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print("Raw:", payload)

        data = json.loads(payload)

        # SESUAI PAYLOAD ESP (lowercase)
        devid = data.get("devid")
        nh3_mics_adc = data.get("nh3_mics")
        nh3_mems_adc = data.get("nh3_mems")
        h2s_adc = data.get("h2s")
        no2_adc = data.get("no2")
        co_adc = data.get("co")
        mq135_adc = data.get("mq135")

        if devid is None:
            print("Invalid data: devid missing")
            return

        # =========================
        # KONVERSI KE PPM
        # =========================

        nh3_mics = convert_adc_to_ppm(nh3_mics_adc, "nh3_mics")
        nh3_mems = convert_adc_to_ppm(nh3_mems_adc, "nh3_mems")
        h2s = convert_adc_to_ppm(h2s_adc, "h2s")
        no2 = convert_adc_to_ppm(no2_adc, "no2")
        co = convert_adc_to_ppm(co_adc, "co")
        mq135 = convert_adc_to_ppm(mq135_adc, "mq135")

        print("PPM:", {
            "nh3_mics": nh3_mics,
            "nh3_mems": nh3_mems,
            "h2s": h2s,
            "no2": no2,
            "co": co,
            "mq135": mq135
        })

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

# =========================
# START MQTT
# =========================

def start_mqtt():
    client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    client.tls_set(ca_certs=CA_CERT)
    client.tls_insecure_set(True)

    client.connect(BROKER, PORT, 60)
    client.loop_start()
