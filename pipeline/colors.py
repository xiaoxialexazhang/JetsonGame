"""Stage 2 -- the two dominant colours of the animal.

Pure numpy k-means over the cropped subject, with two bits of cleverness:
  * pixels near the crop border are sampled as a "background reference" and any
    cluster that looks like the background gets demoted,
  * clusters are ranked by population * vividness so a big flat wall doesn't
    beat the actual animal.
"""
from __future__ import annotations

import colorsys

import numpy as np
from PIL import Image


# ---------------------------------------------------------------- helpers
def hex_of(rgb) -> str:
    r, g, b = (int(max(0, min(255, c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_of(hexstr: str):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def name_color(rgb) -> str:
    """Rough human-readable name -- only used to make the art prompt readable."""
    r, g, b = [c / 255 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hdeg = h * 360
    # near-black reads as black long before v hits 0, as long as it isn't a
    # deep saturated colour like navy or maroon
    if v < 0.16 or (v < 0.24 and s < 0.40):
        return "black"
    if v > 0.90 and s < 0.10:
        return "white"
    # warm low-saturation tones are fur colours, not greys -- test them first
    if s < 0.45 and 14 <= hdeg <= 60:
        return "cream" if v > 0.78 else ("tan" if v > 0.5 else "brown")
    # any dark warm hue reads as brown to a human, however saturated it measures
    if 10 <= hdeg <= 45 and v < 0.62:
        return "brown" if v < 0.45 else "chestnut brown"
    if s < 0.11:
        return "light grey" if v > 0.6 else "grey"
    if hdeg < 12 or hdeg >= 344:
        return "red"
    if hdeg < 32:
        return "rust orange" if v < 0.72 else "orange"
    if hdeg < 46:
        return "golden orange"
    if hdeg < 66:
        return "yellow"
    if hdeg < 160:
        return "green"
    if hdeg < 200:
        return "teal"
    if hdeg < 250:
        return "blue"
    if hdeg < 290:
        return "purple"
    return "pink"


# ---------------------------------------------------------------- k-means
def _kmeans(pix: np.ndarray, k: int = 5, iters: int = 18, seed: int = 7):
    rng = np.random.default_rng(seed)
    # k-means++ style seeding, cheap version
    centers = pix[rng.choice(len(pix), size=1)]
    for _ in range(k - 1):
        d = ((pix[:, None, :] - centers[None, :, :]) ** 2).sum(-1).min(1)
        probs = d / max(d.sum(), 1e-9)
        centers = np.vstack([centers, pix[rng.choice(len(pix), p=probs)]])

    labels = np.zeros(len(pix), dtype=int)
    for _ in range(iters):
        d = ((pix[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        new = d.argmin(1)
        if (new == labels).all():
            break
        labels = new
        for i in range(k):
            m = labels == i
            if m.any():
                centers[i] = pix[m].mean(0)
    return centers, labels


def _vividness(rgb) -> float:
    r, g, b = [c / 255 for c in rgb]
    _, s, v = colorsys.rgb_to_hsv(r, g, b)
    # very dark and very washed-out colours are usually shadow / wall
    return 0.35 + 0.65 * s + 0.30 * min(v, 0.85)


def dominant_pair(img_path, bbox=None, k: int = 5):
    """bbox = (x0,y0,x1,y1) normalised 0-1 from the vision stage, or None.
    Returns (hex1, hex2, name1, name2)."""
    im = Image.open(img_path).convert("RGB")
    W, H = im.size

    if bbox:
        x0, y0, x1, y1 = bbox
        # pad slightly, then clamp
        pad = 0.02
        box = (
            int(max(0, (x0 - pad)) * W), int(max(0, (y0 - pad)) * H),
            int(min(1, (x1 + pad)) * W), int(min(1, (y1 + pad)) * H),
        )
        if box[2] - box[0] > 8 and box[3] - box[1] > 8:
            im = im.crop(box)

    im.thumbnail((160, 160))
    a = np.asarray(im, dtype=np.float64)
    h, w, _ = a.shape

    # background reference = the outer 8% ring of the crop
    ring = max(1, int(min(h, w) * 0.08))
    border = np.concatenate([
        a[:ring].reshape(-1, 3), a[-ring:].reshape(-1, 3),
        a[:, :ring].reshape(-1, 3), a[:, -ring:].reshape(-1, 3),
    ])
    bg = border.mean(0)

    # centre-weighted sample: the animal is in the middle of the crop
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h / 2, w / 2
    dist = np.sqrt(((yy - cy) / cy) ** 2 + ((xx - cx) / cx) ** 2)
    keep = (dist < 0.95).reshape(-1)
    pix = a.reshape(-1, 3)[keep]
    if len(pix) < k * 4:
        pix = a.reshape(-1, 3)

    centers, labels = _kmeans(pix, k=k)

    scored = []
    for i, c in enumerate(centers):
        share = float((labels == i).mean())
        if share < 0.02:
            continue
        bg_dist = float(np.linalg.norm(c - bg))
        bg_penalty = 0.30 if bg_dist < 42 else 1.0     # looks like the backdrop
        scored.append((share * _vividness(c) * bg_penalty, share, tuple(c)))

    scored.sort(reverse=True, key=lambda t: t[0])
    if not scored:
        scored = [(1, 1, (180, 150, 120)), (0.5, 0.5, (90, 70, 55))]

    c1 = scored[0][2]
    # second colour must be visibly different from the first
    c2 = None
    for _s, _sh, c in scored[1:]:
        if np.linalg.norm(np.array(c) - np.array(c1)) > 34:
            c2 = c
            break
    if c2 is None:
        # nothing distinct -> derive a darker companion tone
        c2 = tuple(v * 0.55 for v in c1)

    return hex_of(c1), hex_of(c2), name_color(c1), name_color(c2)
