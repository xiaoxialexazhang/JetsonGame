#!/usr/bin/env python3
"""Populate the farm with 5 hand-made critters. NO API CALLS, NO CAMERA.

Two uses:
  * verify the rasteriser and the game render correctly before you touch the API
  * a safety net: if the wifi dies mid-demo you still have a populated world

    python3 tools/seed_demo.py            # add demo critters
    python3 tools/seed_demo.py --reset    # wipe the roster first
"""
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from pipeline import roster, sprite  # noqa: E402
from pipeline.colors import name_color, rgb_of  # noqa: E402
from tools.demo_specs import DEMO  # noqa: E402

if "--reset" in sys.argv:
    roster.save([])
    print("roster cleared")

for spec, c1, c2, name, title, persona, greeting in DEMO:
    cid = uuid.uuid4().hex[:8]
    stem = f"{spec['species']}-{cid}"
    png = config.AVATAR_DIR / f"{stem}.png"
    sprite.render(spec, c1, c2, png)
    roster.append({
        "id": cid, "name": name, "title": title,
        "persona": persona, "greeting": greeting,
        "species": spec["species"],
        "color1": name_color(rgb_of(c1)), "color2": name_color(rgb_of(c2)),
        "color1_hex": c1, "color2_hex": c2,
        "sprite": str(png.relative_to(config.ROOT)),
        "source": "demo", "confidence": 1.0, "created": time.time(),
    })
    print(f"  + {name:12} {spec['species']:10} -> {png.name}")

print("\ndone. run:  python3 main.py --no-camera")
