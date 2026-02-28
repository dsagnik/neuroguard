"""
alarm.py — Audio alarm manager for the Drowsiness Monitoring System.
Handles warning and critical audio alerts using pygame.mixer.
Prevents overlapping playback and supports continuous alarm mode.
Warning beeps repeat periodically while the alarm level stays active.
"""

import os
import time
import threading

import pygame

import config

# How often to re-play the warning beep while the level stays at WARNING_1 (seconds)
WARNING_REPEAT_INTERVAL = 5.0


class AlarmManager:
    """Manages audio alarm playback with non-blocking, non-overlapping sounds."""

    def __init__(self):
        pygame.mixer.init()
        self._is_playing = False
        self._continuous = False
        self._current_level = ""  # "warning1" | "warning2" | "critical" | ""
        self._lock = threading.Lock()
        self._last_warning_time = 0.0  # tracks when warning was last played

        # Pre-load sound objects (if files exist)
        self._warning_sound = None
        self._critical_sound = None

        if os.path.exists(config.WARNING_SOUND_PATH):
            self._warning_sound = pygame.mixer.Sound(config.WARNING_SOUND_PATH)

        if os.path.exists(config.CRITICAL_SOUND_PATH):
            self._critical_sound = pygame.mixer.Sound(config.CRITICAL_SOUND_PATH)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def play_warning(self):
        """Play the warning sound. Repeats every WARNING_REPEAT_INTERVAL seconds."""
        now = time.time()
        with self._lock:
            if self._current_level == "critical":
                return  # don't downgrade from critical

            # If already in warning mode, only replay after the repeat interval
            if self._current_level == "warning1":
                if now - self._last_warning_time < WARNING_REPEAT_INTERVAL:
                    return
                # Time to repeat the warning beep
                if self._warning_sound:
                    self._warning_sound.play()
                    self._last_warning_time = now
                return

            self._stop_internal()
            self._current_level = "warning1"
            self._continuous = False
            if self._warning_sound:
                self._warning_sound.play()
                self._is_playing = True
                self._last_warning_time = now

    def play_critical(self):
        """Play the critical sound once (non-blocking)."""
        with self._lock:
            if self._current_level == "critical" and self._is_playing:
                return
            self._stop_internal()
            self._current_level = "warning2"
            self._continuous = False
            if self._critical_sound:
                self._critical_sound.play()
                self._is_playing = True

    def play_continuous(self):
        """Play the critical sound in a continuous loop."""
        with self._lock:
            if self._continuous and self._is_playing:
                return  # already looping
            self._stop_internal()
            self._current_level = "critical"
            self._continuous = True
            if self._critical_sound:
                self._critical_sound.play(loops=-1)
                self._is_playing = True

    def stop(self):
        """Stop all alarm sounds."""
        with self._lock:
            self._stop_internal()

    def update(self, alarm_level: str):
        """Set alarm state based on the alarm level string.

        2-tier escalation:
            WARNING_1 → repeating warning beep (every 5s)
            CRITICAL  → continuous critical alarm loop
        Alarm stays active until fatigue drops below ALARM_STOP_THRESHOLD (40).
        """
        if alarm_level == config.STATUS_CRITICAL:
            self.play_continuous()
        elif alarm_level == config.STATUS_WARNING_1:
            self.play_warning()
        else:
            self.stop()

    def cleanup(self):
        """Release pygame mixer resources."""
        self.stop()
        try:
            pygame.mixer.quit()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _stop_internal(self):
        """Stop playback (must be called while holding self._lock)."""
        pygame.mixer.stop()
        self._is_playing = False
        self._continuous = False
        self._current_level = ""
        self._last_warning_time = 0.0
