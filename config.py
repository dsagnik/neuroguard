"""
config.py — Central configuration for the Drowsiness Monitoring System.
All constants, thresholds, file paths, and tuning parameters are stored here.
No magic numbers should appear in other modules.
"""

import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
# ─── Project Paths ────────────────────────────────────────────────────────────
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGS_DIR = os.path.join(os.getcwd(), "logs")  # keep logs outside exe

WARNING_SOUND_PATH = os.path.join(ASSETS_DIR, "warning.wav")
CRITICAL_SOUND_PATH = os.path.join(ASSETS_DIR, "critical.wav")
SESSION_LOG_PATH = os.path.join(LOGS_DIR, "session_log.csv")

# ─── Camera Settings ──────────────────────────────────────────────────────────
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
TARGET_FPS = 30

# ─── MediaPipe Face Mesh Settings ─────────────────────────────────────────────
MAX_NUM_FACES = 1
MIN_DETECTION_CONFIDENCE = 0.35   # lowered for better low-light detection
MIN_TRACKING_CONFIDENCE = 0.35    # lowered for better low-light tracking

# ─── Eye Aspect Ratio (EAR) ──────────────────────────────────────────────────
# MediaPipe Face Mesh landmark indices for left and right eyes
# These follow the standard 6-point eye model for EAR computation.
LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]

# Default EAR threshold used before calibration completes
DEFAULT_EAR_THRESHOLD = 0.20

# Calibration multiplier: threshold = baseline_ear * this value
# Higher value = less sensitive (fewer false positives)
CALIBRATION_EAR_MULTIPLIER = 0.70

# ─── Calibration ──────────────────────────────────────────────────────────────
CALIBRATION_DURATION_SEC = 60  # seconds to collect baseline data

# ─── Blink / Event Duration Thresholds (seconds) ─────────────────────────────
NORMAL_BLINK_MAX_DURATION = 0.7      # blinks shorter than this are normal
LONG_BLINK_MAX_DURATION = 2.5        # blinks between 0.7s and 2.5s are "long"
MICROSLEEP_MIN_DURATION = 2.5        # anything ≥ 2.5 s is a micro-sleep

# ─── Rapid Blink Cluster Detection ───────────────────────────────────────────
RAPID_BLINK_WINDOW_SEC = 15    # sliding window in seconds
RAPID_BLINK_COUNT_THRESHOLD = 7  # blinks within window to trigger cluster event

# ─── Fatigue Score ────────────────────────────────────────────────────────────
FATIGUE_SCORE_MIN = 0
FATIGUE_SCORE_MAX = 100

# Score increments per event type (doubled for faster escalation)
SCORE_LONG_BLINK = 10
SCORE_MICROSLEEP = 40
SCORE_RAPID_BLINK_CLUSTER = 20
SCORE_HEAD_NOD = 20  # reserved for future use

# Score decay: points subtracted per second when no events are occurring
SCORE_DECAY_PER_SEC = 0.5

# Grace period after calibration before scoring begins (seconds)
SCORE_GRACE_PERIOD_SEC = 5

# ─── Alarm Thresholds ──────────────────────────────────────────────────────────────
ALARM_WARNING_THRESHOLD = 25    # fatigue score ≥ 25 → warning beep
ALARM_CRITICAL_THRESHOLD = 60   # fatigue score ≥ 60 → critical alarm
ALARM_SILENCE_THRESHOLD = 40    # all beeping stops when score drops below 40

# Score dampening above warning threshold
SCORE_DAMPENING_FACTOR = 0.5    # 50% reduction above warning (faster than 80%)

# ─── Wide-Eye Recovery Boost ─────────────────────────────────────────────
# If current EAR is well above baseline (eyes wide open), decay rate is boosted
WIDE_EYE_EAR_MULTIPLIER = 1.15  # EAR > baseline * this = "wide open"
WIDE_EYE_DECAY_BOOST = 4.0      # decay multiplied by this when eyes are wide open

# ─── GUI Layout ───────────────────────────────────────────────────────────────
WINDOW_TITLE = "NeuroGuard – AI Fatigue Monitor"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 750
LEFT_PANEL_RATIO = 0.75   # camera feed panel width ratio (larger)
RIGHT_PANEL_RATIO = 0.25  # stats panel width ratio

# Timer interval for the main processing loop (ms)
GUI_TIMER_INTERVAL_MS = 33  # ~30 FPS

# ─── Status Labels ────────────────────────────────────────────────────────────
STATUS_CALIBRATING = "CALIBRATING"
STATUS_NORMAL = "NORMAL"
STATUS_WARNING_1 = "WARNING"
STATUS_WARNING_2 = "ALERT"
STATUS_CRITICAL = "CRITICAL"
STATUS_NO_FACE = "NO FACE DETECTED"

# ─── Colors (RGB tuples for OpenCV drawing) ───────────────────────────────────
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (0, 255, 255)
COLOR_ORANGE = (0, 165, 255)
COLOR_RED = (0, 0, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_CYAN = (255, 255, 0)
