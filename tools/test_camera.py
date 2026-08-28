#!/usr/bin/env python3
"""Step 1 of the bring-up: does the USB webcam work at all?
    python3 tools/test_camera.py          -> live window, S saves a snapshot
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2  # noqa: E402

import config  # noqa: E402

idx = int(sys.argv[1]) if len(sys.argv) > 1 else config.CAM_INDEX
cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
if not cap.isOpened():
    cap = cv2.VideoCapture(idx)
if not cap.isOpened():
    print(f"could not open camera {idx}. try: ls /dev/video*")
    raise SystemExit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_H)
print(f"camera {idx} open at "
      f"{cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f}")
print("S = save a snapshot to data/input   ·   Q = quit")

n = 0
while True:
    ok, frame = cap.read()
    if not ok:
        print("read failed")
        break
    cv2.imshow("camera test", frame)
    k = cv2.waitKey(1) & 0xFF
    if k == ord("q"):
        break
    if k == ord("s"):
        p = config.INPUT_DIR / f"test-{n:03d}.jpg"
        cv2.imwrite(str(p), frame)
        print("saved", p)
        n += 1
cap.release()
cv2.destroyAllWindows()
