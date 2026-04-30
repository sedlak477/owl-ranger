# OWL Ranger

## Usage

Requirements:

- [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)
- **Optional:** `iw` command line tool for when using the WiFi frequency adapter

Example usage:

```sh
uv run measure.py \
  --adapter 'type=<adapter>,name=<adapter identifier>,port=<serial-port>' \
  --steps <number-of-steps> \
  --comment "Comment to identify the measurement"
```

### Parameters

| Parameter           | Type    | Default | Description                                                              |
| :------------------ | :------ | :------ | :----------------------------------------------------------------------- |
| `--owl-port`        | `str`   | `auto`  | Serial port for the OWL platform (auto-discovery if 'auto').             |
| `--angle-offset`    | `float` | `0.0`   | Initial angle offset in radians.                                         |
| `--steps`           | `int`   | `180`   | Number of angle steps (full 360° rotation divided by this).              |
| `--samples`         | `int`   | `10`    | Measurements per angle step.                                             |
| `--no-led`          | `bool`  | `False` | Don't use the user LED to indicate progress.                             |
| `--out`             | `str`   | `out`   | Output directory.                                                        |
| `--comment`         | `str`   | `""`    | Optional comment for metadata.                                           |
| `--adapter`         | `list`  | `[]`    | Configuration for measurement adapters. Can be specified multiple times. |

### Adapter Configuration

The `--adapter` parameter takes a comma-separated `key=value` string. At a minimum, it requires `type`.

Available adapter types and their specific parameters:

#### `qm33120w`

For reading from a QM33120W radio using the Qorvo CLI application.

- `port`: **Required**. Serial port.
- `baudrate`: Connection speed (default: `115200`).
- `timeout`: Read timeout in seconds (default: `1.0`).

#### `nrf54_ble_cs`

For reading from an nRF54 radio using the Nordic Channel Sounding example.

- `port`: **Required**. Serial port.
- `baudrate`: Connection speed (default: `115200`).

#### `nrf54_ble_cs_iq`

For reading from an nRF54 radio using custom Channel Sounding firmware which forwards raw IQ values.

- `port`: **Required**. Serial port.
- `baudrate`: Connection speed (default: `1000000`).

#### `serial_ndjson`

A generic adapter that reads NDJSON-formatted lines from a serial port.

- `port`: **Required**. Serial port.
- `baudrate`: (default: `115200`).
- `timeout`: Read timeout in seconds (default: `3.0`).

#### `wifi_frequency`

Captures the current Wi-Fi frequency/channel of the host machine.

Requires `iw` command line tool to be installed.

- `interface`: **Required**. Wi-Fi interface name (e.g., `wlan0`).

#### `qualisys`

For reading from a Qualisys motion capture system.

Requires `qualisys` optional dependencies, install with `uv sync --extra qualisys`.

Currently on supports 6DOF body tracking with euler angles.

- `host`: **Required**. Hostname or IP address of the Qualisys system.
- `port`: (default: `22223`). Port for the Qualisys system.

#### `pico_nrf24_sniffer`

For reading 2.4GHz ISM band channel occupancy from a Raspberry Pi Pico with an nRF24L01 module.
See TODO for firmware.

- `port`: **Required**. Serial port.
- `baudrate`: Connection speed (default: `115200`).

#### `dummy`

Generates random values for testing without hardware.

- `min_val`: (default: `0.0`).
- `max_val`: (default: `100.0`).
- `delay`: Simulated latency in seconds (default: `0.05`).

---

## Related repositories

[owl-firmware](https://github.com/sedlak477/owl-firmware): The firmware for the OWL platform.  
[pyowl](https://github.com/sedlak477/pyowl): A python library for interacting with the OWL.

## AI Disclosure

Large parts of the project were created with the help of AI tooling.
