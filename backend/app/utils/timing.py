"""Timing utilities for performance instrumentation."""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class TimingResult:
    """Holds timing results for multiple named operations."""
    _timings: dict[str, int] = field(default_factory=dict)

    def set(self, name: str, ms: int) -> None:
        self._timings[name] = ms

    def get(self, name: str) -> int:
        return self._timings.get(name, 0)

    @property
    def total_ms(self) -> int:
        return sum(self._timings.values())

    def to_dict(self) -> dict[str, int]:
        return dict(self._timings)


@contextmanager
def measure_time():
    """Context manager that yields a callable returning elapsed ms.

    Usage:
        with measure_time() as elapsed:
            do_work()
        duration_ms = elapsed()
    """
    start = time.perf_counter()
    result = {"ms": 0}

    def get_elapsed() -> int:
        return result["ms"]

    try:
        yield get_elapsed
    finally:
        result["ms"] = int((time.perf_counter() - start) * 1000)
