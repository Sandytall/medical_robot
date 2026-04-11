#!/usr/bin/env python3
"""
Mars Robot Setup Verification Script
Verifies that all components are properly configured for real hardware only
"""
import sys
import os
import subprocess
import importlib.util

def print_status(status, message):
    """Print status with color coding"""
    colors = {'✅': '\033[92m', '❌': '\033[91m', '⚠️': '\033[93m', 'RESET': '\033[0m'}
    print(f"{colors.get(status, '')}{status} {message}{colors['RESET']}")

def check_file_exists(path, description):
    """Check if a file exists"""
    if os.path.exists(path):
        print_status('✅', f"{description}: {path}")
        return True
    else:
        print_status('❌', f"{description} MISSING: {path}")
        return False

def check_directory_removed(path, description):
    """Check if a directory is removed"""
    if not os.path.exists(path):
        print_status('✅', f"{description} removed: {path}")
        return True
    else:
        print_status('❌', f"{description} still exists: {path}")
        return False

def check_hardware_manager():
    """Check hardware manager configuration"""
    try:
        # Add workspace to path
        workspace_path = '/home/sandeep/pi5/mars_robot/ros2_workspace/src'
        if workspace_path not in sys.path:
            sys.path.insert(0, workspace_path)

        from mars_hardware.mars_hardware.hardware_manager import HardwareManager

        # Test initialization
        config = {}
        hw_manager = HardwareManager(config)

        # Check system info
        info = hw_manager.get_system_info()

        print_status('✅', "Hardware Manager loads successfully")
        print(f"   - Platform: {info['platform']}")
        print(f"   - Architecture: {info['architecture']}")
        print(f"   - Using Real Hardware: {info['using_real_hardware']}")
        print(f"   - Display Overlay Type: {info.get('display_overlay_type', 'unknown')}")
        print(f"   - Force Mock: {info['force_mock']}")

        if not info['using_real_hardware']:
            print_status('❌', "Hardware Manager not configured for real hardware!")
            return False

        if info['force_mock']:
            print_status('❌', "Mock hardware is still enabled!")
            return False

        return True

    except ImportError as e:
        print_status('❌', f"Hardware Manager import failed: {e}")
        return False
    except Exception as e:
        import traceback
        print_status('❌', f"Hardware Manager test failed: {e}")
        print("   Full error details:")
        print(f"   {traceback.format_exc()}")
        return False

def check_terminator_display():
    """Check terminator display overlay"""
    try:
        workspace_path = '/home/sandeep/pi5/mars_robot/ros2_workspace/src'
        if workspace_path not in sys.path:
            sys.path.insert(0, workspace_path)

        from mars_hardware.mars_hardware.real.terminator_display_overlay import TerminatorDisplayOverlay

        # Test basic initialization (without actually starting display)
        config = {'display_overlay': {'resolution': [80, 24]}}
        overlay = TerminatorDisplayOverlay(config)

        # Check if it has the required methods
        required_methods = [
            'initialize', 'show_idle_eyes', 'show_camera_feed',
            'show_robot_mode', 'show_error', 'get_status', 'shutdown'
        ]

        for method in required_methods:
            if not hasattr(overlay, method):
                print_status('❌', f"TerminatorDisplayOverlay missing method: {method}")
                return False

        print_status('✅', "TerminatorDisplayOverlay loads and has all required methods")
        return True

    except ImportError as e:
        print_status('❌', f"TerminatorDisplayOverlay import failed: {e}")
        return False
    except Exception as e:
        print_status('❌', f"TerminatorDisplayOverlay test failed: {e}")
        return False

