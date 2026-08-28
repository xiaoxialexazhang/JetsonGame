#!/usr/bin/env python3
"""Check the API key and each configured model with one tiny call apiece.

Run this before the game -- it turns "the sprite came out as a blob" into a
specific answer about which model name is wrong.

    python3 tools/test_api.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from pipeline import backends  # noqa: E402

print("=" * 60)
b = backends.refresh()
print("=" * 60)

if not config.ANTHROPIC_API_KEY:
    print("\nNo ANTHROPIC_API_KEY set. The game still runs fully local:")
    print("  python3 main.py --offline")
    raise SystemExit(0)

key = config.ANTHROPIC_API_KEY
print(f"\nkey        {key[:14]}...{key[-4:]}  ({len(key)} chars)")

if not b.claude:
    print("\napi.anthropic.com is not reachable from here.")
    print("Check wifi / VPN / proxy, then re-run. The game works offline meanwhile.")
    raise SystemExit(1)

from pipeline import llm  # noqa: E402

stages = [
    ("VISION_MODEL", config.VISION_MODEL, "identifies the animal"),
    ("ARTIST_MODEL", config.ARTIST_MODEL, "draws the sprite"),
    ("CHAT_MODEL", config.CHAT_MODEL, "in-game dialogue"),
]

print()
ok_all = True
for var, model, what in stages:
    t0 = time.time()
    try:
        out = llm.ask(model, "Reply with exactly: ok",
                      "Say ok.", max_tokens=12, temperature=0)
        dt = time.time() - t0
        print(f"  {'OK':4} {var:14} {model:34} {dt:5.2f}s   {what}")
    except Exception as e:      # noqa: BLE001
        ok_all = False
        msg = str(e)
        print(f"  {'FAIL':4} {var:14} {model:34}         {what}")
        print(f"       -> {msg[:150]}")
        if "not_found" in msg or "model" in msg.lower():
            print(f"       -> fix: set {var}= in .env to a model your key can use")

print()
if ok_all:
    print("All three models work. Run:  python3 main.py")
else:
    print("Fix the failing model name(s) in .env, or run with --offline.")
    print("Any stage that fails at runtime falls back to its local path,")
    print("so a bad model name degrades the demo rather than breaking it.")
