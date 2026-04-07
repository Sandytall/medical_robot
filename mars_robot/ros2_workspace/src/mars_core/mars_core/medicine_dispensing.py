#!/usr/bin/env python3
"""
Medicine Dispensing System for Mars Robot
Handles "Hey mars its medicine time" functionality with automated medicine distribution
"""
import time
import json
import threading
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

import cv2
import numpy as np
import rclpy
from rclpy.node import Node

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mars_hardware'))

from mars_hardware.interfaces.arm_interface import ArmSide

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False


class MedicineDispenseState(Enum):
    """Medicine dispensing state"""
    IDLE = "idle"
    SCANNING_FOR_PATIENT = "scanning"
    PATIENT_IDENTIFIED = "patient_identified"
    CONFIRMING_PATIENT = "confirming"
    CHECKING_MEDICATION = "checking_medication"
    DISPENSING = "dispensing"
    COMPLETED = "completed"
    SEARCHING_NEXT = "searching_next"


class MedicineDispensing(Node):
    """Medicine dispensing handler"""

    def __init__(self, hardware_manager, database, config: Dict[str, Any]):
        super().__init__('medicine_dispensing')

        self.hardware = hardware_manager
        self.database = database
        self.config = config

        # Medicine dispensing state
        self.dispensing_active = False
        self.current_state = MedicineDispenseState.IDLE
        self.patients_to_visit = []
        self.current_patient = None
        self.current_patient_index = 0
        self.dispensing_complete = False

        # Configuration
        self.search_timeout = self.config.get('modes', {}).get('medicine', {}).get('search_timeout', 30.0)
        self.call_timeout = self.config.get('modes', {}).get('medicine', {}).get('call_timeout', 30.0)
        self.require_confirmation = self.config.get('modes', {}).get('medicine', {}).get('require_patient_confirmation', True)

        # Face detection
        self.face_cascade = self._load_face_cascade()
        self.min_confidence = 0.4

        # Servo arm positions for medicine dispensing (to be provided by user)
        self.medicine_positions = {
            'home': {'left': [0, 0, 0, 0], 'right': [0, 0, 0, 0]},
            'medicine_grab': {'left': [45, 90, -90, 0], 'right': [-45, 90, -90, 0]},
            'medicine_extend': {'left': [0, 45, -30, 0], 'right': [0, 45, -30, 0]},
            'medicine_drop': {'left': [0, 60, -45, -30], 'right': [0, 60, -45, 30]}
        }

        # Dispensing tracking
        self.current_scan_angle = 0
        self.scan_angles = [-60, -30, 0, 30, 60]
        self.scan_index = 0

        self.get_logger().info("Medicine Dispensing system initialized")

    def _load_face_cascade(self):
        """Load OpenCV face detection cascade"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            return cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            self.get_logger().error(f"Failed to load face cascade: {e}")
            return None

    def start_medicine_time(self) -> bool:
        """Start medicine dispensing routine"""
        try:
            if self.dispensing_active:
                self.get_logger().warning("Medicine time already active")
                return False

            # Get list of patients who need medication
            self.patients_to_visit = self._get_patients_needing_medication()

            if not self.patients_to_visit:
                if self.hardware.audio:
                    self.hardware.audio.play_text("No patients need medication at this time.")
                return False

            self.dispensing_active = True
            self.current_state = MedicineDispenseState.SCANNING_FOR_PATIENT
            self.current_patient_index = 0
            self.dispensing_complete = False

            # Announce medicine time start
            if self.hardware.audio:
                self.hardware.audio.play_text(f"Medicine time started. I need to visit {len(self.patients_to_visit)} patients.")

            # Move arms to home position
            if self.hardware.arms:
                self.hardware.arms.move_to_home_position()

            # Start camera if not streaming
            if not self.hardware.camera.is_streaming():
                self.hardware.camera.start_streaming()

            # Start dispensing thread
            threading.Thread(target=self._medicine_dispensing_loop, daemon=True).start()

            self.get_logger().info(f"Medicine time started for {len(self.patients_to_visit)} patients")
            return True

        except Exception as e:
            self.get_logger().error(f"Medicine time start error: {e}")
            return False

    def stop_medicine_time(self):
        """Stop medicine dispensing routine"""
        try:
            if not self.dispensing_active:
                return

            self.dispensing_active = False
            self.current_state = MedicineDispenseState.IDLE

            # Return arms to home position
            if self.hardware.arms:
                self.hardware.arms.move_to_home_position()

            # Center camera
            if self.hardware.camera_servos:
                self.hardware.camera_servos.center_camera()

            # Stop robot movement
            if self.hardware.motors:
                self.hardware.motors.stop()

            # Announce completion
            if self.hardware.audio:
                if self.dispensing_complete:
                    self.hardware.audio.play_text("Medicine time completed. All patients have been visited.")
                else:
                    self.hardware.audio.play_text("Medicine time stopped.")

            self.get_logger().info("Medicine dispensing stopped")

        except Exception as e:
            self.get_logger().error(f"Medicine time stop error: {e}")

    def _get_patients_needing_medication(self) -> List[Dict[str, Any]]:
        """Get list of patients who need medication at this time"""
        try:
            # Get all patients from database
            all_patients = self.database.get_all_patients()

            # Filter patients who have medications
            patients_with_medication = []

            for patient in all_patients:
                if patient['medications'] and patient['medications'].strip():
                    # In a real implementation, this would check medication schedule
                    # For now, assume all patients with medications need them
                    patients_with_medication.append(patient)

            return patients_with_medication

        except Exception as e:
            self.get_logger().error(f"Patient medication check error: {e}")
            return []

    def _medicine_dispensing_loop(self):
        """Main medicine dispensing loop"""
        try:
            while self.dispensing_active and not self.dispensing_complete:
                try:
                    if self.current_patient_index >= len(self.patients_to_visit):
                        # All patients visited
                        self.dispensing_complete = True
                        break

                    # Get current patient to visit
                    self.current_patient = self.patients_to_visit[self.current_patient_index]

                    # Execute state machine
                    if self.current_state == MedicineDispenseState.SCANNING_FOR_PATIENT:
                        self._scan_for_patient()
                    elif self.current_state == MedicineDispenseState.PATIENT_IDENTIFIED:
                        self._patient_identified()
                    elif self.current_state == MedicineDispenseState.CONFIRMING_PATIENT:
                        self._confirm_patient()
                    elif self.current_state == MedicineDispenseState.CHECKING_MEDICATION:
                        self._check_medication()
                    elif self.current_state == MedicineDispenseState.DISPENSING:
                        self._dispense_medication()
                    elif self.current_state == MedicineDispenseState.COMPLETED:
                        self._patient_completed()

                    time.sleep(0.5)  # State machine update rate

                except Exception as e:
                    self.get_logger().error(f"Medicine loop error: {e}")
                    time.sleep(1.0)

            if self.dispensing_complete:
                self.stop_medicine_time()

        except Exception as e:
            self.get_logger().error(f"Medicine dispensing thread error: {e}")

    def _scan_for_patient(self):
        """Scan area looking for current patient"""
        try:
            patient_name = self.current_patient['name']

            # Update display
            if self.hardware.display:
                self.hardware.display.show_text(f"Looking for:\n{patient_name}")

            # Scan with camera
            scan_start_time = time.time()

            while (time.time() - scan_start_time) < self.search_timeout and self.dispensing_active:
                # Capture frame
                frame = self.hardware.camera.capture_frame()
                if frame is None:
                    continue

                # Look for the specific patient
                found_patient = self._find_specific_patient(frame, self.current_patient)

                if found_patient:
                    self.current_state = MedicineDispenseState.PATIENT_IDENTIFIED
                    return

                # Move camera to scan area
                self._perform_camera_scan()

                time.sleep(0.5)

            # Patient not found - call out their name
            self._call_patient_name()

        except Exception as e:
            self.get_logger().error(f"Patient scanning error: {e}")

    def _find_specific_patient(self, frame: np.ndarray, target_patient: Dict[str, Any]) -> bool:
        """Look for specific patient in camera frame"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                return False

            # Convert frame to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Find face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame)

            if not face_encodings:
                return False

            # Check each face against target patient
            for face_encoding in face_encodings:
                patient_match = self.database.get_patient_by_face(face_encoding, tolerance=0.6)

                if (patient_match and
                    patient_match['patient_id'] == target_patient['patient_id'] and
                    patient_match['confidence'] >= self.min_confidence):

                    self.get_logger().info(f"Found target patient: {patient_match['name']} (confidence: {patient_match['confidence']:.2f})")
                    return True

            return False

        except Exception as e:
            self.get_logger().warning(f"Patient search error: {e}")
            return False

    def _perform_camera_scan(self):
        """Perform systematic camera scan"""
        try:
            if not self.hardware.camera_servos:
                return

            # Move to next scan position
            if self.scan_index < len(self.scan_angles):
                angle = self.scan_angles[self.scan_index]
                self.hardware.camera_servos.set_pan_angle(angle)
                self.scan_index += 1
            else:
                # Reset scan
                self.scan_index = 0

        except Exception as e:
            self.get_logger().warning(f"Camera scan error: {e}")

    def _call_patient_name(self):
        """Call patient name and wait"""
        try:
            patient_name = self.current_patient['name']

            if self.hardware.audio:
                self.hardware.audio.play_text(f"{patient_name}, it's time for your medication. Please come to me.")

            # Wait for patient to appear
            call_start_time = time.time()

            while (time.time() - call_start_time) < self.call_timeout and self.dispensing_active:
                frame = self.hardware.camera.capture_frame()
                if frame is None:
                    continue

                if self._find_specific_patient(frame, self.current_patient):
                    self.current_state = MedicineDispenseState.PATIENT_IDENTIFIED
                    return

                time.sleep(1.0)

            # Patient didn't respond - move to next patient
            self.get_logger().info(f"Patient {patient_name} did not respond - moving to next patient")
            if self.hardware.audio:
                self.hardware.audio.play_text(f"Moving to next patient.")

            self._move_to_next_patient()

        except Exception as e:
            self.get_logger().error(f"Patient calling error: {e}")

    def _patient_identified(self):
        """Handle when target patient is identified"""
        try:
            patient_name = self.current_patient['name']

            if self.hardware.audio:
                self.hardware.audio.play_text(f"Hello {patient_name}. I have your medication.")

            if self.hardware.display:
                self.hardware.display.show_patient_info(
                    patient_name,
                    self.current_patient['patient_id'],
                    "Medication Ready"
                )

            if self.require_confirmation:
                self.current_state = MedicineDispenseState.CONFIRMING_PATIENT
            else:
                self.current_state = MedicineDispenseState.CHECKING_MEDICATION

        except Exception as e:
            self.get_logger().error(f"Patient identification error: {e}")

    def _confirm_patient(self):
        """Confirm patient identity before dispensing"""
        try:
            patient_name = self.current_patient['name']

            if self.hardware.audio:
                self.hardware.audio.play_text(f"Please confirm - are you {patient_name}?")

            # In a real implementation, this would wait for voice confirmation
            # For now, we'll assume confirmation after a brief pause
            time.sleep(3.0)

            # TODO: Implement voice confirmation logic
            confirmed = True  # Placeholder

            if confirmed:
                self.current_state = MedicineDispenseState.CHECKING_MEDICATION
            else:
                if self.hardware.audio:
                    self.hardware.audio.play_text("I apologize for the confusion. Let me look for the correct person.")
                self.current_state = MedicineDispenseState.SCANNING_FOR_PATIENT

        except Exception as e:
            self.get_logger().error(f"Patient confirmation error: {e}")

    def _check_medication(self):
        """Check and announce patient's medication"""
        try:
            patient_name = self.current_patient['name']
            medications = self.current_patient['medications']

            if self.hardware.audio:
                self.hardware.audio.play_text(f"{patient_name}, your medication is: {medications}")

            if self.hardware.display:
                self.hardware.display.show_medication_reminder(
                    patient_name,
                    medications,
                    time.strftime("%H:%M")
                )

            # Ask for confirmation to proceed
            if self.hardware.audio:
                self.hardware.audio.play_text("I will now dispense your medication. Please stand by.")

            self.current_state = MedicineDispenseState.DISPENSING

        except Exception as e:
            self.get_logger().error(f"Medication check error: {e}")

    def _dispense_medication(self):
        """Perform medication dispensing using arm manipulation"""
        try:
            patient_name = self.current_patient['name']

            if self.hardware.audio:
                self.hardware.audio.play_text("Dispensing your medication now.")

            # Execute dispensing sequence
            success = self._execute_dispensing_sequence()

            if success:
                if self.hardware.audio:
                    self.hardware.audio.play_text(f"Here is your medication, {patient_name}. Please take it now.")

                # Wait for patient to take medication
                time.sleep(5.0)

                if self.hardware.audio:
                    self.hardware.audio.play_text("Thank you. Medication dispensed successfully.")

                self.current_state = MedicineDispenseState.COMPLETED
            else:
                if self.hardware.audio:
                    self.hardware.audio.play_text("There was an issue dispensing your medication. Please alert the staff.")

        except Exception as e:
            self.get_logger().error(f"Medication dispensing error: {e}")

    def _execute_dispensing_sequence(self) -> bool:
        """Execute arm movement sequence for dispensing"""
        try:
            if not self.hardware.arms:
                return False

            # Dispensing sequence using predefined positions
            dispensing_steps = [
                ("Moving to grab position", "medicine_grab"),
                ("Extending arm", "medicine_extend"),
                ("Dispensing medication", "medicine_drop"),
                ("Returning to home", "home")
            ]

            for step_description, position_name in dispensing_steps:
                self.get_logger().info(f"Dispensing step: {step_description}")

                if position_name in self.medicine_positions:
                    position = self.medicine_positions[position_name]

                    # Move both arms to position
                    self.hardware.arms.set_arm_angles(ArmSide.LEFT, position['left'])
                    self.hardware.arms.set_arm_angles(ArmSide.RIGHT, position['right'])

                    # Wait for movement completion
                    time.sleep(2.0)

                    # Check if arms are still moving
                    while (self.hardware.arms.is_moving(ArmSide.LEFT) or
                           self.hardware.arms.is_moving(ArmSide.RIGHT)):
                        time.sleep(0.1)

                else:
                    self.get_logger().warning(f"Unknown arm position: {position_name}")

            return True

        except Exception as e:
            self.get_logger().error(f"Dispensing sequence error: {e}")
            return False

    def _patient_completed(self):
        """Handle completion for current patient"""
        try:
            # Log medication dispensed
            self.get_logger().info(f"Medication dispensed to {self.current_patient['name']}")

            # Move to next patient
            self._move_to_next_patient()

        except Exception as e:
            self.get_logger().error(f"Patient completion error: {e}")

    def _move_to_next_patient(self):
        """Move to next patient in list"""
        try:
            self.current_patient_index += 1
            self.current_state = MedicineDispenseState.SCANNING_FOR_PATIENT
            self.scan_index = 0  # Reset camera scan

            if self.current_patient_index < len(self.patients_to_visit):
                next_patient = self.patients_to_visit[self.current_patient_index]
                remaining = len(self.patients_to_visit) - self.current_patient_index

                if self.hardware.audio:
                    self.hardware.audio.play_text(f"Moving to next patient. {remaining} patients remaining.")

                self.get_logger().info(f"Moving to next patient: {next_patient['name']} ({remaining} remaining)")
            else:
                self.dispensing_complete = True

        except Exception as e:
            self.get_logger().error(f"Next patient error: {e}")

    def add_custom_arm_position(self, position_name: str, left_angles: List[float], right_angles: List[float]):
        """Add custom arm position for dispensing"""
        try:
            self.medicine_positions[position_name] = {
                'left': left_angles.copy(),
                'right': right_angles.copy()
            }
            self.get_logger().info(f"Added custom arm position: {position_name}")

        except Exception as e:
            self.get_logger().error(f"Add arm position error: {e}")

    def is_dispensing_active(self) -> bool:
        """Check if medicine dispensing is currently active"""
        return self.dispensing_active

    def get_dispensing_status(self) -> Dict[str, Any]:
        """Get current dispensing status"""
        return {
            'active': self.dispensing_active,
            'current_state': self.current_state.value,
            'current_patient': self.current_patient,
            'current_patient_index': self.current_patient_index,
            'total_patients': len(self.patients_to_visit),
            'patients_remaining': len(self.patients_to_visit) - self.current_patient_index,
            'dispensing_complete': self.dispensing_complete
        }

    def emergency_stop_dispensing(self):
        """Emergency stop during dispensing"""
        try:
            self.get_logger().warning("Emergency stop during medicine dispensing")

            # Stop all movement
            if self.hardware.arms:
                self.hardware.arms.emergency_stop()
            if self.hardware.motors:
                self.hardware.motors.stop()

            # Return to safe position
            if self.hardware.arms:
                self.hardware.arms.move_to_home_position()

            # Stop dispensing
            self.stop_medicine_time()

            if self.hardware.audio:
                self.hardware.audio.play_text("Medicine dispensing stopped for safety reasons.")

        except Exception as e:
            self.get_logger().error(f"Emergency stop error: {e}")

    def cleanup(self):
        """Cleanup medicine dispensing resources"""
        try:
            if self.dispensing_active:
                self.stop_medicine_time()

        except Exception as e:
            self.get_logger().error(f"Medicine dispensing cleanup error: {e}")