"""Appearance extraction: what colour is this animal, and what colour are its eyes.

The species classifier in vision.py answers *what* the animal is. This module
answers *which one* — coat colours, pattern, and eye colour — so two cats don't
have to look identical.

Three stages, each degrading gracefully if the one above it fails:

  1. Segment the animal out of the background.
     DeepLabV3-MobileNetV3 (torchvision, COCO-with-VOC-labels) when torch is
     available; GrabCut seeded on the centre crop when it isn't.

  2. Coat: k-means the masked pixels in CIELAB, name the dominant clusters.
     Lab because Euclidean distance there is roughly perceptual, and because
     chroma (a,b distance from 128) cleanly separates "grey" from "ginger"
     in a way RGB does not.

  3. Eyes: find small blobs in the upper part of the animal, then score them in
     *pairs*. Pairing is what makes this work on a ginger cat — a saturated
     coat produces one big region, never two small symmetric ones.

This runs once per capture, not once per frame. Budget is ~150 ms, which is
invisible next to the capture toast.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

RGB = Tuple[int, int, int]

# VOC-21 indices that DeepLab uses, for the animals we care about.
# There is no goat or rabbit in VOC; goat reads as sheep, rabbit usually as cat
# or dog. We only need the mask, not the label, so a near-miss is harmless.
VOC_ANIMAL_IDS = {3: "bird", 8: "cat", 10: "cow", 12: "dog", 13: "horse", 17: "sheep"}


# --------------------------------------------------------------------------
# colour naming
# --------------------------------------------------------------------------

# Coat names, tuned for animals rather than paint charts — CSS3 colour names
# will happily tell you a cat is "gainsboro", which helps nobody.
# (name, hue_lo, hue_hi) in degrees; only consulted for chromatic colours.
_COAT_HUES: Sequence[Tuple[str, float, float]] = (
    ("ginger", 10, 45),
    ("golden", 45, 65),
    ("olive", 65, 100),
    ("green", 100, 160),
    ("blue", 160, 260),
    ("lilac", 260, 320),
    ("rust", 320, 360),
    ("rust", 0, 10),
)

_EYE_HUES: Sequence[Tuple[str, float, float]] = (
    ("copper", 5, 35),
    ("amber", 35, 50),
    ("yellow", 50, 70),
    ("hazel", 70, 85),
    ("green", 85, 165),
    ("blue", 165, 265),
    ("violet", 265, 320),
    ("copper", 320, 360),
    ("copper", 0, 5),
)


def _to_hsl(rgb: RGB) -> Tuple[float, float, float]:
    """Return (hue_degrees, saturation_0_1, lightness_0_1)."""
    r, g, b = (v / 255.0 for v in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2.0
    if mx == mn:
        return 0.0, 0.0, light
    d = mx - mn
    sat = d / (2.0 - mx - mn) if light > 0.5 else d / (mx + mn)
    if mx == r:
        hue = ((g - b) / d) % 6
    elif mx == g:
        hue = (b - r) / d + 2
    else:
        hue = (r - g) / d + 4
    return hue * 60.0, sat, light


def name_coat_colour(rgb: RGB) -> str:
    """Name one coat colour. Achromatic colours are named by lightness."""
    hue, sat, light = _to_hsl(rgb)
    # Test greyness with chroma (max-min), not HSL saturation. HSL saturation
    # blows up near white and near black — RGB(245,242,240) reports sat 0.20
    # despite being 2% off neutral, which is how a white cat ends up "cream".
    chroma = (max(rgb) - min(rgb)) / 255.0
    if chroma < 0.10:
        # Thresholds sit lower than pure-colour intuition would suggest: white
        # fur photographs at roughly L 0.75-0.85, almost never at 1.0, so a
        # textbook 0.9 cutoff calls every white animal "silver".
        if light < 0.16:
            return "black"
        if light < 0.32:
            return "charcoal"
        if light < 0.55:
            return "grey"
        if light < 0.75:
            return "silver"
        return "white"
    # Warm hues are almost all of animal fur, and there lightness carries the
    # name, not saturation — pale warm fur is "cream" even at high HSL
    # saturation, and dark warm fur is "brown" however vivid it measures.
    if 10 <= hue < 50:
        if light > 0.72:
            return "cream"
        if light < 0.42:
            return "brown"
        return "ginger"
    for name, lo, hi in _COAT_HUES:
        if lo <= hue < hi:
            return name
    return "brown"


def name_eye_colour(rgb: RGB) -> str:
    hue, sat, light = _to_hsl(rgb)
    chroma = (max(rgb) - min(rgb)) / 255.0
    if chroma < 0.09:
        return "grey" if light > 0.45 else "dark"
    # a dark warm iris is brown to everyone except a cat breeder
    if 5 <= hue < 50 and light < 0.35:
        return "brown"
    for name, lo, hi in _EYE_HUES:
        if lo <= hue < hi:
            return name
    return "brown"


# --------------------------------------------------------------------------
# results
# --------------------------------------------------------------------------


@dataclass
class Appearance:
    coat: List[RGB] = field(default_factory=list)        # dominant first
    coat_shares: List[float] = field(default_factory=list)
    coat_names: List[str] = field(default_factory=list)
    eye: Optional[RGB] = None
    eye_name: Optional[str] = None
    eye_points: List[Tuple[int, int]] = field(default_factory=list)
    mask_source: str = "none"
    confidence: float = 0.0

    # -- description ------------------------------------------------------
    @property
    def coat_phrase(self) -> str:
        """'black and white', 'ginger', 'grey and white' …

        Always adjectival, so it drops straight into a sentence. Two-colour
        coats are ordered dark-first, which is simply how people say it:
        'black and white cat', never 'white and black cat'.
        """
        names, shares = self.coat_names, self.coat_shares
        if not names:
            return "indeterminate"
        # collapse duplicates, keeping dominance order
        merged: List[Tuple[str, float, RGB]] = []
        for n, s, c in zip(names, shares, self.coat):
            for i, (mn, ms, mc) in enumerate(merged):
                if mn == n:
                    merged[i] = (mn, ms + s, mc)
                    break
            else:
                merged.append((n, s, c))
        if len(merged) == 1 or merged[1][1] < 0.18:
            return merged[0][0]
        pair = sorted(merged[:2], key=lambda m: _to_hsl(m[2])[2])  # darker first
        return f"{pair[0][0]} and {pair[1][0]}"

    def describe(self, species_display: str) -> str:
        if not self.coat_names:
            return f"a {species_display.lower()}"
        bits = f"a {self.coat_phrase} {species_display.lower()}"
        if self.eye_name and self.eye_name not in ("dark", "grey"):
            bits += f" with {self.eye_name} eyes"
        return bits

    # -- palette for the sprite -------------------------------------------
    def palette(self) -> Optional[Tuple[RGB, RGB, RGB]]:
        """(body, belly, accent).

        Darker coat becomes the body and lighter becomes the belly, which is
        both how these animals are actually marked and how the sprite is shaded.
        The accent (legs, ear insides) darkens a light body but *lightens* a
        dark one — otherwise a black cat gets black legs on a black body and
        reads as a blob.
        """
        if len(self.coat) < 1:
            return None
        if len(self.coat) == 1:
            body = self.coat[0]
            belly = _shift(body, 1.35)
        else:
            a, b = self.coat[0], self.coat[1]
            la, lb = _to_hsl(a)[2], _to_hsl(b)[2]
            body, belly = (a, b) if la <= lb else (b, a)
        accent = _shift(body, 1.9) if _to_hsl(body)[2] < 0.32 else _shift(body, 0.62)
        return body, belly, accent

    def to_dict(self) -> dict:
        return {
            "coat": [list(c) for c in self.coat],
            "coat_shares": self.coat_shares,
            "coat_names": self.coat_names,
            "eye": list(self.eye) if self.eye else None,
            "eye_name": self.eye_name,
            "mask_source": self.mask_source,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> Optional["Appearance"]:
        if not d:
            return None
        return cls(
            coat=[tuple(int(v) for v in c) for c in d.get("coat", [])],
            coat_shares=list(d.get("coat_shares", [])),
            coat_names=list(d.get("coat_names", [])),
            eye=tuple(int(v) for v in d["eye"]) if d.get("eye") else None,
            eye_name=d.get("eye_name"),
            mask_source=d.get("mask_source", "none"),
            confidence=float(d.get("confidence", 0.0)),
        )


def _shift(rgb: RGB, factor: float) -> RGB:
    return tuple(int(max(0, min(255, round(v * factor)))) for v in rgb)  # type: ignore


# --------------------------------------------------------------------------
# stage 1 — segmentation
# --------------------------------------------------------------------------


class GrabCutSegmenter:
    """No-model fallback. Seeds GrabCut with the centre 70% of the frame.

    Good enough when the animal fills the frame, which is what the capture
    streak already selects for. Costs ~80 ms at 480p.
    """

    name = "grabcut"
    available = True

    def mask(self, frame_bgr: np.ndarray) -> Optional[np.ndarray]:
        if cv2 is None:
            return None
        h, w = frame_bgr.shape[:2]
        target = min(w, 320)  # GrabCut is O(pixels) and iterative; 320px keeps it ~150 ms
        small = cv2.resize(frame_bgr, (target, int(target * h / w)))
        sh, sw = small.shape[:2]
        rect = (int(sw * 0.14), int(sh * 0.04), int(sw * 0.72), int(sh * 0.92))
        m = np.zeros((sh, sw), np.uint8)
        try:
            cv2.grabCut(small, m, rect, np.zeros((1, 65), np.float64),
                        np.zeros((1, 65), np.float64), 3, cv2.GC_INIT_WITH_RECT)
        except cv2.error:
            return None
        out = np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        out = cv2.morphologyEx(out, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        return cv2.resize(out, (w, h), interpolation=cv2.INTER_NEAREST)


class DeepLabSegmenter:
    """torchvision DeepLabV3-MobileNetV3, VOC-21 labels, animal classes only.

    ~11M params. Half precision on CUDA. Inference at 320px on the short side —
    the mask is only used to pick pixels, so full resolution buys nothing.
    """

    name = "deeplabv3_mobilenet_v3_large"
    available = True

    def __init__(self, infer_size: int = 320):
        import torch
        import torchvision.models.segmentation as seg

        self._torch = torch
        self.infer_size = infer_size

        weights = seg.DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT
        self.model = seg.deeplabv3_mobilenet_v3_large(weights=weights)
        self.preprocess = weights.transforms()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.eval().to(self.device)
        if self.device.type == "cuda":
            self.model = self.model.half()
        self.name = f"deeplabv3_mnv3 @ {self.device.type}"

    def mask(self, frame_bgr: np.ndarray) -> Optional[np.ndarray]:
        if cv2 is None:
            return None
        torch = self._torch
        h, w = frame_bgr.shape[:2]
        scale = self.infer_size / min(h, w)
        small = cv2.resize(frame_bgr, (int(round(w * scale)), int(round(h * scale))))
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        tensor = torch.from_numpy(rgb).permute(2, 0, 1)
        batch = self.preprocess(tensor).unsqueeze(0).to(self.device)
        if self.device.type == "cuda":
            batch = batch.half()

        with torch.no_grad():
            logits = self.model(batch)["out"][0].float()
        pred = logits.argmax(0).cpu().numpy().astype(np.uint8)

        animal = np.isin(pred, list(VOC_ANIMAL_IDS)).astype(np.uint8) * 255
        if animal.sum() < animal.size * 0.02 * 255:
            return None  # nothing animal-shaped; let the caller fall back
        animal = cv2.morphologyEx(animal, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        return cv2.resize(animal, (w, h), interpolation=cv2.INTER_NEAREST)


def load_segmenter(prefer_model: bool = True):
    if prefer_model:
        try:
            return DeepLabSegmenter()
        except Exception:
            pass
    return GrabCutSegmenter()


# --------------------------------------------------------------------------
# stage 2 — coat
# --------------------------------------------------------------------------


def _erode_for_sampling(mask: np.ndarray) -> np.ndarray:
    """Pull the mask in off its own edge.

    Segmentation boundaries always blend a little background in, and those
    blended pixels form their own k-means cluster that means nothing. Eroding
    by ~2% of the shorter side removes them.
    """
    k = max(3, int(min(mask.shape[:2]) * 0.02) | 1)
    return cv2.erode(mask, np.ones((k, k), np.uint8))


def describe_coat(frame_bgr: np.ndarray, mask: np.ndarray, k: int = 3,
                  min_share: float = 0.12) -> Tuple[List[RGB], List[float], List[str]]:
    inner = _erode_for_sampling(mask)
    if inner.sum() < 255 * 500:
        inner = mask
    px = frame_bgr[inner > 0].reshape(-1, 3)
    if len(px) < 200:
        return [], [], []
    if len(px) > 40000:  # k-means doesn't need every pixel
        # Seeded: an unseeded subsample plus k-means++ made the same photo
        # report "black and white" on one run and "silver and white" on the
        # next, which then persists into the save file forever.
        rng = np.random.default_rng(0)
        px = px[rng.choice(len(px), 40000, replace=False)]

    cv2.setRNGSeed(0)
    lab = cv2.cvtColor(px.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centres = cv2.kmeans(lab, k, None, crit, 5, cv2.KMEANS_PP_CENTERS)

    counts = np.bincount(labels.ravel(), minlength=k).astype(np.float64)
    shares = counts / counts.sum()
    order = np.argsort(-shares)

    colours: List[RGB] = []
    keep_shares: List[float] = []
    names: List[str] = []
    for i in order:
        if shares[i] < min_share and colours:
            break
        bgr = cv2.cvtColor(centres[i].reshape(1, 1, 3).astype(np.uint8), cv2.COLOR_LAB2BGR).reshape(3)
        rgb: RGB = (int(bgr[2]), int(bgr[1]), int(bgr[0]))
        colours.append(rgb)
        keep_shares.append(float(shares[i]))
        names.append(name_coat_colour(rgb))
    return colours, keep_shares, names


# --------------------------------------------------------------------------
# stage 3 — eyes
# --------------------------------------------------------------------------


def _iris_colour(patch_bgr: np.ndarray, patch_mask: np.ndarray) -> Optional[RGB]:
    """Median colour of the iris, with pupil and catchlight thrown out."""
    px = patch_bgr[patch_mask].reshape(-1, 3)
    if len(px) < 20:
        return None
    v = px.max(axis=1).astype(np.float32)
    lo, hi = np.percentile(v, 25), np.percentile(v, 92)
    keep = (v >= lo) & (v <= hi)
    if keep.sum() < 12:
        keep = np.ones(len(px), bool)
    med = np.median(px[keep], axis=0)
    return (int(med[2]), int(med[1]), int(med[0]))


def find_eyes(frame_bgr: np.ndarray, mask: np.ndarray) -> Tuple[Optional[RGB], List[Tuple[int, int]], float]:
    """Locate the eyes and return (median iris RGB, centres, confidence).

    Candidates are small saturated blobs in the upper part of the animal.
    They are then scored in pairs: two blobs of similar size, at similar
    height, separated by a plausible multiple of their own width. A single
    unpaired blob is still accepted but at much lower confidence, because
    that is the case that a ginger coat can fake.
    """
    if cv2 is None:
        return None, [], 0.0

    ys, xs = np.nonzero(mask)
    if len(xs) < 500:
        return None, [], 0.0
    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()
    head_bottom = int(y0 + (y1 - y0) * 0.60)   # eyes live in the top 60%
    area = float(mask[mask > 0].size)

    roi = np.zeros_like(mask)
    roi[y0:head_bottom, x0:x1] = mask[y0:head_bottom, x0:x1]

    # Candidates are pixels whose *chroma* differs from their own
    # neighbourhood — distance in the Lab a/b plane only, with L discarded.
    #
    # Two cues were tried and both fail alone. A global saturation threshold
    # works on a black-and-white cat but finds nothing on a ginger one, where
    # the coat is as saturated as the iris and morphology swallows the eyes
    # into the body. Full-Lab local contrast fixes ginger but then fires on
    # every ear tip and fur boundary, because those are large *lightness*
    # steps. Dropping L keeps what actually distinguishes an eye: a black/white
    # fur edge has near-zero chroma difference, an iris never does.
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    k = min(31, int(max(5, (x1 - x0) * 0.12)) | 1)   # ~1/8 of head width, odd
    local = cv2.medianBlur(lab, k)
    ab = lab[:, :, 1:].astype(np.float32)
    ab_local = local[:, :, 1:].astype(np.float32)
    dist = np.linalg.norm(ab - ab_local, axis=2)
    chroma = np.linalg.norm(ab - 128.0, axis=2)

    V = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)[:, :, 2]
    cand = ((dist > 8) & (chroma > 18) & (V > 40) & (V < 252) & (roi > 0)).astype(np.uint8) * 255
    cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    n, labels, stats, cents = cv2.connectedComponentsWithStats(cand, 8)
    blobs = []
    for i in range(1, n):
        a = stats[i, cv2.CC_STAT_AREA]
        bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if not (area * 0.0004 < a < area * 0.05):
            continue
        if bh == 0 or not (0.35 < bw / bh < 3.0):
            continue
        blobs.append({"i": i, "a": float(a), "x": float(cents[i][0]), "y": float(cents[i][1]),
                      "w": float(bw), "h": float(bh)})
    if not blobs:
        return None, [], 0.0
    blobs.sort(key=lambda b: -b["a"])
    blobs = blobs[:8]

    # --- pair scoring ---
    best, best_score = None, 0.0
    for i in range(len(blobs)):
        for j in range(i + 1, len(blobs)):
            p, q = blobs[i], blobs[j]
            sep = abs(p["x"] - q["x"])
            avg_w = (p["w"] + q["w"]) / 2.0
            if avg_w <= 0 or sep < avg_w * 0.6 or sep > avg_w * 6.0:
                continue
            dy = abs(p["y"] - q["y"])
            level = math.exp(-(dy / max(sep, 1.0)) ** 2 / 0.18)         # roughly level
            similar = min(p["a"], q["a"]) / max(p["a"], q["a"])          # similar size
            score = level * similar
            if score > best_score:
                best, best_score = (p, q), score

    if best is not None and best_score > 0.30:
        chosen, conf = list(best), 0.55 + 0.45 * best_score
    else:
        chosen, conf = [blobs[0]], 0.30

    colours, centres = [], []
    for b in chosen:
        i = b["i"]
        x, y = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
        bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        patch = frame_bgr[y:y + bh, x:x + bw]
        pm = labels[y:y + bh, x:x + bw] == i
        c = _iris_colour(patch, pm)
        if c:
            colours.append(c)
            centres.append((int(b["x"]), int(b["y"])))
    if not colours:
        return None, [], 0.0

    med = tuple(int(np.median([c[k] for c in colours])) for k in range(3))
    return med, centres, float(conf)  # type: ignore


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------


def analyse(frame_bgr: np.ndarray, segmenter) -> Appearance:
    """Full pipeline on one captured frame. Never raises."""
    out = Appearance()
    if cv2 is None or frame_bgr is None:
        return out
    try:
        mask = segmenter.mask(frame_bgr)
        source = getattr(segmenter, "name", "unknown")
        if mask is None or mask.sum() < 255 * 500:
            fallback = GrabCutSegmenter()
            mask = fallback.mask(frame_bgr)
            source = "grabcut (fallback)"
        if mask is None:
            return out
        out.mask_source = source

        out.coat, out.coat_shares, out.coat_names = describe_coat(frame_bgr, mask)
        eye, points, conf = find_eyes(frame_bgr, mask)
        if eye:
            out.eye = eye
            out.eye_name = name_eye_colour(eye)
            out.eye_points = points
            out.confidence = conf
    except Exception:
        return out
    return out
