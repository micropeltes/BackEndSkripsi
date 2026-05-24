from __future__ import annotations

from app.schemas.mqtt import MqttRawPayload, RawSensorSample


class RawAcquisitionService:
    def explode_payload(
        self,
        *,
        payload: MqttRawPayload,
        received_timestamp_ms: int,
    ) -> list[RawSensorSample]:
        temperature_c = payload.environment.temperature_c if payload.environment else None
        humidity_pct = payload.environment.humidity_pct if payload.environment else None

        samples: list[RawSensorSample] = []
        for sensor, adc_value in payload.adc.items():
            samples.append(
                RawSensorSample(
                    device_id=payload.device_id,
                    sensor=sensor,
                    adc=int(adc_value),
                    payload_timestamp_ms=payload.timestamp_ms,
                    received_timestamp_ms=received_timestamp_ms,
                    temperature_c=temperature_c,
                    humidity_pct=humidity_pct,
                )
            )

        return samples
