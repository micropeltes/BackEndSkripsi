import os

from app.core.config import get_settings, load_dotenv


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set in the environment.")
    return value


__all__ = ["get_settings", "load_dotenv", "get_required_env"]
