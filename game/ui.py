"""Speech bubbles, the chat bar, the camera panel, toasts."""
from __future__ import annotations

import pygame

import config as C

_FONTS: dict = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _FONTS:
        try:
            f = pygame.font.SysFont("dejavusansmono,couriernew,monospace", size, bold=bold)
        except Exception:      # noqa: BLE001
            f = pygame.font.Font(None, size)
        _FONTS[key] = f
    return _FONTS[key]


def wrap(text, f, max_w):
    lines, line = [], ""
    for word in str(text).split():
        trial = f"{line} {word}".strip()
        if f.size(trial)[0] <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def panel(surf, rect, fill=C.UI_BG, edge=C.UI_EDGE, radius=8, border=3):
    pygame.draw.rect(surf, fill, rect, border_radius=radius)
    pygame.draw.rect(surf, edge, rect, border, border_radius=radius)


# ---------------------------------------------------------------- bubble
def speech_bubble(surf, cx, bottom_y, text, name=None, max_w=280):
    f = font(18)
    fn = font(15, bold=True)
    lines = wrap(text, f, max_w)
    lh = f.get_height() + 2
    tw = max((f.size(l)[0] for l in lines), default=40)
    pad = 12
    w = min(max_w, tw) + pad * 2
    h = len(lines) * lh + pad * 2 - 2
    if name:
        h += fn.get_height() + 2

    x = int(cx - w / 2)
    y = int(bottom_y - h - 12)
    x = max(8, min(C.SCREEN_W - w - 8, x))
    y = max(8, y)
    rect = pygame.Rect(x, y, w, h)

    shadow = pygame.Surface((w + 6, h + 6), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 70), shadow.get_rect(), border_radius=10)
    surf.blit(shadow, (x - 1, y + 4))

    pygame.draw.rect(surf, C.CREAM, rect, border_radius=10)
    pygame.draw.rect(surf, C.INK, rect, 3, border_radius=10)

    # tail
    tip_x = int(max(rect.left + 16, min(rect.right - 16, cx)))
    pts = [(tip_x - 9, rect.bottom - 2), (tip_x + 9, rect.bottom - 2), (tip_x, rect.bottom + 12)]
    pygame.draw.polygon(surf, C.CREAM, pts)
    pygame.draw.line(surf, C.INK, pts[0], pts[2], 3)
    pygame.draw.line(surf, C.INK, pts[1], pts[2], 3)

    ty = y + pad - 2
    if name:
        surf.blit(fn.render(name, True, (150, 82, 46)), (x + pad, ty))
        ty += fn.get_height() + 2
    for line in lines:
        surf.blit(f.render(line, True, C.INK), (x + pad, ty))
        ty += lh
    return rect


def thinking_bubble(surf, cx, bottom_y, t):
    dots = "." * (1 + int(t * 3) % 3)
    return speech_bubble(surf, cx, bottom_y, dots, max_w=60)


# ---------------------------------------------------------------- chat bar
def chat_bar(surf, critter, buffer_text, caret_on, busy, hint):
    r = pygame.Rect(0, C.SCREEN_H - C.CHAT_BAR_H, C.SCREEN_W, C.CHAT_BAR_H)
    pygame.draw.rect(surf, C.UI_BG, r)
    pygame.draw.line(surf, C.UI_EDGE, (0, r.top), (C.SCREEN_W, r.top), 3)

    f = font(20)
    fs = font(15)
    x = 16

    if critter is not None:
        port = pygame.Rect(x, r.top + 14, 76, 76)
        panel(surf, port, fill=C.UI_BG2, radius=6, border=2)
        img = pygame.transform.scale(critter.base_img, (64, 64))
        surf.blit(img, (port.x + 6, port.y + 6))
        x = port.right + 14
        surf.blit(font(19, bold=True).render(critter.name, True, C.UI_EDGE), (x, r.top + 12))
        sub = f"{critter.data['color1']} {critter.data['species']}"
        surf.blit(fs.render(sub, True, (176, 152, 120)), (x, r.top + 34))

        box = pygame.Rect(x, r.top + 56, C.SCREEN_W - x - 20, 40)
        panel(surf, box, fill=(34, 25, 21), radius=6, border=2)
        if busy:
            surf.blit(f.render(f"{critter.name} is thinking...", True, (150, 130, 105)),
                      (box.x + 12, box.y + 9))
        else:
            shown = buffer_text or ""
            txt = f.render(shown, True, C.CREAM)
            # keep the caret visible on long input
            off = max(0, txt.get_width() - (box.w - 32))
            surf.blit(txt, (box.x + 12 - off, box.y + 9))
            if caret_on:
                cx = box.x + 12 + txt.get_width() - off
                pygame.draw.rect(surf, C.CREAM, (cx + 2, box.y + 10, 2, 20))
            if not shown:
                surf.blit(f.render("say something...", True, (110, 92, 76)),
                          (box.x + 14, box.y + 9))
    else:
        surf.blit(font(21, bold=True).render(hint, True, C.UI_EDGE), (x, r.top + 30))
        surf.blit(fs.render(
            "SPACE catch what the camera sees   ·   click a critter to talk   ·   "
            "ESC step away   ·   C recheck network   ·   Q quit",
            True, (176, 152, 120)), (x, r.top + 62))
    return r


# ---------------------------------------------------------------- camera
def camera_panel(surf, frame_rgb, w=248, busy_text=None):
    h = int(w * 9 / 16)
    r = pygame.Rect(C.SCREEN_W - w - 18, 18, w, h + 30)
    panel(surf, r, fill=C.UI_BG, radius=8, border=3)
    inner = pygame.Rect(r.x + 6, r.y + 6, w - 12, h - 6)

    if frame_rgb is not None:
        img = pygame.image.frombuffer(frame_rgb.tobytes(), frame_rgb.shape[1::-1], "RGB")
        surf.blit(pygame.transform.smoothscale(img, inner.size), inner)
    else:
        pygame.draw.rect(surf, (24, 20, 18), inner)
        surf.blit(font(15).render("no camera", True, (150, 120, 100)),
                  (inner.x + 10, inner.centery - 8))
    pygame.draw.rect(surf, (24, 18, 16), inner, 2)

    label = busy_text or "SPACE  ·  catch it"
    col = (255, 214, 120) if busy_text else C.UI_EDGE
    surf.blit(font(16, bold=True).render(label, True, col), (r.x + 8, r.bottom - 24))
    return r


# ---------------------------------------------------------------- toast
def toast(surf, text, y=None, tone="info"):
    f = font(19, bold=True)
    t = f.render(text, True, C.CREAM)
    w, h = t.get_width() + 28, t.get_height() + 16
    x = (C.SCREEN_W - w) // 2
    y = 22 if y is None else y
    r = pygame.Rect(x, y, w, h)
    bg = {"info": (44, 36, 60), "bad": (96, 40, 40), "good": (46, 78, 46)}[tone]
    pygame.draw.rect(surf, bg, r, border_radius=8)
    pygame.draw.rect(surf, C.UI_EDGE, r, 2, border_radius=8)
    surf.blit(t, (x + 14, y + 8))
