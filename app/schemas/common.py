from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    detail: str
