from __future__ import annotations

from secrets import compare_digest

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings
from app.core.dependencies import get_settings_dependency


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings_dependency),
) -> None:
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API write access is disabled until API_KEY is configured.",
        )

    if x_api_key is None or not compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
