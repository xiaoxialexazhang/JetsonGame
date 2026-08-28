"""The game. Camera preview + wandering critters + click-to-talk."""
from __future__ import annotations

import time

import numpy as np
import pygame

import config as C
from game import chat, jobs, mapgen, ui
from game.critter import Critter
from pipeline import backends, orchestrator

try:
    import cv2
except ImportError:      # the game still runs without a camera
    cv2 = None


class World:
    def __init__(self, camera=None):
        pygame.init()
        pygame.display.set_caption("Critter World  ·  Jetson Orin Nano")
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        pygame.key.set_repeat(300, 35)

        self.play_h = C.SCREEN_H - C.CHAT_BAR_H
        self.bg, self.walkable = mapgen.build(C.SCREEN_W, self.play_h)

        self.camera = camera
        self._preview = None
        self._preview_tick = 0

        self.critters: list[Critter] = []
        self.hitboxes: dict[int, pygame.Rect] = {}
        self.selected: Critter | None = None
        self.convos: dict[str, chat.Conversation] = {}

        self.input_text = ""
        self.awaiting_reply = False
        self.catching = False
        self.status = ""
        self.toast_msg, self.toast_tone, self.toast_until = "", "info", 0.0
        self.running = True

        self.load_roster()

    # ------------------------------------------------------------------ setup
    def load_roster(self):
        self.critters.clear()
        for d in orchestrator.load_roster():
            try:
                c = Critter(d, self.walkable)
                c.spawn_t = 1.0
                self.critters.append(c)
            except Exception as e:      # noqa: BLE001
                print(f"[world] skipping {d.get('name')}: {e}")
        print(f"[world] {len(self.critters)} critters on the farm")

    def notify(self, msg, tone="info", secs=3.0):
        self.toast_msg, self.toast_tone = msg, tone
        self.toast_until = time.time() + secs

    # ------------------------------------------------------------------ actions
    def catch(self):
        """SPACE: snapshot -> pipeline -> new critter. Runs off-thread."""
        if self.catching:
            return
        if self.camera is None or not self.camera.ok:
            self.notify("no camera available", "bad")
            return
        path = self.camera.snapshot()
        if path is None:
            self.notify("camera gave no frame yet", "bad")
            return
        self.catching = True
        self.status = "saving snapshot..."
        print(f"[world] captured {path}")

        def work():
            critter, err = orchestrator.safe_process(
                path, progress=lambda m: jobs.emit("status", text=m))
            if err:
                jobs.emit("catch_failed", message=err)
            else:
                jobs.emit("catch_done", critter=critter)

        jobs.run(work)

    def catch_from_last_file(self):
        """T: re-run the pipeline on the newest file in data/input (no camera)."""
        if self.catching:
            return
        files = sorted(C.INPUT_DIR.glob("*.*"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            self.notify("drop an image into data/input/ first", "bad")
            return
        self.catching = True
        self.status = "re-running on " + files[0].name

        def work():
            critter, err = orchestrator.safe_process(
                files[0], progress=lambda m: jobs.emit("status", text=m))
            jobs.emit("catch_failed", message=err) if err else \
                jobs.emit("catch_done", critter=critter)

        jobs.run(work)

    def select(self, critter: Critter):
        self.selected = critter
        self.input_text = ""
        self.awaiting_reply = False
        cid = critter.data["id"]
        if cid not in self.convos:
            self.convos[cid] = chat.Conversation(critter.data)
            critter.say(critter.data.get("greeting", "Oh! Hello."))
        else:
            critter.say(critter.bubble or "Back again?")

    def deselect(self):
        if self.selected:
            self.selected.hush()
        self.selected = None
        self.input_text = ""
        self.awaiting_reply = False

    def send_message(self):
        text = self.input_text.strip()
        if not text or self.selected is None or self.awaiting_reply:
            return
        critter = self.selected
        cid = critter.data["id"]
        self.input_text = ""
        self.awaiting_reply = True
        critter.think()

        def work():
            reply = self.convos[cid].reply(text)
            jobs.emit("reply", cid=cid, text=reply)

        jobs.run(work)

    # ------------------------------------------------------------------ events
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if e.pos[1] < self.play_h:
                    hit = None
                    for c in reversed(self.critters):     # topmost first
                        r = self.hitboxes.get(id(c))
                        if r and r.collidepoint(e.pos):
                            hit = c
                            break
                    self.select(hit) if hit else self.deselect()

            elif e.type == pygame.TEXTINPUT and self.selected and not self.awaiting_reply:
                if len(self.input_text) < 240:
                    self.input_text += e.text

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.deselect()
                elif e.key == pygame.K_SPACE and self.selected is None:
                    self.catch()
                elif e.key == pygame.K_RETURN:
                    self.send_message()
                elif e.key == pygame.K_BACKSPACE and self.selected:
                    self.input_text = self.input_text[:-1]
                elif self.selected is None:
                    if e.key == pygame.K_q:
                        self.running = False
                    elif e.key == pygame.K_t:
                        self.catch_from_last_file()
                    elif e.key == pygame.K_r:
                        self.load_roster()
                        self.notify("roster reloaded", "good")
                    elif e.key == pygame.K_c:
                        b = backends.refresh()
                        self.notify(b.summary(), "good" if b.claude or b.ollama else "bad", 4)
                    elif e.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()

    def handle_jobs(self):
        for kind, p in jobs.drain():
            if kind == "status":
                self.status = p["text"]
            elif kind == "catch_done":
                data = p["critter"]
                try:
                    c = Critter(data, self.walkable,
                                pos=(self.walkable.centerx, self.walkable.centery))
                    self.critters.append(c)
                    c.say(data.get("greeting", "Hi!"), seconds=6)
                    self.notify(f"{data['name']} the {data['species']} joined!", "good", 4)
                except Exception as ex:      # noqa: BLE001
                    self.notify(f"sprite failed: {ex}", "bad", 5)
                self.catching = False
                self.status = ""
            elif kind == "catch_failed":
                self.notify(p["message"][:70], "bad", 5)
                self.catching = False
                self.status = ""
            elif kind == "reply":
                for c in self.critters:
                    if c.data["id"] == p["cid"]:
                        c.say(p["text"])
                        if self.selected is c:
                            self.awaiting_reply = False
                        break
            elif kind == "error":
                self.notify(p["message"][:70], "bad", 5)
                self.catching = False
                self.awaiting_reply = False

    # ------------------------------------------------------------------ frame
    def update_preview(self):
        if self.camera is None or cv2 is None:
            return
        self._preview_tick += 1
        if self._preview_tick % 3:          # ~20 Hz preview is plenty
            return
        frame = self.camera.read()
        if frame is None:
            return
        small = cv2.resize(frame, (236, 133), interpolation=cv2.INTER_AREA)
        self._preview = np.ascontiguousarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))

    def draw(self, dt, t):
        s = self.screen
        s.blit(self.bg, (0, 0))

        order = sorted(self.critters, key=lambda c: c.y)
        self.hitboxes.clear()
        for c in order:
            r = c.draw(s, selected=(c is self.selected))
            self.hitboxes[id(c)] = r

        for c in order:                     # bubbles above everyone
            top = c.y - c.size + 6
            if c.thinking:
                ui.thinking_bubble(s, c.x, top, t)
            elif c.bubble and (c.bubble_until == 0 or t < c.bubble_until):
                ui.speech_bubble(s, c.x, top, c.bubble, name=c.name)
            elif c.bubble and c.bubble_until and t >= c.bubble_until:
                c.bubble = None

        ui.camera_panel(s, self._preview,
                        busy_text=(self.status or "working...") if self.catching else None)

        hint = ("point the camera at something alive, then press SPACE"
                if not self.catching else self.status)
        ui.chat_bar(s, self.selected, self.input_text,
                    caret_on=(int(t * 2) % 2 == 0),
                    busy=self.awaiting_reply, hint=hint)

        if t < self.toast_until:
            ui.toast(s, self.toast_msg, tone=self.toast_tone)

        b = backends.CURRENT
        mode = "claude" if b.claude else ("local + ollama" if b.ollama else "local only")
        cnt = ui.font(15).render(
            f"{len(self.critters)} on the farm   ·   {mode}", True, (240, 236, 220))
        s.blit(cnt, (22, self.play_h - 26))
        pygame.display.flip()

    # ------------------------------------------------------------------ loop
    def run(self):
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            t = pygame.time.get_ticks() / 1000.0
            self.handle_events()
            self.handle_jobs()
            self.update_preview()
            for c in self.critters:
                c.update(dt, frozen=(c is self.selected))
            self.draw(dt, t)
        pygame.quit()
