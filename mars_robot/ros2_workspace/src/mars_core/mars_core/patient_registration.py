#!/usr/bin/env python3
"""
Patient Registration System for Mars Robot
Handles "Hey Mars register me" functionality with face detection and photo capture
"""
import os
import time
import json
import sqlite3
import threading
import uuid
from typing import Dict, Any, Optional, List, Tuple

import cv2
import numpy as np
import rclpy
from rclpy.node import Node

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("face_recognition not available. Install with: pip install face-recognition")


class PatientDatabase:
    """Patient database manager"""

    def __init__(self, db_path: str = "/shared_data/database/patients.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize patient database"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create patients table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS patients (
                        patient_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        age INTEGER,
                        medical_conditions TEXT,
                        medications TEXT,
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        face_encoding BLOB,
                        photo_count INTEGER DEFAULT 0
                    )
                ''')

                # Create medications table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS patient_medications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id TEXT,
                        medication_name TEXT,
                        dosage TEXT,
                        frequency TEXT,
                        time_slots TEXT,
                        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                    )
                ''')

                # Create photos table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS patient_photos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id TEXT,
                        photo_path TEXT,
                        photo_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        face_encoding BLOB,
                        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                    )
                ''')

                conn.commit()
                print("Patient database initialized")

        except Exception as e:
            print(f"Database initialization error: {e}")

    def register_patient(self, name: str, age: int, medical_conditions: str = "",
                        medications: str = "") -> str:
        """Register a new patient"""
        try:
            patient_id = f"MARS_{uuid.uuid4().hex[:8].upper()}"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO patients (patient_id, name, age, medical_conditions, medications)
                    VALUES (?, ?, ?, ?, ?)
                ''', (patient_id, name, age, medical_conditions, medications))
                conn.commit()

            print(f"Patient registered: {name} (ID: {patient_id})")
            return patient_id

        except Exception as e:
            print(f"Patient registration error: {e}")
            return ""

    def add_patient_photo(self, patient_id: str, photo_path: str, face_encoding: np.ndarray = None):
        """Add a patient photo with face encoding"""
        try:
            encoding_blob = face_encoding.tobytes() if face_encoding is not None else None

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO patient_photos (patient_id, photo_path, face_encoding)
                    VALUES (?, ?, ?)
                ''', (patient_id, photo_path, encoding_blob))

                # Update photo count
                cursor.execute('''
                    UPDATE patients SET photo_count = photo_count + 1 WHERE patient_id = ?
                ''', (patient_id,))

                conn.commit()

        except Exception as e:
            print(f"Photo addition error: {e}")

    def get_patient_by_face(self, face_encoding: np.ndarray, tolerance: float = 0.6) -> Optional[Dict]:
        """Find patient by face encoding"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                return None

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM patient_photos WHERE face_encoding IS NOT NULL')
                photos = cursor.fetchall()

                for photo in photos:
                    stored_encoding = np.frombuffer(photo[4], dtype=np.float64)
                    if stored_encoding.size > 0:
                        distance = face_recognition.face_distance([stored_encoding], face_encoding)[0]
                        if distance <= tolerance:
                            # Get patient details
                            cursor.execute('SELECT * FROM patients WHERE patient_id = ?', (photo[1],))
                            patient = cursor.fetchone()
                            if patient:
                                return {
                                    'patient_id': patient[0],
                                    'name': patient[1],
                                    'age': patient[2],
                                    'medical_conditions': patient[3],
                                    'medications': patient[4],
                                    'confidence': 1.0 - distance
                                }

            return None

        except Exception as e:
            print(f"Face recognition search error: {e}")
            return None

    def get_all_patients(self) -> List[Dict]:
        """Get all registered patients"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM patients ORDER BY name')
                patients = cursor.fetchall()

                return [{
                    'patient_id': patient[0],
                    'name': patient[1],
                    'age': patient[2],
                    'medical_conditions': patient[3],
                    'medications': patient[4],
                    'registration_date': patient[5],
                    'photo_count': patient[7]
                } for patient in patients]

        except Exception as e:
            print(f"Patient retrieval error: {e}")
            return []


class PatientRegistration(Node):
    """Patient registration handler"""

    def __init__(self, hardware_manager, config: Dict[str, Any]):
        super().__init__('patient_registration')

        self.hardware = hardware_manager
        self.config = config
        self.database = PatientDatabase()

        # Registration state
        self.registration_active = False
        self.current_patient_data = {}
        self.registration_step = 0
        self.photos_captured = 0
        self.target_photos = self.config.get('face_recognition', {}).get('photo_capture_count', 50)
        self.photo_interval = self.config.get('face_recognition', {}).get('photo_capture_interval', 0.5)

        # Face detection
        self.face_cascade = self._load_face_cascade()
        self.last_face_detection = None

        # Photo storage
        self.photo_dir = "/shared_data/faces"
        os.makedirs(self.photo_dir, exist_ok=True)

        self.get_logger().info("Patient Registration system initialized")

    def _load_face_cascade(self):
        """Load OpenCV face detection cascade"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            return cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            self.get_logger().error(f"Failed to load face cascade: {e}")
            return None

    def start_registration(self) -> bool:
        """Start patient registration process"""
        try:
            if self.registration_active:
                self.get_logger().warning("Registration already in progress")
                return False

            self.registration_active = True
            self.current_patient_data = {}
            self.registration_step = 0
            self.photos_captured = 0

            # Display registration mode
            if self.hardware.display:
                self.hardware.display.show_text("Patient Registration")

            # Welcome message
            if self.hardware.audio:
                self.hardware.audio.play_text("Welcome! I'll help you register as a new patient. Please look at the camera.")

            # Start registration flow
            threading.Thread(target=self._registration_flow, daemon=True).start()

            self.get_logger().info("Patient registration started")
            return True

        except Exception as e:
            self.get_logger().error(f"Registration start error: {e}")
            return False

    def _registration_flow(self):
        """Main registration workflow"""
        try:
            # Step 1: Get patient name
            if not self._get_patient_name():
                self._end_registration(False)
                return

            # Step 2: Get patient age
            if not self._get_patient_age():
                self._end_registration(False)
                return

            # Step 3: Get medical information
            if not self._get_medical_info():
                self._end_registration(False)
                return

            # Step 4: Face detection and photo capture
            if not self._capture_patient_photos():
                self._end_registration(False)
                return

            # Step 5: Save to database
            patient_id = self._save_patient_data()
            if patient_id:
                self._end_registration(True, patient_id)
            else:
                self._end_registration(False)

        except Exception as e:
            self.get_logger().error(f"Registration flow error: {e}")
            self._end_registration(False)

    def _get_patient_name(self) -> bool:
        """Get patient name via voice input"""
        try:
            if self.hardware.audio:
                self.hardware.audio.play_text("What's your name?")

            # TODO: Implement speech recognition for name capture
            # For now, use a placeholder implementation
            time.sleep(3)  # Wait for response

            # In real implementation, this would capture speech and extract name
            self.current_patient_data['name'] = "Test Patient"  # Placeholder

            if self.hardware.audio:
                self.hardware.audio.play_text(f"Thank you, {self.current_patient_data['name']}")

            return True

        except Exception as e:
            self.get_logger().error(f"Name capture error: {e}")
            return False

    def _get_patient_age(self) -> bool:
        """Get patient age via voice input"""
        try:
            if self.hardware.audio:
                self.hardware.audio.play_text("How old are you?")

            time.sleep(3)  # Wait for response

            # Placeholder implementation
            self.current_patient_data['age'] = 30  # Placeholder

            if self.hardware.audio:
                self.hardware.audio.play_text("Thank you")

            return True

        except Exception as e:
            self.get_logger().error(f"Age capture error: {e}")
            return False

    def _get_medical_info(self) -> bool:
        """Get medical conditions and medications"""
        try:
            if self.hardware.audio:
                self.hardware.audio.play_text("Do you have any medical conditions or take any medications?")

            time.sleep(5)  # Wait for response

            # Placeholder implementation
            self.current_patient_data['medical_conditions'] = ""  # Placeholder
            self.current_patient_data['medications'] = ""  # Placeholder

            return True

        except Exception as e:
            self.get_logger().error(f"Medical info capture error: {e}")
            return False

    def _capture_patient_photos(self) -> bool:
        """Capture patient photos for face recognition"""
        try:
            if self.hardware.audio:
                self.hardware.audio.play_text(f"Perfect! Now I'll capture {self.target_photos} photos of your face. Please turn your head slowly left and right.")

            if self.hardware.display:
                self.hardware.display.show_text("Photo Capture\nLook at camera\nTurn head slowly")

            patient_id = f"temp_{int(time.time())}"
            patient_photo_dir = os.path.join(self.photo_dir, patient_id)
            os.makedirs(patient_photo_dir, exist_ok=True)

            self.photos_captured = 0
            face_encodings = []

            # Start camera if not already streaming
            if not self.hardware.camera.is_streaming():
                self.hardware.camera.start_streaming()

            start_time = time.time()
            max_capture_time = 60.0  # Maximum 60 seconds for photo capture

            while self.photos_captured < self.target_photos and (time.time() - start_time) < max_capture_time:
                try:
                    # Capture frame
                    frame = self.hardware.camera.capture_frame()
                    if frame is None:
                        continue

                    # Detect faces
                    faces = self._detect_faces(frame)

                    if len(faces) > 0:
                        # Draw bounding box around face
                        for (x, y, w, h) in faces:
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                        # Save photo
                        photo_path = os.path.join(patient_photo_dir, f"photo_{self.photos_captured:03d}.jpg")
                        cv2.imwrite(photo_path, frame)

                        # Extract face encoding if face_recognition is available
                        face_encoding = None
                        if FACE_RECOGNITION_AVAILABLE:
                            try:
                                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                encodings = face_recognition.face_encodings(rgb_frame)
                                if encodings:
                                    face_encoding = encodings[0]
                                    face_encodings.append(face_encoding)
                            except Exception as e:
                                self.get_logger().warning(f"Face encoding error: {e}")

                        self.photos_captured += 1

                        # Update progress
                        progress = self.photos_captured / self.target_photos
                        if self.hardware.display:
                            self.hardware.display.show_progress(progress, f"Photos: {self.photos_captured}/{self.target_photos}")

                        self.get_logger().info(f"Photo {self.photos_captured}/{self.target_photos} captured")

                        # Wait for interval
                        time.sleep(self.photo_interval)

                    else:
                        # No face detected, show message
                        if self.hardware.display:
                            self.hardware.display.show_text("Please look at camera\nFace not detected")

                except Exception as e:
                    self.get_logger().warning(f"Photo capture error: {e}")
                    continue

            # Store photo info
            self.current_patient_data['photo_dir'] = patient_photo_dir
            self.current_patient_data['face_encodings'] = face_encodings

            if self.photos_captured >= self.target_photos:
                if self.hardware.audio:
                    self.hardware.audio.play_text(f"Excellent! I captured {self.photos_captured} photos successfully.")
                return True
            else:
                if self.hardware.audio:
                    self.hardware.audio.play_text(f"I only captured {self.photos_captured} photos. This might affect recognition accuracy.")
                return True  # Continue with registration even with fewer photos

        except Exception as e:
            self.get_logger().error(f"Photo capture error: {e}")
            return False

    def _detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in frame using OpenCV"""
        try:
            if self.face_cascade is None:
                return []

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            return faces

        except Exception as e:
            self.get_logger().warning(f"Face detection error: {e}")
            return []

    def _save_patient_data(self) -> str:
        """Save patient data to database"""
        try:
            # Register patient in database
            patient_id = self.database.register_patient(
                name=self.current_patient_data['name'],
                age=self.current_patient_data['age'],
                medical_conditions=self.current_patient_data.get('medical_conditions', ''),
                medications=self.current_patient_data.get('medications', '')
            )

            if not patient_id:
                return ""

            # Rename photo directory to use real patient ID
            temp_dir = self.current_patient_data['photo_dir']
            final_dir = os.path.join(self.photo_dir, patient_id)

            try:
                os.rename(temp_dir, final_dir)
            except OSError:
                # If rename fails, copy files
                os.makedirs(final_dir, exist_ok=True)
                for filename in os.listdir(temp_dir):
                    import shutil
                    shutil.copy2(os.path.join(temp_dir, filename), os.path.join(final_dir, filename))

            # Save photo info to database
            face_encodings = self.current_patient_data.get('face_encodings', [])

            for i, filename in enumerate(os.listdir(final_dir)):
                photo_path = os.path.join(final_dir, filename)
                face_encoding = face_encodings[i] if i < len(face_encodings) else None
                self.database.add_patient_photo(patient_id, photo_path, face_encoding)

            self.get_logger().info(f"Patient data saved successfully: {patient_id}")
            return patient_id

        except Exception as e:
            self.get_logger().error(f"Patient data save error: {e}")
            return ""

    def _end_registration(self, success: bool, patient_id: str = ""):
        """End registration process"""
        try:
            self.registration_active = False

            if success:
                message = f"Registration complete! Your patient ID is {patient_id}. Welcome to our hospital system!"
                if self.hardware.display:
                    self.hardware.display.show_patient_info(
                        self.current_patient_data['name'],
                        patient_id,
                        "Registration Complete"
                    )
                if self.hardware.audio:
                    self.hardware.audio.play_sound_effect('success')
                    self.hardware.audio.play_text(message)

                self.get_logger().info(f"Registration completed successfully: {patient_id}")
            else:
                message = "Registration failed. Please try again later or contact staff for assistance."
                if self.hardware.display:
                    self.hardware.display.show_status("Registration Failed", "error")
                if self.hardware.audio:
                    self.hardware.audio.play_sound_effect('error')
                    self.hardware.audio.play_text(message)

                self.get_logger().warning("Registration failed")

            # Clear patient data
            self.current_patient_data = {}
            self.registration_step = 0
            self.photos_captured = 0

        except Exception as e:
            self.get_logger().error(f"Registration end error: {e}")

    def find_patient_by_camera(self) -> Optional[Dict]:
        """Find patient using current camera view"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                self.get_logger().warning("Face recognition not available")
                return None

            frame = self.hardware.camera.capture_frame()
            if frame is None:
                return None

            # Convert to RGB for face_recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Find face encodings in current frame
            face_encodings = face_recognition.face_encodings(rgb_frame)

            if not face_encodings:
                return None

            # Try to match against database
            for face_encoding in face_encodings:
                patient = self.database.get_patient_by_face(face_encoding)
                if patient:
                    return patient

            return None

        except Exception as e:
            self.get_logger().error(f"Camera patient search error: {e}")
            return None

    def is_registration_active(self) -> bool:
        """Check if registration is currently active"""
        return self.registration_active

    def get_registration_progress(self) -> Dict[str, Any]:
        """Get current registration progress"""
        return {
            'active': self.registration_active,
            'step': self.registration_step,
            'photos_captured': self.photos_captured,
            'target_photos': self.target_photos,
            'current_data': self.current_patient_data
        }