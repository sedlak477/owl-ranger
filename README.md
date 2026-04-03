# OWL Ranger

## Usage

Requirements:

- [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)
- **Optional:** `iw` command line tool for when using the WiFi frequency adapter

Example usage:

```sh
uv run measure.py \
  --adapter 'type=<adapter>,name=<human-readable-name>,port=<serial-port>' \
  --steps <number-of-steps> \
  --step-delay <delay-after-each-step-in-seconds> \
  --comment "Comment to identify the measurement"
```

### Parameters

| Parameter           | Type    | Default | Description                                                              |
| :------------------ | :------ | :------ | :----------------------------------------------------------------------- |
| `--owl-port`        | `str`   | `auto`  | Serial port for the OWL platform (auto-discovery if 'auto').             |
| `--angle-offset`    | `float` | `0.0`   | Initial angle offset in radians.                                         |
| `--steps`           | `int`   | `180`   | Number of angle steps (full 360° rotation divided by this).              |
| `--samples`         | `int`   | `10`    | Measurements per angle step.                                             |
| `--step-delay`      | `float` | `1.0`   | Delay between angle steps in seconds.                                    |
| `--initial-backoff` | `float` | `3.0`   | Initial backoff delay in seconds.                                        |
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

#### `serial`

A generic adapter that reads JSON-formatted lines from a serial port.

- `port`: **Required**. Serial port.
- `baudrate`: (default: `115200`).

#### `wifi_frequency`

Captures the current Wi-Fi frequency/channel of the host machine.

- `interface`: **Required**. Wi-Fi interface name (e.g., `wlan0`).

#### `dummy`

Generates random values for testing without hardware.

- `min_val`: (default: `0.0`).
- `max_val`: (default: `100.0`).
- `delay`: Simulated latency in seconds (default: `0.05`).

---
