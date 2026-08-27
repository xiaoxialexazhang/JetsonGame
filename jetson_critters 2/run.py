#!/usr/bin/env python3
"""Jetson Critters — entry point.

    python run.py                          # CSI camera on a Jetson
    python run.py --camera 0               # USB webcam
    python run.py --camera clips/cat.mp4   # a video file, for testing off-device
    python run.py --headless --frames 120  # smoke test, no window
"""

from __future__ import annotations

import argparse
import sys

from critters.config import CONFIG


def main() -> int:
    p = argparse.ArgumentParser(description="Jetson Critters")
    p.add_argument("--camera", help="'csi', a /dev/video index like 0, or a video file path")
    p.add_argument("--model", help="torchvision classifier (default mobilenet_v3_large)")
    p.add_argument("--ollama-model", help="local model name, e.g. llama3.2:3b")
    p.add_argument("--ollama-url", help="Ollama base URL (default http://127.0.0.1:11434)")
    p.add_argument("--conf", type=float, help="confidence threshold, 0-1")
    p.add_argument("--streak", type=int, help="confident frames required before capture")
    p.add_argument("--headless", action="store_true", help="run without showing a window")
    p.add_argument("--frames", type=int, help="exit after N frames (use with --headless)")
    args = p.parse_args()

    cfg = CONFIG
    if args.camera:
        cfg.camera_source = args.camera
    if args.model:
        cfg.model_name = args.model
    if args.ollama_model:
        cfg.ollama_model = args.ollama_model
    if args.ollama_url:
        cfg.ollama_url = args.ollama_url
    if args.conf is not None:
        cfg.confidence_threshold = args.conf
    if args.streak is not None:
        cfg.capture_streak = args.streak

    if args.headless:
        import os

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    # imported after arg parsing so --help works without pygame installed
    try:
        from critters.app import App
    except ImportError as exc:
        print(f"missing dependency: {exc}\n\n  pip install pygame numpy requests\n", file=sys.stderr)
        return 2

    app = App(cfg, headless=args.headless, max_frames=args.frames)

    print(f"camera : {app.camera.backend if app.camera_ok else 'unavailable — ' + str(app.camera.error)}")
    print(f"vision : {getattr(app.recognizer, 'name', 'unknown')}")
    print(f"llm    : {app.chat.status}  ({cfg.ollama_model} @ {cfg.ollama_url})")
    print(f"save   : {cfg.save_path}")
    print("\nkeys: click a critter to talk · Tab cycle · R release · S save · C recheck LLM · 1-7 spawn manually · Esc quit\n")

    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
