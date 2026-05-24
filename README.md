# Electronic Nose Backend (FastAPI)

Backend ini memproses data mentah ADS1115 dari MQTT menjadi data final siap konsumsi frontend:

- `adc` (raw count)
- `voltage`
- `Rs`
- `ratio` (`Rs/R0` atau `R0/Rs`)
- `ppm` estimasi

## Formula Utama

- ADS1115 gain=1: `voltage = adc_value * 0.000125`
- `Rs = RL * ((VCC - Vout) / Vout)`

## Struktur Project

```text
app/
  core/
    config.py
    dependencies.py
    logging.py
  converters/
    base.py
    mq135.py
    mics6814.py
    fermion_nh3.py
    fermion_h2s.py
    registry.py
  models/
    base.py
    sensor_reading.py
    sensor_calibration.py
  routers/
    health.py
    sensors.py
    calibration.py
  schemas/
    mqtt.py
    sensor.py
    calibration.py
    common.py
  services/
    raw_acquisition_service.py
    conversion_service.py
    calibration_service.py
    sensor_reading_service.py
    sensor_pipeline_service.py
    mqtt_ingestion_service.py
  utils/
    sensor_types.py
    filters.py
    errors.py
    time_utils.py
  database.py
  main.py
```

## Data Flow

1. Device publish raw ADC ke MQTT.
2. `AsyncMqttIngestionService` menerima payload async, validasi schema.
3. `RawAcquisitionService` memecah payload per sensor.
4. `ConversionService` melakukan averaging + konversi menggunakan converter per sensor.
5. Hasil final disimpan ke DB (`sensor_readings`).
6. Frontend ambil endpoint FastAPI final (tanpa raw processing lagi).

## MQTT Payload (Recommended)

```json
{
  "device_id": "esp32c3-01",
  "timestamp_ms": 1716555000123,
  "environment": {
    "temperature_c": 30.1,
    "humidity_pct": 71.3
  },
  "adc": {
    "mq135": 16384,
    "mics6814": 14500,
    "fermion_nh3": 12100,
    "fermion_h2s": 9800
  }
}
```

Legacy key seperti `devid`, `nh3_mics`, `nh3_mems`, `h2s`, `MQ135` tetap didukung.

## Endpoint Utama

- `GET /health`
- `GET /api/v1/sensors/supported`
- `GET /api/v1/sensors/{sensor}/latest?device_id=esp32c3-01`
- `GET /api/v1/sensors/latest?limit=20&device_id=esp32c3-01`
- `POST /api/v1/sensors/convert`
- `PUT /api/v1/calibrations/{sensor}`
- `GET /api/v1/calibrations/{sensor}?device_id=esp32c3-01`

## Contoh Response Final

```json
{
  "sensor": "mq135",
  "adc": 16384,
  "voltage": 2.048,
  "rs": 6910.0,
  "r0": 10000.0,
  "ratio": 0.691,
  "ppm": 145.2,
  "unit": "ppm"
}
```

## Menjalankan

```powershell
.\.venv\Scripts\activate
python -m uvicorn main:app --reload
```

## Frontend Consume Data Final

Frontend Vue cukup hit endpoint:

- latest satu sensor: `/api/v1/sensors/mq135/latest?device_id=esp32c3-01`
- list final terbaru: `/api/v1/sensors/latest?limit=50&device_id=esp32c3-01`

Frontend tidak perlu menghitung `voltage`, `Rs`, `ratio`, atau `ppm` lagi.

## Catatan Kalibrasi

- Nilai kurva (`curve_a`, `curve_b`) di converter saat ini masih placeholder awal.
- Lakukan kalibrasi lab untuk tuning akurasi ppm.
- R0 bisa diubah per device+sensor via endpoint kalibrasi.