def check_pi5_hardware():
    """Check Pi 5 hardware availability"""
    checks = []

    # GPIO devices
    gpio_devices = ['/dev/gpiochip0', '/dev/gpiomem']
    gpio_found = any(os.path.exists(dev) for dev in gpio_devices)
    if gpio_found:
        print_status('✅', "GPIO devices available")
        checks.append(True)
    else:
        print_status('⚠️', "GPIO devices not found (may not be on Pi 5)")
        checks.append(False)

    # Check CPU info
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpu_info = f.read().lower()
            if 'bcm2712' in cpu_info:
                print_status('✅', "Pi 5 CPU detected (BCM2712)")
                checks.append(True)
            elif 'bcm2835' in cpu_info:
                print_status('⚠️', "Older Pi CPU detected (BCM2835)")
                checks.append(False)
            else:
                print_status('⚠️', "Unknown CPU type")
                checks.append(False)
    except:
        print_status('❌', "Could not read CPU info")
        checks.append(False)

    # Check device model
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().lower()
            if 'raspberry pi 5' in model:
                print_status('✅', "Pi 5 model confirmed")
                checks.append(True)
            else:
                print_status('⚠️', f"Different Pi model: {model.strip()}")
                checks.append(False)
    except:
        print_status('⚠️', "Could not read device model")
        checks.append(False)

    return any(checks)

def check_docker_config():
    """Check Docker configuration"""
    docker_file = '/home/sandeep/pi5/mars_robot/docker-compose.pi.yml'
    if not os.path.exists(docker_file):
        print_status('❌', f"Docker compose file missing: {docker_file}")
        return False

    # Read docker file content
    with open(docker_file, 'r') as f:
        content = f.read()

    # Check that USE_MOCK_HARDWARE is not present
    if 'USE_MOCK_HARDWARE' in content:
        print_status('❌', "Docker config still contains USE_MOCK_HARDWARE")
        return False

    # Check for TERM environment variable
    if 'TERM=xterm-256color' in content:
        print_status('✅', "Docker config has terminal color support")
    else:
        print_status('⚠️', "Docker config missing terminal color support")

    print_status('✅', "Docker configuration looks good")
    return True

def main():
    """Main verification function"""
    print("🔍 Mars Robot Setup Verification")
    print("=" * 50)

    all_checks = []

    print("\n📁 File Structure Checks:")
    files_to_check = [
        ('/home/sandeep/pi5/mars_robot/start_terminator_display.py', 'Terminator Display Starter'),
        ('/home/sandeep/pi5/mars_robot/TERMINATOR_DISPLAY_GUIDE.md', 'Usage Guide'),
        ('/home/sandeep/pi5/mars_robot/ros2_workspace/src/mars_hardware/mars_hardware/real/terminator_display_overlay.py', 'Terminator Display Overlay'),
        ('/home/sandeep/pi5/mars_robot/ros2_workspace/src/mars_hardware/mars_hardware/hardware_manager.py', 'Hardware Manager'),
        ('/home/sandeep/pi5/mars_robot/docker-compose.pi.yml', 'Docker Compose Config'),
    ]

    for file_path, description in files_to_check:
        all_checks.append(check_file_exists(file_path, description))

    print("\n🚫 Mock Hardware Removal Checks:")
    all_checks.append(check_directory_removed('/home/sandeep/pi5/mars_robot/ros2_workspace/src/mars_hardware/mars_hardware/mock', 'Mock Hardware Directory'))

    print("\n⚙️ Hardware Manager Checks:")
    all_checks.append(check_hardware_manager())

    print("\n🖥️ Terminator Display Checks:")
    all_checks.append(check_terminator_display())

    print("\n🔧 Pi 5 Hardware Checks:")
    all_checks.append(check_pi5_hardware())

    print("\n🐳 Docker Configuration Checks:")
    all_checks.append(check_docker_config())

    print("\n" + "=" * 50)

    if all(all_checks):
        print_status('✅', "ALL CHECKS PASSED! Mars Robot is ready for deployment.")
        print("\n🚀 Next Steps:")
        print("1. Start Docker: docker-compose -f docker-compose.pi.yml up -d")
        print("2. Open Terminator: terminator")
        print("3. Run Display: python3 start_terminator_display.py")
        return 0
    else:
        failed_count = len([x for x in all_checks if not x])
        print_status('❌', f"{failed_count} checks failed. Please review and fix issues above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)