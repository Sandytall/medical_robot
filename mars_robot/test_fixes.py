#!/usr/bin/env python3
"""
Test script to validate all critical fixes for Mars Robot Pi 5 deployment
This script tests the fixes without requiring actual hardware
"""
import os
import sys
import subprocess
import traceback
from pathlib import Path

def test_setup_py_files():
    """Test that setup.py files don't reference missing executables"""
    print("🔍 Testing setup.py files...")

    setup_files = [
        'ros2_workspace/src/mars_core/setup.py',
        'ros2_workspace/src/mars_hardware/setup.py',
        'ros2_workspace/src/mars_behaviors/setup.py'
    ]

    issues = []

    for setup_file in setup_files:
        if not os.path.exists(setup_file):
            issues.append(f"Missing setup file: {setup_file}")
            continue

        try:
            # Try to parse setup.py
            with open(setup_file, 'r') as f:
                content = f.read()

            # Check for non-existent executables
            if 'command_processor' in content:
                issues.append(f"{setup_file}: Still references command_processor")
            if 'behavior_executor' in content and 'behavior_tree_executor' not in content:
                issues.append(f"{setup_file}: Still references behavior_executor")

        except Exception as e:
            issues.append(f"Error reading {setup_file}: {e}")

    if issues:
        print(f"❌ Setup.py issues found: {issues}")
        return False
    else:
        print("✅ All setup.py files fixed")
        return True

def test_configuration_paths():
    """Test that configuration files have correct paths"""
    print("🔍 Testing configuration paths...")

    config_file = 'config/robot_config.yaml'
    issues = []

    if not os.path.exists(config_file):
        issues.append(f"Missing config file: {config_file}")
    else:
        try:
            with open(config_file, 'r') as f:
                content = f.read()

            # Check for wrong OpenCV path
            if '/opt/opencv/data/' in content:
                issues.append("Still using wrong OpenCV path: /opt/opencv/data/")

            # Verify correct path exists
            if '/usr/share/opencv4/haarcascades/' in content:
                print("✅ Correct OpenCV path found in config")
            else:
                issues.append("Correct OpenCV path not found")

        except Exception as e:
            issues.append(f"Error reading config: {e}")

    if issues:
        print(f"❌ Configuration issues: {issues}")
        return False
    else:
        print("✅ Configuration paths fixed")
        return True

def test_docker_configuration():
    """Test Docker configuration files"""
    print("🔍 Testing Docker configuration...")

    issues = []

    # Check Dockerfile.pi5
    dockerfile = 'Dockerfile.pi5'
    if not os.path.exists(dockerfile):
        issues.append("Missing Dockerfile.pi5")
    else:
        with open(dockerfile, 'r') as f:
            content = f.read()

        if 'FROM ros:humble-ros-base-jammy' not in content:
            issues.append("Dockerfile.pi5 missing correct base image")
        if 'lgpio' not in content:
            issues.append("Dockerfile.pi5 missing lgpio for Pi 5")

    # Check docker-compose.pi.yml
    compose_file = 'docker-compose.pi.yml'
    if not os.path.exists(compose_file):
        issues.append("Missing docker-compose.pi.yml")
    else:
        with open(compose_file, 'r') as f:
            content = f.read()

        if 'privileged: true' not in content:
            issues.append("docker-compose.pi.yml missing privileged mode")
        if 'Dockerfile.pi5' not in content:
            issues.append("docker-compose.pi.yml not using Dockerfile.pi5")

    # Check entrypoint script
    entrypoint = 'entrypoint.pi5.sh'
    if not os.path.exists(entrypoint):
        issues.append("Missing entrypoint.pi5.sh")

    if issues:
        print(f"❌ Docker configuration issues: {issues}")
        return False
    else:
        print("✅ Docker configuration complete")
        return True

