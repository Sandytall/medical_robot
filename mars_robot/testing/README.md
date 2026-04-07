# Mars Robot Testing Utilities

This directory contains comprehensive testing utilities for the Mars Robot system. These tools help validate hardware functionality, system integration, and individual component testing.

## Available Test Scripts

### 1. Gamepad Testing (`test_gamepad.py`)
Tests gamepad functionality for manual control mode.

**Usage:**
```bash
# Basic gamepad testing
python test_gamepad.py

# Test individual inputs
python test_gamepad.py --mode individual

# Get gamepad information
python test_gamepad.py --mode info

# Use alternative input backend
python test_gamepad.py --backend inputs
```

**Features:**
- Tests joystick movement (forward/backward, left/right turning)
- Tests button mappings and functionality
- Speed level control (slow/normal/fast)
- Emergency stop testing
- Real-time input monitoring

**Requirements:**
- `pygame` or `inputs` library
- Connected USB gamepad

### 2. Servo Angle Testing (`test_servo_angles.py`)
Interactive testing of individual servo angles and preset positions.

**Usage:**
```bash
# Interactive mode with mock hardware
python test_servo_angles.py --mock

# Interactive mode with real hardware (on Pi 5)
python test_servo_angles.py

# Run demonstration sequence
python test_servo_angles.py --mode demo --mock

# Run batch test from file
python test_servo_angles.py --mode batch --batch-file servo_test.txt
```

**Interactive Commands:**
- `left <joint> <angle>` - Set left arm joint angle
- `right <joint> <angle>` - Set right arm joint angle
- `pan <angle>` - Set camera pan angle
- `tilt <angle>` - Set camera tilt angle
- `home` - Move all servos to home position
- `preset <name>` - Move to preset position
- `status` - Show current positions
- `demo` - Run demonstration sequence

**Joint Numbers:**
- 0: Base rotation
- 1: Shoulder
- 2: Elbow
- 3: Wrist

### 3. Hardware Testing (`test_hardware.py`)
Comprehensive testing of all hardware components.

**Usage:**
```bash
# Test with mock hardware
python test_hardware.py --mock

# Test with real hardware (on Pi 5)
python test_hardware.py
```

**Tested Components:**
- System information and environment detection
- IMX477 camera (capture, streaming, resolution)
- L298N motor driver (movement, speed control)
- Robotic arms (8 servos, presets, limits)
- Camera servos (pan/tilt control)
- Audio system (TTS, recording, sound effects)
- Display system (emotions, text, modes)
- Emergency stop functionality

**Output:**
- Real-time test progress
- Detailed component status
- Pass/fail results for each test
- JSON results file (`hardware_test_results.json`)

### 4. System Integration Testing (`test_system_integration.py`)
Tests the complete system working together including ROS2 integration.

**Usage:**
```bash
# Basic system checks only
python test_system_integration.py --basic-only

# Full integration testing with direct ROS2 launch
python test_system_integration.py

# Full integration testing with Docker
python test_system_integration.py --docker
```

**Test Coverage:**
- Directory structure validation
- Configuration file presence
- Python dependencies
- ROS2 node communication
- Voice system integration
- Message flow between components

## Test Results

All test scripts generate detailed output and save results:

- **Console Output**: Real-time test progress and results
- **JSON Results**: Detailed test data saved to files
- **Error Logging**: Comprehensive error information for debugging

## Hardware Requirements

### Development Testing (Mock Hardware)
- Python 3.8+
- Required Python packages (see requirements below)
- USB gamepad (for gamepad testing)

### Production Testing (Real Hardware)
- Raspberry Pi 5 with Pi OS 64-bit
- IMX477 camera module
- L298N motor driver board with 2 motors
- 8 servo motors for robotic arms
- 2 servo motors for camera pan/tilt
- USB audio device (speaker + microphone)
- Display for emotions and information
- USB gamepad for manual control

## Python Dependencies

Install required packages:
```bash
# Core dependencies
pip install numpy scipy opencv-python pyyaml

# Audio dependencies
pip install pyaudio pyttsx3 gtts pygame

# Gamepad dependencies
pip install pygame inputs

# ROS2 dependencies (if using ROS2 integration)
# These are typically installed with ROS2
pip install rclpy
```

## Running Tests

### Quick Start (Mock Hardware)
```bash
cd mars_robot/testing

# Test gamepad
python test_gamepad.py

# Test servo angles
python test_servo_angles.py --mock

# Test all hardware
python test_hardware.py --mock

# Test system integration (basic checks)
python test_system_integration.py --basic-only
```

### Production Testing (Pi 5)
```bash
cd mars_robot/testing

# Test all hardware on real Pi 5
python test_hardware.py

# Test servo angles with real servos
python test_servo_angles.py

# Full system integration test
python test_system_integration.py
```

## Test Scenarios

### Pre-deployment Validation
1. Run hardware tests with mock hardware on development machine
2. Validate all components pass mock tests
3. Deploy to Pi 5
4. Run hardware tests with real hardware
5. Run system integration tests

### Troubleshooting Hardware Issues
1. Use individual component tests to isolate problems
2. Check test results JSON files for detailed error information
3. Use interactive servo testing for calibration
4. Test gamepad connectivity and mapping

### Performance Validation
1. Monitor CPU usage during tests (should stay under 80%)
2. Check response times in integration tests
3. Validate real-time performance requirements

## Common Issues and Solutions

### Gamepad Not Detected
- Ensure gamepad is connected and recognized by system
- Try different USB ports
- Use `--backend inputs` if pygame fails
- Check system permissions for input devices

### Servo Movement Issues
- Verify GPIO pin connections match configuration
- Check servo power supply
- Use `--mock` flag to test logic without hardware
- Verify angle limits in configuration

### Audio Problems
- Check USB audio device detection
- Verify ALSA/PulseAudio configuration
- Test with system audio tools first
- Check microphone permissions

### Camera Issues
- Verify camera module connection
- Check Pi camera configuration (`raspi-config`)
- Test with `rpicam-hello` command
- Ensure sufficient power supply

## Configuration Files

Test scripts use configuration files from `../config/`:
- `robot_config.yaml` - Hardware pin mappings and settings
- `voice_config.yaml` - Audio and speech configuration
- `behavior_config.yaml` - Behavior and movement settings

Modify these files to match your specific hardware setup.

## Contributing

When adding new tests:
1. Follow existing code structure and naming conventions
2. Include both mock and real hardware support
3. Add comprehensive error handling
4. Update this README with new test information
5. Include example usage in docstrings