#!/usr/bin/env python3
"""
Text-to-Speech Node for Mars Robot
Handles text-to-speech conversion and audio output
"""
import os
import time
import json
import threading
import queue
from typing import Dict, Any, Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

from std_msgs.msg import String

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    print("pyttsx3 not available. Install with: pip install pyttsx3")

try:
    import gtts
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("gTTS not available. Install with: pip install gtts")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("pygame not available. Install with: pip install pygame")


class TTSNode(Node):
    """Text-to-Speech node for robot voice responses"""

    def __init__(self):
        super().__init__('tts_node')

        # Load configuration
        self.config = self.load_config()

        # TTS engine configuration
        self.engine_type = self.config.get('text_to_speech', {}).get('engine', 'pyttsx3')
        self.voice_config = self.config.get('text_to_speech', {})

        # Initialize TTS engine
        self.tts_engine = None
        self.initialize_tts_engine()

        # Queue for TTS requests
        self.tts_queue = queue.Queue()
        self.speaking = False

        # QoS profile
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            depth=50  # Allow more TTS requests in queue
        )

        # Subscribers
        self.tts_request_sub = self.create_subscription(
            String, '/audio/tts_request', self.tts_request_callback, qos_profile
        )

        self.response_sub = self.create_subscription(
            String, '/robot/response', self.response_callback, qos_profile
        )

        # Publishers
        self.tts_status_pub = self.create_publisher(
            String, '/audio/tts_status', qos_profile
        )

        # Start TTS processing thread
        self.tts_thread = threading.Thread(target=self.process_tts_queue)
        self.tts_thread.daemon = True
        self.tts_thread.start()

        # Statistics
        self.speech_count = 0
        self.total_speech_time = 0.0

        self.get_logger().info(f"TTS Node initialized with engine: {self.engine_type}")

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

    def initialize_tts_engine(self):
        """Initialize the selected TTS engine"""
        try:
            if self.engine_type == 'pyttsx3' and PYTTSX3_AVAILABLE:
                self.tts_engine = TTSPyttsx3Engine(self.voice_config, self.get_logger())
            elif self.engine_type == 'gtts' and GTTS_AVAILABLE:
                self.tts_engine = TTSGoogleEngine(self.voice_config, self.get_logger())
            else:
                self.get_logger().warning(f"TTS engine {self.engine_type} not available, using mock")
                self.tts_engine = TTSMockEngine(self.voice_config, self.get_logger())

            if self.tts_engine.initialize():
                self.get_logger().info(f"TTS engine '{self.engine_type}' initialized successfully")
            else:
                self.get_logger().error("TTS engine initialization failed")

        except Exception as e:
            self.get_logger().error(f"Failed to initialize TTS engine: {e}")
            self.tts_engine = TTSMockEngine(self.voice_config, self.get_logger())

    def tts_request_callback(self, msg: String):
        """Handle TTS request"""
        try:
            # Parse TTS request
            request_data = json.loads(msg.data)
            self.queue_speech(request_data)
        except json.JSONDecodeError:
            # Treat as simple text
            self.queue_speech({'text': msg.data})
        except Exception as e:
            self.get_logger().error(f"Error processing TTS request: {e}")

    def response_callback(self, msg: String):
        """Handle robot response for TTS"""
        try:
            response_data = json.loads(msg.data)
            text = response_data.get('text', '')
            voice_mode = response_data.get('voice_mode', 'default')

            if text:
                self.queue_speech({
                    'text': text,
                    'voice_mode': voice_mode,
                    'priority': response_data.get('priority', 'normal')
                })

        except json.JSONDecodeError:
            # Treat as simple text
            self.queue_speech({'text': msg.data})
        except Exception as e:
            self.get_logger().error(f"Error processing response: {e}")

    def queue_speech(self, speech_data: Dict[str, Any]):
        """Queue speech for TTS processing"""
        try:
            # Add timestamp and ID
            speech_data['timestamp'] = time.time()
            speech_data['speech_id'] = f"tts_{self.speech_count}"

            # Handle priority
            priority = speech_data.get('priority', 'normal')

            if priority == 'urgent':
                # Clear queue for urgent messages
                while not self.tts_queue.empty():
                    try:
                        self.tts_queue.get_nowait()
                    except queue.Empty:
                        break

            self.tts_queue.put(speech_data)
            self.get_logger().debug(f"Queued TTS: '{speech_data.get('text', '')[:50]}...'")

        except Exception as e:
            self.get_logger().error(f"Error queuing speech: {e}")

    def process_tts_queue(self):
        """Process TTS queue in separate thread"""
        while True:
            try:
                # Get next speech request
                speech_data = self.tts_queue.get(timeout=1.0)

                if speech_data:
                    self.speak_text(speech_data)

            except queue.Empty:
                # No requests, continue
                continue
            except Exception as e:
                self.get_logger().error(f"Error in TTS processing thread: {e}")
                time.sleep(1.0)

    def speak_text(self, speech_data: Dict[str, Any]):
        """Speak text using TTS engine"""
        try:
            text = speech_data.get('text', '')
            if not text.strip():
                return

            self.speaking = True
            speech_id = speech_data.get('speech_id', f"speech_{self.speech_count}")

            # Publish status
            self.publish_status('speaking', speech_id)

            start_time = time.time()

            # Use TTS engine to speak
            success = self.tts_engine.speak(text, speech_data)

            end_time = time.time()
            duration = end_time - start_time

            # Update statistics
            self.speech_count += 1
            self.total_speech_time += duration

            # Log speech
            self.get_logger().info(f"Spoke ({duration:.1f}s): '{text[:100]}{'...' if len(text) > 100 else ''}'")

            # Publish completion status
            self.publish_status('completed' if success else 'failed', speech_id, duration)

        except Exception as e:
            self.get_logger().error(f"Error speaking text: {e}")
            self.publish_status('error', speech_data.get('speech_id', 'unknown'))
        finally:
            self.speaking = False

    def publish_status(self, status: str, speech_id: str = '', duration: float = 0.0):
        """Publish TTS status"""
        try:
            status_data = {
                'status': status,
                'speech_id': speech_id,
                'timestamp': time.time(),
                'duration': duration,
                'speaking': self.speaking,
                'queue_size': self.tts_queue.qsize()
            }

            status_msg = String()
            status_msg.data = json.dumps(status_data)
            self.tts_status_pub.publish(status_msg)

        except Exception as e:
            self.get_logger().error(f"Error publishing TTS status: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get TTS statistics"""
        avg_duration = self.total_speech_time / self.speech_count if self.speech_count > 0 else 0

        return {
            'engine': self.engine_type,
            'speech_count': self.speech_count,
            'total_speech_time': self.total_speech_time,
            'average_duration': avg_duration,
            'speaking': self.speaking,
            'queue_size': self.tts_queue.qsize()
        }


class TTSEngineBase:
    """Base class for TTS engines"""

    def __init__(self, config: Dict[str, Any], logger):
        self.config = config
        self.logger = logger

    def initialize(self) -> bool:
        """Initialize TTS engine"""
        raise NotImplementedError

    def speak(self, text: str, options: Dict[str, Any] = None) -> bool:
        """Speak text"""
        raise NotImplementedError

    def shutdown(self):
        """Shutdown TTS engine"""
        pass


class TTSPyttsx3Engine(TTSEngineBase):
    """TTS engine using pyttsx3"""

    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
        self.engine = None

    def initialize(self) -> bool:
        """Initialize pyttsx3 engine"""
        try:
            self.engine = pyttsx3.init()

            # Set voice properties
            rate = self.config.get('rate', 180)
            volume = self.config.get('volume', 0.8)

            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)

            # Try to set voice
            voices = self.engine.getProperty('voices')
            if voices:
                voice_setting = self.config.get('voice', 'default')
                if voice_setting != 'default' and len(voices) > 1:
                    # Try to find matching voice
                    for voice in voices:
                        if voice_setting.lower() in voice.name.lower():
                            self.engine.setProperty('voice', voice.id)
                            break

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize pyttsx3: {e}")
            return False

    def speak(self, text: str, options: Dict[str, Any] = None) -> bool:
        """Speak text using pyttsx3"""
        try:
            if not self.engine:
                return False

            # Handle voice modes
            voice_mode = options.get('voice_mode', 'default') if options else 'default'
            self._apply_voice_mode(voice_mode)

            # Speak text
            self.engine.say(text)
            self.engine.runAndWait()
            return True

        except Exception as e:
            self.logger.error(f"pyttsx3 speech error: {e}")
            return False

    def _apply_voice_mode(self, mode: str):
        """Apply voice mode settings"""
        try:
            voice_modes = self.config.get('voices', {})
            mode_config = voice_modes.get(mode, voice_modes.get('default', {}))

            if 'rate' in mode_config:
                self.engine.setProperty('rate', mode_config['rate'])
            if 'volume' in mode_config:
                self.engine.setProperty('volume', mode_config['volume'])

        except Exception as e:
            self.logger.warning(f"Could not apply voice mode {mode}: {e}")


