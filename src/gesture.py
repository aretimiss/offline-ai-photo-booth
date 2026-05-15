from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import mediapipe as mp
import numpy as np

GestureName = Literal["open_palm", "thumbs_up", "swipe_left", "swipe_right", "fist", "none"]


@dataclass
class GestureEvent:
    hand_detected: bool
    name: GestureName
    confidence: float = 0.0


class GestureRecognizer:
    """Simple and forgiving MediaPipe gesture recognizer for kiosk use."""

    def __init__(self) -> None:
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.45,
            min_tracking_confidence=0.45,
        )
        self.prev_x: float | None = None

    def detect(self, frame_bgr: np.ndarray) -> GestureEvent:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        if not result.multi_hand_landmarks:
            self.prev_x = None
            return GestureEvent(False, "none", 0.0)

        landmarks = result.multi_hand_landmarks[0].landmark

        wrist = landmarks[0]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        thumb_tip = landmarks[4]

        non_thumb_extended = sum(
            1
            for tip in [index_tip, middle_tip, ring_tip, pinky_tip]
            if tip.y < wrist.y + 0.05
        )
        thumb_up = thumb_tip.y < landmarks[3].y + 0.02

        current_x = index_tip.x
        if self.prev_x is not None:
            dx = current_x - self.prev_x
            if dx > 0.12:
                self.prev_x = current_x
                return GestureEvent(True, "swipe_right", min(1.0, abs(dx) * 3))
            if dx < -0.12:
                self.prev_x = current_x
                return GestureEvent(True, "swipe_left", min(1.0, abs(dx) * 3))
        self.prev_x = current_x

        if non_thumb_extended >= 3 and not thumb_up:
            return GestureEvent(True, "open_palm", 0.75)
        if thumb_up and non_thumb_extended <= 2:
            return GestureEvent(True, "thumbs_up", 0.8)
        if non_thumb_extended <= 1:
            return GestureEvent(True, "fist", 0.7)

        return GestureEvent(True, "none", 0.25)

    def close(self) -> None:
        self.hands.close()
