"""Log every COBS frame a serial device sends, with the host time it arrived.

For devices that talk without being asked, such as the UWB tags, which send a
record for every exchange another device starts. Runs until Ctrl+C or
--duration, and writes one JSON line per frame:

    {"timestamp": "<ISO 8601>", "t_host": <epoch s>, "frame": "<hex>", "cobs_ok": true, "crc_ok": true}

"frame" is the frame with COBS removed and nothing else done to it, exactly as
the serial_cobs adapter returns it. A bad frame is written and counted like any
other. If the port disappears (USB unplugged) the logger waits for it to come
back and carries on in the same file.

    uv run log_frames.py --port /dev/serial/by-id/usb-ZEPHYR_uwb-responder_*-if00 \\
        --crc crc16 --out out/tag.jsonl
"""

import argparse
import json
import logging
import time
from datetime import datetime

import serial

from adapters.serial_cobs_adapter import CRCS, CobsReader

logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--port", required=True, help="serial port")
    p.add_argument("--baudrate", type=int, default=115200)
    p.add_argument("--crc", choices=CRCS, default="none", help="check each frame's CRC")
    p.add_argument("--out", required=True, help="JSON lines file, appended to")
    p.add_argument("--duration", type=float, help="stop after this many seconds")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    end = time.monotonic() + args.duration if args.duration else None
    n = bad = 0

    with open(args.out, "a") as out:
        try:
            while end is None or time.monotonic() < end:
                try:
                    with serial.Serial(args.port, args.baudrate, timeout=0.1) as ser:
                        logger.info(f"Logging {args.port} to {args.out}")
                        reader = CobsReader(ser, args.crc)
                        while end is None or time.monotonic() < end:
                            got = reader.read_frame(0.5)
                            if got is None:
                                continue
                            t = time.time()
                            n += 1
                            if not (got["cobs_ok"] and got.get("crc_ok", True)):
                                bad += 1
                            out.write(json.dumps({
                                "timestamp": datetime.fromtimestamp(t).isoformat(),
                                "t_host": t, **got}) + "\n")
                            out.flush()
                except (serial.SerialException, OSError) as e:
                    logger.warning(f"{args.port} unavailable ({e}), waiting for it")
                    time.sleep(1.0)
        except KeyboardInterrupt:
            pass
    logger.info(f"{n} frames, {bad} bad")


if __name__ == "__main__":
    main()
