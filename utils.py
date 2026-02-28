"""
utils.py — Stateless utility functions for the Drowsiness Monitoring System.
Provides EAR computation, landmark extraction, and distance helpers.
Compatible with both old and new MediaPipe APIs.
"""

import math
import sys
import os

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and PyInstaller.
    """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def euclidean_distance(p1, p2):
    """Compute the 2D Euclidean distance between two points.

    Args:
        p1: Tuple or array of (x, y).
        p2: Tuple or array of (x, y).

    Returns:
        Float distance.
    """
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_eye_coordinates_from_landmarks(landmarks, eye_indices, frame_width, frame_height):
    """Get pixel coordinates for eye landmarks from the new Tasks API format.

    Args:
        landmarks: List of NormalizedLandmark objects from FaceLandmarker.
        eye_indices: List of landmark indices for the eye.
        frame_width: Width of the frame in pixels.
        frame_height: Height of the frame in pixels.

    Returns:
        List of (x, y) integer tuples.
    """
    coords = []
    for idx in eye_indices:
        if idx < len(landmarks):
            lm = landmarks[idx]
            x = int(lm.x * frame_width)
            y = int(lm.y * frame_height)
            coords.append((x, y))
    return coords


def compute_ear_from_coords(coords):
    """Compute the Eye Aspect Ratio (EAR) from 6 pixel-coordinate points.

    The EAR formula (Soukupová & Čech, 2016):
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)

    Where the 6 points are ordered:
        p1 = lateral corner, p2 = upper-outer, p3 = upper-inner,
        p4 = medial corner, p5 = lower-inner, p6 = lower-outer.

    Args:
        coords: List of 6 (x, y) tuples for one eye.

    Returns:
        Float EAR value, or 0.0 if coords are insufficient.
    """
    if len(coords) < 6:
        return 0.0

    p1, p2, p3, p4, p5, p6 = coords

    # Vertical distances
    vertical_a = euclidean_distance(p2, p6)
    vertical_b = euclidean_distance(p3, p5)

    # Horizontal distance
    horizontal = euclidean_distance(p1, p4)

    if horizontal == 0:
        return 0.0

    ear = (vertical_a + vertical_b) / (2.0 * horizontal)
    return ear
