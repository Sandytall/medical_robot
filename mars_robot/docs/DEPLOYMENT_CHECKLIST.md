# Mars Robot - Pi 5 Deployment Checklist

## 📋 Pre-Deployment Hardware Checklist

### **Essential Hardware**
- [ ] Raspberry Pi 5 (4GB+ RAM recommended)
- [ ] MicroSD Card (64GB+ Class 10)
- [ ] Official Pi 5 27W USB-C Power Supply
- [ ] Active cooling solution (fan or heatsink)
- [ ] IMX477 Camera Module with CSI cable
- [ ] 2x DC Motors with wheels
- [ ] L298N Motor Driver Board
- [ ] 8x Servo Motors (for robotic arms)
- [ ] 2x Servo Motors (for camera pan/tilt)
- [ ] USB Audio device (mic + speaker)
- [ ] USB Gamepad controller
- [ ] HDMI Display for robot face
- [ ] Jumper wires and breadboard

### **Physical Assembly**
- [ ] Camera module securely connected to CSI port
- [ ] All GPIO connections match pin diagram
- [ ] Motor driver properly powered (external 7-12V supply)
- [ ] Servos connected with proper power distribution
- [ ] Audio device plugged into USB port
- [ ] Gamepad connected and detected
- [ ] Emergency stop button wired to GPIO 12
- [ ] All connections secure and labeled

## 🔧 Software Setup Checklist

### **Operating System**
- [ ] Raspberry Pi OS 64-bit installed
- [ ] SSH enabled
- [ ] Camera interface enabled via raspi-config
- [ ] System updated (`sudo apt update && sudo apt upgrade`)
- [ ] GPU memory split set to 128MB
- [ ] Filesystem expanded

### **Dependencies**
- [ ] Docker and docker-compose installed
- [ ] Python3 and pip installed
- [ ] lgpio library installed for Pi 5
- [ ] picamera2 library installed
- [ ] ALSA audio tools installed
- [ ] espeak text-to-speech installed

### **Mars Robot Code**
- [ ] Repository cloned to `~/mars_robot`
- [ ] All files present and permissions correct
- [ ] Configuration files customized for your hardware
- [ ] Validation tests pass (`python3 test_fixes.py`)
- [ ] Docker image builds successfully

## ⚡ Quick Setup Commands

```bash
# 1. Clone repository
cd ~
git clone [your-repo-url] mars_robot
cd mars_robot

# 2. Run automated setup
chmod +x setup_pi5.sh
./setup_pi5.sh

# 3. Manual deployment (if automated setup skipped)
docker-compose -f docker-compose.pi.yml build
docker-compose -f docker-compose.pi.yml up -d

# 4. Verify deployment
curl http://localhost:8000/health
```

## 🧪 Testing Checklist

### **Hardware Tests**
- [ ] Camera preview: `rpicam-hello --timeout 3000`
- [ ] GPIO access: `python3 -c "import lgpio; print('OK')"`
- [ ] Audio output: `espeak "test"`
- [ ] Audio input: Record and playback test
- [ ] Motor movement: Left/right motor test
- [ ] Servo movement: Arm position test
- [ ] Gamepad input: Button and joystick test
- [ ] Emergency stop: Physical button test

### **Software Tests**
- [ ] Docker containers running: `docker ps`
- [ ] No syntax errors: Validation tests pass
- [ ] Dashboard accessible: http://[PI_IP]:8000
- [ ] Database creation: Check shared_data/database/
- [ ] Log files writing: Check shared_data/logs/
- [ ] ROS2 nodes communication: Check container logs

### **Robot Function Tests**
- [ ] Wake word detection: "Hey Mars" responds
- [ ] Patient registration: Face detection works
- [ ] Manual control: Gamepad controls motors
- [ ] Face following: Tracks movement
- [ ] Question answering: Voice recognition active
- [ ] Medicine dispensing: Arm movements execute
- [ ] Health assessment: Voice logging works
- [ ] Idle behavior: Random movements function

