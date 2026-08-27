"""Main loop: camera in, critters out, chat in the side panel."""

from __future__ import annotations

import time
from typing import Optional

import pygame

from .camera import Camera
from .chat import OllamaChat
from .config import Config
from .species import SPECIES_ORDER
from .ui import Ui
from .vision import RecognitionWorker, load_recognizer
from .world import World

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


class App:
    def __init__(self, config: Config, headless: bool = False, max_frames: Optional[int] = None):
        self.cfg = config
        self.cfg.ensure_dirs()
        self.headless = headless
        self.max_frames = max_frames

        pygame.init()
        pygame.display.set_caption("Jetson Critters")
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((config.width, config.height), flags)
        self.clock = pygame.time.Clock()
        self.ui = Ui(self.screen)

        wr = self.ui.world_rect
        self.world = World((wr.left, wr.top, wr.right, wr.bottom), config.save_path)
        self.world.load()

        self.camera = Camera(
            config.camera_source,
            config.camera_width,
            config.camera_height,
            config.camera_fps,
            config.camera_flip,
        )
        self.camera_ok = self.camera.start()

        self.recognizer = load_recognizer(config.model_name)
        self.worker = RecognitionWorker(
            self.recognizer, config.confidence_threshold, config.capture_streak
        )

        self.chat = OllamaChat(
            config.ollama_url, config.ollama_model, config.llm_timeout, config.llm_max_history
        )
        self.chat.check()

        self.input_text = ""
        self.input_focused = False
        self.frame_index = 0
        self.running = True

    # -- capture ----------------------------------------------------------
    def _save_snapshot(self, frame, species_key: str) -> Optional[str]:
        if cv2 is None or frame is None:
            return None
        path = self.cfg.snapshot_dir / f"{species_key}_{int(time.time())}.jpg"
        try:
            cv2.imwrite(str(path), frame)
            return str(path)
        except Exception:
            return None

    def _handle_capture(self) -> None:
        pending = self.worker.take_capture()
        if pending is None:
            return
        detection, frame = pending
        if not self.world.can_capture(detection.species_key, self.cfg.capture_cooldown):
            return
        snapshot = self._save_snapshot(frame, detection.species_key)
        critter = self.world.add_critter(detection.species_key, snapshot)
        if self.world.selected_id is None:
            self.world.selected_id = critter.id
        self.world.save()

    def _cooldown_left(self) -> float:
        det = self.worker.latest
        if det is None:
            return 0.0
        last = self.world.last_capture_at.get(det.species_key, 0.0)
        return max(0.0, self.cfg.capture_cooldown - (time.time() - last))

    # -- events -----------------------------------------------------------
    def _send_message(self) -> None:
        text = self.input_text.strip()
        critter = self.world.selected
        if not text or critter is None:
            return
        if self.chat.send(critter, text):
            self.input_text = ""
            self.ui.scroll = 0

    def _handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.ui.input_rect.collidepoint(event.pos):
                    self.input_focused = True
                elif self.ui.world_rect.collidepoint(event.pos):
                    hit = self.world.pick(*event.pos)
                    self.world.selected_id = hit.id if hit else None
                    self.input_focused = hit is not None
                    self.ui.scroll = 0
                else:
                    self.input_focused = False
            elif event.button in (4, 5) and self.ui.chat_rect.collidepoint(pygame.mouse.get_pos()):
                self.ui.scroll = max(0, self.ui.scroll + (30 if event.button == 4 else -30))

        elif event.type == pygame.MOUSEWHEEL:
            if self.ui.chat_rect.collidepoint(pygame.mouse.get_pos()):
                self.ui.scroll = max(0, self.ui.scroll + event.y * 30)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.input_focused:
                    self.input_focused = False
                else:
                    self.running = False
                return

            if self.input_focused:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._send_message()
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif event.unicode and event.unicode.isprintable() and len(self.input_text) < 280:
                    self.input_text += event.unicode
                return

            # --- shortcuts available when the text box is not focused ---
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                if idx < len(SPECIES_ORDER):
                    critter = self.world.add_critter(SPECIES_ORDER[idx])
                    self.world.selected_id = critter.id
                    self.world.save()
            elif event.key == pygame.K_r and self.world.selected_id:
                self.world.release(self.world.selected_id)
                self.world.save()
            elif event.key == pygame.K_s:
                self.world.save()
                self.world.toast = ("sanctuary saved", time.time())
            elif event.key == pygame.K_c:
                self.chat.check()
            elif event.key == pygame.K_TAB and self.world.critters:
                ids = [c.id for c in self.world.critters]
                cur = ids.index(self.world.selected_id) if self.world.selected_id in ids else -1
                self.world.selected_id = ids[(cur + 1) % len(ids)]
                self.ui.scroll = 0

    # -- loop -------------------------------------------------------------
    def run(self) -> None:
        t0 = time.time()
        while self.running:
            dt = self.clock.tick(self.cfg.fps) / 1000.0
            t = time.time() - t0

            for event in pygame.event.get():
                self._handle_event(event)

            frame = self.camera.read() if self.camera_ok else None
            self.frame_index += 1
            if frame is not None and self.frame_index % self.cfg.infer_every_n_frames == 0:
                self.worker.submit(frame)
            self._handle_capture()

            self.chat.drain(lambda cid: next((c for c in self.world.critters if c.id == cid), None))
            self.world.update(dt)

            self.screen.fill((26, 30, 28))
            cam_status = self.camera.backend if self.camera_ok else "unavailable"
            self.ui.draw_header(
                self.world,
                getattr(self.recognizer, "name", "unknown"),
                self.chat.status,
                cam_status,
                self.camera_ok,
            )
            self.ui.draw_world(self.world, t)
            self.ui.draw_camera(frame, self.worker, self.camera.error, self._cooldown_left())
            self.ui.draw_chat(self.world.selected, self.input_text, self.input_focused, t)
            pygame.display.flip()

            if self.max_frames is not None and self.frame_index >= self.max_frames:
                self.running = False

        self.shutdown()

    def shutdown(self) -> None:
        try:
            self.world.save()
        finally:
            self.camera.stop()
            pygame.quit()
