#!/usr/bin/env python3
"""Check the endpoint, the key, and each configured model with one tiny call.

Run this before the game -- it turns "the sprite came out as a blob" into a
specific answer about which model name is wrong.

    python3 tools/test_api.py             # probe + one call per stage
    python3 tools/test_api.py --models    # also list what the endpoint offers
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from pipeline import backends  # noqa: E402

WANT_MODELS = "--models" in sys.argv

print("=" * 68)
b = backends.refresh()
print("=" * 68)

print(f"endpoint   {config.API_ENDPOINT}")
print(f"style      {config.API_STYLE}")

if not config.API_KEY:
    print("\nNo INFERENCE_API_KEY set. The game still runs fully local:")
    print("  python3 main.py --offline")
    raise SystemExit(0)

key = config.API_KEY
shown = f"{key[:6]}...{key[-4:]}" if len(key) > 12 else "(short key)"
print(f"key        {shown}  ({len(key)} chars)")

if not b.claude:
    host = backends._endpoint_host()[0]
    print(f"\n{host} is not reachable from here.")
    print("Check wifi / VPN / proxy, then re-run. The game works offline meanwhile.")
    raise SystemExit(1)

from pipeline import llm  # noqa: E402

# Probe the request shape before timing anything, so the first stage isn't
# charged for the probe's latency.
try:
    detected = llm.style()
    print(f"detected   {detected}-style requests")
except Exception as e:      # noqa: BLE001
    print(f"\nprobe failed: {e}")
    raise SystemExit(1)

if WANT_MODELS:
    names = llm.list_models()
    if names:
        print(f"\n{len(names)} models offered by this endpoint:")
        for n in names:
            mark = " <-- configured" if n in (
                config.VISION_MODEL, config.ARTIST_MODEL, config.CHAT_MODEL) else ""
            print(f"  {n}{mark}")
    else:
        print("\nendpoint has no /v1/models listing (that's fine, not all do)")

stages = [
    ("VISION_MODEL", config.VISION_MODEL, "identifies the animal"),
    ("ARTIST_MODEL", config.ARTIST_MODEL, "draws the sprite"),
    ("CHAT_MODEL", config.CHAT_MODEL, "in-game dialogue"),
]

print()
ok_all = True
seen: dict[str, bool] = {}
for var, model, what in stages:
    t0 = time.time()
    try:
        llm.ask(model, "Reply with exactly: ok", "Say ok.",
                max_tokens=12, temperature=0)
        dt = time.time() - t0
        print(f"  {'OK':4} {var:14} {model:44} {dt:5.2f}s   {what}")
        seen[model] = True
    except Exception as e:      # noqa: BLE001
        ok_all = False
        seen[model] = False
        msg = str(e).replace("\n", " ")
        print(f"  {'FAIL':4} {var:14} {model:44}          {what}")
        print(f"       -> {msg[:220]}")
        if "400" in msg or "404" in msg or "not_found" in msg:
            print(f"       -> fix: set {var}= in .env to a model this endpoint has")
            print("       -> run  python3 tools/test_api.py --models  to see the list")

print()
if ok_all:
    print("All three models work. Next:  python3 tools/test_camera.py")
else:
    print("Fix the failing model name(s) in .env, or run with --offline.")
    print("Any stage that fails at runtime falls back to its local path,")
    print("so a bad model name degrades the demo rather than breaking it.")
    raise SystemExit(1)
