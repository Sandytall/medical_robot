#!/usr/bin/env python3
"""
Wake Word Detection Service for Mars Robot
Uses Porcupine for "Hey Mars" detection and communicates with ROS2 via ZMQ
"""
import os
import sys
import time
import struct
import argparse
import threading
import queue
import yaml

try:
    import pvporcupine
except ImportError:
    print("Porcupine not available. Install with: pip install pvporcupine")
    pvporcupine = None

try:
    import pyaudio
except ImportError:
    print("PyAudio not available. Install with: pip install pyaudio")
    pyaudio = None

try:
    import zmq
except ImportError:
    print("ZMQ not available. Install with: pip install zmq")
    zmq = None

import psutil
import numpy as np
from typing import Dict, List, Optional


class WakeWordDetector:
    """Wake word detection service using Porcupine"""

    def __init__(self, config_path: str = "/config/voice_config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self.audio_queue = queue.Queue()

        # Porcupine configuration
        self.porcupine = None
        self.keywords = self.config.get('wake_word', {}).get('keywords', ['mars'])
        self.sensitivities = self.config.get('wake_word', {}).get('sensitivities', [0.7])

        # Audio configuration
        self.sample_rate = self.config.get('wake_word', {}).get('sample_rate', 16000)
        self.frame_length = self.config.get('wake_word', {}).get('frame_length', 512)

        # ZMQ configuration
        self.zmq_context = None
        self.publisher = None

        # PyAudio configuration
        self.audio = None
        self.audio_stream = None

        print(f"WakeWordDetector initialized with keywords: {self.keywords}")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Config file not found: {config_path}. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            print(f"Error loading config: {e}. Using defaults.")
            return {}

    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            # Check if required packages are available
            if not all([pvporcupine, pyaudio, zmq]):
                print("Required packages not available. See import errors above.")
                return False

            # Initialize Porcupine
            if not self._initialize_porcupine():
                return False

            # Initialize ZMQ
            if not self._initialize_zmq():
                return False

            # Initialize PyAudio
            if not self._initialize_audio():
                return False

            print("Wake word detector initialized successfully")
            return True

        except Exception as e:
            print(f"Initialization failed: {e}")
            return False

    def _initialize_porcupine(self) -> bool:
        """Initialize Porcupine wake word detection"""
        try:
            self.porcupine = pvporcupine.create(
                keywords=self.keywords,
                sensitivities=self.sensitivities
            )
            print(f"Porcupine initialized with sample rate: {self.porcupine.sample_rate}")

            # Update sample rate and frame length from Porcupine
            self.sample_rate = self.porcupine.sample_rate
            self.frame_length = self.porcupine.frame_length

            return True
        except Exception as e:
            print(f"Failed to initialize Porcupine: {e}")
            return False

    def _initialize_zmq(self) -> bool:
        """Initialize ZMQ publisher for communication with ROS2"""
        try:
            self.zmq_context = zmq.Context()
            self.publisher = self.zmq_context.socket(zmq.PUB)
            self.publisher.bind("tcp://*:5555")
            print("ZMQ publisher bound to port 5555")
            return True
        except Exception as e:
            print(f"Failed to initialize ZMQ: {e}")
            return False

    def _initialize_audio(self) -> bool:
        """Initialize PyAudio for microphone input"""
        try:
            self.audio = pyaudio.PyAudio()

            # List available audio devices for debugging
            print("Available audio devices:")
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    print(f"  {i}: {info['name']} (channels: {info['maxInputChannels']})")

            # Open audio stream
            self.audio_stream = self.audio.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.frame_length,
                input_device_index=None  # Use default input device
            )

            print(f"Audio stream opened: {self.sample_rate}Hz, frame_length={self.frame_length}")
            return True

        except Exception as e:
            print(f"Failed to initialize audio: {e}")
            return False

    def listen_continuously(self):
        """Main loop for continuous wake word detection"""
        print("Starting continuous wake word listening...")
        self.running = True

        # Start audio monitoring thread
        audio_thread = threading.Thread(target=self._audio_monitor_thread)
        audio_thread.daemon = True
        audio_thread.start()

        detection_count = 0
        last_detection_time = 0

        try:
            while self.running:
                # Read audio data
                try:
                    pcm = self.audio_stream.read(
                        self.frame_length,
                        exception_on_overflow=False
                    )
                    pcm = struct.unpack_from("h" * self.frame_length, pcm)

                    # Process with Porcupine
                    keyword_index = self.porcupine.process(pcm)

                    if keyword_index >= 0:
                        current_time = time.time()

                        # Prevent multiple rapid detections
                        if current_time - last_detection_time > 2.0:
                            detection_count += 1
                            last_detection_time = current_time

                            detected_keyword = self.keywords[keyword_index]
                            print(f"Wake word detected: '{detected_keyword}' (#{detection_count})")

                            # Send notification via ZMQ
                            self._send_wake_word_notification(detected_keyword)

                            # Optional: Play confirmation sound
                            if self.config.get('wake_word', {}).get('confirmation_sounds', False):
                                self._play_confirmation_sound()

                except Exception as e:
                    if self.running:  # Only log if we're still supposed to be running
                        print(f"Audio processing error: {e}")
                    time.sleep(0.1)  # Brief pause before retry

        except KeyboardInterrupt:
            print("\nReceived interrupt signal")
        except Exception as e:
            print(f"Main loop error: {e}")
        finally:
            self.shutdown()

    def _audio_monitor_thread(self):
        """Monitor audio system health in separate thread"""
        while self.running:
            try:
                # Check audio stream health
                if self.audio_stream and not self.audio_stream.is_active():
                    print("Audio stream not active, attempting restart...")
                    self._restart_audio_stream()

                time.sleep(5.0)  # Check every 5 seconds

            except Exception as e:
                print(f"Audio monitor error: {e}")
                time.sleep(1.0)

    def _restart_audio_stream(self):
        """Restart audio stream if it fails"""
        try:
            if self.audio_stream:
                self.audio_stream.close()

            self.audio_stream = self.audio.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.frame_length,
                input_device_index=None
            )
            print("Audio stream restarted successfully")

        except Exception as e:
            print(f"Failed to restart audio stream: {e}")

    def _send_wake_word_notification(self, keyword: str):
        """Send wake word detection notification via ZMQ"""
        try:
            message = {
                'event': 'WAKE_WORD_DETECTED',
                'keyword': keyword,
                'timestamp': time.time()
            }

            # Send as JSON string
            import json
            self.publisher.send_string(json.dumps(message))

            # Also send simple string for backward compatibility
            self.publisher.send_string("WAKE_WORD_DETECTED")

        except Exception as e:
            print(f"Failed to send ZMQ notification: {e}")

    def _play_confirmation_sound(self):
        """Play confirmation sound (if audio output is available)"""
        try:
            # This is a placeholder - in real implementation, you might
            # play a brief beep or other confirmation sound
            print("*beep* (confirmation sound)")
        except Exception as e:
            print(f"Failed to play confirmation sound: {e}")

    def get_system_status(self) -> Dict:
        """Get current system status"""
        return {
            'running': self.running,
            'keywords': self.keywords,
            'sample_rate': self.sample_rate,
            'frame_length': self.frame_length,
            'audio_active': self.audio_stream.is_active() if self.audio_stream else False,
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent
        }

    def shutdown(self):
        """Shutdown wake word detector"""
        print("Shutting down wake word detector...")
        self.running = False

        try:
            if self.audio_stream:
                self.audio_stream.close()
            if self.audio:
                self.audio.terminate()
            if self.porcupine:
                self.porcupine.delete()
            if self.publisher:
                self.publisher.close()
            if self.zmq_context:
                self.zmq_context.term()

        except Exception as e:
            print(f"Error during shutdown: {e}")

        print("Wake word detector shutdown completed")


