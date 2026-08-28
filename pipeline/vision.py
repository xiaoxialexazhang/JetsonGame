"""Stage 1 -- what animal is that?

Claude vision when it's reachable: open vocabulary, any creature, plus a tight
bounding box that stage 2 uses to sample colours from the animal rather than the
wall behind it.

Offline: pipeline/local_vision.py (torchvision ImageNet + a Haar face cascade
for 'person'), which returns the same dict shape with a centre-crop box.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

import config
from pipeline import backends, llm, local_vision

SYSTEM = """You identify the single most prominent animal (or person) in a webcam photo.

Reply with ONLY a JSON object, no prose:
{
  "species":      "one or two lowercase words, the common species: cat, dog, person, goldfish, goat, chicken, duck, cow, horse, pig, rabbit, turtle, hamster, parrot, sheep, frog, snake, lizard...",
  "found":        true or false,
  "confidence":   0.0-1.0,
  "bbox":         [x0, y0, x1, y1]  normalised 0-1, tight around the animal's BODY,
  "build":        "short physical description for an artist: body shape, ear shape, tail, size, notable markings",
  "vibe":         "3-6 words on its apparent mood or energy"
}

Notes:
- A photo of a HUMAN counts: species "person".
- If it is a photo/drawing/plush of an animal, still identify the animal.
- If there is genuinely no animal or person, set found=false and species="unknown".
- bbox must be tight around the creature. If it fills the frame use [0,0,1,1]."""


def identify(image_path) -> dict:
    """Claude if we can reach it, on-device otherwise. Never raises: a failed
    Claude call silently falls through to the local recognizer."""
    if backends.CURRENT.claude:
        try:
            return _identify_claude(image_path)
        except Exception as e:      # noqa: BLE001
            print(f"[vision] Claude failed ({e}); falling back to on-device")
    return _identify_local(image_path)


def _identify_local(image_path) -> dict:
    rgb = np.asarray(Image.open(image_path).convert("RGB"))
    bgr = np.ascontiguousarray(rgb[:, :, ::-1])
    out = local_vision.identify(bgr)
    print(f"[vision] on-device -> {out['species']} ({out['confidence']:.2f})")
    return out


def _identify_claude(image_path) -> dict:
    raw = llm.ask(
        config.VISION_MODEL,
        SYSTEM,
        [llm.image_block(image_path),
         {"type": "text", "text": "Identify the animal. JSON only."}],
        max_tokens=600,
        temperature=0.2,
        prefill="{",
    )
    d = llm.extract_json(raw)

    bbox = d.get("bbox") or [0, 0, 1, 1]
    try:
        bbox = [float(v) for v in bbox][:4]
        x0, y0, x1, y1 = bbox
        bbox = [max(0.0, min(1.0, x0)), max(0.0, min(1.0, y0)),
                max(0.0, min(1.0, x1)), max(0.0, min(1.0, y1))]
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            bbox = [0, 0, 1, 1]
    except Exception:
        bbox = [0, 0, 1, 1]

    return {
        "species": str(d.get("species", "unknown")).lower().strip() or "unknown",
        "found": bool(d.get("found", True)),
        "confidence": float(d.get("confidence", 0.5) or 0.5),
        "bbox": bbox,
        "build": str(d.get("build", "")).strip(),
        "vibe": str(d.get("vibe", "")).strip(),
    }
