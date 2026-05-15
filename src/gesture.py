from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import mediapipe as mp
import numpy as np

GestureName = Literal["open_palm", "thumbs_up", "swipe_left", "swipe_right", "fist", "none"]


@dataclass
class GestureEvent:
    name: GestureName
    confidence: float = 0.0


class GestureRecognizer:
    """
    Lightweight MediaPipe-based gesture recognizer scaffold.
    Heuristics are intentionally simple in v1 and should be tuned for production.
    """

    def __init__(self) -> None:
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self.prev_x: float | None = None

    def detect(self, frame_bgr: np.ndarray) -> GestureEvent:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        if not result.multi_hand_landmarks:
            self.prev_x = None
            return GestureEvent("none", 0.0)

        landmarks = result.multi_hand_landmarks[0].landmark

        tip_ids = [4, 8, 12, 16, 20]
        wrist = landmarks[0]
        tips = [landmarks[i] for i in tip_ids]

        extended = sum(1 for tip in tips[1:] if tip.y < wrist.y)
        thumb_up = tips[0].y < landmarks[2].y

        current_x = tips[1].x
        swipe_threshold = 0.08
        if self.prev_x is not None:
            dx = current_x - self.prev_x
            self.prev_x = current_x
            if dx > swipe_threshold:
                return GestureEvent("swipe_right", min(1.0, abs(dx) * 4))
            if dx < -swipe_threshold:
                return GestureEvent("swipe_left", min(1.0, abs(dx) * 4))
        else:
            self.prev_x = current_x

        if extended >= 3 and not thumb_up:
            return GestureEvent("open_palm", 0.8)
        if thumb_up and extended <= 1:
            return GestureEvent("thumbs_up", 0.8)
        if extended == 0:
            return GestureEvent("fist", 0.8)

        return GestureEvent("none", 0.2)

    def close(self) -> None:
        self.hands.close()
