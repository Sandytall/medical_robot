"""
Camera Interface for IMX477 Camera Management
"""
from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple, Optional, Dict, Any


class CameraInterface(ABC):
    """Abstract interface for camera operations"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize camera hardware"""
        pass

    @abstractmethod
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame and return as numpy array (BGR format)"""
        pass

    @abstractmethod
    def start_streaming(self) -> bool:
        """Start continuous video streaming"""
        pass

    @abstractmethod
    def stop_streaming(self):
        """Stop video streaming"""
        pass

    @abstractmethod
    def is_streaming(self) -> bool:
        """Check if camera is currently streaming"""
        pass

    @abstractmethod
    def set_resolution(self, width: int, height: int) -> bool:
        """Set camera resolution"""
        pass

    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Get current camera resolution as (width, height)"""
        pass

    @abstractmethod
    def set_fps(self, fps: int) -> bool:
        """Set frames per second"""
        pass

    @abstractmethod
    def get_fps(self) -> int:
        """Get current frames per second"""
        pass

    @abstractmethod
    def get_camera_info(self) -> Dict[str, Any]:
        """Get camera calibration and information"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if camera is connected and functional"""
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown camera and release resources"""
        pass