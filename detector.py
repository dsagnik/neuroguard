"""
detector.py — Video capture and face/eye landmark detection module.
Uses OpenCV for webcam capture and MediaPipe FaceLandmarker (Tasks API)
for landmark detection. Returns structured DetectionResult objects.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import os
import time

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import config
from utils import compute_ear_from_coords, get_eye_coordinates_from_landmarks


# Path to the downloaded face landmarker model
MODEL_PATH = os.path.join(config.ASSETS_DIR, "face_landmarker.task")


@dataclass
class DetectionResult:
    """Structured output from a single detection frame."""
    frame: Optional[np.ndarray] = None           # Raw BGR frame
    annotated_frame: Optional[np.ndarray] = None  # Frame with overlays drawn
    face_detected: bool = False
    ear_left: float = 0.0
    ear_right: float = 0.0
    ear_avg: float = 0.0
    left_eye_coords: List[Tuple[int, int]] = field(default_factory=list)
    right_eye_coords: List[Tuple[int, int]] = field(default_factory=list)


class Detector:
    """Captures webcam frames and extracts face mesh / eye landmarks."""

    def __init__(self):
        # Validate model file exists
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Face landmarker model not found at: {MODEL_PATH}\n"
                "Run 'python generate_assets.py' first to download it."
            )

        # Initialise webcam
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

        # Initialise MediaPipe FaceLandmarker (Tasks API)
        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_faces=config.MAX_NUM_FACES,
            min_face_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_face_presence_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(options)

        # Frame counter for timestamp (monotonically increasing ms)
        self._timestamp_ms = 0

        # Face mesh drawing connections — full tesselation subset for light overlay
        # Using canonical face mesh oval for a cleaner look
        self.FACE_OVAL_INDICES = [
            10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
            397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
            172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10
        ]

    def get_frame(self) -> DetectionResult:
        """Capture a frame from the webcam and run face landmark detection.

        Returns:
            DetectionResult with all computed fields populated.
        """
        result = DetectionResult()

        success, frame = self.cap.read()
        if not success or frame is None:
            return result

        # Flip horizontally for a mirror-view experience
        frame = cv2.flip(frame, 1)
        result.frame = frame.copy()

        h, w, _ = frame.shape

        # ── Low-light enhancement via CLAHE ──
        # Convert to LAB color space, apply CLAHE to lightness channel
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        enhanced = cv2.merge([l_channel, a_channel, b_channel])
        enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        # Convert enhanced BGR → RGB for MediaPipe
        rgb_frame = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)

        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Increment timestamp (must be monotonically increasing for VIDEO mode)
        self._timestamp_ms += 33  # ~30 FPS

        # Run face landmark detection
        try:
            face_result = self.landmarker.detect_for_video(mp_image, self._timestamp_ms)
        except Exception:
            result.annotated_frame = frame.copy()
            return result

        annotated = frame.copy()

        if face_result.face_landmarks and len(face_result.face_landmarks) > 0:
            landmarks = face_result.face_landmarks[0]  # First face
            result.face_detected = True

            # Get eye coordinates in pixel space
            result.left_eye_coords = get_eye_coordinates_from_landmarks(
                landmarks, config.LEFT_EYE_INDICES, w, h
            )
            result.right_eye_coords = get_eye_coordinates_from_landmarks(
                landmarks, config.RIGHT_EYE_INDICES, w, h
            )

            # Compute EAR for both eyes
            result.ear_left = compute_ear_from_coords(result.left_eye_coords)
            result.ear_right = compute_ear_from_coords(result.right_eye_coords)
            result.ear_avg = (result.ear_left + result.ear_right) / 2.0

            # Draw face oval (subtle overlay)
            self._draw_face_oval(annotated, landmarks, w, h)

            # Draw eye contours (bright cyan)
            self._draw_eye_contour(annotated, result.left_eye_coords)
            self._draw_eye_contour(annotated, result.right_eye_coords)

        result.annotated_frame = annotated
        return result

    def _draw_face_oval(self, frame, landmarks, w, h):
        """Draw a subtle face oval outline using key face contour landmarks."""
        pts = []
        for idx in self.FACE_OVAL_INDICES:
            if idx < len(landmarks):
                lm = landmarks[idx]
                pts.append((int(lm.x * w), int(lm.y * h)))
        if len(pts) > 2:
            pts_arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts_arr], isClosed=True,
                          color=(100, 100, 100), thickness=1)

    @staticmethod
    def _draw_eye_contour(frame, coords):
        """Draw a closed polygon around the eye landmarks."""
        if len(coords) < 3:
            return
        pts = np.array(coords, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], isClosed=True,
                      color=config.COLOR_CYAN, thickness=2)

    def release(self):
        """Release the webcam and MediaPipe resources."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        try:
            self.landmarker.close()
        except Exception:
            pass
