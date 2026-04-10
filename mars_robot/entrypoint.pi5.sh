#!/bin/bash

# Mars Robot Pi 5 Entrypoint Script
set -e

echo "🚀 Starting Mars Robot on Raspberry Pi 5..."

# Source ROS2 environment
source /opt/ros/humble/setup.bash

# Source workspace if built
if [ -f /ros2_workspace/install/setup.bash ]; then
    source /ros2_workspace/install/setup.bash
    echo "✅ ROS2 workspace sourced"
fi

# Create database directory if it doesn't exist
mkdir -p /shared_data/database /shared_data/faces /shared_data/logs /shared_data/voice
echo "✅ Data directories created"

# Set up GPIO permissions (if not already set)
if [ -w /sys/class/gpio ]; then
    echo "✅ GPIO access available"
else
    echo "⚠️  GPIO access may be limited"
fi

# Check camera access
if [ -c /dev/video0 ]; then
    echo "✅ Camera device available"
else
    echo "⚠️  Camera device not found"
fi

# Check audio devices
if [ -d /dev/snd ]; then
    echo "✅ Audio devices available"
else
    echo "⚠️  Audio devices not found"
fi

# Start FastAPI dashboard in background
echo "🌐 Starting FastAPI dashboard..."
cd /host_services
python3 -m uvicorn dashboard:app --host 0.0.0.0 --port 8000 &
DASHBOARD_PID=$!

# Wait a moment for dashboard to start
sleep 3

# Start wake word detection service in background
echo "🎙️  Starting wake word service..."
python3 wake_word_detector.py &
WAKE_WORD_PID=$!

# Start main robot controller
echo "🤖 Starting Mars Robot Controller..."
cd /ros2_workspace

# Launch main robot controller
ros2 run mars_core robot_controller &
ROBOT_PID=$!

# Function to handle shutdown
cleanup() {
    echo "🛑 Shutting down Mars Robot..."
    kill $ROBOT_PID 2>/dev/null || true
    kill $WAKE_WORD_PID 2>/dev/null || true
    kill $DASHBOARD_PID 2>/dev/null || true

    # Wait for processes to terminate
    wait $ROBOT_PID 2>/dev/null || true
    wait $WAKE_WORD_PID 2>/dev/null || true
    wait $DASHBOARD_PID 2>/dev/null || true

    echo "👋 Mars Robot stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for robot controller (main process)
wait $ROBOT_PID