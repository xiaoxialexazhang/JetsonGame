"""A critter on the map: wanders slowly, hops a little, can be clicked."""
from __future__ import annotations

import math
import random

import pygame

import config as C


class Critter:
    def __init__(self, data: dict, walkable: pygame.Rect, pos=None):
        self.data = data
        self.name = data["name"]
        self.walkable = walkable

        path = C.ROOT / data["sprite"]
        img = pygame.image.load(str(path)).convert_alpha()
        # The PNG on disk is SPRITE_PX * SPRITE_SCALE. Go back down to the true
        # 32x32 logical grid first (an exact integer decimation), then back up by
        # a whole number -- otherwise the pixel art gets resampled into mush.
        img = pygame.transform.scale(img, (C.SPRITE_PX, C.SPRITE_PX))
        n = max(C.SPRITE_PX, (C.DRAW_SIZE // C.SPRITE_PX) * C.SPRITE_PX)
        self.base_img = pygame.transform.scale(img, (n, n))
        self.flipped = pygame.transform.flip(self.base_img, True, False)
        self.size = n

        if pos is None:
            pos = (random.uniform(walkable.left, walkable.right),
                   random.uniform(walkable.top, walkable.bottom))
        self.x, self.y = float(pos[0]), float(pos[1])
        self.target = None
        self.idle_for = random.uniform(0, C.IDLE_MAX)
        self.facing = 1
        self.phase = random.uniform(0, math.tau)
        self.moving = False

        self.bubble = None          # str | None
        self.bubble_until = 0.0
        self.thinking = False
        self.spawn_t = 0.0          # 0 -> 1 pop-in animation

    # ------------------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        n = self.size
        return pygame.Rect(int(self.x - n / 2), int(self.y - n + 8), n, n)

    def say(self, text, seconds=None):
        self.bubble = text
        self.thinking = False
        self.bubble_until = 0.0 if seconds is None else (pygame.time.get_ticks() / 1000 + seconds)

    def think(self):
        self.thinking = True
        self.bubble = None

    def hush(self):
        self.bubble = None
        self.thinking = False

    # ------------------------------------------------------------------
    def _pick_target(self):
        w = self.walkable
        for _ in range(8):
            tx = random.uniform(w.left, w.right)
            ty = random.uniform(w.top, w.bottom)
            if math.hypot(tx - self.x, ty - self.y) > 70:
                self.target = (tx, ty)
                return
        self.target = (random.uniform(w.left, w.right), random.uniform(w.top, w.bottom))

    def update(self, dt, frozen=False):
        self.spawn_t = min(1.0, self.spawn_t + dt * 2.2)
        if frozen:                       # stand still while being talked to
            self.moving = False
            return

        if self.target is None:
            self.idle_for -= dt
            if self.idle_for <= 0:
                self._pick_target()
            self.moving = False
            return

        tx, ty = self.target
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 3:
            self.target = None
            self.idle_for = random.uniform(C.IDLE_MIN, C.IDLE_MAX)
            self.moving = False
            return

        step = C.WALK_SPEED * dt
        self.x += dx / dist * step
        self.y += dy / dist * step
        if abs(dx) > 1.5:
            self.facing = 1 if dx > 0 else -1
        self.moving = True
        self.phase += dt * 7.0

    # ------------------------------------------------------------------
    def draw(self, surf, selected=False, hovered=False):
        n = self.size
        hop = int(abs(math.sin(self.phase)) * 3) if self.moving else 0
        pop = self.spawn_t
        ease = 1 - (1 - pop) ** 3
        scale = 0.55 + 0.45 * ease if pop < 1 else 1.0

        # shadow -- grounds the sprite, straight out of the sticker sheet
        sw = int(n * 0.52 * scale)
        sh = max(4, int(n * 0.17 * scale))
        shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (30, 60, 20, 90), shadow.get_rect())
        surf.blit(shadow, (int(self.x - sw / 2), int(self.y - sh / 2 + 2)))

        img = self.base_img if self.facing >= 0 else self.flipped
        if scale < 1.0:
            s = max(8, int(n * scale))
            img = pygame.transform.scale(img, (s, s))

        w, h = img.get_size()
        pos = (int(self.x - w / 2), int(self.y - h + 6 - hop))

        if selected or hovered:
            ring = pygame.Surface((w + 14, 16), pygame.SRCALPHA)
            col = (255, 244, 180, 200) if selected else (255, 255, 255, 90)
            pygame.draw.ellipse(ring, col, ring.get_rect(), 3)
            surf.blit(ring, (int(self.x - (w + 14) / 2), int(self.y - 8)))

        surf.blit(img, pos)
        return pygame.Rect(pos[0], pos[1], w, h)
