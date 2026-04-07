#!/usr/bin/env python3
"""
Follow Mode System for Mars Robot
Handles "Hey mars follow me" functionality with face tracking and movement
"""
import time
import json
import math
import threading
from typing import Dict, Any, Optional, Tuple, List

import cv2
import numpy as np
import rclpy
from rclpy.node import Node

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False


class FollowMode(Node):
    """Face following behavior handler"""

    def __init__(self, hardware_manager, database, config: Dict[str, Any]):
        super().__init__('follow_mode')

        self.hardware = hardware_manager
        self.database = database
        self.config = config

        # Follow state
        self.follow_active = False
        self.target_found = False
        self.target_person = None
        self.last_detection_time = time.time()
        self.search_timeout = 15.0  # Seconds to search for registered face

        # Movement parameters
        self.target_distance = self.config.get('modes', {}).get('follow', {}).get('target_distance', 1.5)
        self.max_distance = self.config.get('modes', {}).get('follow', {}).get('max_distance', 3.0)
        self.stop_distance = self.config.get('modes', {}).get('follow', {}).get('stop_distance', 0.8)
        self.min_confidence = self.config.get('modes', {}).get('follow', {}).get('min_confidence', 0.4)

        # Speed parameters
        self.linear_speed = self.config.get('modes', {}).get('follow', {}).get('linear_speed', 0.5)
        self.angular_speed = self.config.get('modes', {}).get('follow', {}).get('angular_speed', 1.0)

        # Camera tracking parameters
        self.camera_tracking = self.config.get('modes', {}).get('follow', {}).get('camera_tracking', True)
        self.pan_gain = self.config.get('modes', {}).get('follow', {}).get('pan_gain', 0.5)
        self.tilt_gain = self.config.get('modes', {}).get('follow', {}).get('tilt_gain', 0.3)

        # Face detection
        self.face_cascade = self._load_face_cascade()

        # Movement state
        self.current_linear = 0.0
        self.current_angular = 0.0
        self.following_thread = None

        self.get_logger().info("Follow Mode system initialized")

    def _load_face_cascade(self):
        """Load OpenCV face detection cascade"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            return cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            self.get_logger().error(f"Failed to load face cascade: {e}")
            return None

    def start_follow_mode(self) -> bool:
        """Start follow mode"""
        try:
            if self.follow_active:
                self.get_logger().warning("Follow mode already active")
                return False

            self.follow_active = True
            self.target_found = False
            self.target_person = None
            self.last_detection_time = time.time()

            # Set display to follow mode
            if self.hardware.display:
                self.hardware.display.show_follow_mode()

            # Announce follow mode activation
            if self.hardware.audio:
                self.hardware.audio.play_text("Follow mode activated. Looking for a registered person to follow.")

            # Start camera if not streaming
            if not self.hardware.camera.is_streaming():
                self.hardware.camera.start_streaming()

            # Center camera initially
            if self.hardware.camera_servos:
                self.hardware.camera_servos.center_camera()

            # Start following thread
            self.following_thread = threading.Thread(target=self._follow_loop, daemon=True)
            self.following_thread.start()

            self.get_logger().info("Follow mode started - searching for registered face")
            return True

        except Exception as e:
            self.get_logger().error(f"Follow mode start error: {e}")
            return False

    def stop_follow_mode(self):
        """Stop follow mode"""
        try:
            if not self.follow_active:
                return

            self.follow_active = False
            self.target_found = False

            # Stop robot movement
            self._stop_movement()

            # Center camera
            if self.hardware.camera_servos:
                self.hardware.camera_servos.center_camera()

            # Announce mode exit
            if self.hardware.audio:
                self.hardware.audio.play_text("Follow mode deactivated")

            self.get_logger().info("Follow mode stopped")

        except Exception as e:
            self.get_logger().error(f"Follow mode stop error: {e}")

    def _follow_loop(self):
        """Main follow loop"""
        try:
            search_start_time = time.time()

            while self.follow_active:
                try:
                    # Check for timeout if no target found
                    if not self.target_found:
                        elapsed = time.time() - search_start_time
                        if elapsed > self.search_timeout:
                            self.get_logger().info("Follow mode timeout - no registered person found")
                            if self.hardware.audio:
                                self.hardware.audio.play_text("No registered person found. Exiting follow mode.")
                            self.stop_follow_mode()
                            break

                    # Capture frame from camera
                    frame = self.hardware.camera.capture_frame()
                    if frame is None:
                        time.sleep(0.1)
                        continue

                    # Process frame for face detection and following
                    self._process_frame(frame)

                    # Control loop frequency
                    time.sleep(0.1)  # 10Hz

                except Exception as e:
                    self.get_logger().error(f"Follow loop error: {e}")
                    time.sleep(1.0)

        except Exception as e:
            self.get_logger().error(f"Follow thread error: {e}")

    def _process_frame(self, frame: np.ndarray):
        """Process camera frame for face detection and tracking"""
        try:
            # Detect faces in frame
            faces = self._detect_faces(frame)

            if not faces:
                # No faces detected
                self._handle_no_faces()
                return

            # Find registered faces
            registered_face = self._find_registered_face(frame, faces)

            if registered_face:
                face_rect, person_info, confidence = registered_face
                self._handle_face_detected(frame, face_rect, person_info, confidence)
            else:
                # No registered faces found
                self._handle_no_registered_faces()

        except Exception as e:
            self.get_logger().error(f"Frame processing error: {e}")

    def _detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in frame using OpenCV"""
        try:
            if self.face_cascade is None:
                return []

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=4,
                minSize=(30, 30)
            )
            return faces

        except Exception as e:
            self.get_logger().warning(f"Face detection error: {e}")
            return []

    def _find_registered_face(self, frame: np.ndarray, faces: List[Tuple[int, int, int, int]]) -> Optional[Tuple]:
        """Find registered faces among detected faces"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                return None

            # Convert frame to RGB for face_recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Get face encodings for all detected faces
            face_encodings = face_recognition.face_encodings(rgb_frame)

            if not face_encodings:
                return None

            # Match each face encoding against database
            for i, face_encoding in enumerate(face_encodings):
                patient = self.database.get_patient_by_face(face_encoding, tolerance=0.6)

                if patient and patient['confidence'] >= self.min_confidence:
                    # Find corresponding face rectangle
                    if i < len(faces):
                        face_rect = faces[i]
                        return (face_rect, patient, patient['confidence'])

            return None

        except Exception as e:
            self.get_logger().warning(f"Registered face search error: {e}")
            return None

    def _handle_face_detected(self, frame: np.ndarray, face_rect: Tuple[int, int, int, int],
                            person_info: Dict[str, Any], confidence: float):
        """Handle when a registered face is detected"""
        try:
            x, y, w, h = face_rect

            if not self.target_found:
                # First detection of target
                self.target_found = True
                self.target_person = person_info
                self.get_logger().info(f"Target found: {person_info['name']} (confidence: {confidence:.2f})")

                if self.hardware.audio:
                    self.hardware.audio.play_text(f"Following {person_info['name']}")

                if self.hardware.display:
                    self.hardware.display.show_follow_mode(person_info['name'])

            self.last_detection_time = time.time()

            # Calculate face center and size
            face_center_x = x + w // 2
            face_center_y = y + h // 2
            face_area = w * h

            frame_height, frame_width = frame.shape[:2]
            frame_center_x = frame_width // 2
            frame_center_y = frame_height // 2

            # Calculate movement based on face position
            self._calculate_follow_movement(face_center_x, face_center_y, face_area,
                                          frame_width, frame_height)

            # Update camera tracking if enabled
            if self.camera_tracking:
                self._update_camera_tracking(face_center_x, face_center_y, frame_width, frame_height)

            # Update display with tracking info
            if self.hardware.display:
                self.hardware.display.show_text(
                    f"Following: {person_info['name']}\n"
                    f"Confidence: {confidence:.1%}\n"
                    f"Distance: Adjusting"
                )

        except Exception as e:
            self.get_logger().error(f"Face handling error: {e}")

    def _handle_no_faces(self):
        """Handle when no faces are detected"""
        try:
            if self.target_found:
                # Lost target - check if we should keep searching
                elapsed_since_detection = time.time() - self.last_detection_time

                if elapsed_since_detection > 3.0:  # Lost for 3 seconds
                    self.get_logger().info("Target lost - stopping and searching")
                    self._stop_movement()

                    # Start scanning for target
                    self._scan_for_target()

                if elapsed_since_detection > 10.0:  # Lost for 10 seconds
                    self.get_logger().info("Target lost for too long - exiting follow mode")
                    if self.hardware.audio:
                        self.hardware.audio.play_text("I lost sight of you. Exiting follow mode.")
                    self.stop_follow_mode()

        except Exception as e:
            self.get_logger().error(f"No faces handling error: {e}")

    def _handle_no_registered_faces(self):
        """Handle when faces are detected but none are registered"""
        try:
            if not self.target_found:
                # Still searching for registered face
                if self.hardware.display:
                    self.hardware.display.show_text("Searching for\nregistered person...")

        except Exception as e:
            self.get_logger().error(f"No registered faces handling error: {e}")

    def _calculate_follow_movement(self, face_x: int, face_y: int, face_area: int,
                                 frame_width: int, frame_height: int):
        """Calculate robot movement to follow the face"""
        try:
            frame_center_x = frame_width // 2

            # Calculate horizontal offset (for turning)
            horizontal_offset = face_x - frame_center_x
            horizontal_offset_normalized = horizontal_offset / (frame_width / 2)

            # Calculate distance estimation based on face size
            # Larger face = closer, smaller face = farther
            reference_face_area = 8000  # Approximate face area at target distance
            distance_ratio = reference_face_area / max(face_area, 100)  # Avoid division by zero

            # Calculate movement commands
            # Angular velocity for turning towards face
            angular_velocity = -horizontal_offset_normalized * self.angular_speed

            # Linear velocity based on estimated distance
            if distance_ratio > 1.5:  # Too far - move forward
                linear_velocity = min(self.linear_speed, (distance_ratio - 1.0) * self.linear_speed)
            elif distance_ratio < 0.8:  # Too close - move backward
                linear_velocity = -min(self.linear_speed * 0.5, (0.8 - distance_ratio) * self.linear_speed)
            else:  # Good distance - stop forward/backward movement
                linear_velocity = 0.0

            # Apply deadzone for angular movement
            if abs(angular_velocity) < 0.1:
                angular_velocity = 0.0

            # Apply deadzone for linear movement
            if abs(linear_velocity) < 0.1:
                linear_velocity = 0.0

            # Update movement
            self.current_linear = linear_velocity
            self.current_angular = angular_velocity

            # Send movement commands
            self._send_movement_command(linear_velocity, angular_velocity)

            # Log movement for debugging
            if abs(linear_velocity) > 0.1 or abs(angular_velocity) > 0.1:
                self.get_logger().debug(
                    f"Follow movement: Linear={linear_velocity:.2f}, Angular={angular_velocity:.2f}, "
                    f"Face offset={horizontal_offset}, Distance ratio={distance_ratio:.2f}"
                )

        except Exception as e:
            self.get_logger().error(f"Movement calculation error: {e}")

    def _update_camera_tracking(self, face_x: int, face_y: int, frame_width: int, frame_height: int):
        """Update camera servos to track face"""
        try:
            if not self.hardware.camera_servos:
                return

            frame_center_x = frame_width // 2
            frame_center_y = frame_height // 2

            # Calculate offset from center
            offset_x = face_x - frame_center_x
            offset_y = face_y - frame_center_y

            # Convert to angle adjustments
            max_offset_x = frame_width // 2
            max_offset_y = frame_height // 2

            pan_adjustment = (offset_x / max_offset_x) * 30.0 * self.pan_gain  # Max 30 degree adjustment
            tilt_adjustment = -(offset_y / max_offset_y) * 20.0 * self.tilt_gain  # Max 20 degree adjustment (inverted)

            # Get current camera position
            current_pan = self.hardware.camera_servos.get_pan_angle()
            current_tilt = self.hardware.camera_servos.get_tilt_angle()

            # Calculate new positions
            new_pan = current_pan + pan_adjustment
            new_tilt = current_tilt + tilt_adjustment

            # Apply servo limits
            pan_limits = self.hardware.camera_servos.get_limits()['pan']
            tilt_limits = self.hardware.camera_servos.get_limits()['tilt']

            new_pan = max(pan_limits[0], min(pan_limits[1], new_pan))
            new_tilt = max(tilt_limits[0], min(tilt_limits[1], new_tilt))

            # Move camera if significant change
            if abs(pan_adjustment) > 2.0 or abs(tilt_adjustment) > 2.0:
                self.hardware.camera_servos.set_pan_tilt(new_pan, new_tilt)

        except Exception as e:
            self.get_logger().warning(f"Camera tracking error: {e}")

    def _scan_for_target(self):
        """Scan area looking for lost target"""
        try:
            if not self.hardware.camera_servos:
                return

            # Simple left-right scan
            scan_angles = [-30, 0, 30, 0]

            for angle in scan_angles:
                if not self.follow_active:
                    break

                self.hardware.camera_servos.set_pan_angle(angle)
                time.sleep(0.5)  # Give time for movement and detection

        except Exception as e:
            self.get_logger().warning(f"Target scanning error: {e}")

    def _send_movement_command(self, linear: float, angular: float):
        """Send movement command to robot motors"""
        try:
            # Calculate differential drive motor speeds
            wheel_separation = 0.3  # meters
            max_wheel_speed = 1.0   # m/s

            # Convert to left/right motor speeds
            left_speed = (linear - angular * wheel_separation / 2) / max_wheel_speed * 100.0
            right_speed = (linear + angular * wheel_separation / 2) / max_wheel_speed * 100.0

            # Clamp speeds to valid range
            left_speed = max(-100.0, min(100.0, left_speed))
            right_speed = max(-100.0, min(100.0, right_speed))

            # Send to motors
            if self.hardware.motors:
                self.hardware.motors.set_motor_speed(left_speed, right_speed)

        except Exception as e:
            self.get_logger().error(f"Movement command error: {e}")

    def _stop_movement(self):
        """Stop robot movement"""
        try:
            self.current_linear = 0.0
            self.current_angular = 0.0

            if self.hardware.motors:
                self.hardware.motors.stop()

        except Exception as e:
            self.get_logger().error(f"Stop movement error: {e}")

    def is_follow_active(self) -> bool:
        """Check if follow mode is currently active"""
        return self.follow_active

    def get_follow_status(self) -> Dict[str, Any]:
        """Get current follow status"""
        return {
            'active': self.follow_active,
            'target_found': self.target_found,
            'target_person': self.target_person,
            'current_linear': self.current_linear,
            'current_angular': self.current_angular,
            'last_detection_time': self.last_detection_time,
            'time_since_detection': time.time() - self.last_detection_time if self.target_found else 0
        }

    def cleanup(self):
        """Cleanup follow mode resources"""
        try:
            if self.follow_active:
                self.stop_follow_mode()

        except Exception as e:
            self.get_logger().error(f"Follow mode cleanup error: {e}")