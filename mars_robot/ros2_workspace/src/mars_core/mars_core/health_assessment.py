#!/usr/bin/env python3
"""
Health Assessment System for Mars Robot
Handles "Hey mars i don't feel" functionality with health evaluation and doctor dashboard
"""
import time
import json
import uuid
import threading
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime

import cv2
import numpy as np
import rclpy
from rclpy.node import Node

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("TextBlob not available for sentiment analysis. Install with: pip install textblob")


class SeverityLevel(Enum):
    """Health issue severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthAssessment(Node):
    """Health assessment and monitoring handler"""

    def __init__(self, hardware_manager, database, config: Dict[str, Any]):
        super().__init__('health_assessment')

        self.hardware = hardware_manager
        self.database = database
        self.config = config

        # Health assessment state
        self.assessment_active = False
        self.current_patient = None
        self.assessment_data = {}
        self.assessment_id = ""

        # Configuration
        self.assessment_timeout = self.config.get('modes', {}).get('health_check', {}).get('assessment_timeout', 180.0)
        self.severity_keywords = self.config.get('modes', {}).get('health_check', {}).get('severity_keywords', {})

        # Health questions
        self.health_questions = self.config.get('modes', {}).get('health_check', {}).get('questions', [
            "What symptoms are you experiencing?",
            "Are you having any nausea or vomiting?",
            "Have you taken your medications today?",
            "How well are you sleeping?",
            "On a scale of 1-10, how would you rate your pain?"
        ])

        # Current question state
        self.current_question_index = 0
        self.waiting_for_response = False
        self.question_responses = []

        # Face detection for sentiment analysis
        self.face_cascade = self._load_face_cascade()

        # Dashboard data storage
        self.health_reports = []

        self.get_logger().info("Health Assessment system initialized")

    def _load_face_cascade(self):
        """Load OpenCV face detection cascade"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            return cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            self.get_logger().error(f"Failed to load face cascade: {e}")
            return None

    def start_health_assessment(self) -> bool:
        """Start health assessment process"""
        try:
            if self.assessment_active:
                self.get_logger().warning("Health assessment already active")
                return False

            # First, identify the patient
            patient = self._identify_patient()
            if not patient:
                if self.hardware.audio:
                    self.hardware.audio.play_text("I need to identify you first. Please look at my camera.")

                # Try to identify patient for 15 seconds
                identification_timeout = 15.0
                start_time = time.time()

                while time.time() - start_time < identification_timeout:
                    patient = self._identify_patient()
                    if patient:
                        break
                    time.sleep(1.0)

                if not patient:
                    if self.hardware.audio:
                        self.hardware.audio.play_text("I couldn't identify you. Please register first or contact staff for help.")
                    return False

            self.assessment_active = True
            self.current_patient = patient
            self.assessment_id = f"health_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            self.current_question_index = 0
            self.waiting_for_response = False
            self.question_responses = []

            # Initialize assessment data
            self.assessment_data = {
                'assessment_id': self.assessment_id,
                'patient_id': patient['patient_id'],
                'patient_name': patient['name'],
                'start_time': datetime.now().isoformat(),
                'symptoms': [],
                'responses': [],
                'severity_level': SeverityLevel.LOW,
                'requires_immediate_attention': False,
                'sentiment_analysis': {},
                'photo_path': ""
            }

            # Set display to health check mode
            if self.hardware.display:
                self.hardware.display.show_text(f"Health Check\n{patient['name']}")

            # Welcome message
            if self.hardware.audio:
                self.hardware.audio.play_text(f"Hello {patient['name']}. I'm here to help assess how you're feeling. Let me ask you a few questions.")

            # Start assessment thread
            threading.Thread(target=self._health_assessment_loop, daemon=True).start()

            self.get_logger().info(f"Health assessment started for {patient['name']}")
            return True

        except Exception as e:
            self.get_logger().error(f"Health assessment start error: {e}")
            return False

    def stop_health_assessment(self):
        """Stop health assessment"""
        try:
            if not self.assessment_active:
                return

            self.assessment_active = False

            # Complete assessment data
            if self.assessment_data:
                self.assessment_data['end_time'] = datetime.now().isoformat()
                self.assessment_data['duration_minutes'] = (
                    datetime.fromisoformat(self.assessment_data['end_time']) -
                    datetime.fromisoformat(self.assessment_data['start_time'])
                ).total_seconds() / 60

                # Generate final assessment
                self._generate_final_assessment()

                # Send to doctor dashboard
                self._send_to_dashboard()

            # Announce completion
            if self.hardware.audio:
                self.hardware.audio.play_text("Health assessment complete. I've sent your information to the medical team.")

            self.get_logger().info("Health assessment completed")

        except Exception as e:
            self.get_logger().error(f"Health assessment stop error: {e}")

    def _identify_patient(self) -> Optional[Dict[str, Any]]:
        """Identify patient using face recognition"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                return None

            frame = self.hardware.camera.capture_frame()
            if frame is None:
                return None

            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Find face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame)

            if not face_encodings:
                return None

            # Try to match against database
            for face_encoding in face_encodings:
                patient = self.database.get_patient_by_face(face_encoding)
                if patient and patient['confidence'] >= 0.4:
                    return patient

            return None

        except Exception as e:
            self.get_logger().warning(f"Patient identification error: {e}")
            return None

    def _health_assessment_loop(self):
        """Main health assessment loop"""
        try:
            start_time = time.time()

            # Ask initial question about symptoms
            self._ask_initial_question()

            while self.assessment_active:
                try:
                    # Check for timeout
                    if time.time() - start_time > self.assessment_timeout:
                        self.get_logger().info("Health assessment timeout")
                        if self.hardware.audio:
                            self.hardware.audio.play_text("Assessment time expired. I'll send what I have to the medical team.")
                        break

                    # Continue with health questions if not waiting for response
                    if not self.waiting_for_response:
                        if self.current_question_index < len(self.health_questions):
                            self._ask_health_question()
                        else:
                            # All questions asked, finish assessment
                            break

                    time.sleep(1.0)

                except Exception as e:
                    self.get_logger().error(f"Assessment loop error: {e}")
                    time.sleep(2.0)

            self.stop_health_assessment()

        except Exception as e:
            self.get_logger().error(f"Health assessment thread error: {e}")

    def _ask_initial_question(self):
        """Ask initial question about symptoms"""
        try:
            if self.hardware.audio:
                self.hardware.audio.play_text("What's wrong? Tell me how you're feeling.")

            self.waiting_for_response = True

        except Exception as e:
            self.get_logger().error(f"Initial question error: {e}")

    def _ask_health_question(self):
        """Ask current health question"""
        try:
            if self.current_question_index >= len(self.health_questions):
                return

            question = self.health_questions[self.current_question_index]

            if self.hardware.audio:
                self.hardware.audio.play_text(question)

            if self.hardware.display:
                self.hardware.display.show_text(f"Health Check\nQ{self.current_question_index + 1}: {question[:40]}...")

            self.waiting_for_response = True

        except Exception as e:
            self.get_logger().error(f"Health question error: {e}")

    def handle_voice_response(self, transcript: str) -> bool:
        """Handle voice response during health assessment"""
        try:
            if not self.assessment_active or not self.waiting_for_response:
                return False

            # Record the response
            response_data = {
                'question_index': self.current_question_index,
                'question': self.health_questions[self.current_question_index] if self.current_question_index < len(self.health_questions) else "Initial symptoms",
                'response': transcript,
                'timestamp': datetime.now().isoformat()
            }

            self.question_responses.append(response_data)
            self.assessment_data['responses'] = self.question_responses

            # Analyze response for symptoms and severity
            self._analyze_response(transcript)

            # Move to next question
            self.current_question_index += 1
            self.waiting_for_response = False

            # Acknowledge response
            acknowledgments = ["I understand.", "Thank you.", "I see.", "Okay."]
            import random
            ack = random.choice(acknowledgments)

            if self.hardware.audio:
                self.hardware.audio.play_text(ack)

            self.get_logger().info(f"Health response recorded: {transcript[:50]}...")
            return True

        except Exception as e:
            self.get_logger().error(f"Voice response handling error: {e}")
            return False

    def _analyze_response(self, response: str):
        """Analyze response for severity and symptoms"""
        try:
            response_lower = response.lower()

            # Extract symptoms
            symptoms = self._extract_symptoms(response_lower)
            self.assessment_data['symptoms'].extend(symptoms)

            # Determine severity
            severity = self._determine_severity(response_lower)
            if severity.value > self.assessment_data['severity_level'].value:
                self.assessment_data['severity_level'] = severity

            # Check for immediate attention keywords
            immediate_keywords = ['chest pain', 'can\'t breathe', 'difficulty breathing',
                                'severe pain', 'emergency', 'help', 'call doctor']

            for keyword in immediate_keywords:
                if keyword in response_lower:
                    self.assessment_data['requires_immediate_attention'] = True
                    break

            # Perform sentiment analysis
            sentiment = self._analyze_sentiment(response)
            if sentiment:
                self.assessment_data['sentiment_analysis'] = sentiment

        except Exception as e:
            self.get_logger().error(f"Response analysis error: {e}")

    def _extract_symptoms(self, response: str) -> List[str]:
        """Extract symptoms from response"""
        try:
            symptom_keywords = [
                'pain', 'headache', 'nausea', 'vomiting', 'fever', 'dizzy',
                'tired', 'fatigue', 'cough', 'sore throat', 'stomach ache',
                'back pain', 'chest pain', 'shortness of breath', 'anxiety',
                'depression', 'insomnia', 'constipation', 'diarrhea'
            ]

            found_symptoms = []
            for symptom in symptom_keywords:
                if symptom in response:
                    found_symptoms.append(symptom)

            return found_symptoms

        except Exception as e:
            self.get_logger().error(f"Symptom extraction error: {e}")
            return []

    def _determine_severity(self, response: str) -> SeverityLevel:
        """Determine severity level based on response"""
        try:
            severity_keywords = self.severity_keywords

            # Check high severity keywords
            for keyword in severity_keywords.get('high', []):
                if keyword in response:
                    return SeverityLevel.HIGH

            # Check medium severity keywords
            for keyword in severity_keywords.get('medium', []):
                if keyword in response:
                    return SeverityLevel.MEDIUM

            # Check low severity keywords
            for keyword in severity_keywords.get('low', []):
                if keyword in response:
                    return SeverityLevel.LOW

            # Check for pain scale numbers
            if any(num in response for num in ['8', '9', '10']):
                return SeverityLevel.HIGH
            elif any(num in response for num in ['5', '6', '7']):
                return SeverityLevel.MEDIUM

            return SeverityLevel.LOW

        except Exception as e:
            self.get_logger().error(f"Severity determination error: {e}")
            return SeverityLevel.LOW

    def _analyze_sentiment(self, text: str) -> Optional[Dict[str, Any]]:
        """Analyze sentiment of patient response"""
        try:
            if not TEXTBLOB_AVAILABLE:
                return None

            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1

            # Classify sentiment
            if polarity > 0.1:
                sentiment_label = "positive"
            elif polarity < -0.1:
                sentiment_label = "negative"
            else:
                sentiment_label = "neutral"

            return {
                'polarity': polarity,
                'subjectivity': subjectivity,
                'sentiment_label': sentiment_label
            }

        except Exception as e:
            self.get_logger().warning(f"Sentiment analysis error: {e}")
            return None

    def _generate_final_assessment(self):
        """Generate final assessment summary"""
        try:
            # Capture patient photo for assessment
            self._capture_patient_photo()

            # Determine overall severity
            overall_severity = self.assessment_data['severity_level']

            # Generate summary
            symptoms_summary = ", ".join(set(self.assessment_data['symptoms']))
            if not symptoms_summary:
                symptoms_summary = "No specific symptoms identified"

            # Create assessment summary
            summary = {
                'patient_condition': self._determine_patient_condition(),
                'symptoms_summary': symptoms_summary,
                'recommendation': self._generate_recommendation(),
                'follow_up_required': self._requires_follow_up()
            }

            self.assessment_data['assessment_summary'] = summary

            self.get_logger().info(f"Final assessment generated for {self.current_patient['name']}")

        except Exception as e:
            self.get_logger().error(f"Final assessment generation error: {e}")

    def _capture_patient_photo(self):
        """Capture patient photo for sentiment analysis"""
        try:
            frame = self.hardware.camera.capture_frame()
            if frame is None:
                return

            # Save photo
            photo_filename = f"health_assessment_{self.assessment_id}.jpg"
            photo_path = f"/shared_data/photos/{photo_filename}"

            import os
            os.makedirs(os.path.dirname(photo_path), exist_ok=True)
            cv2.imwrite(photo_path, frame)

            self.assessment_data['photo_path'] = photo_path

            # Analyze facial sentiment
            facial_sentiment = self._analyze_facial_sentiment(frame)
            if facial_sentiment:
                self.assessment_data['facial_sentiment'] = facial_sentiment

        except Exception as e:
            self.get_logger().warning(f"Photo capture error: {e}")

    def _analyze_facial_sentiment(self, frame: np.ndarray) -> Optional[str]:
        """Analyze facial expression for sentiment"""
        try:
            # Simple facial sentiment analysis based on face detection
            # In a real implementation, this would use more sophisticated emotion recognition

            faces = []
            if self.face_cascade is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

            if len(faces) > 0:
                # For now, return a placeholder based on assessment severity
                if self.assessment_data['severity_level'] == SeverityLevel.HIGH:
                    return "distressed"
                elif self.assessment_data['severity_level'] == SeverityLevel.MEDIUM:
                    return "concerned"
                else:
                    return "calm"

            return "neutral"

        except Exception as e:
            self.get_logger().warning(f"Facial sentiment analysis error: {e}")
            return None

    def _determine_patient_condition(self) -> str:
        """Determine patient's overall condition"""
        severity = self.assessment_data['severity_level']
        requires_attention = self.assessment_data['requires_immediate_attention']

        if requires_attention:
            return "Requires immediate medical attention"
        elif severity == SeverityLevel.HIGH:
            return "Significant health concerns"
        elif severity == SeverityLevel.MEDIUM:
            return "Moderate health issues"
        else:
            return "Mild symptoms or general wellness check"

    def _generate_recommendation(self) -> str:
        """Generate care recommendation"""
        severity = self.assessment_data['severity_level']
        requires_attention = self.assessment_data['requires_immediate_attention']

        if requires_attention:
            return "Immediate medical evaluation required"
        elif severity == SeverityLevel.HIGH:
            return "Schedule appointment with doctor within 24 hours"
        elif severity == SeverityLevel.MEDIUM:
            return "Monitor symptoms and schedule routine appointment"
        else:
            return "Continue current care plan, routine monitoring"

    def _requires_follow_up(self) -> bool:
        """Determine if follow-up is required"""
        return (self.assessment_data['severity_level'].value >= SeverityLevel.MEDIUM.value or
                self.assessment_data['requires_immediate_attention'])

    def _send_to_dashboard(self):
        """Send assessment data to doctor dashboard"""
        try:
            # Add to local storage
            self.health_reports.append(self.assessment_data)

            # In a real implementation, this would send to FastAPI dashboard
            # For now, save to file
            report_file = f"/shared_data/reports/health_report_{self.assessment_id}.json"

            import os
            os.makedirs(os.path.dirname(report_file), exist_ok=True)

            with open(report_file, 'w') as f:
                json.dump(self.assessment_data, f, indent=2)

            self.get_logger().info(f"Health report saved to {report_file}")

            # TODO: Implement FastAPI dashboard integration
            # This would send HTTP POST to doctor dashboard

        except Exception as e:
            self.get_logger().error(f"Dashboard reporting error: {e}")

    def is_assessment_active(self) -> bool:
        """Check if health assessment is currently active"""
        return self.assessment_active

    def get_assessment_status(self) -> Dict[str, Any]:
        """Get current assessment status"""
        return {
            'active': self.assessment_active,
            'current_patient': self.current_patient,
            'assessment_id': self.assessment_id,
            'current_question_index': self.current_question_index,
            'total_questions': len(self.health_questions),
            'waiting_for_response': self.waiting_for_response,
            'severity_level': self.assessment_data.get('severity_level', SeverityLevel.LOW).value,
            'requires_immediate_attention': self.assessment_data.get('requires_immediate_attention', False)
        }

    def get_health_reports(self) -> List[Dict[str, Any]]:
        """Get all health reports"""
        return self.health_reports.copy()

    def cleanup(self):
        """Cleanup health assessment resources"""
        try:
            if self.assessment_active:
                self.stop_health_assessment()

        except Exception as e:
            self.get_logger().error(f"Health assessment cleanup error: {e}")