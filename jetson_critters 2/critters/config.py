"""Central configuration. Every value can be overridden with an env var."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    if isinstance(default, bool):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(default, int):
        return int(raw)
    if isinstance(default, float):
        return float(raw)
    return raw


@dataclass
class Config:
    # ---- window -------------------------------------------------------
    width: int = field(default_factory=lambda: _env("CRITTERS_WIDTH", 1280))
    height: int = field(default_factory=lambda: _env("CRITTERS_HEIGHT", 720))
    fps: int = field(default_factory=lambda: _env("CRITTERS_FPS", 60))

    # ---- camera -------------------------------------------------------
    # "csi"  -> Jetson CSI ribbon camera via nvarguscamerasrc
    # "0"    -> /dev/video0 USB webcam (any integer works)
    # a path -> video file, handy for testing without hardware
    camera_source: str = field(default_factory=lambda: str(_env("CRITTERS_CAMERA", "csi")))
    camera_width: int = field(default_factory=lambda: _env("CRITTERS_CAM_W", 1280))
    camera_height: int = field(default_factory=lambda: _env("CRITTERS_CAM_H", 720))
    camera_fps: int = field(default_factory=lambda: _env("CRITTERS_CAM_FPS", 30))
    camera_flip: int = field(default_factory=lambda: _env("CRITTERS_CAM_FLIP", 0))

    # ---- vision -------------------------------------------------------
    model_name: str = field(default_factory=lambda: str(_env("CRITTERS_MODEL", "mobilenet_v3_large")))
    infer_every_n_frames: int = field(default_factory=lambda: _env("CRITTERS_INFER_EVERY", 5))
    confidence_threshold: float = field(default_factory=lambda: _env("CRITTERS_CONF", 0.35))
    # how many consecutive confident reads of the same species before we capture
    capture_streak: int = field(default_factory=lambda: _env("CRITTERS_STREAK", 8))
    # seconds before the same species can be captured again
    capture_cooldown: float = field(default_factory=lambda: _env("CRITTERS_COOLDOWN", 12.0))

    # ---- llm ----------------------------------------------------------
    ollama_url: str = field(default_factory=lambda: str(_env("OLLAMA_URL", "http://127.0.0.1:11434")))
    ollama_model: str = field(default_factory=lambda: str(_env("OLLAMA_MODEL", "llama3.2:3b")))
    llm_timeout: float = field(default_factory=lambda: _env("CRITTERS_LLM_TIMEOUT", 60.0))
    llm_max_history: int = field(default_factory=lambda: _env("CRITTERS_LLM_HISTORY", 12))

    # ---- persistence --------------------------------------------------
    save_path: Path = field(default_factory=lambda: ROOT / "save" / "sanctuary.json")
    snapshot_dir: Path = field(default_factory=lambda: ROOT / "save" / "snapshots")

    def ensure_dirs(self) -> None:
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)


CONFIG = Config()
