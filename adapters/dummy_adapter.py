import random
from typing import Dict, Any
from time import sleep

from .base import MeasurementAdapter
import logging

logger = logging.getLogger(__name__)

class DummyAdapter(MeasurementAdapter):
    """
    A simple dummy adapter that generates random measurements.
    Serving as a minimal blueprint for beginners.
    """
    def __init__(self, name: str, min_val: float = 0.0, max_val: float = 100.0, delay: float = 0.05, **kwargs):
        super().__init__(name, **kwargs)
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.delay = float(delay)

    def __enter__(self):
        logger.info(f"[DummyAdapter:{self.name}] Connecting...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info(f"[DummyAdapter:{self.name}] Disconnecting...")

    def measure(self) -> Dict[str, Any]:
        """Returns a single dummy measurement."""
        sleep(self.delay)
        return {
            "dummy_value": random.uniform(self.min_val, self.max_val),
            "status": "success",
        }
