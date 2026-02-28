"""
generate_assets.py — One-time setup script.
Run this once to:
  1. Download the MediaPipe face_landmarker.task model
  2. Generate warning.wav and critical.wav audio files
"""

import os
import wave
import struct
import math
import urllib.request

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# MediaPipe face landmarker model URL (hosted by Google)
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)
MODEL_PATH = os.path.join(ASSETS_DIR, "face_landmarker.task")


def generate_tone(filename, frequency, duration_ms, volume=0.8, sample_rate=44100):
    """Generate a pure sine-wave tone and save as WAV.

    Args:
        filename: Output WAV file path.
        frequency: Tone frequency in Hz.
        duration_ms: Duration in milliseconds.
        volume: Volume (0.0 – 1.0).
        sample_rate: Audio sample rate.
    """
    n_samples = int(sample_rate * duration_ms / 1000)
    max_amp = 32767  # 16-bit signed max

    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)       # mono
        wav_file.setsampwidth(2)       # 16-bit
        wav_file.setframerate(sample_rate)

        for i in range(n_samples):
            t = i / sample_rate
            # Apply fade-in / fade-out envelope (20 ms)
            envelope = 1.0
            fade_samples = int(0.02 * sample_rate)
            if i < fade_samples:
                envelope = i / fade_samples
            elif i > n_samples - fade_samples:
                envelope = (n_samples - i) / fade_samples

            value = volume * envelope * math.sin(2 * math.pi * frequency * t)
            sample = int(value * max_amp)
            sample = max(-32768, min(32767, sample))
            wav_file.writeframes(struct.pack("<h", sample))


def generate_beeps(filename, frequency, beep_ms, silence_ms, count,
                   volume=0.8, sample_rate=44100):
    """Generate a series of beep tones separated by silence.

    Args:
        filename: Output WAV file path.
        frequency: Beep frequency in Hz.
        beep_ms: Duration of each beep in ms.
        silence_ms: Duration of silence between beeps in ms.
        count: Number of beeps.
        volume: Volume (0.0 – 1.0).
        sample_rate: Audio sample rate.
    """
    max_amp = 32767

    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for beep_idx in range(count):
            # Beep
            n_beep = int(sample_rate * beep_ms / 1000)
            fade_samples = int(0.01 * sample_rate)
            for i in range(n_beep):
                t = i / sample_rate
                envelope = 1.0
                if i < fade_samples:
                    envelope = i / fade_samples
                elif i > n_beep - fade_samples:
                    envelope = (n_beep - i) / fade_samples
                value = volume * envelope * math.sin(2 * math.pi * frequency * t)
                sample = int(value * max_amp)
                sample = max(-32768, min(32767, sample))
                wav_file.writeframes(struct.pack("<h", sample))

            # Silence (except after last beep)
            if beep_idx < count - 1:
                n_silence = int(sample_rate * silence_ms / 1000)
                for _ in range(n_silence):
                    wav_file.writeframes(struct.pack("<h", 0))


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # ── Step 1: Download MediaPipe face landmarker model ──
    if os.path.exists(MODEL_PATH):
        print(f"Face landmarker model already exists: {MODEL_PATH}")
    else:
        print("Downloading face_landmarker.task model (~5 MB)...")
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print(f"Model saved to: {MODEL_PATH}")
        except Exception as e:
            print(f"ERROR: Failed to download model: {e}")
            print(f"Please manually download from:\n  {MODEL_URL}")
            print(f"And place it at:\n  {MODEL_PATH}")
            return

    # ── Step 2: Generate audio assets ──
    warning_path = os.path.join(ASSETS_DIR, "warning.wav")
    critical_path = os.path.join(ASSETS_DIR, "critical.wav")

    print("Generating warning.wav (3 beeps at 800 Hz)...")
    generate_beeps(warning_path, frequency=800, beep_ms=300,
                   silence_ms=200, count=3, volume=0.7)

    print("Generating critical.wav (continuous tone at 1200 Hz)...")
    generate_tone(critical_path, frequency=1200, duration_ms=2000, volume=0.9)

    print(f"\nAll assets ready in: {ASSETS_DIR}")
    print("  - face_landmarker.task")
    print("  - warning.wav")
    print("  - critical.wav")
    print("\nYou can now run: python main.py")


if __name__ == "__main__":
    main()
