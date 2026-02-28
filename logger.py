"""
logger.py — Session event logger for the Drowsiness Monitoring System.
Appends rows to a CSV file with timestamps, EAR, fatigue score, events, etc.
"""

import csv
import os
from datetime import datetime

import config


class SessionLogger:
    """Logs drowsiness detection events to a CSV file."""

    HEADER = [
        "Timestamp",
        "EAR",
        "Fatigue_Score",
        "Event_Type",
        "Alarm_Level",
        "Blink_Duration",
        "Microsleep_Detected",
    ]

    def __init__(self):
        # Ensure the logs directory exists
        os.makedirs(config.LOGS_DIR, exist_ok=True)

        # Open the CSV file in append mode
        file_exists = os.path.exists(config.SESSION_LOG_PATH)
        self._file = open(config.SESSION_LOG_PATH, mode="a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)

        # Write header if the file is new or empty
        if not file_exists or os.path.getsize(config.SESSION_LOG_PATH) == 0:
            self._writer.writerow(self.HEADER)
            self._file.flush()

    def log_event(
        self,
        ear: float,
        fatigue_score: float,
        event_type: str,
        alarm_level: str,
        blink_duration: float,
        microsleep_detected: bool,
    ):
        """Append one event row to the session log.

        Args:
            ear: Current average EAR value.
            fatigue_score: Current fatigue score (0–100).
            event_type: Classification string (e.g. "normal_blink", "microsleep").
            alarm_level: Current alarm level string.
            blink_duration: Duration of the most recent blink in seconds.
            microsleep_detected: Whether a micro-sleep was detected this frame.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        row = [
            timestamp,
            f"{ear:.4f}",
            f"{fatigue_score:.1f}",
            event_type,
            alarm_level,
            f"{blink_duration:.3f}",
            str(microsleep_detected),
        ]
        self._writer.writerow(row)
        self._file.flush()

    def close(self):
        """Close the CSV file handle."""
        if self._file and not self._file.closed:
            self._file.close()
