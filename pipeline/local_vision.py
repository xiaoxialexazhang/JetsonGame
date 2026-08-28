"""On-device species recognition. No network, no API key.

Two detectors, cheapest first:
  1. OpenCV Haar face cascade  -> "person"   (ships with opencv, no download)
  2. torchvision ImageNet-1k   -> an animal  (optional; needs torch)

ImageNet has no "person" class at all, which is why the face cascade exists.
The ImageNet index ranges below are carried over from the earlier
jetson_critters build and extended with fish / chicken / pig / turtle / frog.
"""
from __future__ import annotations

import threading

import numpy as np

import config

# ---------------------------------------------------------------- species map
# inclusive ImageNet-1k index ranges that fold onto one playable species
IMAGENET_RANGES: dict[str, list[tuple[int, int]]] = {
    "goldfish":  [(1, 1)],
    "fish":      [(0, 0), (2, 6), (389, 397)],   # tench, sharks/rays, eels, puffer...
    "chicken":   [(7, 8)],                       # cock, hen
    "bird":      [(9, 24), (80, 100), (127, 146)],
    "turtle":    [(33, 37)],
    "lizard":    [(38, 48)],
    "snake":     [(52, 68)],
    "frog":      [(30, 32)],
    "dog":       [(151, 268)],
    "cat":       [(281, 285)],
    "rabbit":    [(330, 332)],
    "horse":     [(339, 339)],
    "pig":       [(341, 343)],
    "cow":       [(345, 347)],
    "goat":      [(348, 350)],                   # ram, bighorn, ibex
    "bear":      [(294, 297)],
    "fox":       [(277, 280)],
}


def _build_lookup() -> dict[int, str]:
    table: dict[int, str] = {}
    for key, ranges in IMAGENET_RANGES.items():
        for lo, hi in ranges:
            for i in range(lo, hi + 1):
                table.setdefault(i, key)
    return table


IMAGENET_TO_SPECIES = _build_lookup()


# ---------------------------------------------------------------- face -> person
_face_cascade = None
_face_lock = threading.Lock()


def _faces(bgr) -> int:
    """How many frontal faces are in this frame? 0 if opencv data is missing."""
    global _face_cascade
    try:
        import cv2
        with _face_lock:
            if _face_cascade is None:
                path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                _face_cascade = cv2.CascadeClassifier(path)
            cascade = _face_cascade
        if cascade is None or cascade.empty():
            return 0
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        found = cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=6,
                                         minSize=(70, 70))
        return len(found)
    except Exception:      # noqa: BLE001
        return 0


def _face_bbox(bgr):
    """Normalised bbox around the largest face, padded out to a torso."""
    try:
        import cv2
        if _face_cascade is None:
            _faces(bgr)
        if _face_cascade is None or _face_cascade.empty():
            return None
        gray = cv2.equalizeHist(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
        found = _face_cascade.detectMultiScale(gray, 1.15, 6, minSize=(70, 70))
        if len(found) == 0:
            return None
        x, y, w, h = max(found, key=lambda f: f[2] * f[3])
        H, W = gray.shape[:2]
        # widen and drop downward so we sample clothing colour too
        x0 = max(0, x - w * 0.6) / W
        x1 = min(W, x + w * 1.6) / W
        y0 = max(0, y - h * 0.3) / H
        y1 = min(H, y + h * 2.6) / H
        return [x0, y0, x1, y1]
    except Exception:      # noqa: BLE001
        return None


# ---------------------------------------------------------------- imagenet
class _Classifier:
    """Lazily-built torchvision classifier. Safe to construct without torch."""

    def __init__(self):
        self.ok = False
        self.reason = ""
        self.model = None
        self.tf = None
        self.device = "cpu"
        self._lock = threading.Lock()

    def load(self):
        if self.model is not None or self.reason:
            return
        try:
            import torch
            from torchvision import models

            name = config.LOCAL_MODEL
            weights = models.get_model_weights(name).DEFAULT
            model = models.get_model(name, weights=weights)
            model.eval()
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(self.device)
            if self.device == "cuda":
                model = model.half()
            self.model = model
            self.tf = weights.transforms()
            self.ok = True
            print(f"[local_vision] {name} on {self.device}")
        except Exception as e:      # noqa: BLE001
            self.reason = f"{type(e).__name__}: {e}"
            print(f"[local_vision] no on-device classifier ({self.reason})")

    def top_species(self, bgr) -> tuple[str | None, float]:
        """Fold ImageNet probabilities into species buckets, return the best."""
        self.load()
        if not self.ok:
            return None, 0.0
        try:
            import torch
            from PIL import Image

            rgb = bgr[:, :, ::-1]
            img = Image.fromarray(np.ascontiguousarray(rgb))
            with self._lock, torch.no_grad():
                x = self.tf(img).unsqueeze(0).to(self.device)
                if self.device == "cuda":
                    x = x.half()
                probs = torch.softmax(self.model(x).float(), dim=1)[0]
                top = torch.topk(probs, 12)

            buckets: dict[str, float] = {}
            for score, idx in zip(top.values.tolist(), top.indices.tolist()):
                key = IMAGENET_TO_SPECIES.get(idx)
                if key:
                    buckets[key] = buckets.get(key, 0.0) + score
            if not buckets:
                return None, 0.0
            best = max(buckets.items(), key=lambda kv: kv[1])
            return best[0], float(best[1])
        except Exception as e:      # noqa: BLE001
            print(f"[local_vision] inference failed: {e}")
            return None, 0.0


CLASSIFIER = _Classifier()


# ---------------------------------------------------------------- public
def identify(bgr) -> dict:
    """Same contract as pipeline.vision.identify, but fully local.
    Returns species / found / confidence / bbox / build / vibe."""
    species, conf = CLASSIFIER.top_species(bgr)

    if species is None or conf < config.LOCAL_CONF:
        # nothing animal-shaped stood out -- is it a person?
        if _faces(bgr) > 0:
            return {"species": "person", "found": True, "confidence": 0.66,
                    "bbox": _face_bbox(bgr) or [0.2, 0.1, 0.8, 0.95],
                    "build": "a human, drawn as a little farm villager",
                    "vibe": "curious, here in person"}

    if species is None:
        if not CLASSIFIER.ok:
            # No recognizer at all (torch missing). Refusing the capture here
            # would kill the demo, so make a generic critter out of whatever
            # colours are actually in frame -- the colour half still works.
            return {"species": "critter", "found": True, "confidence": 0.15,
                    "bbox": [0.15, 0.15, 0.85, 0.85],
                    "build": "a small round farm creature",
                    "vibe": "mysterious, unidentified"}
        # Recognizer ran fine and genuinely saw nothing animal-shaped.
        return {"species": "unknown", "found": False, "confidence": 0.0,
                "bbox": [0, 0, 1, 1], "build": "", "vibe": ""}

    if conf < config.LOCAL_CONF:
        # low confidence, but better a cute guess than a failed capture
        return {"species": species, "found": True, "confidence": conf,
                "bbox": [0.12, 0.12, 0.88, 0.88],
                "build": "", "vibe": "a bit blurry, hard to read"}

    return {"species": species, "found": True, "confidence": conf,
            # the classifier gives no box; the centre crop is a decent proxy
            "bbox": [0.15, 0.15, 0.85, 0.85],
            "build": "", "vibe": ""}
