#!/usr/bin/env python3
"""
Wake Word Bridge Node for Mars Robot
Bridges ZMQ wake word notifications to ROS2 topics
"""
import json
import time
from typing import Dict, Any

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from std_msgs.msg import Bool, String, Header
from mars_voice.msg import WakeWordEvent  # Custom message type

try:
    import zmq
except ImportError:
    print("ZMQ not available. Install with: pip install zmq")
    zmq = None


class WakeWordBridge(Node):
    """Bridge between ZMQ wake word detector and ROS2"""

    def __init__(self):
        super().__init__('wake_word_bridge')

        # QoS profile for reliable wake word delivery
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Publishers
        self.wake_word_pub = self.create_publisher(
            Bool, '/voice/wake_word_detected', qos_profile
        )

        self.wake_word_event_pub = self.create_publisher(
            String, '/voice/wake_word_event', qos_profile  # Using String instead of custom msg for now
        )

        # ZMQ subscriber
        self.zmq_context = None
        self.subscriber = None
        self.zmq_connected = False

        # Statistics
        self.detection_count = 0
        self.last_detection_time = None
        self.connection_attempts = 0
        self.max_connection_attempts = 10

        # Initialize ZMQ connection
        self.initialize_zmq()

        # Timer for periodic ZMQ polling
        self.zmq_timer = self.create_timer(0.01, self.poll_zmq_messages)  # 100Hz polling

        # Timer for connection monitoring
        self.monitor_timer = self.create_timer(5.0, self.monitor_connection)

        # Timer for publishing statistics
        self.stats_timer = self.create_timer(30.0, self.publish_statistics)

        self.get_logger().info("Wake Word Bridge node initialized")

    def initialize_zmq(self) -> bool:
        """Initialize ZMQ connection to wake word detector"""
        try:
            if zmq is None:
                self.get_logger().error("ZMQ not available")
                return False

            self.zmq_context = zmq.Context()
            self.subscriber = self.zmq_context.socket(zmq.SUB)

            # Configure socket
            self.subscriber.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages

            # Connect to wake word detector
            zmq_address = "tcp://localhost:5555"
            self.subscriber.connect(zmq_address)

            self.zmq_connected = True
            self.get_logger().info(f"ZMQ subscriber connected to {zmq_address}")
            return True

        except Exception as e:
            self.get_logger().error(f"Failed to initialize ZMQ: {e}")
            self.zmq_connected = False
            return False

    def poll_zmq_messages(self):
        """Poll for ZMQ messages from wake word detector"""
        if not self.zmq_connected or not self.subscriber:
            return

        try:
            # Non-blocking receive
            message = self.subscriber.recv_string(zmq.NOBLOCK)
            self.process_wake_word_message(message)

        except zmq.Again:
            # No message available - this is normal
            pass
        except zmq.ZMQError as e:
            self.get_logger().warning(f"ZMQ error: {e}")
            if e.errno == zmq.ETERM:
                # Context was terminated
                self.zmq_connected = False
        except Exception as e:
            self.get_logger().error(f"Error polling ZMQ messages: {e}")

    def process_wake_word_message(self, message: str):
        """Process received wake word message"""
        try:
            self.detection_count += 1
            current_time = self.get_clock().now()
            self.last_detection_time = current_time

            self.get_logger().info(f"Wake word message received: {message}")

            # Try to parse as JSON first
            wake_word_data = self.parse_wake_word_message(message)

            # Publish simple boolean notification
            bool_msg = Bool()
            bool_msg.data = True
            self.wake_word_pub.publish(bool_msg)

            # Publish detailed event information
            event_msg = String()
            event_msg.data = json.dumps(wake_word_data)
            self.wake_word_event_pub.publish(event_msg)

            self.get_logger().info(
                f"Wake word detection #{self.detection_count} published to ROS2 topics"
            )

        except Exception as e:
            self.get_logger().error(f"Error processing wake word message: {e}")

    def parse_wake_word_message(self, message: str) -> Dict[str, Any]:
        """Parse wake word message and extract information"""
        try:
            # Try parsing as JSON
            data = json.loads(message)
            if isinstance(data, dict) and 'event' in data:
                return {
                    'keyword': data.get('keyword', 'mars'),
                    'timestamp': data.get('timestamp', time.time()),
                    'confidence': data.get('confidence', 1.0),
                    'detection_count': self.detection_count
                }
        except (json.JSONDecodeError, TypeError):
            # Fallback to simple string parsing
            pass

        # Handle simple string messages
        if "WAKE_WORD_DETECTED" in message:
            return {
                'keyword': 'mars',
                'timestamp': time.time(),
                'confidence': 1.0,
                'detection_count': self.detection_count
            }

        # Default fallback
        return {
            'keyword': 'unknown',
            'timestamp': time.time(),
            'confidence': 0.5,
            'detection_count': self.detection_count,
            'raw_message': message
        }

    def monitor_connection(self):
        """Monitor ZMQ connection health"""
        if not self.zmq_connected:
            self.connection_attempts += 1
            self.get_logger().warning(
                f"ZMQ not connected, attempt {self.connection_attempts}"
            )

            if self.connection_attempts <= self.max_connection_attempts:
                self.get_logger().info("Attempting to reconnect to ZMQ...")
                if self.initialize_zmq():
                    self.connection_attempts = 0
            else:
                self.get_logger().error("Max connection attempts reached, giving up")

    def publish_statistics(self):
        """Publish periodic statistics"""
        stats = {
            'detection_count': self.detection_count,
            'zmq_connected': self.zmq_connected,
            'connection_attempts': self.connection_attempts,
            'uptime_seconds': time.time() - self.get_clock().now().nanoseconds / 1e9
        }

        if self.last_detection_time:
            time_since_last = (self.get_clock().now() - self.last_detection_time).nanoseconds / 1e9
            stats['seconds_since_last_detection'] = time_since_last

        self.get_logger().info(f"Wake word bridge stats: {stats}")

    def get_status(self) -> Dict[str, Any]:
        """Get current bridge status"""
        return {
            'node_name': self.get_name(),
            'zmq_connected': self.zmq_connected,
            'detection_count': self.detection_count,
            'connection_attempts': self.connection_attempts,
            'last_detection': self.last_detection_time.nanoseconds if self.last_detection_time else None
        }

    def shutdown_zmq(self):
        """Shutdown ZMQ connection"""
        try:
            if self.subscriber:
                self.subscriber.close()
            if self.zmq_context:
                self.zmq_context.term()
            self.get_logger().info("ZMQ connection closed")
        except Exception as e:
            self.get_logger().error(f"Error closing ZMQ connection: {e}")

    def destroy_node(self):
        """Cleanup when node is destroyed"""
        self.shutdown_zmq()
        super().destroy_node()


