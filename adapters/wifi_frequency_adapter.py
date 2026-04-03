import subprocess
import re
from typing import Dict, Any

from .base import MeasurementAdapter
import logging

logger = logging.getLogger(__name__)

class WifiFrequencyAdapter(MeasurementAdapter):
    """
    An adapter to get the current channel of a wifi interface using iw CLI.
    """
    def __init__(self, name: str, interface: str, **kwargs):
        super().__init__(name, **kwargs)
        self.interface = interface

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def measure(self) -> Dict[str, Any]:
        """Returns a single dummy measurement."""
        output = subprocess.run(
            ["iw", "dev", self.interface, "link"],
            capture_output=True,
            text=True,
            check=True
        )

        freq_match = re.search(r"freq:\s*([0-9.]+)", output.stdout)
        if not freq_match:
            return {
                "wifi_freq": None,
            }

        return {
            "wifi_freq": float(freq_match.group(1)),
        }
