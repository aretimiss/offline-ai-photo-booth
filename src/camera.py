from __future__ import annotations

import cv2
import numpy as np


class CameraService:
    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720) -> None:
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap: cv2.VideoCapture | None = None

    def start(self) -> bool:
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return True

    def read_frame(self) -> np.ndarray | None:
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        return frame if ok else None

    def stop(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
