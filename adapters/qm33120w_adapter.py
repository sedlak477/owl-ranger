import serial
import re
import logging
from typing import Dict, Any

from .base import MeasurementAdapter

logger = logging.getLogger(__name__)

class QM33120WAdapter(MeasurementAdapter):
    """
    Adapter for Qorvo QM33120W running the CLI binary.
    Parses textual logs containing 'distance[cm]' and 'loc_az_pdoa'.
    """
    def __init__(self, name: str, port: str, baudrate: str = "115200", timeout: str = "1", **kwargs):
        super().__init__(name, **kwargs)
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)
        self.serial = None
        
        self.pattern_distance = re.compile(r"distance\[cm\]=([0-9.-]+)")
        self.pattern_loc_az_pdoa = re.compile(r"loc_az_pdoa=([0-9.-]+)")
        self.pattern_loc_az = re.compile(r"loc_az=([0-9.-]+)")

    def __enter__(self):
        logger.info(f"[QM33120WAdapter:{self.name}] Connecting to {self.port} at {self.baudrate} bps...")
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout
        )
        self.serial.reset_input_buffer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.serial and self.serial.is_open:
            logger.info(f"[QM33120WAdapter:{self.name}] Disconnecting from {self.port}...")
            self.serial.close()

    def measure(self) -> Dict[str, Any]:
        """
        Reads a single line from the serial port and returns a measurement.
        Lines not containing 'distance[cm]' are treated as failures.
        """
        # Discard any buffered data so we read the freshest output from the device
        self.serial.reset_input_buffer()
        line = self.serial.readline().decode('utf-8', errors='ignore').strip()

        if not line:
            logger.warning(f"[QM33120WAdapter:{self.name}] Timeout reading from serial")
            return {
                "distance_cm": float('nan'),
                "loc_az_pdoa": float('nan'),
                "loc_az": float('nan'),
                "status": "timeout",
                "raw_response": "",
            }

        match_dist = self.pattern_distance.search(line)
        if not match_dist:
            logger.warning(f"[QM33120WAdapter:{self.name}] Failed to parse distance from response: {line}")
            return {
                "distance_cm": float('nan'),
                "loc_az_pdoa": float('nan'),
                "loc_az": float('nan'),
                "status": "failed",
                "raw_response": line,
            }

        distance_cm = float(match_dist.group(1))

        match_pdoa = self.pattern_loc_az_pdoa.search(line)
        loc_az_pdoa = float(match_pdoa.group(1)) if match_pdoa else float('nan')

        match_az = self.pattern_loc_az.search(line)
        loc_az = float(match_az.group(1)) if match_az else float('nan')

        return {
            "distance_cm": distance_cm,
            "loc_az_pdoa": loc_az_pdoa,
            "loc_az": loc_az,
            "status": "success",
            "raw_response": line,
        }
