"""
fatigue_engine.py — Core fatigue analysis engine.
Handles adaptive calibration, event classification, fatigue scoring, and alarm state.
Contains NO GUI logic — purely computational.
"""

import time
from dataclasses import dataclass, field
from typing import List
from collections import deque

import numpy as np

import config


@dataclass
class FatigueState:
    """Snapshot of the fatigue engine state for a single frame."""
    # Phase
    is_calibrating: bool = True
    calibration_progress: float = 0.0  # 0.0 – 1.0

    # EAR data
    current_ear: float = 0.0
    baseline_ear: float = 0.0
    ear_threshold: float = config.DEFAULT_EAR_THRESHOLD

    # Blink / event tracking
    blink_duration: float = 0.0
    blink_count_last_60s: int = 0
    consecutive_low_frames: int = 0
    microsleep_count: int = 0
    last_event: str = ""  # "normal_blink", "long_blink", "microsleep", "rapid_cluster", ""

    # Fatigue score
    fatigue_score: float = 0.0

    # Alarm
    alarm_level: str = config.STATUS_NORMAL  # NORMAL / WARNING / ALERT / CRITICAL

    # Face
    face_detected: bool = False


class FatigueEngine:
    """Rule-based fatigue analysis engine with adaptive calibration."""

    def __init__(self):
        # ── Calibration state ──
        self._calibrating = True
        self._calibration_start: float = 0.0
        self._calibration_ears: List[float] = []

        # ── Baseline values (set after calibration) ──
        self._baseline_ear: float = 0.0
        self._ear_threshold: float = config.DEFAULT_EAR_THRESHOLD

        # ── Blink tracking ──
        self._eyes_closed: bool = False
        self._close_start_time: float = 0.0
        self._consecutive_low_frames: int = 0

        # ── Blink history (timestamps of completed blinks within last 60 s) ──
        self._blink_timestamps: deque = deque()

        # ── Rapid blink cluster tracking ──
        self._rapid_blink_timestamps: deque = deque()
        self._rapid_cluster_cooldown: float = 0.0  # prevent repeated triggers

        # ── Event counters ──
        self._microsleep_count: int = 0
        self._total_blinks: int = 0

        # ── Fatigue score ──
        self._fatigue_score: float = 0.0
        self._last_decay_time: float = time.time()
        self._last_event: str = ""

        # ── Current blink duration (for display) ──
        self._current_blink_duration: float = 0.0

        # ── Grace period (no scoring right after calibration) ──
        self._monitoring_start_time: float = 0.0

        # ── Alarm hysteresis ──
        self._alarm_active: bool = False
        self._peak_reached: bool = False

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def update(self, ear: float, face_detected: bool) -> FatigueState:
        """Process one frame of EAR data and return the current fatigue state.

        Args:
            ear: Average Eye Aspect Ratio for this frame.
            face_detected: Whether a face was detected in this frame.

        Returns:
            FatigueState dataclass with all current metrics.
        """
        now = time.time()
        self._last_event = ""

        if not face_detected:
            return self._build_state(ear, face_detected)

        # ── Phase 1: Calibration ──
        if self._calibrating:
            return self._handle_calibration(ear, face_detected, now)

        # ── Phase 2: Monitoring ──
        in_grace = (now - self._monitoring_start_time) < config.SCORE_GRACE_PERIOD_SEC
        self._detect_events(ear, now, suppress_scoring=in_grace)
        self._apply_score_decay(now, ear)
        self._clamp_score()

        return self._build_state(ear, face_detected)

    def reset(self):
        """Reset the engine to its initial state."""
        self.__init__()

    # ──────────────────────────────────────────────────────────────────────────
    # Calibration
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_calibration(self, ear: float, face_detected: bool,
                            now: float) -> FatigueState:
        """Collect EAR samples during calibration and compute baseline."""
        if self._calibration_start == 0.0:
            self._calibration_start = now

        elapsed = now - self._calibration_start

        # Only collect EAR samples when eyes are likely open (rough filter)
        if ear > 0.15:
            self._calibration_ears.append(ear)

        # Check if calibration period is complete
        if elapsed >= config.CALIBRATION_DURATION_SEC:
            self._finish_calibration()

        state = self._build_state(ear, face_detected)
        state.is_calibrating = self._calibrating
        state.calibration_progress = min(
            elapsed / config.CALIBRATION_DURATION_SEC, 1.0
        )
        return state

    def _finish_calibration(self):
        """Compute baseline EAR and dynamic threshold from collected samples."""
        if len(self._calibration_ears) > 10:
            self._baseline_ear = float(np.median(self._calibration_ears))
        else:
            # Fallback if too few samples
            self._baseline_ear = 0.28

        self._ear_threshold = self._baseline_ear * config.CALIBRATION_EAR_MULTIPLIER
        self._calibrating = False
        self._last_decay_time = time.time()
        self._monitoring_start_time = time.time()

    # ──────────────────────────────────────────────────────────────────────────
    # Event Detection
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_events(self, ear: float, now: float, suppress_scoring: bool = False):
        """Detect blinks, long blinks, micro-sleeps, and rapid blink clusters.

        Args:
            suppress_scoring: If True, detect events but don't add to fatigue score
                              (used during grace period).
        """

        if ear < self._ear_threshold:
            # Eyes are below threshold
            self._consecutive_low_frames += 1

            if not self._eyes_closed:
                # Transition: open → closed
                self._eyes_closed = True
                self._close_start_time = now

            # Update current blink duration (live, while eyes are still closed)
            self._current_blink_duration = now - self._close_start_time

        else:
            # Eyes are above threshold
            if self._eyes_closed:
                # Transition: closed → open — classify the event
                duration = now - self._close_start_time
                self._current_blink_duration = duration
                self._classify_blink(duration, now, suppress_scoring)
                self._eyes_closed = False

            self._consecutive_low_frames = 0

        # Check for ongoing micro-sleep (eyes still closed > threshold)
        if self._eyes_closed:
            ongoing_duration = now - self._close_start_time
            if ongoing_duration >= config.MICROSLEEP_MIN_DURATION:
                # Trigger micro-sleep while eyes are still closed
                if self._last_event != "microsleep":
                    self._last_event = "microsleep"
                    self._microsleep_count += 1
                    if not suppress_scoring:
                        self._add_score(config.SCORE_MICROSLEEP)
                    # Reset close_start so we don't re-trigger every frame
                    self._close_start_time = now

        # Check for rapid blink cluster
        self._check_rapid_blink_cluster(now, suppress_scoring)

    def _classify_blink(self, duration: float, now: float, suppress_scoring: bool = False):
        """Classify a completed blink event by its duration."""
        if duration < config.NORMAL_BLINK_MAX_DURATION:
            # Normal blink — no score change
            self._last_event = "normal_blink"
        elif duration < config.LONG_BLINK_MAX_DURATION:
            # Long blink
            self._last_event = "long_blink"
            if not suppress_scoring:
                self._add_score(config.SCORE_LONG_BLINK)
        else:
            # Micro-sleep (already handled in real-time, but catch edge-case)
            self._last_event = "microsleep"
            self._microsleep_count += 1
            if not suppress_scoring:
                self._add_score(config.SCORE_MICROSLEEP)

        # Record blink timestamps
        self._total_blinks += 1
        self._blink_timestamps.append(now)
        self._rapid_blink_timestamps.append(now)

        # Prune old blink timestamps (older than 60 s)
        cutoff_60 = now - 60.0
        while self._blink_timestamps and self._blink_timestamps[0] < cutoff_60:
            self._blink_timestamps.popleft()

    def _check_rapid_blink_cluster(self, now: float, suppress_scoring: bool = False):
        """Detect if the recent blink rate constitutes a rapid blink cluster."""
        # Prune timestamps outside the sliding window
        cutoff = now - config.RAPID_BLINK_WINDOW_SEC
        while (self._rapid_blink_timestamps and
               self._rapid_blink_timestamps[0] < cutoff):
            self._rapid_blink_timestamps.popleft()

        if (len(self._rapid_blink_timestamps) >= config.RAPID_BLINK_COUNT_THRESHOLD
                and now - self._rapid_cluster_cooldown > config.RAPID_BLINK_WINDOW_SEC):
            self._last_event = "rapid_cluster"
            if not suppress_scoring:
                self._add_score(config.SCORE_RAPID_BLINK_CLUSTER)
            self._rapid_cluster_cooldown = now

    # ──────────────────────────────────────────────────────────────────────────
    # Score Decay
    # ──────────────────────────────────────────────────────────────────────────

    def _apply_score_decay(self, now: float, ear: float = 0.0):
        """Gradually reduce fatigue score. Faster when eyes are wide open."""
        elapsed = now - self._last_decay_time
        if elapsed >= 1.0:
            seconds_passed = int(elapsed)
            decay_rate = config.SCORE_DECAY_PER_SEC

            # Wide-eye recovery boost: if EAR is well above baseline,
            # the driver is alert — decay faster
            if (self._baseline_ear > 0 and
                    ear > self._baseline_ear * config.WIDE_EYE_EAR_MULTIPLIER):
                decay_rate *= config.WIDE_EYE_DECAY_BOOST

            decay = seconds_passed * decay_rate
            self._fatigue_score -= decay
            self._last_decay_time = now

    def _clamp_score(self):
        """Ensure fatigue score stays within [0, 100]."""
        self._fatigue_score = max(
            config.FATIGUE_SCORE_MIN,
            min(config.FATIGUE_SCORE_MAX, self._fatigue_score)
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Alarm State
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_alarm_level(self) -> str:
        """Determine alarm level with hysteresis.

        Rules:
          - Score >= 25: WARNING activates (first beep)
          - Score >= 60: CRITICAL activates
          - ALL alarms STOP when score drops below 40
          - Between 25-39 while score is RISING: alarm is on
          - Between 25-39 while DECLINING from >= 40: alarm stays on (hysteresis)
          - Below 40 after being active: silence
        """
        score = self._fatigue_score

        # Critical
        if score >= config.ALARM_CRITICAL_THRESHOLD:
            self._alarm_active = True
            self._peak_reached = True
            return config.STATUS_CRITICAL

        # If alarm was active and we're coming down, keep alarm on until below 40
        if self._alarm_active and self._peak_reached:
            if score >= config.ALARM_SILENCE_THRESHOLD:
                return config.STATUS_WARNING_1
            else:
                # Score dropped below 40 — silence everything
                self._alarm_active = False
                self._peak_reached = False
                return config.STATUS_NORMAL

        # Warning (initial activation while score is still rising)
        if score >= config.ALARM_WARNING_THRESHOLD:
            self._alarm_active = True
            # Mark peak_reached once score crosses the silence threshold (40)
            if score >= config.ALARM_SILENCE_THRESHOLD:
                self._peak_reached = True
            return config.STATUS_WARNING_1

        # Below warning threshold — no alarm
        self._alarm_active = False
        self._peak_reached = False
        return config.STATUS_NORMAL

    def _add_score(self, points: float):
        """Add fatigue score with dampening above the warning threshold."""
        if self._fatigue_score >= config.ALARM_WARNING_THRESHOLD:
            points *= config.SCORE_DAMPENING_FACTOR
        self._fatigue_score += points

    # ──────────────────────────────────────────────────────────────────────────
    # State Builder
    # ──────────────────────────────────────────────────────────────────────────

    def _build_state(self, ear: float, face_detected: bool) -> FatigueState:
        """Construct the FatigueState snapshot for the current frame."""
        # Count blinks in last 60 seconds
        now = time.time()
        cutoff_60 = now - 60.0
        while self._blink_timestamps and self._blink_timestamps[0] < cutoff_60:
            self._blink_timestamps.popleft()

        return FatigueState(
            is_calibrating=self._calibrating,
            calibration_progress=(
                min((now - self._calibration_start) / config.CALIBRATION_DURATION_SEC, 1.0)
                if self._calibrating and self._calibration_start > 0 else 0.0
            ),
            current_ear=ear,
            baseline_ear=self._baseline_ear,
            ear_threshold=self._ear_threshold,
            blink_duration=self._current_blink_duration,
            blink_count_last_60s=len(self._blink_timestamps),
            consecutive_low_frames=self._consecutive_low_frames,
            microsleep_count=self._microsleep_count,
            last_event=self._last_event,
            fatigue_score=self._fatigue_score,
            alarm_level=self._compute_alarm_level(),
            face_detected=face_detected,
        )
