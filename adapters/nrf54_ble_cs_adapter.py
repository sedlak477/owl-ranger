import serial
import re
import logging
from typing import Dict, Any

from .base import MeasurementAdapter

logger = logging.getLogger(__name__)

class NRF54BLECSAdapter(MeasurementAdapter):
    """
    An adapter for nRF54 Bluetooth Low Energy Channel Sounding measurements using the nRF channel_sounding_ras_* example.
    """
    def __init__(self, name: str, port: str, baudrate: int = 115200, timeout: float = 1.0, **kwargs):
        super().__init__(name, **kwargs)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        
        self.pattern_ifft = re.compile(r"ifft: *([0-9.]+)")
        self.pattern_phase_slope = re.compile(r"phase_slope: *([0-9.]+)")
        self.pattern_rtt = re.compile(r"rtt: *([0-9.]+)")
        self.pattern_tone_quality = re.compile(r"tone_quality: *([0-9]+)")
        self.pattern_channel_iq = re.compile(r"c([0-9]+)\((-?[0-9.]+);(-?[0-9.]+)\|(-?[0-9.]+);(-?[0-9.]+)\)")

    def __enter__(self):
        logger.info(f"[NRF54BLECSAdapter:{self.name}] Connecting to {self.port} at {self.baudrate} bps...")
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout
        )
        self.serial.reset_input_buffer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.serial and self.serial.is_open:
            logger.info(f"[NRF54BLECSAdapter:{self.name}] Disconnecting from {self.port}...")
            self.serial.close()

    def measure(self) -> Dict[str, Any]:
        """
        Reads a single measurement from the serial port.
        The reading includes the IFFT, phase slope, and RTT distance estimates.
        """
        line = self.serial.readline().decode('utf-8', errors='ignore').strip()
        while self.serial.in_waiting > 0:
            line = self.serial.readline().decode('utf-8', errors='ignore').strip()
            
        if not line:
            logger.warning(f"[NRF54BLECSAdapter:{self.name}] Timeout reading from serial")
            return {"status": "serial_timeout"}

        match_ifft = self.pattern_ifft.search(line)
        match_phase_slope = self.pattern_phase_slope.search(line)
        match_rtt = self.pattern_rtt.search(line)   
        match_tone_quality = self.pattern_tone_quality.search(line)

        if not match_ifft or not match_phase_slope or not match_rtt:
            logger.warning(f"[NRF54BLECSAdapter:{self.name}] Failed to parse measurement from response: {line}")
            return {
                "status": "failed",
                "raw_response": line,
            }
        
        ifft = float(match_ifft.group(1))
        phase_slope = float(match_phase_slope.group(1))
        rtt = float(match_rtt.group(1))
        tone_quality = int(match_tone_quality.group(1)) if match_tone_quality else None
        channel_iq = {}
        for match in self.pattern_channel_iq.finditer(line):
            channel = int(match.group(1))
            init_real = float(match.group(2))
            init_imag = float(match.group(3))
            ref_real = float(match.group(4))
            ref_imag = float(match.group(5))
            channel_iq[channel] = (init_real, init_imag, ref_real, ref_imag)

        return {
            "ifft": ifft,
            "phase_slope": phase_slope,
            "rtt": rtt,
            "tone_quality": tone_quality,
            "channel_iq": channel_iq,
            "status": "success",
            "raw_response": line,
        }