class MockWakeWordBridge(WakeWordBridge):
    """Mock wake word bridge for testing without ZMQ"""

    def __init__(self):
        # Initialize parent without ZMQ
        Node.__init__(self, 'wake_word_bridge_mock')

        # Publishers (same as parent)
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.wake_word_pub = self.create_publisher(
            Bool, '/voice/wake_word_detected', qos_profile
        )

        self.wake_word_event_pub = self.create_publisher(
            String, '/voice/wake_word_event', qos_profile
        )

        # Mock state
        self.detection_count = 0
        self.zmq_connected = True  # Always "connected" in mock mode

        # Timer for simulated wake word detection
        self.mock_timer = self.create_timer(10.0, self.simulate_wake_word)

        self.get_logger().info("Mock Wake Word Bridge initialized")

    def simulate_wake_word(self):
        """Simulate periodic wake word detection for testing"""
        mock_message = json.dumps({
            'event': 'WAKE_WORD_DETECTED',
            'keyword': 'mars',
            'timestamp': time.time()
        })

        self.get_logger().info("Simulating wake word detection")
        self.process_wake_word_message(mock_message)

    def initialize_zmq(self) -> bool:
        """Mock ZMQ initialization"""
        self.get_logger().info("Mock ZMQ initialization (no actual ZMQ)")
        return True

    def poll_zmq_messages(self):
        """Mock ZMQ polling (no actual polling)"""
        pass

    def monitor_connection(self):
        """Mock connection monitoring"""
        pass


def main(args=None):
    """Main entry point"""
    rclpy.init(args=args)

    try:
        # Check if ZMQ is available and choose appropriate bridge
        if zmq is None:
            node = MockWakeWordBridge()
        else:
            node = WakeWordBridge()

        rclpy.spin(node)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error in wake word bridge: {e}")
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()