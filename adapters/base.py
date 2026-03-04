from abc import ABC, abstractmethod
from typing import List, Dict, Any

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
    def measure_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        """
        Request a batch of measurements from the device.
        
        Args:
            batch_size: Number of measurements to collect.
            
        Returns:
            A list of measurement dictionaries. Each dictionary represents
            one measurement and can contain arbitrary key-value pairs representing
            the read data. Minimum expected structure is adapter-dependent.
        """
        pass
