from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque


class RollingAverageFilter:
    def __init__(self, window_size: int) -> None:
        self.window_size = window_size
        self._buffers: dict[str, Deque[int]] = defaultdict(
            lambda: deque(maxlen=self.window_size)
        )

    def push(self, key: str, value: int) -> float:
        buffer = self._buffers[key]
        buffer.append(value)
        return float(sum(buffer) / len(buffer))

    def clear(self) -> None:
        self._buffers.clear()
