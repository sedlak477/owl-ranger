from typing import Dict, Any
from time import sleep

from .base import MeasurementAdapter
import logging

logger = logging.getLogger(__name__)

class WaitAdapter(MeasurementAdapter):
    """
    An adapter that only waits: each measure() call sleeps for `duration` seconds.
    Useful to slow down sampling, e.g. to let the payload settle between samples.
    """
    def __init__(self, name: str, duration: float, **kwargs):
        super().__init__(name, **kwargs)
        try:
            self.duration = float(duration)
        except (TypeError, ValueError):
            raise ValueError(f"duration must be a number of seconds, got '{duration}'")
        if self.duration < 0:
            raise ValueError(f"duration must not be negative, got {self.duration}")
        # Record the duration in the sidecar's adapter configuration
        self.config["duration"] = self.duration

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def measure(self) -> Dict[str, Any]:
        """Sleeps for the configured duration."""
        sleep(self.duration)
        return {"status": "success"}
