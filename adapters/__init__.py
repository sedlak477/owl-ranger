from typing import Dict, Type
import importlib
from .base import MeasurementAdapter

# Simple explicit registry mapping standard adapter types
_REGISTRY: Dict[str, Type[MeasurementAdapter]] = {}

_BUILTIN_ADAPTERS = {
    "dummy": (".dummy_adapter", "DummyAdapter"),
    "serial_ndjson": (".serial_ndjson_adapter", "SerialNDJSONAdapter"),
    "qm33120w": (".qm33120w_adapter", "QM33120WAdapter"),
    "nrf54_ble_cs": (".nrf54_ble_cs_adapter", "NRF54BLECSAdapter"),
    "nrf54_ble_cs_iq": (".nrf54_ble_cs_iq_adapter", "NRF54BLECSIQAdapter"),
    "pico_nrf24_sniffer": (".pico_nrf24_sniffer_adapter", "PicoNRF24SnifferAdapter"),
    "wifi_frequency": (".wifi_frequency_adapter", "WifiFrequencyAdapter"),
    "qualisys": (".qualisys_adapter", "QualisysAdapter"),
}

def register_adapter(adapter_type: str, adapter_class: Type[MeasurementAdapter]):
    """Registers a new adapter class under a specific string type."""
    _REGISTRY[adapter_type] = adapter_class

def get_adapter(adapter_type: str, name: str, **kwargs) -> MeasurementAdapter:
    """Instantiates a registered adapter by its type."""
    if adapter_type not in _REGISTRY and adapter_type in _BUILTIN_ADAPTERS:
        module_name, class_name = _BUILTIN_ADAPTERS[adapter_type]
        module = importlib.import_module(module_name, package=__name__)
        adapter_class = getattr(module, class_name)
        register_adapter(adapter_type, adapter_class)

    adapter_class = _REGISTRY.get(adapter_type)
    if not adapter_class:
        available = list(set(list(_REGISTRY.keys()) + list(_BUILTIN_ADAPTERS.keys())))
        raise ValueError(f"Unknown adapter type: '{adapter_type}'. Available adapters: {available}")
    
    # Pass arbitrary config kwargs to the chosen adapter instantiation
    return adapter_class(name=name, **kwargs)
