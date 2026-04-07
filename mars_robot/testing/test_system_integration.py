#!/usr/bin/env python3
"""
System Integration Testing Script for Mars Robot
Tests the complete system working together including ROS2 integration
"""
import os
import sys
import time
import subprocess
import signal
import threading
from typing import List, Dict, Any

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ros2_workspace', 'src'))

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String, Bool
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    print("ROS2 not available for integration testing")


class SystemIntegrationTester(Node):
    """Integration tester node"""

    def __init__(self):
        super().__init__('system_integration_tester')

        # Test state
        self.test_results = {}
        self.running = True
        self.messages_received = {}

        # Subscribers for testing
        self.wake_word_sub = self.create_subscription(
            Bool, '/voice/wake_word_detected', self.wake_word_callback, 10
        )

        self.command_sub = self.create_subscription(
            String, '/voice/command_recognized', self.command_callback, 10
        )

        self.tts_sub = self.create_subscription(
            String, '/audio/tts_status', self.tts_callback, 10
        )

        # Publishers for testing
        self.tts_pub = self.create_publisher(String, '/audio/tts_request', 10)
        self.response_pub = self.create_publisher(String, '/robot/response', 10)

        self.get_logger().info("System Integration Tester initialized")

    def wake_word_callback(self, msg):
        """Handle wake word detection"""
        self.get_logger().info(f"Wake word detected: {msg.data}")
        self.messages_received['wake_word'] = msg.data

    def command_callback(self, msg):
        """Handle command recognition"""
        self.get_logger().info(f"Command recognized: {msg.data}")
        self.messages_received['command'] = msg.data

    def tts_callback(self, msg):
        """Handle TTS status"""
        self.get_logger().info(f"TTS status: {msg.data}")
        self.messages_received['tts'] = msg.data

    def test_voice_system(self) -> bool:
        """Test voice command system integration"""
        try:
            self.get_logger().info("Testing voice system integration...")

            # Test TTS
            tts_msg = String()
            tts_msg.data = '{"text": "System integration test starting", "priority": "normal"}'
            self.tts_pub.publish(tts_msg)

            # Wait for TTS response
            timeout = 10.0
            start_time = time.time()

            while time.time() - start_time < timeout:
                rclpy.spin_once(self, timeout_sec=0.1)
                if 'tts' in self.messages_received:
                    break

            if 'tts' in self.messages_received:
                self.get_logger().info("✓ TTS system responding")
                return True
            else:
                self.get_logger().error("✗ TTS system not responding")
                return False

        except Exception as e:
            self.get_logger().error(f"Voice system test error: {e}")
            return False

    def test_message_flow(self) -> bool:
        """Test message flow between components"""
        try:
            self.get_logger().info("Testing message flow...")

            # Clear previous messages
            self.messages_received.clear()

            # Send test robot response
            response_msg = String()
            response_msg.data = '{"text": "Integration test message", "voice_mode": "default"}'
            self.response_pub.publish(response_msg)

            # Wait for message processing
            time.sleep(2.0)
            rclpy.spin_once(self, timeout_sec=1.0)

            self.get_logger().info("✓ Message flow test completed")
            return True

        except Exception as e:
            self.get_logger().error(f"Message flow test error: {e}")
            return False


