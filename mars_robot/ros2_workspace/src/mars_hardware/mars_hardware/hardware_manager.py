"""
Mars Robot Hardware Manager
Detects environment (Pi 5 vs Development) and provides appropriate hardware implementations
"""
import os
import platform
from typing import Dict, Any

from .interfaces.camera_interface import CameraInterface
from .interfaces.motor_interface import MotorInterface
from .interfaces.arm_interface import ArmInterface
from .interfaces.camera_servo_interface import CameraServoInterface
from .interfaces.audio_interface import AudioInterface
from .interfaces.display_interface import DisplayInterface
from .interfaces.display_overlay_interface import DisplayOverlayInterface

from .real.real_camera import RealCamera
from .real.real_motors import RealMotors
from .real.real_arms import RealArms
from .real.real_camera_servos import RealCameraServos
from .real.real_audio import RealAudio
from .real.real_display import RealDisplay
from .real.terminator_display_overlay import TerminatorDisplayOverlay


class HardwareManager:
    """Main hardware abstraction manager that detects environment and provides appropriate interfaces"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_pi = self.detect_pi_environment()
        # Force real hardware only - no mock hardware allowed
        self.force_mock = False

        self._initialize_hardware()

    def detect_pi_environment(self) -> bool:
        """Detect if we're running on a Raspberry Pi 5"""
        try:
            # Check for GPIO devices (gpiomem or gpiochip0)
            if not (os.path.exists('/dev/gpiomem') or os.path.exists('/dev/gpiochip0')):
                return False

            # Check CPU info for Pi hardware (BCM2835 for Pi 1-4, BCM2712 for Pi 5)
            with open('/proc/cpuinfo', 'r') as f:
                cpu_info = f.read()
                if 'bcm2835' not in cpu_info.lower() and 'bcm2712' not in cpu_info.lower():
                    return False

            # Check for Pi 5 specific hardware
            if os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read()
                    if 'raspberry pi 5' in model.lower():
                        return True

            return True
        except Exception:
            return False

    def _initialize_hardware(self):
        """Initialize hardware interfaces - only real hardware, no mock"""
        if not self.is_pi:
            print("⚠️  Warning: Not running on Raspberry Pi 5. Hardware may not function correctly.")

        # Camera Interface - always real hardware
        self.camera: CameraInterface = RealCamera(self.config.get('camera', {}))

        # Motor Interface (L298N dual motor driver) - always real hardware
        self.motors: MotorInterface = RealMotors(self.config.get('motors', {}))

        # Arm Interface (2 arms × 4 servos each) - always real hardware
        self.arms: ArmInterface = RealArms(self.config.get('arms', {}))

        # Camera Servo Interface (pan/tilt for camera) - always real hardware
        self.camera_servos: CameraServoInterface = RealCameraServos(self.config.get('camera_servos', {}))

        # Audio Interface (speaker + microphone) - always real hardware
        self.audio: AudioInterface = RealAudio(self.config.get('audio', {}))

        # Display Interface (emotion display) - always real hardware
        self.display: DisplayInterface = RealDisplay(self.config.get('display', {}))

        # Display Overlay Interface - use terminator terminal display
        self.display_overlay: DisplayOverlayInterface = TerminatorDisplayOverlay(self.config.get('display_overlay', {}))

        print("✅ Hardware manager initialized with REAL HARDWARE ONLY")

    def get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        return {
            'is_pi': self.is_pi,
            'force_mock': False,  # Never using mock hardware
            'platform': platform.system(),
            'architecture': platform.machine(),
            'using_real_hardware': True,  # Always using real hardware
            'display_overlay_type': 'terminator_terminal',
            'hardware_status': {
                'camera': self.camera.is_connected(),
                'motors': self.motors.is_connected(),
                'arms': self.arms.is_connected(),
                'camera_servos': self.camera_servos.is_connected(),
                'audio': self.audio.is_connected(),
                'display': self.display.is_connected(),
                'display_overlay': hasattr(self.display_overlay, 'is_initialized') and self.display_overlay.is_initialized
            }
        }

    def emergency_stop(self):
        """Emergency stop all hardware"""
        try:
            self.motors.emergency_stop()
            self.arms.emergency_stop()
            self.camera_servos.stop()
            print("Emergency stop executed successfully")
        except Exception as e:
            print(f"Error during emergency stop: {e}")

    def shutdown(self):
        """Graceful shutdown of all hardware"""
        try:
            self.camera.shutdown()
            self.motors.shutdown()
            self.arms.shutdown()
            self.camera_servos.shutdown()
            self.audio.shutdown()
            self.display.shutdown()
            self.display_overlay.shutdown()
            print("Hardware manager shutdown completed")
        except Exception as e:
            print(f"Error during shutdown: {e}")