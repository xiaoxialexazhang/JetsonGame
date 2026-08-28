"""Threaded camera capture.

Supports the Jetson CSI camera (nvarguscamerasrc), any USB/V4L2 webcam, and a
plain video file so the project can be exercised without hardware attached.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - cv2 missing means camera is simply unavailable
    cv2 = None


def gstreamer_pipeline(width: int, height: int, fps: int, flip: int, sensor_id: int = 0) -> str:
    """Standard Jetson CSI pipeline: NVMM capture -> BGR for OpenCV."""
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){width}, height=(int){height}, "
        f"framerate=(fraction){fps}/1 ! "
        f"nvvidconv flip-method={flip} ! "
        f"video/x-raw, width=(int){width}, height=(int){height}, format=(string)BGRx ! "
        f"videoconvert ! video/x-raw, format=(string)BGR ! appsink drop=true max-buffers=1"
    )


class Camera:
    """Grabs frames on a background thread so the render loop never blocks."""

    def __init__(self, source: str, width: int, height: int, fps: int, flip: int = 0):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self.flip = flip

        self._cap = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.error: Optional[str] = None
        self.backend = "none"

    # -- lifecycle ------------------------------------------------------
    def start(self) -> bool:
        if cv2 is None:
            self.error = "opencv-python is not installed"
            return False

        try:
            if self.source == "csi":
                pipeline = gstreamer_pipeline(self.width, self.height, self.fps, self.flip)
                self._cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                self.backend = "csi/gstreamer"
            elif self.source.isdigit():
                self._cap = cv2.VideoCapture(int(self.source))
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.backend = f"v4l2:/dev/video{self.source}"
            else:
                self._cap = cv2.VideoCapture(self.source)
                self.backend = f"file:{self.source}"
        except Exception as exc:  # pragma: no cover
            self.error = f"camera open failed: {exc}"
            return False

        if not self._cap or not self._cap.isOpened():
            self.error = f"could not open camera source '{self.source}'"
            self._cap = None
            return False

        self._running = True
        self._thread = threading.Thread(target=self._loop, name="camera", daemon=True)
        self._thread.start()
        return True

    def _loop(self) -> None:
        idle = 1.0 / max(self.fps, 1)
        while self._running and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok:
                # video files: loop back to the start; live cameras: brief retry
                if self.backend.startswith("file:"):
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.05)
                continue
            with self._lock:
                self._frame = frame
            time.sleep(idle * 0.5)

    def read(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    @property
    def is_running(self) -> bool:
        return self._running and self._frame is not None

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