class TTSGoogleEngine(TTSEngineBase):
    """TTS engine using Google TTS"""

    def initialize(self) -> bool:
        """Initialize Google TTS"""
        try:
            # Check if pygame is available for audio playback
            if not PYGAME_AVAILABLE:
                self.logger.error("pygame required for Google TTS playback")
                return False

            pygame.mixer.init()
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Google TTS: {e}")
            return False

    def speak(self, text: str, options: Dict[str, Any] = None) -> bool:
        """Speak text using Google TTS"""
        try:
            import tempfile

            # Create TTS
            tts = gtts.gTTS(text=text, lang='en')

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                tts.save(tmp_file.name)

                # Play audio
                pygame.mixer.music.load(tmp_file.name)
                pygame.mixer.music.play()

                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                # Clean up
                os.unlink(tmp_file.name)

            return True

        except Exception as e:
            self.logger.error(f"Google TTS error: {e}")
            return False


class TTSMockEngine(TTSEngineBase):
    """Mock TTS engine for testing"""

    def initialize(self) -> bool:
        """Initialize mock TTS"""
        self.logger.info("Mock TTS engine initialized")
        return True

    def speak(self, text: str, options: Dict[str, Any] = None) -> bool:
        """Mock speech (print text)"""
        try:
            voice_mode = options.get('voice_mode', 'default') if options else 'default'

            # Calculate estimated speech time (150 words per minute average)
            word_count = len(text.split())
            speech_time = max(1.0, word_count / 2.5)  # 150 wpm / 60 seconds

            self.logger.info(f"[TTS {voice_mode.upper()}]: {text}")

            # Simulate speech delay
            time.sleep(speech_time)

            return True

        except Exception as e:
            self.logger.error(f"Mock TTS error: {e}")
            return False


def main(args=None):
    """Main entry point"""
    rclpy.init(args=args)

    try:
        node = TTSNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in TTS node: {e}")
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()