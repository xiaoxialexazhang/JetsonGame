#!/usr/bin/env python3
"""Runs the whole app headless with a fake camera and a fake recogniser.

No Jetson, no camera, no Ollama required. Proves the pipeline end to end:
  detection -> capture -> critter in world -> chat message -> reply in history.

    python smoke_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

try:
    import pygame  # noqa: F401

    RENDER_BACKEND = "real pygame"
except ImportError:
    import fake_pygame

    fake_pygame.install()
    RENDER_BACKEND = "fake pygame (logic only — install pygame for a real render check)"

import numpy as np  # noqa: E402

from critters.app import App  # noqa: E402
from critters.config import Config  # noqa: E402
from critters.species import IMAGENET_TO_SPECIES, SPECIES  # noqa: E402
from critters.vision import Detection  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        FAILURES.append(label)


def _evt(type_, **kwargs):
    """Build an event object that works with real pygame or the stub."""
    try:
        import pygame

        return pygame.event.Event(type_, **kwargs)
    except (ImportError, AttributeError):
        import fake_pygame

        return fake_pygame.Event(type_, **kwargs)


class FakeRecognizer:
    """Alternates cat and goat so both capture paths get exercised."""

    name = "fake"
    available = True

    def __init__(self):
        self.calls = 0

    def classify(self, frame):
        self.calls += 1
        key = "cat" if (self.calls // 12) % 2 == 0 else "goat"
        return Detection(species_key=key, raw_label=f"fake {key}", confidence=0.92)


def main() -> int:
    print(f"render backend: {RENDER_BACKEND}\n")
    print("=== species roster ===")
    check("cat is in the roster", "cat" in SPECIES)
    check("goat is in the roster", "goat" in SPECIES, f"{len(SPECIES)} species total")
    check("goat has horns and a beard", SPECIES["goat"].horns and SPECIES["goat"].beard)
    check("ImageNet 281 (tabby) maps to cat", IMAGENET_TO_SPECIES.get(281) == "cat")
    check("ImageNet 350 (ibex) maps to goat", IMAGENET_TO_SPECIES.get(350) == "goat")
    check("no coin/trade fields survived", not any(
        hasattr(sp, attr) for sp in SPECIES.values() for attr in ("price", "coins", "rarity", "trade_value")
    ))

    tmp = Path(tempfile.mkdtemp(prefix="critters-smoke-"))
    cfg = Config()
    cfg.save_path = tmp / "sanctuary.json"
    cfg.snapshot_dir = tmp / "snapshots"
    cfg.camera_source = "9999"  # nothing there — camera should fail gracefully
    cfg.capture_streak = 3
    cfg.capture_cooldown = 0.0

    print("\n=== boot ===")
    app = App(cfg, headless=True, max_frames=1)
    check("app boots without a camera", app.camera_ok is False, str(app.camera.error))
    check("recogniser loaded", app.recognizer is not None, getattr(app.recognizer, "name", "?"))

    # swap in the fake recogniser and feed it synthetic frames
    app.worker.recognizer = FakeRecognizer()
    frame = (np.random.rand(240, 320, 3) * 255).astype("uint8")

    print("\n=== capture pipeline ===")
    for _ in range(40):
        app.worker._run(frame)   # synchronous inference, deterministic for the test
        app._handle_capture()

    captured = {c.species_key for c in app.world.critters}
    check("a cat was captured from the camera path", "cat" in captured)
    check("a goat was captured from the camera path", "goat" in captured,
          f"world holds {len(app.world.critters)}: {sorted(captured)}")
    check("every critter got a name", all(c.name for c in app.world.critters))
    check("every critter got a greeting", all(c.history for c in app.world.critters))

    print("\n=== chat ===")
    critter = app.world.critters[0]
    app.world.selected_id = critter.id
    before = len(critter.history)
    app.chat.send(critter, "hello, who are you?")
    check("user message recorded", len(critter.history) == before + 1)
    check("critter marked as thinking", critter.thinking)

    # simulate a reply arriving from the worker thread
    app.chat.results.put((critter.id, "*chews something* I'm me. Obviously.", True))
    app.chat.drain(lambda cid: next((c for c in app.world.critters if c.id == cid), None))
    check("reply landed in history", critter.history[-1].role == "assistant")
    check("thinking flag cleared", not critter.thinking)

    prompt = app.chat._system_prompt(critter)
    check("system prompt names the critter", critter.name in prompt)
    check("system prompt carries the persona", critter.species.persona[:30] in prompt)

    print("\n=== interaction ===")
    import pygame as pg

    target = app.world.critters[0]
    app.world.selected_id = None
    app.input_focused = False
    app._handle_event(_evt(pg.MOUSEBUTTONDOWN, button=1, pos=(int(target.x), int(target.y))))
    check("clicking a critter selects it", app.world.selected_id == target.id)
    check("clicking a critter focuses the chat box", app.input_focused)

    empty = (app.ui.world_rect.x + 4, app.ui.world_rect.y + 4)
    app._handle_event(_evt(pg.MOUSEBUTTONDOWN, button=1, pos=empty))
    check("clicking empty grass deselects", app.world.selected_id is None)

    app.world.selected_id = target.id
    app.input_focused = True
    app.input_text = ""
    for ch in "hi":
        app._handle_event(_evt(pg.KEYDOWN, key=ord(ch), unicode=ch))
    check("typing reaches the input box", app.input_text == "hi", repr(app.input_text))
    app._handle_event(_evt(pg.KEYDOWN, key=pg.K_BACKSPACE, unicode=""))
    check("backspace works", app.input_text == "h")

    app.input_focused = False
    n_before = len(app.world.critters)
    app._handle_event(_evt(pg.KEYDOWN, key=pg.K_2, unicode="2"))
    check("number key spawns a species", len(app.world.critters) == n_before + 1)

    app.input_focused = True
    app.input_text = ""
    app._handle_event(_evt(pg.KEYDOWN, key=pg.K_2, unicode="2"))
    check("number key types instead of spawning while focused", app.input_text == "2")
    app.input_text = ""
    app.input_focused = False

    print("\n=== render + persistence ===")
    app.max_frames = app.frame_index + 30
    app.running = True
    app.run()  # exercises every draw path with critters present
    check("render loop completed", app.frame_index >= 30)
    check("save file written", cfg.save_path.exists())

    from critters.world import World

    reloaded = World((0, 0, 800, 600), cfg.save_path)
    reloaded.load()
    check("reload restores critters", len(reloaded.critters) == len(app.world.critters),
          f"{len(reloaded.critters)} restored")
    check("reload restores chat history",
          any(len(c.history) > 1 for c in reloaded.critters))

    print("\n=== manual spawn (demo without hardware) ===")
    app2 = App(cfg, headless=True, max_frames=1)
    n0 = len(app2.world.critters)
    app2.world.add_critter("goat")
    check("manual goat spawn works", len(app2.world.critters) == n0 + 1)
    app2.shutdown()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
