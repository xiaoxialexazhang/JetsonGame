#!/usr/bin/env python3
"""Step 2: run the full photo -> villager pipeline on a still image, no pygame.
    python3 tools/test_pipeline.py data/input/test-000.jpg
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from pipeline import orchestrator  # noqa: E402

if len(sys.argv) < 2:
    files = sorted(config.INPUT_DIR.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("usage: python3 tools/test_pipeline.py <image>")
        raise SystemExit(1)
    img = files[0]
    print(f"(no arg given, using newest: {img.name})")
else:
    img = Path(sys.argv[1])

critter, err = orchestrator.safe_process(img, progress=lambda m: None)
if err:
    print("FAILED:", err)
    raise SystemExit(1)

print("\n--- result ---")
for k in ("name", "title", "species", "color1", "color2", "color1_hex", "color2_hex"):
    print(f"{k:12} {critter[k]}")
print(f"{'sprite':12} {critter['sprite']}")
print(f"{'greeting':12} {critter['greeting']}")
print(f"\npersona: {critter['persona']}")
print("\nopen the sprite to check it looks right.")
