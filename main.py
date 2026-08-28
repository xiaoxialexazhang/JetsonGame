#!/usr/bin/env python3
"""Critter World -- point a camera at an animal, get a pixel villager.

    python3 main.py                 # normal
    python3 main.py --no-camera     # keyboard-only, press T to use data/input/
    python3 main.py --cam 1         # pick a different /dev/video*
"""
from __future__ import annotations

import argparse

import config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--cam", type=int, default=config.CAM_INDEX)
    ap.add_argument("--offline", action="store_true",
                    help="force the fully-local path even if Claude is reachable")
    args = ap.parse_args()

    if args.offline:
        config.OFFLINE = True

    # Decide once, up front, what this session can reach. Nothing below here
    # cares whether we're online -- each stage asks pipeline.backends.
    from pipeline import backends
    b = backends.refresh()
    if not b.claude:
        print("   running fully local: on-device species + template sprites"
              + (" + Ollama dialogue" if b.ollama else " + canned dialogue"))
        if not b.torch:
            print("   (no torch -- species detection will be limited; "
                  "faces still resolve to 'person')")

    cam = None
    if not args.no_camera:
        from pipeline.capture import Camera
        cam = Camera(args.cam)
        import time
        for _ in range(40):                  # give the driver a moment
            if cam.read() is not None:
                break
            time.sleep(0.05)
        if not cam.ok:
            print(f"!! camera {args.cam} did not open ({cam.error}).")
            print("   try: ls /dev/video*   or run with --no-camera")

    from game.world import World
    World(cam).run()
    if cam:
        cam.close()


if __name__ == "__main__":
    main()
