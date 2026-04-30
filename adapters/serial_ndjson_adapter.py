import serial
import json
import logging
from typing import Dict, Any

from .base import MeasurementAdapter

logger = logging.getLogger(__name__)

class SerialNDJSONAdapter(MeasurementAdapter):
    """
    A generic serial adapter supporting textual (JSON or CSV-like) 
    measurements from embedded devices.
    """
    def __init__(self, name: str, port: str, baudrate: int = 115200, timeout: float = 3.0, **kwargs):
        super().__init__(name, **kwargs)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def __enter__(self):
        logger.info(f"[SerialNDJSONAdapter:{self.name}] Connecting to {self.port} at {self.baudrate} bps...")
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout
        )
        self.serial.reset_input_buffer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.serial and self.serial.is_open:
            logger.info(f"[SerialNDJSONAdapter:{self.name}] Disconnecting from {self.port}...")
            self.serial.close()

    def measure(self) -> Dict[str, Any]:
        """
        Reads a single measurement from the serial port.
        Assumes the device responds with one JSON line per measurement.
        """
        self.serial.reset_input_buffer()

        line = None
        data = None
        for _ in range(2):
            line = self.serial.readline().decode('utf-8', errors='ignore').strip()
            
            if not line:
                break
                
            try:
                data = json.loads(line)
                break
            except json.JSONDecodeError:
                pass

        if not line:
            logger.warning(f"[{self.name}] Timeout reading from serial")
            return {"status": "timeout", "raw_response": line}
        
        if not data:
            logger.warning(f"[{self.name}] Could not parse line: {line}")
            return {"status": "parse_error", "raw_response": line}

        data["status"] = "success"
        data["raw_response"] = line
        return data
