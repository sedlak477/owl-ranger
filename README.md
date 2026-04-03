# OWL Ranger

## Usage

Requirements: [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)

Example usage:
```sh
uv run measure.py --comment "Comment to identify the measurement" --adapter 'type=<adapter>,name=<human-readable-name>,port=<serial-port>' --steps <number-of-steps> --step-delay <delay-between-steps-in-seconds>
```

### Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--owl-port` | `str` | `auto` | Serial port for the OWL platform (auto-discovery if 'auto'). |
| `--angle-offset` | `float` | `0.0` | Initial angle offset in radians. |
| `--steps` | `int` | `180` | Number of angle steps. |
| `--samples` | `int` | `10` | Measurements per angle step. |
| `--step-delay` | `float` | `1.0` | Delay between angle steps in seconds. |
| `--initial-backoff` | `float` | `3.0` | Initial backoff delay in seconds. |
| `--out` | `str` | `out` | Output directory. |
| `--comment` | `str` | `""` | Optional comment for metadata. |
| `--adapter` | `list` | `[]` | Configuration for measurement adapters. Can be specified multiple times. |

#### Adapter Configuration
The `--adapter` parameter takes a comma-separated key=value string. At a minimum, it requires `type` and `name`.

Example:
`--adapter "type=serial,name=s1,port=/dev/ttyACM0,baudrate=115200"`

Available adapters:
- `dummy`: Dummy adapter for testing.
- `serial`: Serial adapter for reading JSON from a serial port.
- `qm33120w`: QM33120W adapter for reading from a QM33120W radio.
- `nrf54_ble_cs`: nRF54 BLE CS adapter for reading from an nRF54 BLE CS radio using the channel sounding example application.
