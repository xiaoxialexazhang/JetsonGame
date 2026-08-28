"""Rasteriser: shape-primitive JSON  ->  Stardew-style pixel-art PNG.

Claude only has to think about anatomy (an ellipse body, two triangle ears,
four little leg rects, two dot eyes). Everything that makes it *look* like
Stardew -- the palette ramps, the chunky dark outline, the low resolution --
is handled here in code, so the art style stays consistent no matter what the
model returns.
"""
from __future__ import annotations

import colorsys

import numpy as np
from PIL import Image, ImageDraw

import config
from pipeline.colors import rgb_of

# The keys Claude is allowed to use as a fill.
PALETTE_KEYS = [
    "base", "shade", "light",
    "accent", "accent_shade", "accent_light",
    "outline", "dark", "eye", "eye_hl", "white", "cream", "pink", "hoof",
]


# ---------------------------------------------------------------- palette
def _shift(rgb, v_mul, s_mul, v_add=0.0):
    r, g, b = [c / 255 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = max(0.0, min(1.0, s * s_mul))
    v = max(0.0, min(1.0, v * v_mul + v_add))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def build_palette(color1_hex: str, color2_hex: str) -> dict:
    """Turn the two measured colours into a full Stardew-ish ramp."""
    base = rgb_of(color1_hex)
    accent = rgb_of(color2_hex)

    # Guarantee the base is never so dark that shading vanishes.
    if sum(base) < 110:
        base = _shift(base, 1.0, 1.0, v_add=0.16)

    pal = {
        "base": base,
        "shade": _shift(base, 0.66, 1.18),
        "light": _shift(base, 1.20, 0.70, v_add=0.06),
        "accent": accent,
        "accent_shade": _shift(accent, 0.66, 1.18),
        "accent_light": _shift(accent, 1.20, 0.70, v_add=0.06),
        # Stardew outlines are a very dark, slightly warm version of the fill
        "outline": _shift(base, 0.30, 1.05),
        "dark": (46, 32, 30),
        "eye": (38, 26, 26),
        "eye_hl": (255, 255, 255),
        "white": (250, 248, 240),
        "cream": (246, 232, 200),
        "pink": (240, 150, 162),
        "hoof": (74, 54, 44),
    }
    # keep the outline readable even for near-black animals
    if sum(pal["outline"]) > 200:
        pal["outline"] = _shift(pal["outline"], 0.55, 1.1)
    if sum(pal["outline"]) < 45:
        pal["outline"] = (26, 18, 20)
    return pal


# ---------------------------------------------------------------- drawing
def _fill(pal, key):
    return pal.get(str(key).lower().strip(), pal["base"])


def _mirror_x(pts, n):
    return [(n - 1 - x, y) for x, y in pts]


def _draw_shape(d: ImageDraw.ImageDraw, s: dict, pal: dict, n: int, mirror=False):
    kind = str(s.get("shape", s.get("type", "ellipse"))).lower()
    col = _fill(pal, s.get("fill", "base"))

    def mx(x):
        return (n - 1 - x) if mirror else x

    if kind in ("ellipse", "circle", "oval"):
        if "cx" in s:
            cx, cy = float(s["cx"]), float(s["cy"])
            rx = float(s.get("rx", s.get("r", 4)))
            ry = float(s.get("ry", s.get("r", rx)))
            x0, y0, x1, y1 = cx - rx, cy - ry, cx + rx, cy + ry
        else:
            x0, y0 = float(s.get("x", 0)), float(s.get("y", 0))
            x1, y1 = x0 + float(s.get("w", 4)), y0 + float(s.get("h", 4))
        if mirror:
            x0, x1 = mx(x1), mx(x0)
        d.ellipse([x0, y0, x1, y1], fill=col)

    elif kind in ("rect", "rectangle", "box"):
        x0, y0 = float(s.get("x", 0)), float(s.get("y", 0))
        x1, y1 = x0 + float(s.get("w", 4)) - 1, y0 + float(s.get("h", 4)) - 1
        if mirror:
            x0, x1 = mx(x1), mx(x0)
        d.rectangle([x0, y0, x1, y1], fill=col)

    elif kind in ("poly", "polygon", "triangle"):
        pts = [(float(p[0]), float(p[1])) for p in s.get("points", [])]
        if len(pts) < 3:
            return
        if mirror:
            pts = [(mx(x), y) for x, y in pts]
        d.polygon(pts, fill=col)

    elif kind in ("pixel", "dot", "px"):
        x, y = float(s.get("x", 0)), float(s.get("y", 0))
        w = float(s.get("w", 1)) - 1
        h = float(s.get("h", 1)) - 1
        if mirror:
            x = mx(x + w) if w else mx(x)
        d.rectangle([x, y, x + w, y + h], fill=col)

    elif kind == "line":
        pts = [(float(p[0]), float(p[1])) for p in s.get("points", [])]
        if len(pts) < 2:
            return
        if mirror:
            pts = [(mx(x), y) for x, y in pts]
        d.line(pts, fill=col, width=int(s.get("width", 1)))


def _outline(img: Image.Image, color) -> Image.Image:
    """Grow a 1px dark border around the silhouette -- the single biggest thing
    that makes low-res art read as 'Stardew' rather than 'blurry blob'."""
    a = np.array(img)
    alpha = a[..., 3] > 8
    grown = np.zeros_like(alpha)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        grown |= np.roll(np.roll(alpha, dy, 0), dx, 1)
    ring = grown & ~alpha
    a[ring] = (*color, 255)
    return Image.fromarray(a, "RGBA")


def _trim_and_center(img: Image.Image, n: int) -> Image.Image:
    bb = img.getbbox()
    if not bb:
        return img
    cropped = img.crop(bb)
    w, h = cropped.size
    scale = min((n - 2) / max(w, 1), (n - 2) / max(h, 1), 1.0)
    if scale < 1.0:
        cropped = cropped.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)
        w, h = cropped.size
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    out.paste(cropped, ((n - w) // 2, n - h - 1), cropped)   # feet on the ground
    return out


# ---------------------------------------------------------------- public
def render(spec: dict, color1_hex: str, color2_hex: str, out_path,
           n: int = config.SPRITE_PX, scale: int = config.SPRITE_SCALE) -> str:
    pal = build_palette(color1_hex, color2_hex)

    canvas = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    shapes = spec.get("parts", spec.get("shapes", []))
    shapes = [s for s in shapes if isinstance(s, dict)]
    shapes.sort(key=lambda s: float(s.get("z", 0)))

    for s in shapes:
        if s.get("mirror"):          # draw the mirrored twin first (ears, legs)
            _draw_shape(d, s, pal, n, mirror=True)
        _draw_shape(d, s, pal, n, mirror=False)

    canvas = _trim_and_center(canvas, n)
    canvas = _outline(canvas, pal["outline"])
    canvas = canvas.resize((n * scale, n * scale), Image.NEAREST)
    canvas.save(out_path)
    return str(out_path)


def fallback_spec(species: str) -> dict:
    """If the artist call fails we still put *something* cute on the map:
    a generic Stardew blob-creature with ears, legs, eyes."""
    return {
        "species": species,
        "parts": [
            {"shape": "rect", "x": 9, "y": 24, "w": 4, "h": 6, "fill": "shade", "z": 2, "mirror": True},
            {"shape": "poly", "points": [[8, 11], [11, 2], [15, 12]], "fill": "base", "z": 3, "mirror": True},
            {"shape": "poly", "points": [[10, 11], [12, 6], [14, 12]], "fill": "pink", "z": 4, "mirror": True},
            {"shape": "ellipse", "cx": 16, "cy": 17, "rx": 10, "ry": 9, "fill": "base", "z": 6},
            {"shape": "ellipse", "cx": 16, "cy": 23, "rx": 6, "ry": 4, "fill": "accent", "z": 7},
            {"shape": "ellipse", "cx": 16, "cy": 11, "rx": 7, "ry": 4, "fill": "light", "z": 7},
            {"shape": "pixel", "x": 11, "y": 15, "w": 2, "h": 3, "fill": "eye", "z": 9, "mirror": True},
            {"shape": "pixel", "x": 15, "y": 19, "w": 2, "h": 1, "fill": "pink", "z": 9},
            {"shape": "rect", "x": 15, "y": 26, "w": 2, "h": 4, "fill": "outline", "z": 9},
        ],
    }
