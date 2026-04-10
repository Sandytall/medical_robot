# Mars Robot - Quick Reference Card

## 🚀 Quick Start Commands

```bash
# Start Mars Robot
cd ~/mars_robot
docker-compose -f docker-compose.pi.yml up -d

# Stop Mars Robot  
docker-compose -f docker-compose.pi.yml down

# View Logs
docker-compose -f docker-compose.pi.yml logs -f

# Access Dashboard
# http://[PI_IP]:8000

# Emergency Stop
docker-compose -f docker-compose.pi.yml down
```

## 🔧 Hardware Test Commands

```bash
# Test Camera
rpicam-hello --timeout 3000

# Test Audio Output
espeak "Mars robot test"

# Test Audio Input
arecord -d 3 -f cd test.wav && aplay test.wav

# Test GPIO
python3 -c "import lgpio; print('GPIO OK')"

# Check Temperature
vcgencmd measure_temp
```

## 🎮 Voice Commands

| Command | Function |
|---------|----------|
| "Hey Mars register me" | Patient Registration |
| "Hey Mars manual mode" | Gamepad Control |
| "Hey Mars follow me" | Face Following |
| "Hey Mars I have a question" | Q&A Mode |
| "Hey Mars it's medicine time" | Medicine Dispensing |
| "Hey Mars I don't feel good" | Health Assessment |

## 📊 Monitoring

```bash
# System Resources
htop

# Container Status
docker stats

# Service Health
curl http://localhost:8000/health

# Temperature Check
vcgencmd measure_temp
```

## 🆘 Emergency Procedures

```bash
# Immediate Stop
docker-compose -f docker-compose.pi.yml down

# Hardware Emergency
# Press physical emergency button (GPIO 12)
# Or disconnect motor power

# System Recovery
sudo reboot
```

## 📍 Important Paths

| Path | Description |
|------|-------------|
| `~/mars_robot/` | Main code directory |
| `shared_data/database/` | Patient database |
| `shared_data/logs/` | System logs |
| `config/robot_config.yaml` | Hardware configuration |

## 🔌 GPIO Pin Reference

| Pin | Function |
|-----|----------|
| GPIO 18 | Left Motor PWM |
| GPIO 19-20 | Left Motor Direction |
| GPIO 21 | Right Motor PWM |
| GPIO 22-23 | Right Motor Direction |
| GPIO 2-4,17 | Left Arm Servos |
| GPIO 6-9 | Right Arm Servos |
| GPIO 10-11 | Camera Servos |
| GPIO 12 | Emergency Stop |

## 📞 Quick Diagnostics

```bash
# All-in-one health check
cd ~/mars_robot && python3 test_fixes.py

# Network connectivity
ping google.com

# Disk space
df -h

# Memory usage
free -h
```