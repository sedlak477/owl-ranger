from abc import ABC, abstractmethod
from typing import Dict, Any

class MeasurementAdapter(ABC):
    """
    Abstract Base Class for all measurement adapters.
    """
    def __init__(self, name: str, **kwargs):
        """
        Initializes the adapter.
        
        Args:
            name: A unique logical name for this adapter instance 
                  (useful when multiple adapters of the same type are used).
            **kwargs: Adapter-specific configuration parameters.
        """
        self.name = name
        self.config = kwargs
    
    @abstractmethod
    def __enter__(self):
        """
        Establish connection and perform setup.
        Returns the adapter instance.
        """
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Cleanly tear down the connection.
        """
        pass

    @abstractmethod
    def measure(self) -> Dict[str, Any]:
        """
        Request a single measurement from the device.
        
        Returns:
            A dictionary representing one measurement. Can contain arbitrary
            key-value pairs. Must always include a 'status' key with value
            'success', 'failed', or 'timeout'. On failure, numeric fields
            should be set to float('nan').
        """
        pass
