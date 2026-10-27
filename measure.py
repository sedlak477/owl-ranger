import re
from datetime import datetime
import os
import json
from types import TracebackType
from typing import Any
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from pyowl import OWL
import math
import time
from time import sleep
import argparse
import pandas as pd
from contextlib import ExitStack
import uuid
import logging
import serial.tools.list_ports
from wakepy import keep
import random
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("wakepy").setLevel(logging.WARNING)
logging.getLogger("tqdm").setLevel(logging.WARNING)

from adapters import get_adapter, MeasurementAdapter


def parse_adapter_config(config_str: str) -> MeasurementAdapter:
    """Parses a comma-separated key=value string and instantiates the adapter."""
    config = {}
    for part in config_str.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            config[k.strip()] = v.strip()
            
    if "type" not in config:
        raise argparse.ArgumentTypeError(f"Adapter config '{config_str}' is missing required 'type' field.")
        
    adapter_type = config.pop("type")
    name = config.pop("name", f"adapter_{uuid.uuid4().hex[:6]}")
    
    try:
        adapter_instance = get_adapter(adapter_type, name, **config)
        return adapter_instance
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Failed to instantiate adapter '{adapter_type}': {e}")


def parse_args():
    parser = argparse.ArgumentParser(description="OWL Measurement Script")
    parser.add_argument("--owl-port", type=str, default="auto", help="Serial port for the OWL platform (default: 'auto' for auto-discovery)")
    parser.add_argument("--angle-offset", type=float, default=0.0, help="Initial angle offset in radians (default: 0.0)")
    parser.add_argument("--steps", type=int, default=180, help="Number of angle steps (default: 180)")
    parser.add_argument("--samples", type=int, default=10, help="Measurements per angle (default: 10)")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle the order of the angles randomly (default: False)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for angle shuffling (default: None/random seed)")
    parser.add_argument("--no-led", action="store_true", help="Turn off the LED during measurement (default: False)")
    parser.add_argument("--out", type=str, default="out", help="Output directory (default: 'out')")
    parser.add_argument("--comment", type=str, default="", help="Optional comment to include in the sidecar metadata")
    parser.add_argument(
        "--adapter", 
        action="append", 
        default=[],
        type=parse_adapter_config,
        help="Adapter configuration string, e.g., 'type=dummy,name=sen1' or 'type=serial_ndjson,name=s1,port=/dev/ttyACM0,baudrate=115200'. Can be specified multiple times."
    )
    parser.add_argument(
        "--recover",
        type=str,
        default=None,
        metavar="JSONL",
        help="Convert an in-progress file (e.g. 'out/.20261023160703.inprogress.jsonl') from an aborted run to CSV instead of measuring. The OWL is not used."
    )
    return parser.parse_args()


TEMP_SUFFIX = ".inprogress"
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"


def temp_base_path(out_dir: str, start_timestamp: str) -> str:
    """Path prefix of the hidden in-progress files, e.g. 'out/.20261023160703.inprogress'."""
    return os.path.join(out_dir, f".{start_timestamp}{TEMP_SUFFIX}")


def read_jsonl(path: str) -> list[dict[str, Any]]:
    """Reads measurement records from a JSONL file, skipping a truncated or corrupt line from an aborted write."""
    records = []
    with open(path) as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"Skipping unparsable line {line_number} in {path}")
    return records


def write_csv(records: list[dict[str, Any]], filename: str):
    pd.DataFrame(records).to_csv(filename, index=False)
    logger.info(f"Measurements saved to {filename} ({len(records)} records)")


