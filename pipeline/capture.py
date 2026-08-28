"""Stage 0 -- webcam. A background thread keeps the newest frame available so
the pygame loop can grab it every tick without ever blocking on the driver."""
from __future__ import annotations

import sys
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
        # V4L2 is right on Jetson/Linux; AVFoundation is right on macOS. Asking
        # for V4L2 on a Mac just wastes a couple of seconds failing.
        if sys.platform == "darwin":
            backends_to_try = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        elif sys.platform.startswith("linux"):
            backends_to_try = [cv2.CAP_V4L2, cv2.CAP_ANY]
        else:
            backends_to_try = [cv2.CAP_ANY]

        cap = None
        for backend in backends_to_try:
            cap = cv2.VideoCapture(self.index, backend)
            if cap.isOpened():
                break
            cap.release()
            cap = None
        if cap is None:
            self.error = (f"could not open camera {self.index}"
                          + (" -- on macOS, grant Camera permission to your terminal in "
                             "System Settings > Privacy & Security > Camera"
                             if sys.platform == "darwin" else ""))
            return None
        if sys.platform.startswith("linux"):
            # MJPG lets a USB cam hit 720p30 over USB2; AVFoundation dislikes it
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
