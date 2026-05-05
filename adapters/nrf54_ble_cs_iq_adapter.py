import serial
import json
import logging
from typing import Dict, Any

from .base import MeasurementAdapter

logger = logging.getLogger(__name__)

class NRF54BLECSIQAdapter(MeasurementAdapter):
    """
    An adapter for nRF54 Bluetooth Low Energy Channel Sounding IQ measurements using custom firmware.
    """
    def __init__(self, name: str, port: str, baudrate: int = 1000000, timeout: float = 1.0, **kwargs):
        super().__init__(name, **kwargs)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def __enter__(self):
        logger.info(f"[NRF54BLECSIQAdapter:{self.name}] Connecting to {self.port} at {self.baudrate} bps...")
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout
        )
        self.serial.reset_input_buffer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.serial and self.serial.is_open:
            logger.info(f"[NRF54BLECSIQAdapter:{self.name}] Disconnecting from {self.port}...")
            self.serial.close()

    def measure(self) -> Dict[str, Any]:
        """
        Reads a single measurement from the serial port.
        Discards old measurements in the buffer and reads the latest report.
        """
        self.serial.reset_input_buffer()

        data = None
        line = None
        for _ in range(2):
            try:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    data = json.loads(line)
                    break
            except json.JSONDecodeError:
                pass

        if data is None:
            logger.warning(f"[NRF54BLECSIQAdapter:{self.name}] Error reading JSON from serial port. Last line: {line}")
            return {"status": "read_failed", "raw_response": line}
        
        data["status"] = "success"
        data["raw_response"] = line

        return data
