#!/bin/bash

# Mars Robot - Raspberry Pi 5 Automated Setup Script
# This script automates the setup process for Mars Robot on Pi 5

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/tmp/mars_robot_setup.log"
exec > >(tee -a ${LOG_FILE})
exec 2>&1

echo -e "${BLUE}"
echo "=================================================================="
echo "🤖 Mars Hospital Robot - Raspberry Pi 5 Setup Script"
echo "=================================================================="
echo -e "${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if running on Pi 5
check_pi5() {
    print_info "Checking if running on Raspberry Pi 5..."

    if ! command -v rpicam-hello &> /dev/null; then
        print_error "This doesn't appear to be a Raspberry Pi with camera support"
        exit 1
    fi

    # Check for Pi 5 specific features
    if [ -f /proc/device-tree/model ]; then
        model=$(cat /proc/device-tree/model)
        if [[ $model == *"Raspberry Pi 5"* ]]; then
            print_status "Detected Raspberry Pi 5"
        else
            print_warning "This script is optimized for Pi 5, but will continue anyway"
        fi
    fi
}

# Function to check system requirements
check_requirements() {
    print_info "Checking system requirements..."

    # Check available space
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ $available_space -lt 8000000 ]; then  # 8GB in KB
        print_error "Insufficient disk space. Need at least 8GB free."
        exit 1
    fi

    # Check memory
    total_mem=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [ $total_mem -lt 2000 ]; then  # 2GB
        print_warning "Less than 2GB RAM detected. Performance may be limited."
    fi

    print_status "System requirements check passed"
}

# Function to update system
update_system() {
    print_info "Updating system packages..."
    sudo apt update
    sudo apt upgrade -y
    print_status "System updated"
}

# Function to install Docker
install_docker() {
    print_info "Installing Docker..."

    if command -v docker &> /dev/null; then
        print_status "Docker already installed"
        return
    fi

    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER

    # Install docker-compose
    sudo apt install -y docker-compose

    rm get-docker.sh
    print_status "Docker installed"
}

# Function to install system dependencies
install_dependencies() {
    print_info "Installing system dependencies..."

    sudo apt install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget \
        nano \
        htop \
        alsa-utils \
        espeak \
        espeak-data \
        ffmpeg \
        python3-lgpio \
        python3-gpiozero \
        python3-picamera2 \
        python3-opencv \
        python3-numpy \
        python3-yaml \
        joystick \
        jstest-gtk

    print_status "System dependencies installed"
}

# Function to enable required interfaces
enable_interfaces() {
    print_info "Enabling required Pi interfaces..."

    # Enable camera, SPI, I2C via raspi-config non-interactive
    sudo raspi-config nonint do_camera 0
    sudo raspi-config nonint do_spi 0
    sudo raspi-config nonint do_i2c 0
    sudo raspi-config nonint do_ssh 0

    # Expand filesystem
    sudo raspi-config nonint do_expand_rootfs

    print_status "Interfaces enabled"
}

# Function to test hardware
test_hardware() {
    print_info "Testing hardware components..."

    # Test camera
    print_info "Testing camera..."
    if timeout 10 rpicam-hello --timeout 2000; then
        print_status "Camera test passed"
    else
        print_warning "Camera test failed - check connections"
    fi

    # Test GPIO
    print_info "Testing GPIO access..."
    if python3 -c "import lgpio; h=lgpio.gpiochip_open(0); lgpio.gpiochip_close(h); print('GPIO OK')"; then
        print_status "GPIO test passed"
    else
        print_error "GPIO test failed - check permissions"
    fi

    # Test audio
    print_info "Testing audio..."
    if command -v espeak &> /dev/null; then
        echo "Mars robot audio test" | espeak
        print_status "Audio test completed"
    else
        print_warning "Audio test skipped - espeak not available"
    fi
}

