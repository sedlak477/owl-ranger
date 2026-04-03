from typing import Dict, Type
from .base import MeasurementAdapter

# Simple explicit registry mapping standard adapter types
_REGISTRY: Dict[str, Type[MeasurementAdapter]] = {}

def register_adapter(adapter_type: str, adapter_class: Type[MeasurementAdapter]):
    """Registers a new adapter class under a specific string type."""
    _REGISTRY[adapter_type] = adapter_class

def get_adapter(adapter_type: str, name: str, **kwargs) -> MeasurementAdapter:
    """Instantiates a registered adapter by its type."""
    adapter_class = _REGISTRY.get(adapter_type)
    if not adapter_class:
        raise ValueError(f"Unknown adapter type: '{adapter_type}'. Available adapters: {list(_REGISTRY.keys())}")
    
    # Pass arbitrary config kwargs to the chosen adapter instantiation
    return adapter_class(name=name, **kwargs)

# Implicitly load built-in adapters on initialization
from .dummy_adapter import DummyAdapter
from .serial_adapter import SerialAdapter
from .qm33120w_adapter import QM33120WAdapter
from .nrf54_ble_cs_adapter import NRF54BLECSAdapter
from .wifi_frequency_adapter import WifiFrequencyAdapter

register_adapter("dummy", DummyAdapter)
register_adapter("serial", SerialAdapter)
register_adapter("qm33120w", QM33120WAdapter)
register_adapter("nrf54_ble_cs", NRF54BLECSAdapter)
register_adapter("wifi_frequency", WifiFrequencyAdapter)
