def start_mqtt() -> None:
    raise RuntimeError(
        "MQTT startup is now managed automatically by app.main lifespan. "
        "Run the API with: python -m uvicorn main:app --reload"
    )
