"""Stage 0 -- webcam. A background thread keeps the newest frame available so
the pygame loop can grab it every tick without ever blocking on the driver."""
from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

import cv2

import config


class Camera:
    def __init__(self, index: int = config.CAM_INDEX):
        self.index = index
        self._frame = None          # BGR numpy array
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.ok = False
        self.error = ""
        self.cap = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    def _open(self):
        # V4L2 is the right backend for a USB cam on Jetson.
        cap = cv2.VideoCapture(self.index, cv2.CAP_V4L2)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.index)   # fall back to default backend
        if not cap.isOpened():
            self.error = f"could not open camera {self.index}"
            return None
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_H)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _loop(self):
        self.cap = self._open()
        if self.cap is None:
            return
        self.ok = True
        while not self._stop.is_set():
            grabbed, frame = self.cap.read()
            if not grabbed:
                time.sleep(0.05)
                continue
            with self._lock:
                self._frame = frame
        self.cap.release()

    # ------------------------------------------------------------------
    def read(self):
        """Newest BGR frame, or None."""
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def snapshot(self) -> Path | None:
        """Freeze the current frame to data/input/ and return its path."""
        frame = self.read()
        if frame is None:
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = config.INPUT_DIR / f"snap-{stamp}.jpg"
        cv2.imwrite(str(path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        return path

    def close(self):
        self._stop.set()
