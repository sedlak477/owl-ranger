import serial
from typing import Dict, Any

from .base import MeasurementAdapter
import logging

logger = logging.getLogger(__name__)

class PicoNRF24SnifferAdapter(MeasurementAdapter):
    """
    Check channel occupancy of 2.4GHz ISM band using RP2040 and nRF24L01.
    Use firmware from TODO
    """
    def __init__(self, name: str, port: str, baudrate: int = 115200, **kwargs):
        super().__init__(name, **kwargs)
        self.port = port
        self.baudrate = baudrate
        self._serial = None
        self._buffer = b""
        self._cached_measurement = None

    def __enter__(self):
        logger.info(f"[PicoNRF24SnifferAdapter:{self.name}] Connecting to {self.port}...")
        self._serial = serial.Serial(self.port, self.baudrate, timeout=0)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info(f"[PicoNRF24SnifferAdapter:{self.name}] Disconnecting...")
        if self._serial:
            self._serial.close()
            self._serial = None

    def measure(self) -> Dict[str, Any]:
        """Returns instantly with latest cached measurement."""
        if self._serial and self._serial.in_waiting > 0:
            self._buffer += self._serial.read(self._serial.in_waiting)
            
            if b'\n' in self._buffer:
                lines = self._buffer.split(b'\n')
                self._buffer = lines[-1]
                
                # Find latest non-empty complete line
                for line in reversed(lines[:-1]):
                    decoded = line.decode('ascii', errors='ignore').strip()
                    if not decoded:
                        continue
                    try:
                        occupancy = [float(x) for x in decoded.split()]
                        self._cached_measurement = {
                            "occupancy": occupancy,
                            "status": "success"
                        }
                        break
                    except ValueError:
                        continue

        if self._cached_measurement:
            return self._cached_measurement
        return {"status": "waiting"}
