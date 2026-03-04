import serial
import re
import logging
import math
from typing import List, Dict, Any

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
        
        # Regex to parse the relevant fields out of the response:
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
        # Flush initial garbage
        self.serial.reset_input_buffer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.serial and self.serial.is_open:
            logger.info(f"[QM33120WAdapter:{self.name}] Disconnecting from {self.port}...")
            self.serial.close()

    def measure_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        """
        Reads lines from the serial port until it finds `batch_size` 
        valid measurements containing distance and PDoA.
        """        
        # Flush the buffer to ensure we only get fresh measurements starting from now
        if self.serial and self.serial.is_open:
            self.serial.reset_input_buffer()

        results = []
        
        # We might need to send a command to start ranging, 
        # but the manual suggests it might stream INITF/RESPF logs automatically 
        # once the session is created through CLI commands or auto-started.
        # If an explicit trigger is needed per batch, it would be added here.
        
        # We read lines until we collect enough samples. 
        # We add a safety fallback counter to avoid spinning forever if disconnected.
        max_attempts = batch_size * 10
        attempts = 0
        
        while len(results) < batch_size and attempts < max_attempts:
            line = self.serial.readline().decode('utf-8', errors='ignore').strip()
            attempts += 1
            
            if not line:
                continue
                
            match_dist = self.pattern_distance.search(line)
            if match_dist:
                distance_cm = float(match_dist.group(1))
                
                # Optional fields
                match_pdoa = self.pattern_loc_az_pdoa.search(line)
                loc_az_pdoa = float(match_pdoa.group(1)) if match_pdoa else float('nan')
                
                match_az = self.pattern_loc_az.search(line)
                loc_az = float(match_az.group(1)) if match_az else float('nan')
                
                results.append({
                    "distance_cm": distance_cm,
                    "loc_az_pdoa": loc_az_pdoa,
                    "loc_az": loc_az,
                    "raw_response": line
                })
                
        if len(results) < batch_size:
            logger.warning(f"[{self.name}] Only collected {len(results)}/{batch_size} measurements due to timeouts.")

        return results