## 📊 Performance Checklist

### **System Monitoring**
- [ ] CPU usage < 80% during operation
- [ ] Memory usage < 90% 
- [ ] Temperature < 75°C under load
- [ ] No Docker container restarts
- [ ] All services respond to health checks
- [ ] Log files not growing excessively

### **Network & Connectivity**
- [ ] Pi accessible via SSH
- [ ] Dashboard accessible from network
- [ ] WiFi connection stable
- [ ] No network timeouts in logs

## 🛡️ Safety & Security Checklist

### **Safety Features**
- [ ] Emergency stop button functional
- [ ] Motor speed limits configured correctly
- [ ] Servo angle limits prevent collisions
- [ ] Temperature monitoring active
- [ ] CPU throttling prevents overheating
- [ ] Graceful shutdown on power loss

### **Security**
- [ ] Default passwords changed
- [ ] SSH keys configured (optional)
- [ ] Firewall rules set if needed
- [ ] Database files have proper permissions
- [ ] Voice data privacy measures in place

## 🔧 Configuration Checklist

### **Robot Configuration** (`config/robot_config.yaml`)
- [ ] GPIO pin assignments match hardware
- [ ] Motor speed limits appropriate
- [ ] Servo angle limits configured
- [ ] Camera resolution suitable for performance
- [ ] Audio device names correct
- [ ] Face detection parameters tuned

### **Voice Configuration** (`config/voice_config.yaml`)
- [ ] Wake word sensitivity adjusted
- [ ] Microphone gain optimal
- [ ] Speaker volume appropriate
- [ ] Voice recognition language set

### **Behavior Configuration** (`config/behavior_config.yaml`)
- [ ] Movement speeds safe for environment
- [ ] Timeout values appropriate
- [ ] Arm presets defined correctly
- [ ] Idle behavior patterns set

## 📈 Deployment Validation

### **Automated Tests**
```bash
# Run full test suite
cd ~/mars_robot
python3 test_fixes.py

# Hardware integration test
python3 testing/test_hardware.py

# System integration test  
python3 testing/test_system_integration.py
```

### **Manual Validation**
- [ ] All 7 robot functions tested
- [ ] Voice commands work reliably
- [ ] Hardware responds correctly
- [ ] Dashboard shows live data
- [ ] Error reporting functional
- [ ] Performance within limits

## 🚀 Go-Live Checklist

### **Final Steps**
- [ ] All tests passing
- [ ] Documentation accessible
- [ ] Support contacts available
- [ ] Backup procedures documented
- [ ] Monitoring systems active
- [ ] Emergency procedures posted

### **Deployment Sign-off**
- [ ] **Technical Lead**: All systems operational
- [ ] **Safety Officer**: Safety protocols verified
- [ ] **Operations Team**: Procedures documented
- [ ] **End User**: Training completed

## 📞 Post-Deployment

### **Immediate (First 24 Hours)**
- [ ] Continuous monitoring active
- [ ] No critical errors in logs
- [ ] Performance metrics stable
- [ ] User training completed
- [ ] Support hotline available

### **Week 1**
- [ ] Usage patterns analyzed
- [ ] Performance optimizations applied
- [ ] User feedback collected
- [ ] Any issues resolved

### **Month 1**
- [ ] System performance review
- [ ] Maintenance schedule established
- [ ] User satisfaction survey
- [ ] Future enhancement planning

---

## 🎯 Success Criteria

✅ **Mars Robot is successfully deployed when:**

1. All hardware components functional
2. All 7 robot functions operational
3. Performance metrics within specifications
4. Safety systems verified
5. User training completed
6. Documentation accessible
7. Support procedures active

---

**Document Version**: 1.0  
**Last Updated**: April 2026  
**Next Review**: Monthly

*This checklist ensures reliable and safe deployment of the Mars Hospital Robot on Raspberry Pi 5.*