def test_hardware_implementations():
    """Test that hardware implementations are no longer stubs"""
    print("🔍 Testing hardware implementations...")

    hardware_files = [
        'ros2_workspace/src/mars_hardware/mars_hardware/real/real_motors.py',
        'ros2_workspace/src/mars_hardware/mars_hardware/real/real_camera.py',
        'ros2_workspace/src/mars_hardware/mars_hardware/real/real_arms.py',
        'ros2_workspace/src/mars_hardware/mars_hardware/real/real_audio.py'
    ]

    issues = []

    for hw_file in hardware_files:
        if not os.path.exists(hw_file):
            issues.append(f"Missing hardware file: {hw_file}")
            continue

        try:
            with open(hw_file, 'r') as f:
                content = f.read()

            # Check if still contains placeholder implementations
            if 'print("Not implemented")' in content and 'return False' in content:
                issues.append(f"{hw_file}: Still has placeholder implementation")

            # Check for actual implementation (look for real hardware libraries)
            has_implementation = any([
                'lgpio' in content,
                'picamera2' in content,
                'pyttsx3' in content,
                'subprocess' in content,  # For system audio calls
                'threading' in content,   # For proper async operations
                'try:' in content and 'except:' in content  # Proper error handling
            ])

            if not has_implementation and 'real_' in hw_file:
                issues.append(f"{hw_file}: Missing actual hardware implementation")

        except Exception as e:
            issues.append(f"Error reading {hw_file}: {e}")

    if issues:
        print(f"❌ Hardware implementation issues: {issues}")
        return False
    else:
        print("✅ Hardware implementations completed")
        return True

def test_dashboard_implementation():
    """Test that FastAPI dashboard exists"""
    print("🔍 Testing FastAPI dashboard...")

    dashboard_file = 'host_services/dashboard.py'
    issues = []

    if not os.path.exists(dashboard_file):
        issues.append("Missing dashboard.py")
    else:
        with open(dashboard_file, 'r') as f:
            content = f.read()

        if 'FastAPI' not in content:
            issues.append("Dashboard missing FastAPI implementation")
        if '/api/health/alerts' not in content:
            issues.append("Dashboard missing health alerts endpoint")
        if 'sqlite3' not in content:
            issues.append("Dashboard missing database integration")

    if issues:
        print(f"❌ Dashboard issues: {issues}")
        return False
    else:
        print("✅ FastAPI dashboard implemented")
        return True

def test_syntax_errors():
    """Test for Python syntax errors"""
    print("🔍 Testing for syntax errors...")

    python_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    issues = []

    for py_file in python_files:
        try:
            # Try to compile the Python file
            with open(py_file, 'r') as f:
                source = f.read()
            compile(source, py_file, 'exec')

        except SyntaxError as e:
            issues.append(f"Syntax error in {py_file}: {e}")
        except Exception as e:
            issues.append(f"Error checking {py_file}: {e}")

    if issues:
        print(f"❌ Syntax errors found: {issues}")
        return False
    else:
        print(f"✅ All {len(python_files)} Python files syntax clean")
        return True

def test_docker_build_dependencies():
    """Test Docker build will not fail due to missing packages"""
    print("🔍 Testing Docker build dependencies...")

    dockerfile = 'Dockerfile.pi5'
    if not os.path.exists(dockerfile):
        print("❌ Dockerfile.pi5 missing")
        return False

    with open(dockerfile, 'r') as f:
        content = f.read()

    # Check for essential packages
    required_packages = [
        'python3-pip',
        'ros-humble-cv-bridge',
        'python3-opencv',
        'python3-numpy',
        'python3-fastapi',
        'python3-lgpio',
        'ffmpeg',
        'espeak'
    ]

    missing_packages = []
    for package in required_packages:
        if package not in content:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Dockerfile missing packages: {missing_packages}")
        return False
    else:
        print("✅ Docker build dependencies look complete")
        return True

def run_all_tests():
    """Run all validation tests"""
    print("🚀 Running Mars Robot Fix Validation Tests")
    print("=" * 50)

    # Change to the directory containing this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    tests = [
        ("Setup.py Files", test_setup_py_files),
        ("Configuration Paths", test_configuration_paths),
        ("Docker Configuration", test_docker_configuration),
        ("Hardware Implementations", test_hardware_implementations),
        ("FastAPI Dashboard", test_dashboard_implementation),
        ("Python Syntax", test_syntax_errors),
        ("Docker Dependencies", test_docker_build_dependencies)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("🏁 VALIDATION RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Mars Robot is ready for Pi 5 deployment!")
        return True
    else:
        print(f"\n⚠️  {failed} tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)