class MockWakeWordDetector(WakeWordDetector):
    """Mock wake word detector for development without Porcupine"""

    def __init__(self, config_path: str = "/config/voice_config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self.keywords = ["mars"]
        self.zmq_context = None
        self.publisher = None
        print("Mock wake word detector initialized (no audio processing)")

    def initialize(self) -> bool:
        """Initialize mock detector"""
        try:
            if not self._initialize_zmq():
                return False
            print("Mock wake word detector initialized")
            return True
        except Exception as e:
            print(f"Mock initialization failed: {e}")
            return False

    def listen_continuously(self):
        """Mock listening with keyboard input"""
        print("Mock wake word detector - Press Enter to simulate wake word detection")
        print("Type 'quit' to exit")

        self.running = True
        try:
            while self.running:
                user_input = input().strip().lower()
                if user_input == 'quit':
                    break
                elif user_input == '' or 'mars' in user_input:
                    print("Wake word detected: 'mars' (simulated)")
                    self._send_wake_word_notification('mars')
                else:
                    print(f"Unknown input: {user_input}")

        except KeyboardInterrupt:
            print("\nReceived interrupt signal")
        finally:
            self.shutdown()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Mars Robot Wake Word Detector')
    parser.add_argument('--config', default='/config/voice_config.yaml',
                       help='Path to voice configuration file')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock detector for development')

    args = parser.parse_args()

    # Choose detector based on mode
    if args.mock or not all([pvporcupine, pyaudio]):
        detector = MockWakeWordDetector(args.config)
    else:
        detector = WakeWordDetector(args.config)

    # Initialize and run
    if detector.initialize():
        try:
            detector.listen_continuously()
        except Exception as e:
            print(f"Runtime error: {e}")
    else:
        print("Failed to initialize wake word detector")
        sys.exit(1)


if __name__ == "__main__":
    main()