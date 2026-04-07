#!/usr/bin/env python3
"""
Speech Processor Node for Mars Robot
Handles speech-to-text conversion using Whisper and other engines
"""
import os
import time
import json
import tempfile
import threading
import queue
from typing import Dict, Any, Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

import numpy as np
from std_msgs.msg import Bool, String
from sensor_msgs.msg import Image

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Whisper not available. Install with: pip install openai-whisper")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    print("SpeechRecognition not available. Install with: pip install SpeechRecognition")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("PyAudio not available. Install with: pip install pyaudio")


class SpeechProcessor(Node):
    """Speech-to-text processing node"""

    def __init__(self):
        super().__init__('speech_processor')

        # Load configuration
        self.config = self.load_config()

        # Speech recognition engine
        self.engine = self.config.get('speech_recognition', {}).get('engine', 'whisper')
        self.model_size = self.config.get('speech_recognition', {}).get('model', 'base')

        # Initialize speech recognition
        self.whisper_model = None
        self.sr_recognizer = None
        self.initialize_recognition_engine()

        # Audio settings
        self.sample_rate = self.config.get('speech_recognition', {}).get('sample_rate', 16000)
        self.max_duration = self.config.get('speech_recognition', {}).get('max_recording_duration', 10.0)
        self.min_duration = self.config.get('speech_recognition', {}).get('min_recording_duration', 1.0)

        # State management
        self.listening = False
        self.recording = False
        self.audio_queue = queue.Queue()

        # QoS profile
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            depth=10
        )

        # Subscribers
        self.wake_word_sub = self.create_subscription(
            Bool, '/voice/wake_word_detected', self.wake_word_callback, qos_profile
        )

        # Publishers
        self.command_pub = self.create_publisher(
            String, '/voice/command_recognized', qos_profile
        )

        self.transcript_pub = self.create_publisher(
            String, '/voice/transcript', qos_profile
        )

        self.status_pub = self.create_publisher(
            String, '/voice/speech_status', qos_profile
        )

        # Audio interface
        self.audio_interface = None
        self.initialize_audio_interface()

        # Statistics
        self.processing_count = 0
        self.successful_recognitions = 0
        self.failed_recognitions = 0

        self.get_logger().info(f"Speech Processor initialized with engine: {self.engine}")

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            import yaml
            config_path = "/config/voice_config.yaml"
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            self.get_logger().warning(f"Could not load config: {e}. Using defaults.")
            return {}

    def initialize_recognition_engine(self):
        """Initialize the selected speech recognition engine"""
        try:
            if self.engine == 'whisper' and WHISPER_AVAILABLE:
                self.get_logger().info(f"Loading Whisper model: {self.model_size}")
                self.whisper_model = whisper.load_model(self.model_size)
                self.get_logger().info("Whisper model loaded successfully")

            elif self.engine in ['google', 'sphinx'] and SR_AVAILABLE:
                self.sr_recognizer = sr.Recognizer()
                # Adjust for ambient noise
                self.get_logger().info(f"SpeechRecognition engine initialized: {self.engine}")

            else:
                self.get_logger().warning("No suitable speech recognition engine available")
                # Use mock recognizer
                self.engine = 'mock'

        except Exception as e:
            self.get_logger().error(f"Failed to initialize recognition engine: {e}")
            self.engine = 'mock'

    def initialize_audio_interface(self):
        """Initialize audio interface for recording"""
        try:
            # This would normally use the hardware abstraction layer
            # For now, we'll use a simple interface
            if PYAUDIO_AVAILABLE:
                self.audio_interface = SimpleAudioInterface(
                    sample_rate=self.sample_rate,
                    logger=self.get_logger()
                )
            else:
                self.get_logger().warning("PyAudio not available, using mock audio")
                self.audio_interface = MockAudioInterface()

        except Exception as e:
            self.get_logger().error(f"Failed to initialize audio interface: {e}")
            self.audio_interface = MockAudioInterface()

    def wake_word_callback(self, msg: Bool):
        """Handle wake word detection"""
        if msg.data and not self.listening:
            self.get_logger().info("Wake word detected, starting to listen for command")
            self.start_listening()

    def start_listening(self):
        """Start listening for voice command"""
        if self.listening:
            self.get_logger().warning("Already listening")
            return

        self.listening = True
        self.publish_status("listening")

        # Start listening in separate thread
        listen_thread = threading.Thread(target=self.listen_for_command)
        listen_thread.daemon = True
        listen_thread.start()

    def listen_for_command(self):
        """Listen for voice command and process it"""
        try:
            self.get_logger().info("Listening for voice command...")

            # Record audio
            audio_data = self.record_audio()

            if audio_data is not None:
                # Process speech to text
                transcript = self.process_speech(audio_data)

                if transcript:
                    self.get_logger().info(f"Recognized: '{transcript}'")

                    # Publish transcript
                    transcript_msg = String()
                    transcript_msg.data = transcript
                    self.transcript_pub.publish(transcript_msg)

                    # Process command
                    command = self.extract_command(transcript)
                    if command:
                        command_msg = String()
                        command_msg.data = json.dumps(command)
                        self.command_pub.publish(command_msg)

                    self.successful_recognitions += 1
                    self.publish_status("recognized")
                else:
                    self.failed_recognitions += 1
                    self.publish_status("recognition_failed")
            else:
                self.publish_status("recording_failed")

        except Exception as e:
            self.get_logger().error(f"Error in speech processing: {e}")
            self.publish_status("error")
        finally:
            self.listening = False
            self.processing_count += 1

    def record_audio(self) -> Optional[np.ndarray]:
        """Record audio from microphone"""
        try:
            return self.audio_interface.record_audio(duration=self.max_duration)
        except Exception as e:
            self.get_logger().error(f"Audio recording failed: {e}")
            return None

    def process_speech(self, audio_data: np.ndarray) -> Optional[str]:
        """Process audio data to extract speech"""
        try:
            if self.engine == 'whisper':
                return self.process_with_whisper(audio_data)
            elif self.engine in ['google', 'sphinx']:
                return self.process_with_speech_recognition(audio_data)
            elif self.engine == 'mock':
                return self.mock_speech_recognition(audio_data)
            else:
                self.get_logger().error(f"Unknown speech engine: {self.engine}")
                return None

        except Exception as e:
            self.get_logger().error(f"Speech processing error: {e}")
            return None

    def process_with_whisper(self, audio_data: np.ndarray) -> Optional[str]:
        """Process audio using Whisper"""
        try:
            if self.whisper_model is None:
                return None

            # Whisper expects float32 audio normalized to [-1, 1]
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data.astype(np.float32)

            # Process with Whisper
            result = self.whisper_model.transcribe(audio_float)
            text = result['text'].strip()

            # Check confidence if available
            confidence = result.get('confidence', 1.0)
            min_confidence = self.config.get('speech_recognition', {}).get('confidence_threshold', 0.3)

            if confidence < min_confidence:
                self.get_logger().warning(f"Low confidence recognition: {confidence}")
                return None

            return text

        except Exception as e:
            self.get_logger().error(f"Whisper processing error: {e}")
            return None

    def process_with_speech_recognition(self, audio_data: np.ndarray) -> Optional[str]:
        """Process audio using speech_recognition library"""
        try:
            if self.sr_recognizer is None:
                return None

            # Convert numpy array to AudioData
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            audio_file = sr.AudioData(audio_bytes, self.sample_rate, 2)

            # Recognize speech
            if self.engine == 'google':
                text = self.sr_recognizer.recognize_google(audio_file)
            elif self.engine == 'sphinx':
                text = self.sr_recognizer.recognize_sphinx(audio_file)
            else:
                return None

            return text.strip()

        except sr.UnknownValueError:
            self.get_logger().warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            self.get_logger().error(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            self.get_logger().error(f"Speech recognition error: {e}")
            return None

    def mock_speech_recognition(self, audio_data: np.ndarray) -> Optional[str]:
        """Mock speech recognition for testing"""
        # Simulate some processing time
        time.sleep(1.0)

        # Return a predefined command based on duration
        duration = len(audio_data) / self.sample_rate
        if duration > 3.0:
            return "register me please"
        elif duration > 2.0:
            return "follow me"
        else:
            return "i have a question"

    def extract_command(self, transcript: str) -> Optional[Dict[str, Any]]:
        """Extract command from transcript"""
        try:
            # Convert to lowercase for matching
            text_lower = transcript.lower()

            # Load command patterns from config
            commands = self.config.get('commands', {})

            # Check each command pattern
            for command_type, command_config in commands.items():
                patterns = command_config.get('patterns', [])

                for pattern in patterns:
                    if pattern.lower() in text_lower:
                        return {
                            'command': command_type,
                            'transcript': transcript,
                            'confidence': 1.0,
                            'timestamp': time.time()
                        }

            # No specific command found, return as general query
            return {
                'command': 'general_query',
                'transcript': transcript,
                'confidence': 0.5,
                'timestamp': time.time()
            }

        except Exception as e:
            self.get_logger().error(f"Command extraction error: {e}")
            return None

    def publish_status(self, status: str):
        """Publish speech processing status"""
        status_msg = String()
        status_msg.data = json.dumps({
            'status': status,
            'timestamp': time.time(),
            'processing_count': self.processing_count
        })
        self.status_pub.publish(status_msg)

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        total = self.successful_recognitions + self.failed_recognitions
        success_rate = self.successful_recognitions / total if total > 0 else 0

        return {
            'engine': self.engine,
            'processing_count': self.processing_count,
            'successful_recognitions': self.successful_recognitions,
            'failed_recognitions': self.failed_recognitions,
            'success_rate': success_rate,
            'listening': self.listening
        }


class SimpleAudioInterface:
    """Simple audio recording interface using PyAudio"""

    def __init__(self, sample_rate: int = 16000, logger=None):
        self.sample_rate = sample_rate
        self.logger = logger
        self.audio = None
        self.initialize()

    def initialize(self):
        """Initialize PyAudio"""
        try:
            import pyaudio
            self.audio = pyaudio.PyAudio()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize audio: {e}")

    def record_audio(self, duration: float = 5.0) -> Optional[np.ndarray]:
        """Record audio for specified duration"""
        try:
            if not self.audio:
                return None

            chunk = 1024
            format = self.audio.get_format_from_width(2)  # 16-bit
            channels = 1

            stream = self.audio.open(
                format=format,
                channels=channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=chunk
            )

            frames = []
            num_chunks = int(self.sample_rate / chunk * duration)

            for _ in range(num_chunks):
                data = stream.read(chunk)
                frames.append(data)

            stream.stop_stream()
            stream.close()

            # Convert to numpy array
            audio_data = b''.join(frames)
            return np.frombuffer(audio_data, dtype=np.int16)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Recording error: {e}")
            return None

    def shutdown(self):
        """Shutdown audio interface"""
        if self.audio:
            self.audio.terminate()


class MockAudioInterface:
    """Mock audio interface for testing"""

    def record_audio(self, duration: float = 5.0) -> Optional[np.ndarray]:
        """Generate mock audio data"""
        # Generate some random audio data
        samples = int(16000 * duration)
        return np.random.randint(-1000, 1000, samples, dtype=np.int16)


def main(args=None):
    """Main entry point"""
    rclpy.init(args=args)

    try:
        node = SpeechProcessor()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in speech processor: {e}")
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()