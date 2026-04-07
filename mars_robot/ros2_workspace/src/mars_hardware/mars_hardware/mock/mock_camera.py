"""
Mock Camera Implementation for Development
"""
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any
import time
import threading

from ..interfaces.camera_interface import CameraInterface


class MockCamera(CameraInterface):
    """Mock camera implementation using webcam or generated images"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.width = self.config.get('resolution', [640, 480])[0]
        self.height = self.config.get('resolution', [640, 480])[1]
        self.fps = self.config.get('fps', 30)

        self.cap = None
        self.streaming = False
        self.use_webcam = self.config.get('use_webcam', True)
        self.generate_test_pattern = self.config.get('generate_test_pattern', False)

        # For generated test patterns
        self.frame_counter = 0
        self.last_frame = None
        self.streaming_thread = None

    def initialize(self) -> bool:
        """Initialize mock camera"""
        try:
            if self.use_webcam:
                # Try to open system webcam
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    print("No webcam found, switching to generated test pattern")
                    self.generate_test_pattern = True
                    self.use_webcam = False
                else:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            print(f"Mock camera initialized: {self.width}x{self.height} @ {self.fps}fps")
            return True
        except Exception as e:
            print(f"Mock camera initialization failed: {e}")
            return False

    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame"""
        try:
            if self.use_webcam and self.cap is not None:
                ret, frame = self.cap.read()
                if ret:
                    # Resize frame to specified resolution
                    frame = cv2.resize(frame, (self.width, self.height))
                    self.last_frame = frame
                    return frame

            # Generate test pattern
            frame = self._generate_test_frame()
            self.last_frame = frame
            return frame

        except Exception as e:
            print(f"Mock camera capture failed: {e}")
            return None

    def _generate_test_frame(self) -> np.ndarray:
        """Generate a test pattern frame"""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Add timestamp
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        cv2.putText(frame, f"Mock Camera {timestamp}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Add frame counter
        cv2.putText(frame, f"Frame: {self.frame_counter}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Add moving circle for motion
        center_x = int(self.width / 2 + 100 * np.sin(self.frame_counter * 0.1))
        center_y = int(self.height / 2 + 50 * np.cos(self.frame_counter * 0.1))
        cv2.circle(frame, (center_x, center_y), 20, (0, 0, 255), -1)

        # Add fake face rectangle (for face detection testing)
        face_x = int(self.width / 2 - 50)
        face_y = int(self.height / 2 - 50)
        cv2.rectangle(frame, (face_x, face_y), (face_x + 100, face_y + 100), (255, 0, 0), 2)
        cv2.putText(frame, "MOCK FACE", (face_x + 10, face_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

        self.frame_counter += 1
        return frame

    def start_streaming(self) -> bool:
        """Start continuous video streaming"""
        if self.streaming:
            return True

        self.streaming = True
        print("Mock camera streaming started")
        return True

    def stop_streaming(self):
        """Stop video streaming"""
        self.streaming = False
        print("Mock camera streaming stopped")

    def is_streaming(self) -> bool:
        """Check if camera is currently streaming"""
        return self.streaming

    def set_resolution(self, width: int, height: int) -> bool:
        """Set camera resolution"""
        self.width = width
        self.height = height

        if self.use_webcam and self.cap is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        print(f"Mock camera resolution set to {width}x{height}")
        return True

    def get_resolution(self) -> Tuple[int, int]:
        """Get current camera resolution"""
        return (self.width, self.height)

    def set_fps(self, fps: int) -> bool:
        """Set frames per second"""
        self.fps = fps

        if self.use_webcam and self.cap is not None:
            self.cap.set(cv2.CAP_PROP_FPS, fps)

        print(f"Mock camera FPS set to {fps}")
        return True

    def get_fps(self) -> int:
        """Get current frames per second"""
        return self.fps

    def get_camera_info(self) -> Dict[str, Any]:
        """Get camera calibration and information"""
        return {
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'format': 'BGR8',
            'camera_model': 'MockCamera_v1.0',
            'distortion_model': 'plumb_bob',
            'camera_matrix': [[800.0, 0.0, self.width/2], [0.0, 800.0, self.height/2], [0.0, 0.0, 1.0]],
            'distortion_coefficients': [0.0, 0.0, 0.0, 0.0, 0.0]
        }

    def is_connected(self) -> bool:
        """Check if camera is connected and functional"""
        if self.use_webcam:
            return self.cap is not None and self.cap.isOpened()
        return True  # Always connected for test pattern mode

    def shutdown(self):
        """Shutdown camera and release resources"""
        self.stop_streaming()
        if self.cap is not None:
            self.cap.release()
        print("Mock camera shutdown completed")