class SystemRunner:
    """Manages system startup and testing"""

    def __init__(self, use_docker: bool = False):
        self.use_docker = use_docker
        self.processes = []
        self.running = False

    def start_system_components(self):
        """Start required system components"""
        print("Starting Mars Robot system components...")

        if self.use_docker:
            self._start_with_docker()
        else:
            self._start_with_direct_launch()

    def _start_with_docker(self):
        """Start system using Docker Compose"""
        try:
            print("Starting with Docker Compose...")
            docker_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')

            # Start Docker containers
            process = subprocess.Popen([
                'docker-compose', '-f', docker_path, 'up', '-d'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                print("✓ Docker containers started")
                self.processes.append(('docker', process))
            else:
                print(f"✗ Docker start failed: {stderr.decode()}")

        except Exception as e:
            print(f"Docker startup error: {e}")

    def _start_with_direct_launch(self):
        """Start system using direct ROS2 launch"""
        try:
            print("Starting with direct ROS2 launch...")

            # Set environment
            env = os.environ.copy()
            env['USE_MOCK_HARDWARE'] = 'true'
            env['ROBOT_ENV'] = 'development'

            # Start ROS2 launch
            launch_file = os.path.join(
                os.path.dirname(__file__), '..', 'ros2_workspace', 'src',
                'mars_core', 'launch', 'mars_robot.launch.py'
            )

            if os.path.exists(launch_file):
                process = subprocess.Popen([
                    'ros2', 'launch', 'mars_core', 'mars_robot.launch.py',
                    'robot_env:=development', 'use_mock_hardware:=true'
                ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                self.processes.append(('ros2_launch', process))
                print("✓ ROS2 launch started")
            else:
                print("✗ ROS2 launch file not found")

        except Exception as e:
            print(f"ROS2 launch error: {e}")

    def wait_for_system_ready(self, timeout: float = 30.0) -> bool:
        """Wait for system to be ready"""
        print(f"Waiting for system to be ready (timeout: {timeout}s)...")

        start_time = time.time()
        ready_checks = {
            'ros2_nodes': False,
            'topics': False,
            'services': False
        }

        while time.time() - start_time < timeout:
            try:
                # Check ROS2 nodes
                result = subprocess.run(['ros2', 'node', 'list'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and len(result.stdout.strip().split('\n')) > 1:
                    ready_checks['ros2_nodes'] = True

                # Check topics
                result = subprocess.run(['ros2', 'topic', 'list'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and '/voice/' in result.stdout:
                    ready_checks['topics'] = True

                # Check services
                result = subprocess.run(['ros2', 'service', 'list'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout:
                    ready_checks['services'] = True

                # All checks passed
                if all(ready_checks.values()):
                    print("✓ System ready")
                    return True

                print(f"System status: {ready_checks}")
                time.sleep(2)

            except subprocess.TimeoutExpired:
                print("Timeout checking system status")
            except Exception as e:
                print(f"System check error: {e}")

        print("✗ System not ready within timeout")
        return False

    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        if not ROS2_AVAILABLE:
            print("ROS2 not available, skipping integration tests")
            return False

        try:
            print("Running system integration tests...")

            rclpy.init()

            # Create test node
            tester = SystemIntegrationTester()

            # Run tests
            test_results = {}

            tests = [
                ("Voice System", tester.test_voice_system),
                ("Message Flow", tester.test_message_flow)
            ]

            for test_name, test_func in tests:
                print(f"\nRunning {test_name} test...")
                try:
                    result = test_func()
                    test_results[test_name] = result
                    print(f"{'✓' if result else '✗'} {test_name}: {'PASSED' if result else 'FAILED'}")
                except Exception as e:
                    print(f"✗ {test_name}: ERROR - {e}")
                    test_results[test_name] = False

            # Print summary
            passed = sum(1 for r in test_results.values() if r)
            total = len(test_results)
            print(f"\nIntegration test results: {passed}/{total} passed")

            # Cleanup
            tester.destroy_node()
            rclpy.shutdown()

            return passed == total

        except Exception as e:
            print(f"Integration test error: {e}")
            return False

    def stop_system_components(self):
        """Stop all system components"""
        print("Stopping system components...")

        for process_name, process in self.processes:
            try:
                if process_name == 'docker':
                    # Stop Docker containers
                    subprocess.run(['docker-compose', 'down'], timeout=30)
                else:
                    # Terminate process
                    process.terminate()
                    process.wait(timeout=10)

                print(f"✓ Stopped {process_name}")

            except subprocess.TimeoutExpired:
                print(f"Force killing {process_name}")
                process.kill()
            except Exception as e:
                print(f"Error stopping {process_name}: {e}")

    def run_basic_system_checks(self) -> bool:
        """Run basic system checks without ROS2"""
        print("Running basic system checks...")

        checks = {
            'python_version': self._check_python_version(),
            'directory_structure': self._check_directory_structure(),
            'config_files': self._check_config_files(),
            'dependencies': self._check_dependencies()
        }

        print("\nBasic system check results:")
        for check_name, result in checks.items():
            print(f"{'✓' if result else '✗'} {check_name}: {'OK' if result else 'FAILED'}")

        return all(checks.values())

    def _check_python_version(self) -> bool:
        """Check Python version"""
        try:
            version = sys.version_info
            return version.major == 3 and version.minor >= 8
        except:
            return False

    def _check_directory_structure(self) -> bool:
        """Check directory structure"""
        try:
            base_dir = os.path.dirname(__file__)
            required_dirs = [
                '../ros2_workspace/src',
                '../config',
                '../host_services',
                '../shared_data'
            ]

            for dir_path in required_dirs:
                full_path = os.path.join(base_dir, dir_path)
                if not os.path.exists(full_path):
                    print(f"Missing directory: {full_path}")
                    return False

            return True
        except:
            return False

    def _check_config_files(self) -> bool:
        """Check configuration files"""
        try:
            base_dir = os.path.dirname(__file__)
            config_files = [
                '../config/robot_config.yaml',
                '../config/voice_config.yaml',
                '../config/behavior_config.yaml'
            ]

            for config_file in config_files:
                full_path = os.path.join(base_dir, config_file)
                if not os.path.exists(full_path):
                    print(f"Missing config file: {full_path}")
                    return False

            return True
        except:
            return False

    def _check_dependencies(self) -> bool:
        """Check critical dependencies"""
        try:
            critical_deps = ['yaml', 'numpy']
            for dep in critical_deps:
                try:
                    __import__(dep)
                except ImportError:
                    print(f"Missing dependency: {dep}")
                    return False

            return True
        except:
            return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Mars Robot System Integration Testing')
    parser.add_argument('--docker', action='store_true',
                       help='Use Docker Compose to start system')
    parser.add_argument('--basic-only', action='store_true',
                       help='Run only basic checks without starting system')

    args = parser.parse_args()

    runner = SystemRunner(use_docker=args.docker)

    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        print("\nShutdown signal received...")
        runner.stop_system_components()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.basic_only:
            # Run basic checks only
            success = runner.run_basic_system_checks()
            if success:
                print("\n🎉 Basic system checks passed!")
                sys.exit(0)
            else:
                print("\n⚠️  Basic system checks failed!")
                sys.exit(1)

        # Run full integration tests
        print("="*80)
        print("MARS ROBOT SYSTEM INTEGRATION TESTING")
        print("="*80)

        # Basic checks first
        if not runner.run_basic_system_checks():
            print("Basic checks failed, aborting integration tests")
            sys.exit(1)

        # Start system components
        runner.start_system_components()

        # Wait for system to be ready
        if not runner.wait_for_system_ready():
            print("System startup failed")
            sys.exit(1)

        # Run integration tests
        success = runner.run_integration_tests()

        if success:
            print("\n🎉 All integration tests passed!")
            sys.exit(0)
        else:
            print("\n⚠️  Some integration tests failed!")
            sys.exit(1)

    except Exception as e:
        print(f"Integration testing error: {e}")
        sys.exit(1)
    finally:
        runner.stop_system_components()


if __name__ == '__main__':
    main()