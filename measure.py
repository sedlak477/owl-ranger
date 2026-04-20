import re
from datetime import datetime
import os
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from pyowl import OWL
import math
from time import sleep
import argparse
import pandas as pd
from contextlib import ExitStack
import uuid
import logging
import serial.tools.list_ports
from wakepy import keep

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
    parser.add_argument("--step-delay", type=float, default=1.0, help="Delay between angle steps in seconds (default: 1.0)")
    parser.add_argument("--initial-backoff", type=float, default=3.0, help="Initial backoff delay in seconds (default: 3.0)")
    parser.add_argument("--no-led", action="store_true", help="Turn off the LED during measurement (default: False)")
    parser.add_argument("--out", type=str, default="out", help="Output directory (default: 'out')")
    parser.add_argument("--comment", type=str, default="", help="Optional comment to include in the sidecar metadata")
    parser.add_argument(
        "--adapter", 
        action="append", 
        default=[],
        type=parse_adapter_config,
        help="Adapter configuration string, e.g., 'type=dummy,name=sen1' or 'type=serial,name=s1,port=/dev/ttyACM0,baudrate=115200'. Can be specified multiple times."
    )
    return parser.parse_args()


def create_sidecar(filename: str, args: argparse.Namespace, adapters: list, timestamp: str):
    """Generates the measurement sidecar markdown file with all metadata and adapter configurations."""
    with open(filename, "w") as f:
        f.write("# Measurement Metadata\n\n")
        if args.comment:
            f.write(f"**Comment**: {args.comment}\n\n")
        f.write(f"- **Initial Angle Offset [rad]**: {args.angle_offset}\n")
        f.write(f"- **Number of Angle Steps**: {args.steps}\n")
        f.write(f"- **Measurements per Angle**: {args.samples}\n")
        f.write(f"- **Adapters Configured**: {len(adapters)}\n")
        f.write(f"- **Timestamp**: {timestamp}\n\n")
        
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
    os.makedirs(args.out, exist_ok=True)

    step_size = 2 * math.pi / args.steps
    all_measurements = []

    # Determine OWL port
    owl_port = args.owl_port
    if owl_port.lower() == "auto":
        owl_port = find_owl_port()

    with ExitStack() as stack:
        # Make sure logs don't mess up the progress bars
        stack.enter_context(logging_redirect_tqdm())
        # Keep the system awake during the measurement
        stack.enter_context(keep.running())
        
        logger.info(f"Initializing OWL platform on {owl_port}...")
        owl = stack.enter_context(OWL(owl_port))

        try:
            if not args.no_led:
                owl.set_LED(True)
            owl.set_target(0)
            owl._serial.flush()
            sleep(args.initial_backoff)

            logger.info("Initializing measuring adapters...")
            adapters = []
            for adapter_instance in args.adapter:
                ready_adapter = stack.enter_context(adapter_instance)
                adapters.append(ready_adapter)
                
            logger.info("Initialization complete.")
            
            # We start with empty results list, will be populated within the loop
            pbar_outer = tqdm(range(args.steps), desc="Overall Progress")
            for i in pbar_outer:
                current_angle = step_size * i + args.angle_offset
                owl.set_target(current_angle)
                sleep(args.step_delay)

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
                            "angle_idx": i,
                            "sample_idx": sample_idx,
                            **meas
                        }
                        all_measurements.append(meas_record)

            df = pd.DataFrame(all_measurements)
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{args.out}/{timestamp}.csv"

            df.to_csv(filename, index=False)
            logger.info(f"Measurements saved to {filename}")

            sidecar_filename = f"{args.out}/{timestamp}.md"
            create_sidecar(sidecar_filename, args, adapters, timestamp)

        finally:
            if not args.no_led:
                owl.set_LED(False)
    
    # Sound a bell to indicate completion
    print('\a', end='', flush=True)

if __name__ == "__main__":
    main()
