"""
Real Camera Implementation for IMX477 on Raspberry Pi 5
"""
import cv2
import numpy as np
import threading
import time
from typing import Tuple, Optional, Dict, Any

from ..interfaces.camera_interface import CameraInterface

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False


class RealCamera(CameraInterface):
    """Real IMX477 camera implementation for Raspberry Pi 5 using picamera2"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.picam2 = None
        self.is_initialized = False
        self.is_streaming_active = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.capture_thread = None

        # Camera settings from config
        camera_config = self.config.get('camera', {})
        self.device = camera_config.get('device', '/dev/video0')
        self.resolution = camera_config.get('resolution', [640, 480])
        self.fps = camera_config.get('fps', 30)
        self.format = camera_config.get('format', 'BGR888')

    def initialize(self) -> bool:
        """Initialize IMX477 camera using picamera2"""
        if not PICAMERA_AVAILABLE:
            print("❌ RealCamera: picamera2 not available. Falling back to OpenCV...")
            return self._initialize_opencv()

        try:
            # Initialize picamera2
            self.picam2 = Picamera2()

            # Create camera configuration
            config = self.picam2.create_preview_configuration(
                main={"size": tuple(self.resolution), "format": self.format}
            )
            self.picam2.configure(config)

            # Start camera
            self.picam2.start()
            time.sleep(2)  # Allow camera to warm up

            self.is_initialized = True
            print(f"✅ RealCamera: IMX477 initialized via picamera2 ({self.resolution[0]}x{self.resolution[1]})")
            return True

        except Exception as e:
            print(f"❌ RealCamera picamera2 initialization failed: {e}")
            return self._initialize_opencv()

    def _initialize_opencv(self) -> bool:
        """Fallback initialization using OpenCV"""
        try:
            self.cap = cv2.VideoCapture(0)  # Use default camera
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            # Test capture
            ret, frame = self.cap.read()
            if ret:
                self.is_initialized = True
                print(f"✅ RealCamera: Initialized via OpenCV ({self.resolution[0]}x{self.resolution[1]})")
                return True
            else:
                print("❌ RealCamera: OpenCV test capture failed")
                return False

        except Exception as e:
            print(f"❌ RealCamera OpenCV initialization failed: {e}")
            return False

    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame from IMX477"""
        if not self.is_initialized:
            return None

        try:
            if self.picam2:
                # Use picamera2
                frame = self.picam2.capture_array()
                if frame is not None:
                    # Convert to BGR format for consistency
                    if len(frame.shape) == 3 and frame.shape[2] == 3:
                        return frame
                    else:
                        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                # Use OpenCV
                ret, frame = self.cap.read()
                return frame if ret else None

        except Exception as e:
            print(f"❌ RealCamera frame capture error: {e}")
            return None

        return None

    def start_streaming(self) -> bool:
        """Start continuous camera streaming"""
        if not self.is_initialized or self.is_streaming_active:
            return False

        try:
            self.is_streaming_active = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            print("✅ RealCamera: Streaming started")
            return True

        except Exception as e:
            print(f"❌ RealCamera streaming start error: {e}")
            self.is_streaming_active = False
            return False

    def _capture_loop(self):
        """Continuous capture loop for streaming"""
        while self.is_streaming_active:
            try:
                frame = self.capture_frame()
                if frame is not None:
                    with self.frame_lock:
                        self.current_frame = frame

                # Control frame rate
                time.sleep(1.0 / self.fps)

            except Exception as e:
                print(f"❌ RealCamera capture loop error: {e}")
                break

    def stop_streaming(self):
        """Stop camera streaming"""
        self.is_streaming_active = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        print("✅ RealCamera: Streaming stopped")

    def is_streaming(self) -> bool:
        """Check if camera is currently streaming"""
        return self.is_streaming_active

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the most recent frame from streaming"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def set_resolution(self, width: int, height: int) -> bool:
        """Set camera resolution"""
        try:
            # Stop streaming if active
            was_streaming = self.is_streaming_active
            if was_streaming:
                self.stop_streaming()

            self.resolution = [width, height]

            if self.picam2:
                # Reconfigure picamera2
                config = self.picam2.create_preview_configuration(
                    main={"size": (width, height), "format": self.format}
                )
                self.picam2.configure(config)
            else:
                # Set OpenCV resolution
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

            # Restart streaming if it was active
            if was_streaming:
                self.start_streaming()

            print(f"✅ RealCamera: Resolution set to {width}x{height}")
            return True

        except Exception as e:
            print(f"❌ RealCamera resolution change error: {e}")
            return False

    def get_resolution(self) -> Tuple[int, int]:
        """Get current camera resolution"""
        return tuple(self.resolution)

    def set_fps(self, fps: int) -> bool:
        """Set camera FPS"""
        try:
            self.fps = fps
            if not self.picam2 and hasattr(self, 'cap'):
                self.cap.set(cv2.CAP_PROP_FPS, fps)
            print(f"✅ RealCamera: FPS set to {fps}")
            return True
        except Exception as e:
            print(f"❌ RealCamera FPS change error: {e}")
            return False

    def get_fps(self) -> int:
        """Get current camera FPS"""
        return self.fps

    def get_camera_info(self) -> Dict[str, Any]:
        """Get camera information"""
        info = {
            'initialized': self.is_initialized,
            'streaming': self.is_streaming_active,
            'resolution': self.resolution,
            'fps': self.fps,
            'device': self.device,
            'backend': 'picamera2' if self.picam2 else 'opencv',
            'picamera2_available': PICAMERA_AVAILABLE
        }

        if self.picam2:
            try:
                info['camera_properties'] = self.picam2.camera_properties
            except:
                pass

        return info

    def is_connected(self) -> bool:
        """Check if camera is connected and working"""
        if not self.is_initialized:
            return False

        # Quick test capture
        test_frame = self.capture_frame()
        return test_frame is not None

    def shutdown(self):
        """Properly shutdown camera and cleanup resources"""
        try:
            # Stop streaming
            if self.is_streaming_active:
                self.stop_streaming()

            # Cleanup picamera2
            if self.picam2:
                self.picam2.stop()
                self.picam2.close()
                self.picam2 = None

            # Cleanup OpenCV
            if hasattr(self, 'cap'):
                self.cap.release()

            self.is_initialized = False
            print("✅ RealCamera: Shutdown completed")

        except Exception as e:
            print(f"⚠️  RealCamera shutdown error: {e}")