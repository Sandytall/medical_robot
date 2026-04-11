#!/usr/bin/env python3
"""
Main Robot Controller for Mars Hospital Robot
Central control system that coordinates all robot functions and modes
"""
import os
import sys
import time
import json
import threading
import queue
import psutil
from enum import Enum
from typing import Dict, Any, Optional, List

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

from std_msgs.msg import String, Bool, Float32
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image, JointState
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

# Add path for hardware manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mars_hardware'))
from mars_hardware import HardwareManager
from mars_hardware.interfaces.display_interface import EmotionType

# Import robot function modules
from .patient_registration import PatientRegistration, PatientDatabase
from .manual_control import ManualControl
from .follow_mode import FollowMode
from .question_answering import QuestionAnswering
from .medicine_dispensing import MedicineDispensing
from .health_assessment import HealthAssessment
from .idle_behavior import IdleBehavior
from .display_overlay_service import DisplayOverlayService


class RobotMode(Enum):
    """Robot operating modes"""
    IDLE = "idle"
    MANUAL = "manual"
    FOLLOW = "follow"
    REGISTRATION = "registration"
    QUESTION = "question"
    MEDICINE = "medicine"
    HEALTH_CHECK = "health_check"
    EMERGENCY = "emergency"


class RobotController(Node):
    """Main robot controller node"""

    def __init__(self):
        super().__init__('robot_controller')

        # Load configuration
        self.config = self._load_config()

        # Robot state
        self.current_mode = RobotMode.IDLE
        self.previous_mode = RobotMode.IDLE
        self.is_emergency_stopped = False
        self.last_activity_time = time.time()

        # System monitoring
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.temperature = 0.0
        self.cpu_limit = self.config.get('system', {}).get('cpu_limit', 80.0)

        # Initialize hardware manager
        self.hardware = None
        self.hardware_ready = False
        self._initialize_hardware()

        # Initialize robot function modules
        self.database = None
        self.registration_module = None
        self.manual_control_module = None
        self.follow_mode_module = None
        self.qa_module = None
        self.medicine_module = None
        self.health_module = None
        self.idle_module = None
        self.display_overlay_service = None
        self._initialize_robot_modules()

        # QoS profiles
        self.reliable_qos = QoSProfile(reliability=QoSReliabilityPolicy.RELIABLE, depth=10)

        # Publishers
        self.mode_pub = self.create_publisher(String, '/robot/current_mode', self.reliable_qos)
        self.status_pub = self.create_publisher(String, '/robot/status', self.reliable_qos)
        self.response_pub = self.create_publisher(String, '/robot/response', self.reliable_qos)
        self.diagnostics_pub = self.create_publisher(DiagnosticArray, '/diagnostics', self.reliable_qos)
        self.emergency_stop_pub = self.create_publisher(Bool, '/robot/emergency_stop', self.reliable_qos)

        # Subscribers
        self.wake_word_sub = self.create_subscription(
            Bool, '/voice/wake_word_detected', self.wake_word_callback, self.reliable_qos
        )
        self.command_sub = self.create_subscription(
            String, '/voice/command_recognized', self.command_callback, self.reliable_qos
        )
        self.emergency_sub = self.create_subscription(
            Bool, '/robot/emergency_stop', self.emergency_stop_callback, self.reliable_qos
        )

        # Command queue for processing
        self.command_queue = queue.Queue()

        # Timers
        self.mode_timer = self.create_timer(0.1, self.mode_update_loop)  # 10Hz mode update
        self.monitoring_timer = self.create_timer(1.0, self.system_monitoring_loop)  # 1Hz monitoring
        self.diagnostics_timer = self.create_timer(5.0, self.publish_diagnostics)  # 5s diagnostics
        self.activity_timer = self.create_timer(10.0, self.check_activity_timeout)  # 10s activity check

        # Mode handlers
        self.mode_handlers = {
            RobotMode.IDLE: self._handle_idle_mode,
            RobotMode.MANUAL: self._handle_manual_mode,
            RobotMode.FOLLOW: self._handle_follow_mode,
            RobotMode.REGISTRATION: self._handle_registration_mode,
            RobotMode.QUESTION: self._handle_question_mode,
            RobotMode.MEDICINE: self._handle_medicine_mode,
            RobotMode.HEALTH_CHECK: self._handle_health_check_mode,
            RobotMode.EMERGENCY: self._handle_emergency_mode
        }

        # Mode start times (for timeouts)
        self.mode_start_time = time.time()
        self.mode_timeouts = {
            RobotMode.MANUAL: 600.0,      # 10 minutes
            RobotMode.FOLLOW: 300.0,      # 5 minutes
            RobotMode.REGISTRATION: 120.0, # 2 minutes
            RobotMode.QUESTION: 60.0,     # 1 minute
            RobotMode.MEDICINE: 1800.0,   # 30 minutes
            RobotMode.HEALTH_CHECK: 180.0, # 3 minutes
        }

        # Statistics
        self.mode_changes = 0
        self.commands_processed = 0
        self.emergency_stops = 0

        self.get_logger().info("Mars Robot Controller initialized")

        # Initialize display and announce startup
        self._startup_sequence()

    def _load_config(self) -> Dict[str, Any]:
        """Load robot configuration"""
        try:
            import yaml
            config_files = [
                '/config/robot_config.yaml',
                '/config/behavior_config.yaml'
            ]

            config = {}
            for config_file in config_files:
                try:
                    with open(config_file, 'r') as f:
                        file_config = yaml.safe_load(f)
                        config.update(file_config)
                except FileNotFoundError:
                    self.get_logger().warning(f"Config file not found: {config_file}")
                except Exception as e:
                    self.get_logger().error(f"Error loading {config_file}: {e}")

            return config

        except Exception as e:
            self.get_logger().error(f"Failed to load configuration: {e}")
            return {}

    def _initialize_hardware(self):
        """Initialize hardware manager"""
        try:
            # Initialize hardware with configuration
            hardware_config = self.config.get('hardware', {})
            self.hardware = HardwareManager(hardware_config)

            # Initialize all hardware components
            self.get_logger().info("Initializing hardware components...")

            if self.hardware.camera.initialize():
                self.get_logger().info("✓ Camera initialized")
            else:
                self.get_logger().warning("✗ Camera initialization failed")

            if self.hardware.motors.initialize():
                self.get_logger().info("✓ Motors initialized")
            else:
                self.get_logger().warning("✗ Motor initialization failed")

            if self.hardware.arms.initialize():
                self.get_logger().info("✓ Arms initialized")
            else:
                self.get_logger().warning("✗ Arms initialization failed")

            if self.hardware.camera_servos.initialize():
                self.get_logger().info("✓ Camera servos initialized")
            else:
                self.get_logger().warning("✗ Camera servos initialization failed")

            if self.hardware.audio.initialize():
                self.get_logger().info("✓ Audio initialized")
            else:
                self.get_logger().warning("✗ Audio initialization failed")

            if self.hardware.display.initialize():
                self.get_logger().info("✓ Display initialized")
            else:
                self.get_logger().warning("✗ Display initialization failed")

            self.hardware_ready = True
            self.get_logger().info("Hardware initialization completed")

        except Exception as e:
            self.get_logger().error(f"Hardware initialization failed: {e}")
            self.hardware_ready = False

    def _initialize_robot_modules(self):
        """Initialize robot function modules"""
        try:
            # Initialize patient database
            self.database = PatientDatabase()

            # Initialize function modules
            self.registration_module = PatientRegistration(self.hardware, self.config)
            self.manual_control_module = ManualControl(self.hardware, self.config)
            self.follow_mode_module = FollowMode(self.hardware, self.database, self.config)
            self.qa_module = QuestionAnswering(self.hardware, self.config)
            self.medicine_module = MedicineDispensing(self.hardware, self.database, self.config)
            self.health_module = HealthAssessment(self.hardware, self.database, self.config)
            self.idle_module = IdleBehavior(self.hardware, self.config)

            # Initialize display overlay service
            if self.hardware and self.hardware.display_overlay:
                self.display_overlay_service = DisplayOverlayService(
                    self.hardware.display_overlay,
                    self.config.get('display_overlay', {})
                )
                self.display_overlay_service.initialize()

            # Start idle behavior by default
            self.idle_module.start_idle_behavior()

            self.get_logger().info("Robot function modules initialized")

        except Exception as e:
            self.get_logger().error(f"Robot modules initialization failed: {e}")

    def _startup_sequence(self):
        """Robot startup sequence"""
        try:
            # Update display overlay to show startup
            if self.display_overlay_service:
                self.display_overlay_service.update_robot_state("starting_up", False)

            if self.hardware and self.hardware.display:
                self.hardware.display.show_text("MARS Robot Starting...")
                time.sleep(1)
                self.hardware.display.show_emotion(EmotionType.HAPPY, 2.0)

            if self.hardware and self.hardware.audio:
                self.hardware.audio.play_sound_effect('startup')
                time.sleep(0.5)
                self.hardware.audio.play_text("Hello! I am MARS, your hospital assistant. I'm ready to help!")

            # Update display overlay to show ready state
            if self.display_overlay_service:
                self.display_overlay_service.update_robot_state("idle", True)

            self._publish_status("startup_complete")
            self.get_logger().info("🚀 MARS Robot startup sequence completed")

        except Exception as e:
            self.get_logger().error(f"Startup sequence error: {e}")

    def wake_word_callback(self, msg: Bool):
        """Handle wake word detection"""
        if msg.data:
            self.last_activity_time = time.time()

            if self.hardware and self.hardware.audio:
                # Random response to wake word
                responses = self.config.get('wake_word', {}).get('responses', ['hey'])
                import random
                response = random.choice(responses)
                self.hardware.audio.play_text(response)

            self._publish_status("wake_word_detected")
            self.get_logger().info("Wake word detected - robot activated")

    def command_callback(self, msg: String):
        """Handle recognized voice commands"""
        try:
            command_data = json.loads(msg.data)
            command_type = command_data.get('command', '')
            transcript = command_data.get('transcript', '')

            self.last_activity_time = time.time()
            self.commands_processed += 1

            self.get_logger().info(f"Processing command: {command_type} - '{transcript}'")

            # Add command to queue for processing
            self.command_queue.put(command_data)

        except json.JSONDecodeError:
            self.get_logger().error(f"Invalid command JSON: {msg.data}")
        except Exception as e:
            self.get_logger().error(f"Command processing error: {e}")

    def emergency_stop_callback(self, msg: Bool):
        """Handle emergency stop signal"""
        if msg.data:
            self.emergency_stop()

    def emergency_stop(self):
        """Execute emergency stop"""
        try:
            self.get_logger().warning("🚨 EMERGENCY STOP ACTIVATED")

            self.is_emergency_stopped = True
            self.emergency_stops += 1
            self.previous_mode = self.current_mode
            self.current_mode = RobotMode.EMERGENCY

            # Update display overlay for emergency
            if self.display_overlay_service:
                self.display_overlay_service.show_error("EMERGENCY STOP ACTIVATED", "emergency")

            # Stop all hardware
            if self.hardware:
                self.hardware.emergency_stop()

            # Notify display and audio
            if self.hardware and self.hardware.display:
                self.hardware.display.show_status("EMERGENCY STOP", "error")

            if self.hardware and self.hardware.audio:
                self.hardware.audio.play_sound_effect('alert')
                self.hardware.audio.play_text("Emergency stop activated")

            # Publish emergency stop
            stop_msg = Bool()
            stop_msg.data = True
            self.emergency_stop_pub.publish(stop_msg)

            self._publish_status("emergency_stop")

        except Exception as e:
            self.get_logger().error(f"Emergency stop execution error: {e}")

    def clear_emergency_stop(self):
        """Clear emergency stop and return to previous mode"""
        try:
            if self.is_emergency_stopped:
                self.get_logger().info("Clearing emergency stop")

                self.is_emergency_stopped = False
                self.current_mode = self.previous_mode if self.previous_mode != RobotMode.EMERGENCY else RobotMode.IDLE

                # Clear display overlay error
                if self.display_overlay_service:
                    self.display_overlay_service.clear_error()
                    self.display_overlay_service.update_robot_state(self.current_mode.value, True)

                if self.hardware and self.hardware.audio:
                    self.hardware.audio.play_text("Emergency stop cleared")

                self._publish_status("emergency_cleared")

        except Exception as e:
            self.get_logger().error(f"Emergency clear error: {e}")

    def update_camera_feed(self, camera_frame=None):
        """Update display overlay with camera feed"""
        try:
            if self.display_overlay_service and camera_frame is not None:
                self.display_overlay_service.update_camera_feed(camera_frame, True)
        except Exception as e:
            self.get_logger().error(f"Camera feed update error: {e}")

    def show_display_error(self, error_message: str, error_type: str = "warning"):
        """Show error on display overlay"""
        try:
            if self.display_overlay_service:
                self.display_overlay_service.show_error(error_message, error_type)
        except Exception as e:
            self.get_logger().error(f"Display error show error: {e}")

    def clear_display_error(self):
        """Clear display overlay error"""
        try:
            if self.display_overlay_service:
                self.display_overlay_service.clear_error()
        except Exception as e:
            self.get_logger().error(f"Display error clear error: {e}")

    def mode_update_loop(self):
        """Main mode update loop"""
        try:
            # Process pending commands
            self._process_command_queue()

            # Handle current mode
            if self.current_mode in self.mode_handlers:
                self.mode_handlers[self.current_mode]()

            # Check mode timeouts
            self._check_mode_timeout()

            # Publish current mode
            self._publish_current_mode()

        except Exception as e:
            self.get_logger().error(f"Mode update loop error: {e}")

    def _process_command_queue(self):
        """Process queued voice commands"""
        try:
            while not self.command_queue.empty():
                try:
                    command_data = self.command_queue.get_nowait()
                    self._handle_voice_command(command_data)
                except queue.Empty:
                    break
                except Exception as e:
                    self.get_logger().error(f"Command processing error: {e}")

        except Exception as e:
            self.get_logger().error(f"Command queue processing error: {e}")

    def _handle_voice_command(self, command_data: Dict[str, Any]):
        """Handle voice command and change mode if necessary"""
        try:
            command_type = command_data.get('command', '')
            transcript = command_data.get('transcript', '').lower()

            # Map command types to modes
            command_mode_map = {
                'registration': RobotMode.REGISTRATION,
                'manual_mode': RobotMode.MANUAL,
                'follow_mode': RobotMode.FOLLOW,
                'question_mode': RobotMode.QUESTION,
                'medicine_time': RobotMode.MEDICINE,
                'health_check': RobotMode.HEALTH_CHECK
            }

            # Special commands
            if 'stop' in transcript or 'halt' in transcript:
                self._change_mode(RobotMode.IDLE)
                return

            if 'emergency' in transcript:
                self.emergency_stop()
                return

            # Mode changes
            if command_type in command_mode_map:
                new_mode = command_mode_map[command_type]
                self._change_mode(new_mode)

            # Pass command to current mode handler
            self._pass_command_to_current_mode(command_data)

        except Exception as e:
            self.get_logger().error(f"Voice command handling error: {e}")

    def _pass_command_to_current_mode(self, command_data: Dict[str, Any]):
        """Pass command to current mode for specific handling"""
        try:
            transcript = command_data.get('transcript', '')

            if self.current_mode == RobotMode.QUESTION and self.qa_module:
                self.qa_module.handle_voice_input(transcript)

            elif self.current_mode == RobotMode.HEALTH_CHECK and self.health_module:
                self.health_module.handle_voice_response(transcript)

            elif self.current_mode == RobotMode.REGISTRATION and self.registration_module:
                # Registration module handles its own speech processing
                pass

            elif self.current_mode == RobotMode.IDLE and self.idle_module:
                # Check for greetings in idle mode
                greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon']
                if any(greeting in transcript.lower() for greeting in greetings):
                    self.idle_module.respond_to_presence()

        except Exception as e:
            self.get_logger().error(f"Command passing error: {e}")

    def _change_mode(self, new_mode: RobotMode):
        """Change robot operating mode"""
        try:
            if new_mode == self.current_mode:
                return

            old_mode = self.current_mode

            # Stop previous mode
            self._stop_current_mode(old_mode)

            self.current_mode = new_mode
            self.mode_start_time = time.time()
            self.mode_changes += 1

            self.get_logger().info(f"Mode changed: {old_mode.value} → {new_mode.value}")

            # Update display overlay service
            if self.display_overlay_service:
                self.display_overlay_service.update_robot_state(new_mode.value, True)

            # Update display
            if self.hardware and self.hardware.display:
                if new_mode == RobotMode.IDLE:
                    self.hardware.display.show_idle_mode()
                elif new_mode == RobotMode.MANUAL:
                    self.hardware.display.show_manual_mode()
                elif new_mode == RobotMode.FOLLOW:
                    self.hardware.display.show_follow_mode()
                elif new_mode == RobotMode.QUESTION:
                    self.hardware.display.show_question_mode()

            # Announce mode change
            if self.hardware and self.hardware.audio and new_mode != RobotMode.IDLE:
                mode_names = {
                    RobotMode.MANUAL: "Manual control mode activated",
                    RobotMode.FOLLOW: "Follow mode activated",
                    RobotMode.REGISTRATION: "Patient registration started",
                    RobotMode.QUESTION: "Question mode activated",
                    RobotMode.MEDICINE: "Medicine time started",
                    RobotMode.HEALTH_CHECK: "Health check started"
                }

                if new_mode in mode_names:
                    self.hardware.audio.play_text(mode_names[new_mode])

            self._publish_status(f"mode_changed_to_{new_mode.value}")

        except Exception as e:
            self.get_logger().error(f"Mode change error: {e}")

    def _stop_current_mode(self, mode: RobotMode):
        """Stop the current mode's activities"""
        try:
            if mode == RobotMode.MANUAL and self.manual_control_module:
                self.manual_control_module.stop_manual_control()

            elif mode == RobotMode.FOLLOW and self.follow_mode_module:
                self.follow_mode_module.stop_follow_mode()

            elif mode == RobotMode.REGISTRATION and self.registration_module:
                # Registration will handle its own cleanup when mode changes
                pass

            elif mode == RobotMode.QUESTION and self.qa_module:
                self.qa_module.stop_question_mode()

            elif mode == RobotMode.MEDICINE and self.medicine_module:
                self.medicine_module.stop_medicine_time()

            elif mode == RobotMode.HEALTH_CHECK and self.health_module:
                self.health_module.stop_health_assessment()

            elif mode == RobotMode.IDLE and self.idle_module:
                self.idle_module.stop_idle_behavior()

        except Exception as e:
            self.get_logger().error(f"Mode stop error: {e}")

    def _check_mode_timeout(self):
        """Check if current mode has timed out"""
        try:
            if self.current_mode in self.mode_timeouts:
                timeout = self.mode_timeouts[self.current_mode]
                elapsed = time.time() - self.mode_start_time

                if elapsed > timeout:
                    self.get_logger().info(f"Mode {self.current_mode.value} timed out after {timeout}s")
                    self._change_mode(RobotMode.IDLE)

        except Exception as e:
            self.get_logger().error(f"Mode timeout check error: {e}")

    def check_activity_timeout(self):
        """Check for general activity timeout"""
        try:
            idle_timeout = self.config.get('modes', {}).get('idle', {}).get('default_duration', 300.0)
            elapsed = time.time() - self.last_activity_time

            if elapsed > idle_timeout and self.current_mode != RobotMode.IDLE:
                self.get_logger().info(f"Activity timeout after {elapsed:.1f}s - returning to idle")
                self._change_mode(RobotMode.IDLE)

        except Exception as e:
            self.get_logger().error(f"Activity timeout check error: {e}")

    # Mode handlers
    def _handle_idle_mode(self):
        """Handle idle mode"""
        try:
            if self.idle_module and not self.idle_module.is_idle_active():
                self.idle_module.start_idle_behavior()
        except Exception as e:
            self.get_logger().error(f"Idle mode handler error: {e}")

    def _handle_manual_mode(self):
        """Handle manual control mode"""
        try:
            if self.manual_control_module and not self.manual_control_module.is_manual_active():
                success = self.manual_control_module.start_manual_control()
                if not success:
                    self.get_logger().warning("Failed to start manual control - returning to idle")
                    self._change_mode(RobotMode.IDLE)
        except Exception as e:
            self.get_logger().error(f"Manual mode handler error: {e}")

    def _handle_follow_mode(self):
        """Handle follow mode"""
        try:
            if self.follow_mode_module and not self.follow_mode_module.is_follow_active():
                success = self.follow_mode_module.start_follow_mode()
                if not success:
                    self.get_logger().warning("Failed to start follow mode - returning to idle")
                    self._change_mode(RobotMode.IDLE)
        except Exception as e:
            self.get_logger().error(f"Follow mode handler error: {e}")

    def _handle_registration_mode(self):
        """Handle registration mode"""
        try:
            if self.registration_module and not self.registration_module.is_registration_active():
                success = self.registration_module.start_registration()
                if not success:
                    self.get_logger().warning("Failed to start registration - returning to idle")
                    self._change_mode(RobotMode.IDLE)
        except Exception as e:
            self.get_logger().error(f"Registration mode handler error: {e}")

    def _handle_question_mode(self):
        """Handle question mode"""
        try:
            if self.qa_module and not self.qa_module.is_qa_active():
                success = self.qa_module.start_question_mode()
                if not success:
                    self.get_logger().warning("Failed to start question mode - returning to idle")
                    self._change_mode(RobotMode.IDLE)
        except Exception as e:
            self.get_logger().error(f"Question mode handler error: {e}")

    def _handle_medicine_mode(self):
        """Handle medicine dispensing mode"""
        try:
            if self.medicine_module and not self.medicine_module.is_dispensing_active():
                success = self.medicine_module.start_medicine_time()
                if not success:
                    self.get_logger().warning("Failed to start medicine mode - returning to idle")
                    self._change_mode(RobotMode.IDLE)
        except Exception as e:
            self.get_logger().error(f"Medicine mode handler error: {e}")

    def _handle_health_check_mode(self):
        """Handle health check mode"""
        try:
            if self.health_module and not self.health_module.is_assessment_active():
                success = self.health_module.start_health_assessment()
                if not success:
                    self.get_logger().warning("Failed to start health check - returning to idle")
                    self._change_mode(RobotMode.IDLE)
        except Exception as e:
            self.get_logger().error(f"Health check mode handler error: {e}")

    def _handle_emergency_mode(self):
        """Handle emergency mode"""
        # Keep robot stopped and wait for manual intervention
        # All hardware should already be stopped by emergency_stop()
        pass

    def system_monitoring_loop(self):
        """Monitor system resources and performance"""
        try:
            # CPU and memory monitoring
            self.cpu_usage = psutil.cpu_percent(interval=None)
            self.memory_usage = psutil.virtual_memory().percent

            # Temperature monitoring (if available)
            try:
                # Try to read CPU temperature (Pi specific)
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    self.temperature = float(f.read().strip()) / 1000.0
            except:
                self.temperature = 0.0

            # CPU throttling if needed
            if self.cpu_usage > self.cpu_limit:
                self._throttle_system()

            # Log performance metrics
            if self.cpu_usage > 70.0 or self.memory_usage > 80.0:
                self.get_logger().warning(
                    f"High resource usage: CPU={self.cpu_usage:.1f}%, Memory={self.memory_usage:.1f}%"
                )

        except Exception as e:
            self.get_logger().error(f"System monitoring error: {e}")

    def _throttle_system(self):
        """Throttle system to reduce CPU usage"""
        try:
            self.get_logger().warning(f"CPU usage high ({self.cpu_usage:.1f}%), throttling system")

            # Reduce update rates temporarily
            if hasattr(self, 'mode_timer'):
                self.mode_timer.cancel()
                self.mode_timer = self.create_timer(0.2, self.mode_update_loop)  # Reduce to 5Hz

            # Reduce camera frame rate if streaming
            if self.hardware and self.hardware.camera:
                current_fps = self.hardware.camera.get_fps()
                if current_fps > 15:
                    self.hardware.camera.set_fps(15)

        except Exception as e:
            self.get_logger().error(f"System throttling error: {e}")

    def publish_diagnostics(self):
        """Publish system diagnostics"""
        try:
            diagnostics_array = DiagnosticArray()
            diagnostics_array.header.stamp = self.get_clock().now().to_msg()

            # System diagnostics
            sys_status = DiagnosticStatus()
            sys_status.name = "mars_robot_system"
            sys_status.message = f"Mode: {self.current_mode.value}"

            if self.cpu_usage < 80.0 and self.memory_usage < 90.0:
                sys_status.level = DiagnosticStatus.OK
            elif self.cpu_usage < 90.0 and self.memory_usage < 95.0:
                sys_status.level = DiagnosticStatus.WARN
            else:
                sys_status.level = DiagnosticStatus.ERROR

            sys_status.values = [
                KeyValue(key="cpu_usage", value=f"{self.cpu_usage:.1f}%"),
                KeyValue(key="memory_usage", value=f"{self.memory_usage:.1f}%"),
                KeyValue(key="temperature", value=f"{self.temperature:.1f}°C"),
                KeyValue(key="current_mode", value=self.current_mode.value),
                KeyValue(key="emergency_stopped", value=str(self.is_emergency_stopped)),
                KeyValue(key="hardware_ready", value=str(self.hardware_ready)),
                KeyValue(key="mode_changes", value=str(self.mode_changes)),
                KeyValue(key="commands_processed", value=str(self.commands_processed))
            ]

            diagnostics_array.status.append(sys_status)

            # Hardware diagnostics
            if self.hardware:
                hw_info = self.hardware.get_system_info()
                hw_status = hw_info.get('hardware_status', {})

                for component, connected in hw_status.items():
                    comp_status = DiagnosticStatus()
                    comp_status.name = f"mars_hardware_{component}"
                    comp_status.level = DiagnosticStatus.OK if connected else DiagnosticStatus.ERROR
                    comp_status.message = "Connected" if connected else "Not connected"
                    diagnostics_array.status.append(comp_status)

            self.diagnostics_pub.publish(diagnostics_array)

        except Exception as e:
            self.get_logger().error(f"Diagnostics publishing error: {e}")

    def _publish_current_mode(self):
        """Publish current robot mode"""
        try:
            mode_msg = String()
            mode_msg.data = self.current_mode.value
            self.mode_pub.publish(mode_msg)

        except Exception as e:
            self.get_logger().error(f"Mode publishing error: {e}")

    def _publish_status(self, status: str, details: Dict[str, Any] = None):
        """Publish robot status"""
        try:
            status_data = {
                'status': status,
                'timestamp': time.time(),
                'mode': self.current_mode.value,
                'emergency_stopped': self.is_emergency_stopped,
                'hardware_ready': self.hardware_ready
            }

            if details:
                status_data.update(details)

            status_msg = String()
            status_msg.data = json.dumps(status_data)
            self.status_pub.publish(status_msg)

        except Exception as e:
            self.get_logger().error(f"Status publishing error: {e}")

    def _publish_response(self, text: str, voice_mode: str = "default", priority: str = "normal"):
        """Publish robot response for TTS"""
        try:
            response_data = {
                'text': text,
                'voice_mode': voice_mode,
                'priority': priority,
                'timestamp': time.time(),
                'mode': self.current_mode.value
            }

            response_msg = String()
            response_msg.data = json.dumps(response_data)
            self.response_pub.publish(response_msg)

        except Exception as e:
            self.get_logger().error(f"Response publishing error: {e}")

    def get_robot_status(self) -> Dict[str, Any]:
        """Get current robot status"""
        return {
            'current_mode': self.current_mode.value,
            'emergency_stopped': self.is_emergency_stopped,
            'hardware_ready': self.hardware_ready,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'temperature': self.temperature,
            'mode_changes': self.mode_changes,
            'commands_processed': self.commands_processed,
            'emergency_stops': self.emergency_stops,
            'last_activity': self.last_activity_time
        }

    def shutdown(self):
        """Shutdown robot controller"""
        try:
            self.get_logger().info("Shutting down Mars Robot Controller...")

            # Move to safe positions
            if self.hardware:
                if self.hardware.arms:
                    self.hardware.arms.move_to_home_position()
                if self.hardware.camera_servos:
                    self.hardware.camera_servos.center_camera()
                if self.hardware.motors:
                    self.hardware.motors.stop()

            # Announce shutdown
            if self.hardware and self.hardware.audio:
                self.hardware.audio.play_text("Shutting down. Goodbye!")

            if self.hardware and self.hardware.display:
                self.hardware.display.show_text("Shutting Down...")
                time.sleep(1)
                self.hardware.display.clear_display()

            # Shutdown function modules
            if self.registration_module:
                self.registration_module.cleanup()
            if self.manual_control_module:
                self.manual_control_module.cleanup()
            if self.follow_mode_module:
                self.follow_mode_module.cleanup()
            if self.qa_module:
                self.qa_module.cleanup()
            if self.medicine_module:
                self.medicine_module.cleanup()
            if self.health_module:
                self.health_module.cleanup()
            if self.idle_module:
                self.idle_module.cleanup()

            # Shutdown display overlay service
            if self.display_overlay_service:
                self.display_overlay_service.shutdown()

            # Shutdown hardware
            if self.hardware:
                self.hardware.shutdown()

            self.get_logger().info("Robot controller shutdown completed")

        except Exception as e:
            self.get_logger().error(f"Shutdown error: {e}")

    def destroy_node(self):
        """Cleanup when node is destroyed"""
        self.shutdown()
        super().destroy_node()


def main(args=None):
    """Main entry point"""
    rclpy.init(args=args)

    try:
        controller = RobotController()

        def signal_handler(signum, frame):
            controller.get_logger().info("Received shutdown signal")
            controller.shutdown()
            rclpy.shutdown()

        import signal
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        rclpy.spin(controller)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Robot controller error: {e}")
    finally:
        if 'controller' in locals():
            controller.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()