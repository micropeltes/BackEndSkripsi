import os
import re
from pathlib import Path

ALLOWED_KEYS = {"DB_URL", "API_KEY", "SECRET_KEY"}
BLOCKED_KEYS = {"PATH", "LD_PRELOAD", "PYTHONPATH"}
SAFE_VALUE = re.compile(r"^[a-zA-Z0-9_\-.:/@]+$")


def load_dotenv(dotenv_path: str = ".env") -> None:
    env_file = Path(dotenv_path)
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key in BLOCKED_KEYS:
            continue

        if key not in ALLOWED_KEYS:
            continue

        if not SAFE_VALUE.match(value):
            continue

        os.environ.setdefault(key, value)
