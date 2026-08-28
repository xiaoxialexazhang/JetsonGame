#!/usr/bin/env python3
"""Render every demo spec across several colour pairs onto one PNG so you can
eyeball whether the art style holds up. No API calls.

    python3 tools/contact_sheet.py   ->  data/contact_sheet.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

import config  # noqa: E402
from pipeline import sprite  # noqa: E402
from tools.demo_specs import CAT, CHICKEN, DOG, FISH, GOAT, PERSON  # noqa: E402

SPECS = [("cat", CAT), ("dog", DOG), ("chicken", CHICKEN),
         ("goat", GOAT), ("fish", FISH), ("person", PERSON)]

PAIRS = [
    ("#e08a3c", "#f6efe2"),   # orange + cream
    ("#3a3a44", "#f0c33c"),   # charcoal + gold
    ("#8a5a34", "#e8d8b8"),   # brown + tan
    ("#6a8fd8", "#2c3a66"),   # blue + navy
    ("#d8d2c4", "#8a7f6c"),   # white + grey
    ("#5aa050", "#e0e8b0"),   # green + pale
]

cell = config.SPRITE_PX * config.SPRITE_SCALE
sheet = Image.new("RGBA", (cell * len(PAIRS), cell * len(SPECS)), (110, 168, 62, 255))

tmp = config.DATA / "_tmp.png"
for row, (_name, spec) in enumerate(SPECS):
    for col, (c1, c2) in enumerate(PAIRS):
        sprite.render(spec, c1, c2, tmp)
        s = Image.open(tmp).convert("RGBA")
        sheet.alpha_composite(s, (col * cell, row * cell))
try:
    tmp.unlink(missing_ok=True)
except OSError:
    pass

out = config.DATA / "contact_sheet.png"
sheet.save(out)
print("wrote", out, sheet.size)
