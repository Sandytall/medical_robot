# Mars Robot Terminator Display Guide

## Overview
The Mars Robot now uses a terminal-based display overlay that runs directly in terminator instead of creating a separate pygame window. This provides better integration and easier debugging.

## Quick Start

1. **Open Terminator**:
   ```bash
   terminator
   ```

2. **Start the Display Overlay**:
   ```bash
   cd /home/sandeep/pi5/mars_robot
   python3 start_terminator_display.py
   ```

3. **The display will show**:
   - Animated ASCII eyes with emotions
   - Robot status and mode
   - Ready/not ready indicator
   - Real-time status updates

## Features

### ASCII Eye Emotions
- **Normal**: Standard open eyes
- **Closed**: Horizontal lines (for blinking)
- **Sleepy**: Half-closed eyes
- **Looking Left/Right**: Eyes with shifted pupils
- **Squinting**: Narrow eyes
- **Love**: Heart-shaped eyes

### Display Modes
- **Idle Eyes**: Animated eyes with automatic blinking
- **Camera Feed**: ASCII representation of camera input
- **Status Display**: System status messages
- **Error Display**: Error alerts with red borders
- **Mode Display**: Current robot mode and ready status

### Status Indicators
- **Top Right**: Ready status (● READY / ○ NOT READY)
- **Top Left**: Current robot mode
- **Bottom**: Status line with time and robot info

## Integration with Docker

The terminator display works alongside the Docker container:

1. **Start Docker Container**:
   ```bash
   cd /home/sandeep/pi5/mars_robot
   docker-compose -f docker-compose.pi.yml up -d
   ```

2. **Open Terminator for Display**:
   ```bash
   terminator &
   ```

3. **In Terminator, run**:
   ```bash
   python3 start_terminator_display.py
   ```

## How It Works

### Real Hardware Only
- ✅ **NO MORE MOCK HARDWARE**: All mock components have been completely removed
- ✅ **Real Camera**: Uses Pi 5 camera module
- ✅ **Real Motors**: L298N motor driver control
- ✅ **Real Servos**: Direct GPIO servo control for arms and camera pan/tilt
- ✅ **Real Audio**: PulseAudio to Bluetooth speaker
- ✅ **Real Display**: Terminator terminal display

### Hardware Detection
The system automatically detects Raspberry Pi 5 by checking:
- GPIO devices (`/dev/gpiochip0` or `/dev/gpiomem`)
- CPU info for BCM2712 (Pi 5 specific)
- Device tree model information

### Terminal Display Technology
- **ANSI Escape Codes**: For cursor positioning and colors
- **Unicode Characters**: Box drawing characters for borders
- **ASCII Art**: Custom eye designs with animations
- **Color Support**: 256-color terminal support
- **Real-time Updates**: 10 FPS display refresh rate

## Troubleshooting

### Display Not Showing
1. Check terminator is running:
   ```bash
   ps aux | grep terminator
   ```

2. Verify terminal supports colors:
   ```bash
   echo $TERM
   # Should show: xterm-256color
   ```

3. Test terminal capabilities:
   ```bash
   python3 -c "import sys; print('TTY:', sys.stdout.isatty())"
   ```

### Hardware Not Detected
1. Check Pi 5 detection:
   ```bash
   # Check GPIO devices
   ls -la /dev/gpio*
   
   # Check CPU info
   grep -i bcm /proc/cpuinfo
   
   # Check device model
   cat /proc/device-tree/model
   ```

2. Verify permissions:
   ```bash
   # Add user to gpio group
   sudo usermod -a -G gpio $USER
   
   # Check current groups
   groups
   ```

### Bluetooth Audio Issues
1. Check PulseAudio:
   ```bash
   pactl list short sinks
   pactl get-default-sink
   ```

2. Test Bluetooth connection:
   ```bash
   bluetoothctl show
   bluetoothctl paired-devices
   ```

3. Run TTS test:
   ```bash
   python3 test_bluetooth_tts.py
   ```

## Commands Reference

### Start Full System
```bash
# 1. Start Docker container
docker-compose -f docker-compose.pi.yml up -d

# 2. Open terminator and start display
terminator -e "python3 /home/sandeep/pi5/mars_robot/start_terminator_display.py" &

# 3. Check dashboard (optional)
firefox http://localhost:8000
```

### Stop System
```bash
# Stop display (Ctrl+C in terminator)
# Stop Docker
docker-compose -f docker-compose.pi.yml down
```

### Monitor Logs
```bash
# Docker logs
docker-compose -f docker-compose.pi.yml logs -f

# Hardware status
docker exec -it mars_robot_mars_robot_1 python3 -c "
from mars_hardware.hardware_manager import HardwareManager
hw = HardwareManager()
print(hw.get_system_info())
"
```

## Display Commands During Operation

While the terminator display is running, the robot can:

1. **Change Eye Emotions**: Show different emotional states
2. **Display Camera Feed**: ASCII representation of camera input
3. **Show Status**: System status and error messages
4. **Mode Changes**: Visual indication of robot operation modes
5. **Ready Status**: Clear indication when robot is ready for operation

The display automatically updates based on robot state and user interactions.

## Benefits of Terminator Display

1. **Better Integration**: Runs in same terminal as other commands
2. **Easier Debugging**: Can see logs and display together
3. **No X11 Dependencies**: Works in any terminal environment
4. **Lower Resource Usage**: No GPU/graphical overhead
5. **Better SSH Support**: Works over SSH connections
6. **Immediate Visibility**: No separate windows to manage

This setup provides a robust, real hardware-only Mars Robot system with an integrated terminal display that's perfect for Pi 5 deployment!