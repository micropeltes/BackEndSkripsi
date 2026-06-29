# Electronic Nose Backend

FastAPI backend for ingesting MQTT sensor readings, storing processed sensor
measurements, and exposing sensor/calibration APIs.

## Security-related configuration

The API disables browser cross-origin access by default. Set `CORS_ALLOW_ORIGINS`
to a comma-separated allowlist of trusted frontend origins, for example:

```env
CORS_ALLOW_ORIGINS=https://example.com,https://admin.example.com
CORS_ALLOW_CREDENTIALS=false
```

If `CORS_ALLOW_CREDENTIALS=true`, do not use `*` in `CORS_ALLOW_ORIGINS`; the
application rejects that combination at startup.

MQTT TLS certificate verification is enabled by default whenever
`MQTT_CA_CERT` is configured. Only set `MQTT_TLS_INSECURE=true` for temporary
development troubleshooting because it disables broker certificate hostname and
chain verification.
