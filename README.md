# OWL Ranger

A script for stepping through orientations and recording measurements.

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
| `--motor`           | `str`   | `""`    | SimpleFOC motor settings applied at the start, e.g. `VP=0.5,AP=20,LV=3.14`. Can be specified multiple times. |
| `--recover`         | `str`   | `None`  | Convert an in-progress file from an aborted run to CSV instead of measuring. |

### Motor settings

`--motor` sets SimpleFOC motor settings through [pyowl](https://github.com/sedlak477/pyowl) before the OWL moves to 0, e.g. the velocity and angle PID gains (`VP`, `VI`, `VD`, `VR`, `VL`, `AP`, ...) and the velocity limit (`LV`, rad/s). The codes are the firmware's `M` commands without the `M`. Settings stay in effect until the OWL restarts, so the sidecar records the angle/velocity PID settings and limits read back from the OWL on every run, marking the ones set via `--motor`.

### Partial results and recovery

While measuring, records are streamed to a hidden `.<start-timestamp>.inprogress.jsonl` file (plus a matching `.md` sidecar) in the output directory, flushed after every angle step.
On success they are converted to `<timestamp>.csv` / `<timestamp>.md` and removed.
If a run is aborted after recording data, the in-progress files are kept (use `ls -a` to see them) and can be converted without the OWL:

```sh
uv run measure.py --recover out/.20261023160703.inprogress.jsonl
```

The recovered sidecar gets a `Recovery` section noting the record count and last step index.

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
- `use_dtr`: If `true`, toggles DTR pin on only when reading measurements (default: `false`).

#### `serial_cobs`

A generic adapter for devices that answer with one binary frame, COBS-encoded and terminated by `0x00`.
Each measurement clears the input, sends the optional request, and returns the next frame.

- `port`: **Required**. Serial port.
- `baudrate`: Connection speed (default: `115200`).
- `timeout`: Seconds to wait for the frame (default: `1.0`).
- `request`: Bytes to send before each measurement, with Python string escapes, e.g. `request=x` or `request=x\n` (default: none, just read the next frame).
- `crc`: `crc16` checks the frame's last two bytes as a little-endian CRC-16/CCITT-FALSE over the rest (default: `none`).
- `settle`: Seconds to wait after opening before discarding input, so a frame the device sends when the port opens is not taken as the first reply (default: `0.3`).

Returns `frame` (the frame with COBS removed, as hex, otherwise untouched), `cobs_ok`, `crc_ok` when a CRC is configured, and `bad_frames`, the running count of bad frames.
The status is `success`, `failed` for a bad frame, or `timeout` when no frame arrives in time.
A bad frame is kept in the data and counted; it is never retried. What is inside the frame is up to the device and is decoded afterwards, not here.

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

#### `wait`

Records nothing, each measurement just sleeps.

- `duration`: **Required**. Sleep time in seconds.

The duration is per sample, so with `--samples N` each angle step waits `N * duration`.

---

## Related resources

[owl-firmware](https://github.com/sedlak477/owl-firmware): The firmware for the OWL platform.  
[pyowl](https://github.com/sedlak477/pyowl): A python library for interacting with the OWL.  
[owl-hardware](https://github.com/sedlak477/owl-hardware): Hardware design files for the OWL platform.  
[Dataset](https://doi.org/10.3217/kh254-z8374): Orientation-diverse BLE Channel Sounding and UWB ranging measurements recorded with the OWL.

## AI Disclosure

Large parts of the project were created with the help of AI tooling.
