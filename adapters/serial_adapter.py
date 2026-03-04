import serial
import json
import logging
from typing import List, Dict, Any

from .base import MeasurementAdapter

logger = logging.getLogger(__name__)

class SerialAdapter(MeasurementAdapter):
    """
    A generic serial adapter supporting textual (JSON or CSV-like) 
    measurements from embedded devices.
    """
    def __init__(self, name: str, port: str, baudrate: str = "115200", timeout: str = "1", **kwargs):
        super().__init__(name, **kwargs)
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)
        self.serial = None

    def __enter__(self):
        logger.info(f"[SerialAdapter:{self.name}] Connecting to {self.port} at {self.baudrate} bps...")
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.serial and self.serial.is_open:
            logger.info(f"[SerialAdapter:{self.name}] Disconnecting from {self.port}...")
            self.serial.close()

    def measure_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        """
        Requests and reads a batch of measurements from the serial port.
        Assumes the device responds with one JSON line per measurement.
        """
        logger.info(f"[SerialAdapter:{self.name}] Measuring batch of {batch_size}...")
        
        # Depending on the firmware, a command might need to be sent here, e.g.:
        # self.serial.write(f"MEASURE {batch_size}\n".encode())
        
        results = []
        for _ in range(batch_size):
            line = self.serial.readline().decode('utf-8').strip()
            
            if not line:
                logger.warning(f"[{self.name}] Timeout reading from serial")
                continue
                
            try:
                # Assuming JSON reporting format for generic extensibility
                data = json.loads(line)
                results.append(data)
            except json.JSONDecodeError:
                # Fallback to simple generic text reading if unparseable
                logger.warning(f"[{self.name}] Failed to parse JSON, saving raw: {line}")
                results.append({"raw_response": line})

        return results
