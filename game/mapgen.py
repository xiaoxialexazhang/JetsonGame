"""Static Stardew-ish farm background, drawn once into a Surface at startup."""
from __future__ import annotations

import math
import random

import pygame

import config as C

FLOWERS = [(246, 232, 96), (250, 250, 250), (238, 150, 190), (150, 190, 250)]


def _grass_tile(rng, size):
    s = pygame.Surface((size, size))
    base = rng.choice([C.GRASS_A, C.GRASS_A, C.GRASS_A, C.GRASS_B, C.GRASS_C])
    s.fill(base)
    # little tufts -- 2px darker marks, the classic Stardew grass texture
    for _ in range(rng.randint(1, 3)):
        x, y = rng.randrange(size - 3), rng.randrange(size - 3)
        d = tuple(max(0, c - 22) for c in base)
        pygame.draw.rect(s, d, (x, y, 2, 1))
        pygame.draw.rect(s, d, (x + 1, y + 1, 1, 2))
    if rng.random() < 0.035:
        x, y = rng.randrange(4, size - 6), rng.randrange(4, size - 6)
        col = rng.choice(FLOWERS)
        pygame.draw.rect(s, col, (x, y, 2, 2))
        pygame.draw.rect(s, tuple(max(0, c - 60) for c in col), (x, y + 2, 2, 1))
    return s


def _dirt_tile(rng, size):
    s = pygame.Surface((size, size))
    s.fill(C.DIRT_A if rng.random() < 0.7 else C.DIRT_B)
    for _ in range(rng.randint(2, 5)):
        x, y = rng.randrange(size - 2), rng.randrange(size - 2)
        pygame.draw.rect(s, tuple(max(0, c - 18) for c in C.DIRT_A), (x, y, 2, 1))
    return s


def _blossom_tree(surf, x, y, rng, scale=1.0):
    """Chunky pink-blossom tree like the Stardew spring farm."""
    w = int(84 * scale)
    trunk_w = max(8, int(14 * scale))
    trunk_h = int(34 * scale)
    # canopy: three overlapping blobs
    for (ox, oy, r) in ((-w // 4, -6, w // 3), (w // 4, -6, w // 3), (0, -int(22 * scale), int(w / 2.6))):
        pygame.draw.circle(surf, C.BLOSSOM_D, (x + ox, y - trunk_h + oy + 2), r)
    for (ox, oy, r) in ((-w // 4, -8, w // 3), (w // 4, -8, w // 3), (0, -int(24 * scale), int(w / 2.6))):
        pygame.draw.circle(surf, C.BLOSSOM, (x + ox, y - trunk_h + oy), r)
    # speckles
    for _ in range(int(26 * scale)):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(0, w * 0.42)
        px = int(x + math.cos(a) * d)
        py = int(y - trunk_h - int(10 * scale) + math.sin(a) * d * 0.6)
        pygame.draw.rect(surf, (255, 214, 234), (px, py, 3, 3))
    pygame.draw.rect(surf, C.TRUNK, (x - trunk_w // 2, y - trunk_h, trunk_w, trunk_h))
    pygame.draw.rect(surf, tuple(max(0, c - 30) for c in C.TRUNK),
                     (x - trunk_w // 2, y - trunk_h, 4, trunk_h))
    pygame.draw.ellipse(surf, (86, 132, 48), (x - trunk_w, y - 5, trunk_w * 2, 10))


def _fence_run(surf, x0, y0, x1, y1):
    pygame.draw.line(surf, C.FENCE, (x0, y0 + 6), (x1, y1 + 6), 4)
    pygame.draw.line(surf, C.FENCE, (x0, y0 + 16), (x1, y1 + 16), 4)
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) // 46))
    for i in range(n + 1):
        t = i / n
        px = int(x0 + (x1 - x0) * t)
        py = int(y0 + (y1 - y0) * t)
        pygame.draw.rect(surf, C.FENCE, (px - 3, py, 7, 26))
        pygame.draw.rect(surf, C.FENCE_D, (px - 3, py, 2, 26))
        pygame.draw.rect(surf, C.FENCE_D, (px - 3, py + 24, 7, 2))


def build(width, height, seed=1234) -> tuple[pygame.Surface, pygame.Rect]:
    """Returns (background_surface, walkable_rect)."""
    rng = random.Random(seed)
    bg = pygame.Surface((width, height))
    t = C.TILE

    # path: a soft sine band across the middle
    def on_path(cx, cy):
        band = height * 0.5 + math.sin(cx / 150.0) * height * 0.13
        return abs(cy - band) < 46

    for gy in range(0, height, t):
        for gx in range(0, width, t):
            cx, cy = gx + t / 2, gy + t / 2
            tile = _dirt_tile(rng, t) if on_path(cx, cy) else _grass_tile(rng, t)
            bg.blit(tile, (gx, gy))

    m = 26   # fence margin
    _fence_run(bg, m, m, width - m, m)                       # top
    _fence_run(bg, m, height - m - 26, width - m, height - m - 26)   # bottom
    for yy in range(m, height - m - 26, 46):                 # sides
        pygame.draw.rect(bg, C.FENCE, (m - 3, yy, 7, 26))
        pygame.draw.rect(bg, C.FENCE_D, (m - 3, yy, 2, 26))
        pygame.draw.rect(bg, C.FENCE, (width - m - 3, yy, 7, 26))
        pygame.draw.rect(bg, C.FENCE_D, (width - m - 3, yy, 2, 26))

    for (tx, ty, sc) in ((88, 120, 1.0), (width - 110, 150, 0.85),
                         (150, height - 60, 0.9), (width - 170, height - 46, 1.0),
                         (width // 2 + 60, 104, 0.7)):
        _blossom_tree(bg, tx, ty, rng, sc)

    walkable = pygame.Rect(m + 40, m + 56, width - 2 * (m + 40), height - 2 * (m + 56))
    return bg, walkable
