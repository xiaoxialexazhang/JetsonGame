"""The whole snapshot -> villager pipeline, in one place.

    photo ──▶ (1) Claude vision: species + bbox
          ──▶ (2) k-means on the bbox: colour1, colour2
          ──▶ (3) three text params
          ──▶ (4) Claude artist: shape spec ──▶ rasteriser ──▶ sprite.png
          ──▶ (5) Claude: name + personality
          ──▶ appended to data/critters.json, ready for the game to spawn
"""
from __future__ import annotations

import time
import traceback
import uuid
from pathlib import Path

import config
from pipeline import avatar, colors, persona, roster, vision

# kept as aliases so callers don't need to know where this moved
load_roster = roster.load
save_roster = roster.save
append_roster = roster.append


def _unique_name(name: str) -> str:
    """Two brown dogs shouldn't both be called Scout -- the player has to be able
    to tell them apart in the chat bar."""
    taken = {c.get("name", "") for c in roster.load()}
    if name not in taken:
        return name
    for suffix in ("II", "Jr", "the Second", "Too"):
        cand = f"{name} {suffix}"
        if cand not in taken:
            return cand
    n = 2
    while f"{name} {n}" in taken:
        n += 1
    return f"{name} {n}"


def _rel(path) -> str:
    """Store paths relative to the repo when we can, absolute when we can't --
    an image dragged in from /tmp or a USB stick must not crash the capture."""
    p = Path(path).resolve()
    try:
        return str(p.relative_to(config.ROOT))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------- pipeline
def process(image_path, progress=None) -> dict:
    """Run every stage. `progress(text)` is called between stages so the game
    can show what's happening. Returns the new critter dict.
    Raises on unrecoverable failure (e.g. no animal in frame)."""
    def say(msg):
        print(f"[pipeline] {msg}")
        if progress:
            progress(msg)

    image_path = Path(image_path).resolve()
    t0 = time.time()

    # (1) species -------------------------------------------------------
    say("looking at the photo...")
    seen = vision.identify(image_path)
    if not seen["found"] or seen["species"] in ("unknown", ""):
        raise ValueError("I couldn't find an animal in that shot - try again.")
    species = seen["species"]
    say(f"it's a {species}!")

    # (2) colours -------------------------------------------------------
    c1, c2, n1, n2 = colors.dominant_pair(image_path, bbox=seen["bbox"])
    say(f"colours: {n1} + {n2}")

    # (3) the three text parameters -------------------------------------
    params = {"species": species, "color1": n1, "color2": n2,
              "color1_hex": c1, "color2_hex": c2}
    print(f"[pipeline] params = {params}")

    # (4) avatar --------------------------------------------------------
    say(f"drawing a {n1} {species}...")
    cid = uuid.uuid4().hex[:8]
    stem = f"{species.replace(' ', '_')}-{cid}"
    png, _spec = avatar.make(species, c1, c2, n1, n2,
                             build=seen.get("build", ""), vibe=seen.get("vibe", ""),
                             stem=stem)

    # (5) who are they? -------------------------------------------------
    say("waking them up...")
    who = persona.invent(species, n1, n2, seen.get("vibe", ""))
    who["name"] = _unique_name(who["name"])

    critter = {
        "id": cid,
        "name": who["name"],
        "title": who["title"],
        "persona": who["persona"],
        "greeting": who["greeting"],
        "species": species,
        "color1": n1, "color2": n2,
        "color1_hex": c1, "color2_hex": c2,
        "sprite": _rel(png),
        "source": _rel(image_path),
        "confidence": seen.get("confidence", 0.5),
        "created": time.time(),
    }
    roster.append(critter)
    say(f"{who['name']} joined the farm  ({time.time() - t0:.1f}s)")
    return critter


def safe_process(image_path, progress=None):
    """Never raise -- returns (critter | None, error_message | None)."""
    try:
        return process(image_path, progress), None
    except Exception as e:     # noqa: BLE001
        traceback.print_exc()
        return None, str(e)