def recover(jsonl_path: str):
    """Writes the CSV and sidecar for an aborted run from its in-progress files, then removes them."""
    if not jsonl_path.endswith(f"{TEMP_SUFFIX}.jsonl"):
        raise ValueError(f"Not an in-progress file: {jsonl_path}")
    records = read_jsonl(jsonl_path)
    if not records:
        raise ValueError(f"No records found in {jsonl_path}")

    out_dir = os.path.dirname(jsonl_path)
    temp_base = jsonl_path.removesuffix(".jsonl")
    # Name the outputs after the last record, matching normal runs which are named after their end time
    timestamp = datetime.fromisoformat(records[-1]["timestamp"]).strftime(TIMESTAMP_FORMAT)
    final_base = os.path.join(out_dir, timestamp)
    if os.path.exists(f"{final_base}.csv"):
        raise FileExistsError(f"{final_base}.csv already exists, not overwriting")

    write_csv(records, f"{final_base}.csv")

    temp_sidecar = f"{temp_base}.md"
    if os.path.exists(temp_sidecar):
        last_step = records[-1]["step_idx"]
        with open(temp_sidecar, "a") as f:
            f.write("## Recovery\n\n")
            f.write(f"- **Recovered from**: `{os.path.basename(jsonl_path)}`\n")
            f.write("- **Note**: Timestamp above is the run start; the file name is the time of the last record\n")
            f.write(f"- **Records**: {len(records)}\n")
            f.write(f"- **Last Step Index**: {last_step} (run aborted, measurement incomplete)\n")
        os.replace(temp_sidecar, f"{final_base}.md")
        logger.info(f"Sidecar metadata saved to {final_base}.md")
    else:
        logger.warning(f"No sidecar found at {temp_sidecar}, metadata not recovered")

    os.remove(jsonl_path)


def create_sidecar(filename: str, args: argparse.Namespace, adapters: list, timestamp: str):
    """Generates the measurement sidecar markdown file with all metadata and adapter configurations."""
    with open(filename, "w") as f:
        f.write("# Measurement Metadata\n\n")
        if args.comment:
            f.write(f"**Comment**: {args.comment}\n\n")
        f.write(f"- **Initial Angle Offset [rad]**: {args.angle_offset}\n")
        f.write(f"- **Number of Angle Steps**: {args.steps}\n")
        f.write(f"- **Measurements per Angle**: {args.samples}\n")
        f.write(f"- **Shuffled Angles**: {args.shuffle}\n")
        if args.shuffle:
            f.write(f"- **Shuffle Seed**: {args.seed}\n")
        f.write(f"- **Adapters Configured**: {len(adapters)}\n")
        pretty_ts = datetime.strptime(timestamp, TIMESTAMP_FORMAT).strftime("%A, %d. %b %Y %H:%M:%S %Z")
        f.write(f"- **Timestamp**: {pretty_ts} ({timestamp})\n\n")
        
        if adapters:
            f.write("## Adapter Configurations\n\n")
            for adapter in adapters:
                f.write(f"### {adapter.name}\n")
                f.write(f"- **Type**: {adapter.__class__.__name__}\n")
                if hasattr(adapter, 'config') and adapter.config:
                    for k, v in adapter.config.items():
                        f.write(f"- **{k}**: {v}\n")
                f.write("\n")
    
    logger.info(f"Sidecar metadata saved to {filename}")


def find_owl_port() -> str:
    """Attempts to auto-discover the OWL platform serial port."""
    # We look for the known vendor/product ID pair or descriptor string for the Generic OWL
    # The known ID from the hardcoded path was something like 'Generic_OWL_E204E04D968BE7C6'
    # but more safely we can just scan for 'OWL' in the description or hwid.
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "OWL" in p.description or (p.hwid and "OWL" in p.hwid):
            logger.info(f"Auto-discovered OWL on {p.device}")
            return p.device
        
    raise RuntimeError("Could not auto-discover the OWL platform serial port. Please specify --owl-port manually.")


