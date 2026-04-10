# Mars Hospital Robot - Raspberry Pi 5 Setup Guide

Complete deployment guide for setting up the Mars hospital robot system on Raspberry Pi 5.

## 📋 Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Pi OS Setup](#pi-os-setup)
3. [Hardware Connections](#hardware-connections)
4. [Software Installation](#software-installation)
5. [System Deployment](#system-deployment)
6. [Configuration & Testing](#configuration--testing)
7. [Troubleshooting](#troubleshooting)
8. [Monitoring & Maintenance](#monitoring--maintenance)

---

## 🔧 Hardware Requirements

### **Core Components**
- **Raspberry Pi 5** (8GB recommended)
- **MicroSD Card** (64GB Class 10 or higher)
- **Power Supply** (27W USB-C official Pi 5 power supply)
- **Cooling** (Active cooler recommended for continuous operation)

### **Robot Hardware**
- **IMX477 Camera Module** (12.3MP with CSI ribbon cable)
- **L298N Motor Driver Board** (for 2 DC motors)
- **DC Motors** (2x with wheels for mobility)
- **Servo Motors** (8x for robotic arms + 2x for camera pan/tilt)
- **USB Audio Device** (Speaker + Microphone combined or separate)
- **Display** (HDMI display for robot face/emotions)
- **USB Gamepad** (for manual control mode)

### **Wiring & Accessories**
- **Jumper Wires** (Male-Female for GPIO connections)
- **Breadboard or PCB** (for clean connections)
- **USB Hub** (if more USB ports needed)
- **Ethernet Cable** (for initial setup)

---

## 🖥️ Pi OS Setup

### **1. Flash Pi OS**

```bash
# Download Raspberry Pi Imager
# https://www.raspberrypi.org/software/

# Flash Raspberry Pi OS (64-bit) to SD card
# Recommended: "Raspberry Pi OS (64-bit) with desktop"

# Enable SSH and WiFi during flashing:
# - Set username: pi
# - Set password: [your-secure-password]
# - Configure WiFi network
# - Enable SSH
```

### **2. Initial Boot & SSH Access**

```bash
# Find Pi IP address
nmap -sn 192.168.1.0/24

# SSH into Pi
ssh pi@[PI_IP_ADDRESS]

# Update system
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### **3. Enable Required Interfaces**

```bash
# Enable camera and GPIO
sudo raspi-config

# Navigate to:
# 3 Interface Options
#   → I1 Camera → Enable
#   → I2 SSH → Enable (should already be enabled)
#   → I4 SPI → Enable
#   → I5 I2C → Enable
# 5 Advanced Options
#   → A1 Expand Filesystem

# Finish and reboot
sudo reboot
```

### **4. Test Camera**

```bash
# Test IMX477 camera
rpicam-hello --timeout 5000

# Should display camera preview for 5 seconds
# If successful: ✅ Camera working
# If failed: Check camera cable and connections
```

---

## 🔌 Hardware Connections

### **GPIO Pin Assignments**

```
Raspberry Pi 5 GPIO Pinout:
┌─────────────────────────────────┐
│  3V3  5V   │ │  5V  GND      │
│  GPIO2 5V   │ │  GND GPIO14   │
│  GPIO3 GND  │ │  GPIO15 GPIO18│ ← Left Motor Enable (PWM)
│  GPIO4 GPIO14│ │ GND GPIO23    │ ← Left Motor IN2
│  GND   GPIO15│ │ GPIO24 GPIO10 │
│  GPIO17 GPIO18│ │ GND GPIO9    │
│  GPIO27 GND  │ │ GPIO25 GPIO11 │
│  GPIO22 GPIO23│ │ GPIO8 GND    │
│  3V3   GPIO24│ │ GND GPIO7     │
│  GPIO10 GND  │ │ GPIO1 GPIO12  │
│  GPIO9 GPIO25│ │ GPIO7 GND     │ 
│  GPIO11 GPIO8│ │ GPIO16 GPIO20 │
│  GND   GPIO7  │ │ GPIO26 GPIO21 │ ← Right Motor Enable (PWM)
└─────────────────────────────────┘
```

### **Motor Driver (L298N) Connections**

```bash
L298N → Raspberry Pi 5
─────────────────────
ENA   → GPIO 18 (Pin 12) # Left Motor Speed (PWM)
IN1   → GPIO 19 (Pin 35) # Left Motor Direction 1
IN2   → GPIO 20 (Pin 38) # Left Motor Direction 2

ENB   → GPIO 21 (Pin 40) # Right Motor Speed (PWM)
IN3   → GPIO 22 (Pin 15) # Right Motor Direction 1
IN4   → GPIO 23 (Pin 16) # Right Motor Direction 2

VCC   → 5V (Pin 2)       # Power for L298N
GND   → GND (Pin 6)      # Common Ground

# Motor Outputs
OUT1, OUT2 → Left DC Motor
OUT3, OUT4 → Right DC Motor

# External Motor Power (7-12V)
+12V → L298N VIN (for motors)
GND  → L298N GND (shared with Pi GND)
```

### **Servo Motor Connections**

```bash
Left Arm (4 servos):
─────────────────
Servo 0 (Base)     → GPIO 2  (Pin 3)
Servo 1 (Shoulder) → GPIO 3  (Pin 5)
Servo 2 (Elbow)    → GPIO 4  (Pin 7)
Servo 3 (Wrist)    → GPIO 17 (Pin 11)

Right Arm (4 servos):
─────────────────
Servo 0 (Base)     → GPIO 6  (Pin 31)
Servo 1 (Shoulder) → GPIO 7  (Pin 26)
Servo 2 (Elbow)    → GPIO 8  (Pin 24)
Servo 3 (Wrist)    → GPIO 9  (Pin 21)

Camera Servos:
─────────────
Pan Servo  → GPIO 10 (Pin 19)
Tilt Servo → GPIO 11 (Pin 23)

Power:
─────
All Servos VCC → 5V (External power supply recommended)
All Servos GND → GND (shared with Pi)
```

### **Audio Device Connection**

```bash
# USB Audio (Speaker + Microphone)
USB Audio Device → Any USB port on Pi 5

# Test audio devices
aplay -l    # List audio output devices
arecord -l  # List audio input devices
```

### **Camera Module**

```bash
# IMX477 Camera → CSI Port
Camera ribbon cable → CSI connector (next to HDMI ports)

# Ensure:
- Blue side of ribbon toward USB ports
- Camera firmly connected
- Cable not damaged
```

---

## 💾 Software Installation

### **1. Install Docker**

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose -y

# Reboot to apply group changes
sudo reboot
```

### **2. Clone Mars Robot Code**

```bash
# Clone repository (replace with your actual repo)
cd ~
git clone https://github.com/your-username/mars_robot.git
# OR copy files via SCP:
# scp -r mars_robot/ pi@[PI_IP]:~/

cd mars_robot
```

### **3. Install System Dependencies**

```bash
# Install system packages
sudo apt install -y \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    nano \
    htop \
    alsa-utils \
    espeak \
    ffmpeg

# Install Pi 5 GPIO library
sudo apt install -y python3-lgpio python3-gpiozero

# Install camera libraries
sudo apt install -y python3-picamera2

# Test GPIO access
python3 -c "import lgpio; print('GPIO library working')"
```

---

## 🚀 System Deployment

### **1. Build and Deploy**

```bash
cd ~/mars_robot

# Build Docker image for Pi 5
docker-compose -f docker-compose.pi.yml build

# This may take 20-30 minutes on Pi 5
# Monitor progress and CPU temperature
```

### **2. Start Mars Robot System**

```bash
# Start all services
docker-compose -f docker-compose.pi.yml up -d

# Check container status
docker-compose -f docker-compose.pi.yml ps

# View logs
docker-compose -f docker-compose.pi.yml logs -f
```

### **3. Access Services**

```bash
# FastAPI Dashboard
http://[PI_IP]:8000

# Check container logs
docker logs mars_robot_mars_robot_1

# Enter container for debugging
docker exec -it mars_robot_mars_robot_1 bash
```

---

## ⚙️ Configuration & Testing

### **1. Verify Hardware Connections**

```bash
# Test GPIO pins
python3 -c "
import lgpio
h = lgpio.gpiochip_open(0)
print('GPIO chip opened successfully')
lgpio.gpiochip_close(h)
"

# Test camera
rpicam-hello --timeout 2000

# Test audio output
espeak "Mars robot audio test"

# Test audio input
arecord -d 3 -f cd test.wav && aplay test.wav
```

### **2. Robot Function Tests**

```bash
# Enter Mars robot container
docker exec -it mars_robot_mars_robot_1 bash

# Test individual components
cd /ros2_workspace
source install/setup.bash

# Test robot controller
ros2 run mars_core robot_controller
```

### **3. Gamepad Setup**

```bash
# Connect USB gamepad and test
ls /dev/input/  # Should show js0 or similar

# Test gamepad input
cd ~/mars_robot/testing
python3 test_gamepad.py

# Follow prompts to test all buttons and joysticks
```

### **4. Voice Command Testing**

```bash
# Test wake word detection
# Say "Hey Mars" near microphone
# Check logs for recognition

# Test voice commands:
# "Hey Mars register me"
# "Hey Mars manual mode" 
# "Hey Mars follow me"
# "Hey Mars I have a question"
# "Hey Mars it's medicine time"
# "Hey Mars I don't feel good"
```

---

## 🔧 Troubleshooting

### **Common Issues & Solutions**

#### **Docker Build Fails**

```bash
# Check available space
df -h

# Clean Docker cache
docker system prune -a

# Increase swap (if low memory)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

#### **GPIO Permission Issues**

```bash
# Add user to gpio group
sudo usermod -aG gpio $USER

# Set GPIO permissions
sudo chmod 666 /dev/gpiochip0
sudo chmod 666 /dev/gpiomem

# Restart container
docker-compose -f docker-compose.pi.yml restart
```

#### **Camera Not Working**

```bash
# Check camera detection
rpicam-hello --list-cameras

# Enable legacy camera support if needed
sudo raspi-config
# Advanced Options → GL Driver → Legacy

# Check camera cable connection
# Blue side toward USB ports
```

#### **Audio Issues**

```bash
# List audio devices
aplay -l
arecord -l

# Set default audio device
sudo nano /etc/asound.conf
# Add:
# defaults.pcm.card 1
# defaults.ctl.card 1

# Restart ALSA
sudo systemctl restart alsa-state
```

#### **Motor Control Issues**

```bash
# Check GPIO pin connections
# Verify L298N power supply
# Test with simple GPIO script:

python3 << EOF
import lgpio
import time

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, 18, 0)  # Motor enable pin
lgpio.gpio_write(h, 18, 1)  # Enable motor
time.sleep(1)
lgpio.gpio_write(h, 18, 0)  # Disable motor
lgpio.gpiochip_close(h)
print("Motor test completed")
EOF
```

#### **High CPU Usage**

```bash
# Monitor system resources
htop

# Check container resource usage
docker stats

# Reduce camera FPS if needed
# Edit config/robot_config.yaml:
# fps: 15  # Reduce from 30

# Restart services
docker-compose -f docker-compose.pi.yml restart
```

### **Emergency Recovery**

```bash
# Stop all services
docker-compose -f docker-compose.pi.yml down

# Reset to safe state
sudo systemctl stop docker
sudo systemctl start docker

# Hardware emergency stop
# Disconnect power to motors/servos
# Use physical emergency stop button (GPIO 12)
```

---

## 📊 Monitoring & Maintenance

### **1. System Monitoring**

```bash
# Real-time system stats
htop

# CPU temperature
vcgencmd measure_temp

# Docker container status
docker stats

# Service logs
docker-compose -f docker-compose.pi.yml logs -f --tail=50
```

### **2. Performance Optimization**

```bash
# Set CPU governor for performance
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Monitor CPU usage (should stay < 80%)
# Access dashboard: http://[PI_IP]:8000
# Check robot status panel

# Optimize GPU memory split
sudo raspi-config
# Advanced Options → Memory Split → 128
```

### **3. Regular Maintenance**

```bash
# Daily checks
curl -f http://localhost:8000/health || echo "Service down"

# Weekly maintenance
docker-compose -f docker-compose.pi.yml down
docker system prune -f
docker-compose -f docker-compose.pi.yml up -d

# Update system monthly
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### **4. Backup & Recovery**

```bash
# Backup database
cp shared_data/database/patients.db ~/backup/patients_$(date +%Y%m%d).db

# Backup configuration
cp -r config/ ~/backup/config_$(date +%Y%m%d)/

# System image backup (on development machine)
# Create full SD card image for disaster recovery
dd if=/dev/sdX of=mars_robot_backup.img bs=1M status=progress
```

---

## 🎯 Final Checklist

### **Pre-Deployment Verification**

- [ ] **Hardware Connected**: All GPIO pins connected correctly
- [ ] **Power Supply**: Adequate power for Pi 5 + peripherals
- [ ] **Camera Working**: `rpicam-hello` shows preview
- [ ] **Audio Working**: Speaker output and microphone input tested
- [ ] **GPIO Access**: `lgpio` library working
- [ ] **Docker Running**: Containers start without errors
- [ ] **Network Access**: Dashboard accessible on port 8000
- [ ] **Robot Response**: "Hey Mars" triggers response

### **Robot Functions Verified**

- [ ] **Patient Registration**: Face detection + photo capture
- [ ] **Manual Control**: Gamepad controls motors
- [ ] **Face Following**: Follows registered faces
- [ ] **Question Answering**: Responds to voice questions
- [ ] **Medicine Dispensing**: Arm movements work
- [ ] **Health Assessment**: Voice logging to dashboard
- [ ] **Idle Behavior**: Random movements and greetings

### **Safety & Emergency**

- [ ] **Emergency Stop**: Hardware button stops all movement
- [ ] **Resource Monitoring**: CPU usage < 80%
- [ ] **Error Reporting**: Issues logged to dashboard
- [ ] **Safe Shutdown**: Clean shutdown procedures work

---

## 📞 Support & Resources

### **Documentation**
- [Mars Robot User Manual](USER_MANUAL.md)
- [API Documentation](API_REFERENCE.md)
- [Hardware Troubleshooting](HARDWARE_TROUBLESHOOTING.md)

### **Logs & Debugging**
```bash
# Main robot logs
docker logs mars_robot_mars_robot_1

# System logs
sudo journalctl -f

# Hardware specific logs
dmesg | grep -i gpio
dmesg | grep -i camera
dmesg | grep -i audio
```

### **Contact Information**
- **Technical Support**: [your-support-email]
- **Hardware Issues**: [hardware-support-email]
- **Emergency Contact**: [emergency-contact]

---

**🤖 Mars Robot is now ready for hospital deployment on Raspberry Pi 5! 🏥**

*Last updated: April 2026*