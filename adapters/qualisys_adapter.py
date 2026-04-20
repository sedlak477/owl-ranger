from typing import Dict, Any
from qtm_rt import connect
from .base import MeasurementAdapter
import asyncio
import logging

logger = logging.getLogger(__name__)

class QualisysAdapter(MeasurementAdapter):
    """
    Adapter for Qualisys motion capture system.
    """
    def __init__(self, name: str, host: str, port: int = 22223, **kwargs):
        super().__init__(name, **kwargs)
        
        self.host = host
        self.port = port
        self.connection = None
        self.loop = None

    def __enter__(self):
        logger.info(f"[QualisysAdapter:{self.name}] Connecting to {self.host}:{self.port}...")
        self.loop = asyncio.new_event_loop()
        self.connection = self.loop.run_until_complete(connect(self.host, port=self.port))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info(f"[QualisysAdapter:{self.name}] Disconnecting...")
        if self.connection:
            self.connection.disconnect()
        if self.loop:
            self.loop.close()

    def measure(self) -> Dict[str, Any]:
        """Returns a single dummy measurement."""
        frame = self.loop.run_until_complete(self.connection.get_current_frame(["6deuler"]))

        component, bodies = frame.get_6d_euler()

        return {
            "bodies": [{
                "position": {
                    "x": position.x,
                    "y": position.y,
                    "z": position.z
                },
                "rotation": {
                    "roll": angles.a1,
                    "pitch": angles.a2,
                    "yaw": angles.a3
                }
            } for (position, angles) in bodies]
        }