def main():
    args = parse_args()

    if args.recover:
        recover(args.recover)
        return

    os.makedirs(args.out, exist_ok=True)

    start_time = time.time()
    start_timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    temp_base = temp_base_path(args.out, start_timestamp)
    temp_jsonl = f"{temp_base}.jsonl"
    temp_sidecar = f"{temp_base}.md"

    step_size = 2 * math.pi / args.steps
    angles = list(range(args.steps))
    if args.shuffle:
        args.seed = random.randrange(sys.maxsize) if args.seed is None else args.seed
        logger.info(f"Shuffling angles with seed {args.seed}")
        random.Random(args.seed).shuffle(angles)

    # Determine OWL port
    owl_port = args.owl_port
    if owl_port.lower() == "auto":
        owl_port = find_owl_port()

    def handle_abort(exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> bool:
        """Registered first so it runs last, after the in-progress file is closed and flushed."""
        if exc_type is None:
            return False
        if os.path.exists(temp_jsonl) and os.path.getsize(temp_jsonl) > 0:
            logger.error(f"Measurement aborted. Recover partial data with: --recover {temp_jsonl}")
        else:
            # Nothing was recorded, so drop the in-progress files instead of leaving an orphaned sidecar
            for path in (temp_jsonl, temp_sidecar):
                if os.path.exists(path):
                    os.remove(path)
        return False

    with ExitStack() as stack:
        stack.push(handle_abort)
        # Make sure logs don't mess up the progress bars
        stack.enter_context(logging_redirect_tqdm())
        # Keep the system awake during the measurement
        stack.enter_context(keep.running())
        
        logger.info(f"Initializing OWL platform on {owl_port}...")
        owl = stack.enter_context(OWL(owl_port))

        try:
            if not args.no_led:
                owl.set_LED(True)
            owl.goto(0)

            logger.info("Initializing measuring adapters...")
            adapters = []
            for adapter_instance in args.adapter:
                ready_adapter = stack.enter_context(adapter_instance)
                adapters.append(ready_adapter)
                
            logger.info("Initialization complete.")

            # Stream records to a hidden in-progress file so an aborted run can be recovered with --recover
            create_sidecar(temp_sidecar, args, adapters, start_timestamp)
            jsonl_file = stack.enter_context(open(temp_jsonl, "a"))
            logger.info(f"Streaming measurements to {temp_jsonl}")

            pbar_outer = tqdm(list(enumerate(angles)), desc="Overall Progress")
            for step_idx, angle_idx in pbar_outer:
                current_angle = step_size * angle_idx + args.angle_offset
                owl.goto(current_angle)

                # Collect samples one at a time across all adapters, interleaved,
                # so each adapter's readings are as close in time as possible.
                for sample_idx in tqdm(range(args.samples), desc="Samples", leave=False):
                    for adapter in adapters:
                        measured_angle = owl.get_absolute_angle()
                        raw_angle = owl.get_mechanical_angle()
                        meas = adapter.measure()
                        meas_record = {
                            "timestamp": datetime.now().isoformat(),
                            "angle": current_angle,
                            "measured_angle": measured_angle,
                            "raw_angle": raw_angle,
                            "adapter_name": adapter.name,
                            "angle_idx": angle_idx,
                            "step_idx": step_idx,
                            "sample_idx": sample_idx,
                            **meas
                        }
                        jsonl_file.write(json.dumps(meas_record, default=str) + "\n")
                # Flush once per step: cheap, and bounds the loss on a crash to the current step
                jsonl_file.flush()

            jsonl_file.close()

            timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
            write_csv(read_jsonl(temp_jsonl), f"{args.out}/{timestamp}.csv")
            create_sidecar(f"{args.out}/{timestamp}.md", args, adapters, timestamp)

            os.remove(temp_jsonl)
            os.remove(temp_sidecar)

        finally:
            if not args.no_led:
                owl.set_LED(False)
    
    duration = time.time() - start_time
    minutes = int(duration // 60)
    seconds = duration % 60
    logger.info(f"Measurement took {minutes} min {seconds:.0f} sec")
    
    # Sound a bell to indicate completion
    print('\a', end='', flush=True)

if __name__ == "__main__":
    main()
