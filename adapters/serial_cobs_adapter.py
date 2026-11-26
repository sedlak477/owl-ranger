import binascii
import codecs
import logging
import time
from typing import Any, Dict, Optional

import serial

from .base import MeasurementAdapter

logger = logging.getLogger(__name__)

# Checks the adapter can run on a decoded frame. The CRC sits in the frame's last
# two bytes, little endian, and covers everything before it.
CRCS = ("none", "crc16")


def cobs_decode(data: bytes) -> Optional[bytes]:
    """Decode one COBS-encoded frame (without its 0x00). None if malformed."""
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        code = data[i]
        if code == 0 or i + code > n:
            return None
        out += data[i + 1:i + code]
        i += code
        if code != 0xFF and i < n:
            out.append(0)
    return bytes(out)


def crc16_ok(frame: bytes) -> bool:
    """CRC-16/CCITT-FALSE over all but the last two bytes, which hold it (LE)."""
    if len(frame) < 2:
        return False
    return binascii.crc_hqx(frame[:-2], 0xFFFF) == (frame[-2] | (frame[-1] << 8))


class CobsReader:
    """Reads 0x00-delimited COBS frames from an open serial port."""

    def __init__(self, ser: serial.Serial, crc: str = "none"):
        if crc not in CRCS:
            raise ValueError(f"crc must be one of {CRCS}, not '{crc}'")
        self.serial = ser
        self.crc = crc
        self.buf = bytearray()

    def clear(self):
        """Forget everything received so far, on the host and in this reader."""
        self.serial.reset_input_buffer()
        self.buf.clear()

    def read_frame(self, timeout: float) -> Optional[Dict[str, Any]]:
        """The next frame, or None if none completed within @timeout seconds.

        Returns {"frame": <decoded bytes as hex>, "cobs_ok": bool} plus
        "crc_ok" when a CRC is configured. A frame that does not decode keeps
        its raw bytes in "frame" with cobs_ok False. Empty frames (back-to-back
        delimiters) are skipped.
        """
        end = time.monotonic() + timeout
        while True:
            i = self.buf.find(0)
            while i == 0:  # a delimiter with nothing before it
                del self.buf[:1]
                i = self.buf.find(0)
            if i > 0:
                raw = bytes(self.buf[:i])
                del self.buf[:i + 1]
                return self._result(raw)
            left = end - time.monotonic()
            if left <= 0:
                return None
            self.serial.timeout = min(left, 0.05)
            self.buf += self.serial.read(max(1, self.serial.in_waiting))

    def _result(self, raw: bytes) -> Dict[str, Any]:
        frame = cobs_decode(raw)
        if frame is None:
            out = {"frame": raw.hex(), "cobs_ok": False}
            if self.crc != "none":
                out["crc_ok"] = False
            return out
        out = {"frame": frame.hex(), "cobs_ok": True}
        if self.crc == "crc16":
            out["crc_ok"] = crc16_ok(frame)
        return out


class SerialCOBSAdapter(MeasurementAdapter):
    """
    A generic serial adapter for devices that answer with one binary frame,
    COBS-encoded and terminated by 0x00.

    Each measurement clears the input, sends the optional request, and returns
    the next frame. Returns "frame" (the frame with COBS removed, as hex,
    otherwise untouched), "cobs_ok", "crc_ok" when a CRC is configured, and
    "bad_frames", the running count of bad frames. The status is "success",
    "failed" for a bad frame, or "timeout" when no frame arrives in time. A bad
    frame is kept in the data and counted; it is never retried. What is inside
    the frame is up to the device and is decoded afterwards, not here.
    """

    def __init__(self, name: str, port: str, baudrate: int = 115200, timeout: float = 1.0,
                 request: str = "", crc: str = "none", settle: float = 0.3, **kwargs):
        super().__init__(name, port=port, baudrate=baudrate, timeout=timeout,
                         request=request, crc=crc, settle=settle, **kwargs)
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)
        # Escapes as in a Python string, so request=x\n on the command line
        # sends "x" and a newline.
        self.request = codecs.decode(request, "unicode_escape").encode("latin-1")
        if crc not in CRCS:
            raise ValueError(f"crc must be one of {CRCS}, not '{crc}'")
        self.crc = crc
        self.settle = float(settle)
        self.serial = None
        self.reader = None
        self.bad_frames = 0

    def __enter__(self):
        logger.info(f"[SerialCOBSAdapter:{self.name}] Connecting to {self.port}...")
        self.serial = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        self.reader = CobsReader(self.serial, self.crc)
        # A device may announce itself when the port opens; let that arrive
        # and discard it, so the first measure() gets its own reply.
        time.sleep(self.settle)
        self.reader.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.serial and self.serial.is_open:
            logger.info(f"[SerialCOBSAdapter:{self.name}] Disconnecting from {self.port}...")
            self.serial.close()

    def measure(self) -> Dict[str, Any]:
        self.reader.clear()
        if self.request:
            self.serial.write(self.request)
        got = self.reader.read_frame(self.timeout)
        if got is None:
            logger.warning(f"[{self.name}] Timeout waiting for a frame")
            return {"status": "timeout", "bad_frames": self.bad_frames}

        good = got["cobs_ok"] and got.get("crc_ok", True)
        if not good:
            self.bad_frames += 1
            logger.warning(f"[{self.name}] Bad frame ({self.bad_frames} so far)")
        got["status"] = "success" if good else "failed"
        got["bad_frames"] = self.bad_frames
        return got