# Function to configure system settings
configure_system() {
    print_info "Configuring system settings..."

    # Set CPU governor to performance
    echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null

    # Increase GPU memory split for camera
    if ! grep -q "gpu_mem=128" /boot/config.txt; then
        echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    fi

    # Increase swap size for Docker builds
    sudo dphys-swapfile swapoff
    sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
    sudo dphys-swapfile setup
    sudo dphys-swapfile swapon

    print_status "System configured"
}

# Function to build and deploy Mars robot
deploy_mars_robot() {
    print_info "Building and deploying Mars Robot..."

    # Validate that we're in the right directory
    if [ ! -f "docker-compose.pi.yml" ] || [ ! -f "Dockerfile.pi5" ]; then
        print_error "Missing required files. Make sure you're in the mars_robot directory."
        exit 1
    fi

    # Run validation tests first
    print_info "Running pre-deployment validation..."
    if python3 test_fixes.py; then
        print_status "Validation tests passed"
    else
        print_error "Validation tests failed. Please fix issues before continuing."
        exit 1
    fi

    # Build Docker image
    print_info "Building Docker image (this may take 20-30 minutes)..."
    if docker-compose -f docker-compose.pi.yml build; then
        print_status "Docker image built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi

    # Start services
    print_info "Starting Mars Robot services..."
    if docker-compose -f docker-compose.pi.yml up -d; then
        print_status "Mars Robot services started"
    else
        print_error "Failed to start services"
        exit 1
    fi

    # Wait for services to be ready
    print_info "Waiting for services to initialize..."
    sleep 10

    # Check health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_status "Health check passed"
    else
        print_warning "Health check failed - services may still be starting"
    fi
}

# Function to show final status
show_status() {
    print_info "Checking final status..."

    # Get Pi IP address
    PI_IP=$(hostname -I | cut -d' ' -f1)

    echo -e "${GREEN}"
    echo "=================================================================="
    echo "🎉 Mars Robot Setup Complete!"
    echo "=================================================================="
    echo -e "${NC}"

    echo "📊 System Information:"
    echo "   • Pi IP Address: $PI_IP"
    echo "   • Dashboard URL: http://$PI_IP:8000"
    echo "   • CPU Temperature: $(vcgencmd measure_temp)"
    echo "   • Memory Usage: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"

    echo ""
    echo "🚀 Next Steps:"
    echo "   1. Open dashboard: http://$PI_IP:8000"
    echo "   2. Test voice commands: 'Hey Mars'"
    echo "   3. Check logs: docker-compose -f docker-compose.pi.yml logs -f"
    echo "   4. Read documentation: docs/PI5_SETUP_GUIDE.md"

    echo ""
    echo "🎮 Voice Commands to Try:"
    echo "   • 'Hey Mars register me'"
    echo "   • 'Hey Mars manual mode'"
    echo "   • 'Hey Mars I have a question'"

    echo ""
    echo "📞 Support:"
    echo "   • View logs: docker logs mars_robot_mars_robot_1"
    echo "   • Emergency stop: docker-compose -f docker-compose.pi.yml down"
    echo "   • Quick reference: docs/QUICK_REFERENCE.md"

    echo ""
    print_status "Setup log saved to: $LOG_FILE"
}

# Main setup function
main() {
    print_info "Starting Mars Robot Pi 5 setup..."
    print_info "This will take approximately 30-45 minutes"
    print_info "Setup log: $LOG_FILE"
    echo ""

    # Ask for confirmation
    read -p "Continue with Mars Robot setup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi

    # Run setup steps
    check_pi5
    check_requirements
    update_system
    install_docker
    install_dependencies
    enable_interfaces
    configure_system
    test_hardware

    print_warning "A reboot is recommended before final deployment."
    read -p "Reboot now and continue setup after reboot? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Rebooting... Please run this script again after reboot to complete deployment."
        sudo reboot
    else
        deploy_mars_robot
        show_status
    fi
}

# Check if this is a continuation after reboot
if [ "$1" = "--continue" ]; then
    print_info "Continuing Mars Robot deployment after reboot..."
    deploy_mars_robot
    show_status
else
    main
fi