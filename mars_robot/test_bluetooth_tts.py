#!/usr/bin/env python3
"""
Test script to verify Bluetooth TTS works in Docker container
"""
import time
import sys

def test_pyttsx3():
    """Test pyttsx3 TTS"""
    print("🔊 Testing pyttsx3 TTS...")
    try:
        import pyttsx3
        engine = pyttsx3.init()

        # Set voice properties
        engine.setProperty('rate', 150)  # Speed
        engine.setProperty('volume', 1.0)  # Volume

        # Test message
        test_message = "Hello! I am Mars Robot speaking through Bluetooth. TTS test successful!"
        print(f"Speaking: {test_message}")

        engine.say(test_message)
        engine.runAndWait()

        print("✅ pyttsx3 TTS test completed")
        return True

    except Exception as e:
        print(f"❌ pyttsx3 TTS failed: {e}")
        return False

def test_espeak():
    """Test espeak TTS as fallback"""
    print("🔊 Testing espeak TTS...")
    try:
        import subprocess

        test_message = "Mars Robot espeak test successful!"
        print(f"Speaking: {test_message}")

        # Use espeak with ALSA output
        subprocess.run(['espeak', '-s', '150', test_message], check=True)

        print("✅ espeak TTS test completed")
        return True

    except Exception as e:
        print(f"❌ espeak TTS failed: {e}")
        return False

def test_audio_devices():
    """Check available audio devices"""
    print("🔍 Checking audio devices...")
    try:
        import subprocess

        # Check PulseAudio sinks
        result = subprocess.run(['pactl', 'list', 'short', 'sinks'],
                              capture_output=True, text=True)
        print("Available audio sinks:")
        print(result.stdout)

        # Check default sink
        result = subprocess.run(['pactl', 'get-default-sink'],
                              capture_output=True, text=True)
        print(f"Default sink: {result.stdout.strip()}")

        return True

    except Exception as e:
        print(f"❌ Audio device check failed: {e}")
        return False

def main():
    """Run all TTS tests"""
    print("🚀 Mars Robot Bluetooth TTS Test")
    print("=" * 40)

    # Check audio devices first
    test_audio_devices()
    print()

    # Test different TTS engines
    pyttsx3_works = test_pyttsx3()
    time.sleep(2)

    espeak_works = test_espeak()
    time.sleep(1)

    print("\n" + "=" * 40)
    print("📋 Test Results:")
    print(f"  pyttsx3 TTS: {'✅ PASS' if pyttsx3_works else '❌ FAIL'}")
    print(f"  espeak TTS:  {'✅ PASS' if espeak_works else '❌ FAIL'}")

    if pyttsx3_works or espeak_works:
        print("\n🎉 SUCCESS! Bluetooth TTS is working!")
        return 0
    else:
        print("\n❌ FAILED! Bluetooth TTS not working")
        return 1

if __name__ == "__main__":
    sys.exit(main())