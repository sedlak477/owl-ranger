import serial
import re
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
        
        self.pattern_start = re.compile(r"--- QoS Connection Event Report ---")
        self.pattern_conn_evt = re.compile(r"conn_evt= *([0-9]+)")
        self.pattern_nak = re.compile(r"nak= *([0-9]+)")
        self.pattern_crc = re.compile(r"crc= *([0-9]+)")
        self.pattern_rx_to = re.compile(r"rx_to= *([0-9]+)")
        self.pattern_retx_est = re.compile(r"retx_est= *([0-9]+)")
        self.pattern_ifft = re.compile(r"ifft: *([0-9.]+)")
        self.pattern_phase_slope = re.compile(r"phase_slope: *([0-9.]+)")
        self.pattern_rtt = re.compile(r"rtt: *([0-9.]+)")
        self.pattern_de_quality = re.compile(r"DE Quality: *([a-zA-Z_]+)")
        self.pattern_received_power_level = re.compile(r"RPL: *(-?[0-9.]+)")
        self.pattern_channel_iq = re.compile(r"CH: *(\d+) *LI: *([+-]?\d+) *LQ: *([+-]?\d+) *LE: *([+-]?[0-9.]+) *RI: *([+-]?\d+) *RQ: *([+-]?\d+) *RE: *([+-]?[0-9.]+) *TQI: *([a-zA-Z_]+)")

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

        raw_lines = []
        # Find start of report
        while True:
            raw_line = self.serial.readline()
            if not raw_line:
                logger.warning(f"[NRF54BLECSIQAdapter:{self.name}] Timeout reading from serial")
                return {"status": "serial_timeout"}
            
            line = raw_line.decode('utf-8', errors='ignore').strip()
            if self.pattern_start.search(line):
                raw_lines.append(line)
                break

        data: Dict[str, Any] = {"channel_iq": {}}
        
        # Parse report until empty line
        while True:
            raw_line = self.serial.readline()
            if not raw_line:
                break
                
            line = raw_line.decode('utf-8', errors='ignore').strip()
            if not line:
                break
                
            raw_lines.append(line)
            
            if match := self.pattern_conn_evt.search(line):
                data["conn_evt"] = int(match.group(1))
            if match := self.pattern_nak.search(line):
                data["nak"] = int(match.group(1))
            if match := self.pattern_crc.search(line):
                data["crc"] = int(match.group(1))
            if match := self.pattern_rx_to.search(line):
                data["rx_to"] = int(match.group(1))
            if match := self.pattern_retx_est.search(line):
                data["retx_est"] = int(match.group(1))
            if match := self.pattern_ifft.search(line):
                data["ifft"] = float(match.group(1))
            if match := self.pattern_phase_slope.search(line):
                data["phase_slope"] = float(match.group(1))
            if match := self.pattern_rtt.search(line):
                data["rtt"] = float(match.group(1))
            if match := self.pattern_de_quality.search(line):
                data["de_quality"] = match.group(1)
            if match := self.pattern_received_power_level.search(line):
                data["rpl"] = float(match.group(1))
                
            for match in self.pattern_channel_iq.finditer(line):
                ch = int(match.group(1))
                if ch in data["channel_iq"]:
                    logger.warning(f"[NRF54BLECSIQAdapter:{self.name}] Duplicate channel IQ for channel {ch}")
                    
                data["channel_iq"][ch] = {
                    "li": int(match.group(2)),
                    "lq": int(match.group(3)),
                    "le": float(match.group(4)),
                    "ri": int(match.group(5)),
                    "rq": int(match.group(6)),
                    "re": float(match.group(7)),
                    "tqi": match.group(8)
                }

        data["status"] = "success"
        data["raw_response"] = "\n".join(raw_lines)
        return data
