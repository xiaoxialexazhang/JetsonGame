"""Critters are drawn procedurally from the body plan in species.py — no art assets to ship."""

from __future__ import annotations

import math

import pygame

from .species import SPECIES


def _ellipse(surf, color, cx, cy, rx, ry):
    pygame.draw.ellipse(surf, color, pygame.Rect(cx - rx, cy - ry, rx * 2, ry * 2))


def draw_shadow(surf, x: float, y: float, scale: float) -> None:
    shadow = pygame.Surface((int(70 * scale), int(20 * scale)), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 55), shadow.get_rect())
    surf.blit(shadow, (x - 35 * scale, y + 22 * scale))


def draw_critter(surf, critter, t: float, selected: bool = False) -> None:
    """Draw one critter centred on (critter.x, critter.y)."""
    sp = SPECIES[critter.species_key]
    s = critter.scale
    x, y = critter.x, critter.y
    face = critter.facing
    bob = math.sin(critter._bob) * 1.8 * s
    y += bob

    draw_shadow(surf, x, critter.y, s)

    if selected:
        ring = pygame.Surface((int(110 * s), int(50 * s)), pygame.SRCALPHA)
        pygame.draw.ellipse(ring, (255, 226, 120, 90), ring.get_rect(), width=max(2, int(3 * s)))
        surf.blit(ring, (x - 55 * s, critter.y + 8 * s))

    body, belly, accent = sp.body, sp.belly, sp.accent

    # legs
    leg_w = max(3, int(5 * s))
    for i, off in enumerate((-14, -5, 6, 15)):
        swing = math.sin(critter._bob + i) * 2.5 * s if critter._pause <= 0 else 0
        lx = x + off * s
        pygame.draw.line(surf, accent, (lx, y + 10 * s), (lx + swing, y + 26 * s), leg_w)

    # tail
    if sp.long_tail:
        tail_x = x - 26 * s * face
        curl = math.sin(critter._bob * 0.8) * 6 * s
        pygame.draw.lines(
            surf,
            body,
            False,
            [
                (tail_x, y + 2 * s),
                (tail_x - 12 * s * face, y - 6 * s + curl),
                (tail_x - 16 * s * face, y - 20 * s + curl),
            ],
            max(3, int(5 * s)),
        )
    else:
        _ellipse(surf, body, x - 24 * s * face, y + 2 * s, 6 * s, 6 * s)

    # torso
    _ellipse(surf, body, x, y, 26 * s, 17 * s)
    _ellipse(surf, belly, x, y + 6 * s, 19 * s, 10 * s)

    # head
    hx = x + 20 * s * face
    hy = y - 12 * s
    _ellipse(surf, body, hx, hy, 15 * s, 13 * s)

    # ears
    if sp.pointy_ears:
        for sign in (-1, 1):
            base = (hx + sign * 7 * s, hy - 9 * s)
            pygame.draw.polygon(
                surf,
                body,
                [base, (base[0] + sign * 7 * s, base[1] - 12 * s), (base[0] + sign * 9 * s, base[1] + 1 * s)],
            )
    elif sp.floppy_ears:
        for sign in (-1, 1):
            _ellipse(surf, accent, hx + sign * 12 * s, hy - 1 * s, 5 * s, 9 * s)
    else:
        for sign in (-1, 1):
            _ellipse(surf, accent, hx + sign * 11 * s, hy - 4 * s, 4 * s, 5 * s)

    # horns
    if sp.horns:
        for sign in (-1, 1):
            start = (hx + sign * 6 * s, hy - 10 * s)
            pygame.draw.lines(
                surf,
                (218, 208, 186) if sp.key == "goat" else (200, 196, 188),
                False,
                [start, (start[0] + sign * 4 * s, start[1] - 11 * s), (start[0] - sign * 3 * s, start[1] - 18 * s)],
                max(3, int(4 * s)),
            )

    # muzzle + beard
    mx = hx + 11 * s * face
    _ellipse(surf, belly, mx, hy + 5 * s, 7 * s, 5 * s)
    if sp.beard:
        pygame.draw.polygon(
            surf,
            belly,
            [
                (mx - 4 * s, hy + 9 * s),
                (mx + 3 * s, hy + 9 * s),
                (mx - 1 * s, hy + 22 * s),
            ],
        )

    # face
    blink = (math.sin(t * 1.7 + critter._bob) > 0.985)
    eye_x = hx + 5 * s * face
    if blink:
        pygame.draw.line(surf, (30, 26, 24), (eye_x - 3 * s, hy - 2 * s), (eye_x + 3 * s, hy - 2 * s), max(1, int(2 * s)))
    else:
        _ellipse(surf, (30, 26, 24), eye_x, hy - 2 * s, 2.6 * s, 3.0 * s)
        _ellipse(surf, (255, 255, 255), eye_x + 0.9 * s, hy - 3.2 * s, 0.9 * s, 0.9 * s)
    _ellipse(surf, (60, 44, 44), mx + 2 * s * face, hy + 3 * s, 1.8 * s, 1.4 * s)

    if critter.thinking:
        for i in range(3):
            alpha_t = (t * 3 + i * 0.5) % 1.5
            if alpha_t < 1.0:
                r = (2 + i) * s
                _ellipse(surf, (250, 250, 255), hx + (6 + i * 7) * s * face, hy - (20 + i * 8) * s, r, r)


def draw_badge(surf, species_key: str, rect: pygame.Rect) -> None:
    """A small square species emblem, used in the roster strip."""
    sp = SPECIES[species_key]
    pygame.draw.rect(surf, (46, 52, 46), rect, border_radius=8)
    cx, cy = rect.centerx, rect.centery + 2
    _ellipse(surf, sp.body, cx, cy + 3, 11, 8)
    _ellipse(surf, sp.body, cx + 8, cy - 5, 7, 6)
    if sp.horns:
        for sign in (-1, 1):
            pygame.draw.line(surf, (216, 208, 190), (cx + 8 + sign * 3, cy - 10), (cx + 8 + sign * 6, cy - 16), 2)
    if sp.pointy_ears:
        for sign in (-1, 1):
            pygame.draw.polygon(
                surf, sp.body, [(cx + 8 + sign * 3, cy - 9), (cx + 8 + sign * 6, cy - 15), (cx + 8 + sign * 7, cy - 8)]
            )
