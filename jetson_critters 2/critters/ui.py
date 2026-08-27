"""All rendering: the sanctuary view, the camera HUD, and the chat panel."""

from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple

import numpy as np
import pygame

from .species import SPECIES
from .sprites import draw_badge, draw_critter

# palette
BG = (26, 30, 28)
PANEL = (36, 42, 39)
PANEL_EDGE = (58, 68, 62)
GRASS_TOP = (74, 108, 74)
GRASS_BOT = (52, 82, 56)
TEXT = (226, 232, 226)
MUTED = (146, 158, 148)
ACCENT = (146, 208, 128)
WARN = (232, 176, 96)
BAD = (222, 118, 106)
USER_BUBBLE = (62, 78, 96)
CRITTER_BUBBLE = (52, 62, 54)


def font(size: int, bold: bool = False) -> pygame.font.Font:
    for name in ("dejavusans", "arial", "freesans"):
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f:
                return f
        except Exception:
            continue
    return pygame.font.Font(None, size)


def wrap(text: str, fnt: pygame.font.Font, max_w: int) -> List[str]:
    lines: List[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        words, cur = para.split(" "), ""
        for w in words:
            trial = w if not cur else f"{cur} {w}"
            if fnt.size(trial)[0] <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                # hard-break a single over-long word
                while fnt.size(w)[0] > max_w and len(w) > 1:
                    cut = len(w)
                    while cut > 1 and fnt.size(w[:cut])[0] > max_w:
                        cut -= 1
                    lines.append(w[:cut])
                    w = w[cut:]
                cur = w
        lines.append(cur)
    return lines


def frame_to_surface(frame_bgr: np.ndarray, size: Tuple[int, int]) -> pygame.Surface:
    rgb = frame_bgr[:, :, ::-1]
    surf = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
    return pygame.transform.smoothscale(surf, size)


class Ui:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        w, h = screen.get_size()

        self.f_title = font(22, bold=True)
        self.f_head = font(16, bold=True)
        self.f_body = font(15)
        self.f_small = font(13)
        self.f_tiny = font(11)

        right_w = 400
        margin = 12
        header_h = 52
        self.header = pygame.Rect(0, 0, w, header_h)
        self.world_rect = pygame.Rect(
            margin, header_h + margin, w - right_w - margin * 3, h - header_h - margin * 2
        )
        rx = self.world_rect.right + margin
        cam_h = int(right_w * 9 / 16) + 46
        self.cam_rect = pygame.Rect(rx, header_h + margin, right_w, cam_h)
        self.chat_rect = pygame.Rect(
            rx, self.cam_rect.bottom + margin, right_w, h - self.cam_rect.bottom - margin * 2
        )
        self.input_rect = pygame.Rect(
            self.chat_rect.x + 10, self.chat_rect.bottom - 44, self.chat_rect.w - 20, 34
        )
        self.log_rect = pygame.Rect(
            self.chat_rect.x + 10,
            self.chat_rect.y + 78,
            self.chat_rect.w - 20,
            self.input_rect.top - (self.chat_rect.y + 78) - 8,
        )
        self.scroll = 0
        self._grass = self._make_grass(self.world_rect.size)

    # -- background -------------------------------------------------------
    def _make_grass(self, size) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface(size)
        for y in range(h):
            t = y / max(h - 1, 1)
            surf.fill(
                (
                    int(GRASS_TOP[0] + (GRASS_BOT[0] - GRASS_TOP[0]) * t),
                    int(GRASS_TOP[1] + (GRASS_BOT[1] - GRASS_TOP[1]) * t),
                    int(GRASS_TOP[2] + (GRASS_BOT[2] - GRASS_TOP[2]) * t),
                ),
                pygame.Rect(0, y, w, 1),
            )
        rng = np.random.default_rng(7)
        for _ in range(420):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            shade = int(rng.integers(-14, 14))
            base = surf.get_at((x, y))
            pygame.draw.line(
                surf,
                (max(0, base[0] + shade), max(0, base[1] + shade), max(0, base[2] + shade)),
                (x, y),
                (x, y + 5),
                1,
            )
        return surf

    def _panel(self, rect: pygame.Rect, title: Optional[str] = None) -> None:
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_EDGE, rect, width=1, border_radius=10)
        if title:
            self.screen.blit(self.f_head.render(title, True, TEXT), (rect.x + 12, rect.y + 10))

    # -- header -----------------------------------------------------------
    def draw_header(
        self, world, recognizer_name: str, chat_status: str, cam_status: str, cam_ok: bool
    ) -> None:
        pygame.draw.rect(self.screen, PANEL, self.header)
        pygame.draw.line(self.screen, PANEL_EDGE, (0, self.header.bottom), (self.header.right, self.header.bottom))
        self.screen.blit(self.f_title.render("Jetson Critters", True, TEXT), (16, 13))

        counts = world.counts()
        x = 190
        for key in SPECIES:
            n = counts.get(key, 0)
            rect = pygame.Rect(x, 10, 32, 32)
            draw_badge(self.screen, key, rect)
            col = TEXT if n else (78, 88, 80)
            self.screen.blit(self.f_tiny.render(str(n), True, col), (rect.right - 6, rect.bottom - 12))
            x += 44

        def chip(label: str, ok: bool, xpos: int) -> int:
            col = ACCENT if ok else BAD
            surf = self.f_small.render(label, True, col)
            self.screen.blit(surf, (xpos, 19))
            return xpos + surf.get_width() + 18

        rx = x + 24
        rx = chip(f"cam: {cam_status}", cam_ok, rx)
        rx = chip(f"vision: {recognizer_name}", "stub" not in recognizer_name, rx)
        chip(f"llm: {chat_status}", chat_status.startswith("ready"), rx)

    # -- world ------------------------------------------------------------
    def draw_world(self, world, t: float) -> None:
        self.screen.blit(self._grass, self.world_rect.topleft)
        pygame.draw.rect(self.screen, PANEL_EDGE, self.world_rect, width=1, border_radius=10)

        if not world.critters:
            msg = "No critters yet — point the camera at an animal."
            sub = "A cat or a goat works. Hold steady until the capture ring fills."
            m = self.f_head.render(msg, True, (238, 244, 236))
            s = self.f_small.render(sub, True, (206, 218, 204))
            self.screen.blit(m, m.get_rect(center=(self.world_rect.centerx, self.world_rect.centery - 12)))
            self.screen.blit(s, s.get_rect(center=(self.world_rect.centerx, self.world_rect.centery + 14)))

        for critter in sorted(world.critters, key=lambda c: c.y):
            draw_critter(self.screen, critter, t, selected=(critter.id == world.selected_id))
            label = self.f_tiny.render(critter.name, True, (245, 248, 244))
            bg = pygame.Surface((label.get_width() + 10, label.get_height() + 4), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 110), bg.get_rect(), border_radius=6)
            pos = (critter.x - bg.get_width() / 2, critter.y + 30 * critter.scale)
            self.screen.blit(bg, pos)
            self.screen.blit(label, (pos[0] + 5, pos[1] + 2))

        if world.toast:
            text, ts = world.toast
            age = time.time() - ts
            if age < 3.5:
                alpha = 255 if age < 2.5 else int(255 * (1 - (age - 2.5)))
                surf = self.f_head.render(text, True, (30, 34, 30))
                pad = pygame.Surface((surf.get_width() + 28, surf.get_height() + 16), pygame.SRCALPHA)
                pygame.draw.rect(pad, (*ACCENT, alpha), pad.get_rect(), border_radius=10)
                pad.blit(surf, (14, 8))
                pad.set_alpha(alpha)
                self.screen.blit(pad, (self.world_rect.centerx - pad.get_width() / 2, self.world_rect.y + 20))
            else:
                world.toast = None

    # -- camera -----------------------------------------------------------
    def draw_camera(self, frame, worker, cam_error: Optional[str], cooldown_left: float) -> None:
        self._panel(self.cam_rect, "Camera")
        view = pygame.Rect(self.cam_rect.x + 10, self.cam_rect.y + 36, self.cam_rect.w - 20, int((self.cam_rect.w - 20) * 9 / 16))

        if frame is not None:
            self.screen.blit(frame_to_surface(frame, view.size), view.topleft)
        else:
            pygame.draw.rect(self.screen, (22, 26, 24), view, border_radius=6)
            msg = cam_error or "waiting for frames…"
            for i, line in enumerate(wrap(msg, self.f_small, view.w - 24)):
                surf = self.f_small.render(line, True, MUTED)
                self.screen.blit(surf, (view.x + 12, view.centery - 10 + i * 18))
        pygame.draw.rect(self.screen, PANEL_EDGE, view, width=1, border_radius=6)

        det = worker.latest if worker else None
        y = view.bottom + 8
        if det is not None:
            label = f"{det.display}  ·  {det.raw_label}  {det.confidence:.0%}"
            colour = ACCENT if det.confidence >= worker.threshold else WARN
        else:
            label = "nothing recognised"
            colour = MUTED
        self.screen.blit(self.f_small.render(label, True, colour), (view.x, y))

        # capture progress ring / bar
        bar = pygame.Rect(view.x, y + 20, view.w, 6)
        pygame.draw.rect(self.screen, (28, 32, 30), bar, border_radius=3)
        prog = worker.progress() if worker else 0.0
        if cooldown_left > 0:
            pygame.draw.rect(self.screen, (70, 78, 72), pygame.Rect(bar.x, bar.y, bar.w, bar.h), border_radius=3)
            self.screen.blit(
                self.f_tiny.render(f"cooldown {cooldown_left:.0f}s", True, MUTED), (bar.x, bar.bottom + 4)
            )
        elif prog > 0:
            pygame.draw.rect(
                self.screen, ACCENT, pygame.Rect(bar.x, bar.y, int(bar.w * min(prog, 1.0)), bar.h), border_radius=3
            )
            self.screen.blit(self.f_tiny.render("hold steady…", True, ACCENT), (bar.x, bar.bottom + 4))

    # -- chat -------------------------------------------------------------
    def draw_chat(self, critter, input_text: str, focused: bool, t: float) -> None:
        self._panel(self.chat_rect)

        if critter is None:
            self.screen.blit(self.f_head.render("Nobody selected", True, TEXT), (self.chat_rect.x + 12, self.chat_rect.y + 10))
            hint = "Click a critter in the sanctuary to talk to it."
            self.screen.blit(self.f_small.render(hint, True, MUTED), (self.chat_rect.x + 12, self.chat_rect.y + 38))
            return

        sp = critter.species
        self.screen.blit(self.f_head.render(critter.name, True, TEXT), (self.chat_rect.x + 12, self.chat_rect.y + 10))
        sub = f"{sp.display} · {critter.trait}"
        for i, line in enumerate(wrap(sub, self.f_tiny, self.chat_rect.w - 24)[:2]):
            self.screen.blit(self.f_tiny.render(line, True, MUTED), (self.chat_rect.x + 12, self.chat_rect.y + 34 + i * 14))
        pygame.draw.line(
            self.screen,
            PANEL_EDGE,
            (self.chat_rect.x + 10, self.chat_rect.y + 70),
            (self.chat_rect.right - 10, self.chat_rect.y + 70),
        )

        # build bubbles bottom-up so the newest message is always visible
        max_w = self.log_rect.w - 40
        blocks = []
        for msg in critter.history:
            lines = wrap(msg.text, self.f_body, max_w)
            h = len(lines) * 19 + 14
            blocks.append((msg.role, lines, h))
        if critter.thinking:
            dots = "." * (1 + int(t * 2) % 3)
            blocks.append(("assistant", [dots], 33))

        total = sum(b[2] + 8 for b in blocks)
        max_scroll = max(0, total - self.log_rect.h)
        self.scroll = min(self.scroll, max_scroll)
        y = self.log_rect.y - self.scroll + (self.log_rect.h - total if total < self.log_rect.h else 0)

        clip = self.screen.get_clip()
        self.screen.set_clip(self.log_rect)
        for role, lines, h in blocks:
            width = min(max_w, max((self.f_body.size(l)[0] for l in lines), default=20)) + 20
            if role == "user":
                rect = pygame.Rect(self.log_rect.right - width, y, width, h)
                colour, fg = USER_BUBBLE, TEXT
            else:
                rect = pygame.Rect(self.log_rect.x, y, width, h)
                colour, fg = CRITTER_BUBBLE, (222, 236, 220)
            if rect.bottom > self.log_rect.y and rect.y < self.log_rect.bottom:
                pygame.draw.rect(self.screen, colour, rect, border_radius=10)
                for i, line in enumerate(lines):
                    self.screen.blit(self.f_body.render(line, True, fg), (rect.x + 10, rect.y + 7 + i * 19))
            y += h + 8
        self.screen.set_clip(clip)

        # input box
        pygame.draw.rect(self.screen, (24, 28, 26), self.input_rect, border_radius=8)
        pygame.draw.rect(
            self.screen, ACCENT if focused else PANEL_EDGE, self.input_rect, width=1, border_radius=8
        )
        shown = input_text
        while self.f_body.size(shown)[0] > self.input_rect.w - 22 and shown:
            shown = shown[1:]
        if shown:
            self.screen.blit(self.f_body.render(shown, True, TEXT), (self.input_rect.x + 10, self.input_rect.y + 8))
        elif not focused:
            self.screen.blit(
                self.f_small.render("click here, then type · Enter to send", True, MUTED),
                (self.input_rect.x + 10, self.input_rect.y + 9),
            )
        if focused and math.sin(t * 6) > 0:
            cx = self.input_rect.x + 10 + self.f_body.size(shown)[0] + 1
            pygame.draw.line(self.screen, TEXT, (cx, self.input_rect.y + 7), (cx, self.input_rect.bottom - 7))
