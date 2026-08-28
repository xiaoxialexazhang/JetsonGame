"""Stage 3+4 -- (species, colour1, colour2) -> a Stardew-style pixel sprite.

Claude acts as the pixel artist but only outputs *anatomy as shapes*; the
palette ramps, outline and resolution are applied by pipeline/sprite.py so the
style is identical across every animal.
"""
from __future__ import annotations

import json
import time

import config
from pipeline import backends, llm, sprite, templates

SYSTEM = """You are a pixel artist for a cozy farm game in the exact visual style of Stardew Valley.

You draw ONE front-facing animal on a 32x32 grid using simple shape primitives.
Output ONLY a JSON object. No prose, no markdown fence.

COORDINATES
- Origin (0,0) is TOP-LEFT. x grows right, y grows DOWN.
- Keep every shape inside x:2..29 and y:2..30. A dark outline is added around
  your silhouette afterwards, so never touch the very edge.
- The animal should stand on the ground: its lowest pixels around y=28..30.
- The animal should FILL the canvas: roughly 22-27 px wide and 20-28 px tall.
  Small timid sprites look bad. Go big.

SHAPES  (all coordinates are integers in the 32x32 space)
  {"shape":"ellipse","cx":16,"cy":19,"rx":10,"ry":8,"fill":"base","z":5}
  {"shape":"rect","x":10,"y":25,"w":3,"h":5,"fill":"shade","z":2}
  {"shape":"poly","points":[[7,12],[10,3],[14,13]],"fill":"base","z":6}
  {"shape":"pixel","x":12,"y":17,"w":2,"h":3,"fill":"eye","z":9}
  "z" = paint order, LOW is painted first / behind. Use 1..10.
  Add "mirror": true to any shape and its left/right mirror twin is drawn for
  free. USE THIS for the pair of ears, the pair of front legs, cheek blush, etc.
  Only give coordinates for the LEFT-hand one (x < 16).

FILLS (use these names only)
  "base"          the animal's main colour
  "shade"         darker version of base -- belly shadow, underside, back legs
  "light"         lighter version of base -- top of head/back highlight
  "accent"        the animal's second colour -- patches, chest, muzzle, wings
  "accent_shade", "accent_light"
  "dark"          near-black, for hard details
  "eye"           eye dots        "eye_hl"  tiny white eye glint
  "white", "cream", "pink" (nose, tongue, inner ear, blush), "hoof"

STARDEW STYLE RULES -- follow all of them
1. Chunky and cute. One big rounded body ellipse is the foundation. Heads are
   large relative to the body; legs are short 2-4 px stubs.
2. Front-facing, symmetric, looking straight at the player.
3. Eyes are simple dark rectangles 2px wide, 2-3px tall, placed in the upper
   third of the head, about 5-7 px apart. No pupils, no detail. Optionally one
   1x1 "eye_hl" pixel in the upper-left of each eye.
4. Shade the LOWER portion of the body with "shade" and put a small "light"
   patch on the UPPER back/head. Three tones total is the whole look.
5. Silhouette carries the identity: pointed triangle ears for a cat, floppy
   ellipse ears for a dog, horns for a goat, a comb+beak for a chicken, a fin
   and tail for a fish, hair+shirt for a person. Exaggerate the one feature
   that makes the species instantly readable.
6. Use "accent" for a real marking -- a chest bib, a saddle patch, a muzzle,
   wings, a belly. Do not just tint the whole animal.
7. 12-22 shapes total. Fewer, bolder shapes beat many tiny ones.

LEG GEOMETRY -- get this right or the animal looks like a floating blob:
  * the main body ellipse must END around y=26 (e.g. cy=17..19 with ry=8..9),
  * leg rects run y=24..30 at LOW z (1-3) so the body covers their tops and only
    3-4 px of leg pokes out below,
  * add one {"shape":"rect","x":15,"y":26,"w":2,"h":4,"fill":"outline","z":9}
    to notch a gap between the two front legs.
  Legless animals (fish, snake, bird in flight) skip all of this.

WORKED EXAMPLE -- an orange cat with a cream chest:
{"species":"cat","parts":[
 {"shape":"rect","x":9,"y":24,"w":4,"h":6,"fill":"shade","z":2,"mirror":true},
 {"shape":"poly","points":[[23,20],[30,10],[27,23]],"fill":"shade","z":3},
 {"shape":"poly","points":[[6,12],[8,1],[14,13]],"fill":"base","z":4,"mirror":true},
 {"shape":"poly","points":[[8,11],[9,5],[12,12]],"fill":"pink","z":5,"mirror":true},
 {"shape":"ellipse","cx":16,"cy":17,"rx":10,"ry":9,"fill":"base","z":6},
 {"shape":"ellipse","cx":16,"cy":23,"rx":6,"ry":4,"fill":"accent","z":7},
 {"shape":"ellipse","cx":16,"cy":11,"rx":7,"ry":4,"fill":"light","z":7},
 {"shape":"pixel","x":11,"y":15,"w":2,"h":3,"fill":"eye","z":9,"mirror":true},
 {"shape":"pixel","x":11,"y":15,"w":1,"h":1,"fill":"eye_hl","z":10,"mirror":true},
 {"shape":"pixel","x":15,"y":19,"w":2,"h":1,"fill":"pink","z":9},
 {"shape":"pixel","x":5,"y":18,"w":3,"h":1,"fill":"dark","z":9,"mirror":true},
 {"shape":"rect","x":15,"y":26,"w":2,"h":4,"fill":"outline","z":9}
]}

Return the same JSON shape: {"species": "...", "parts": [ ... ]}"""


def _prompt(species, c1_name, c2_name, c1_hex, c2_hex, build, vibe):
    return f"""Draw this animal.

species:        {species}
main colour:    {c1_name} ({c1_hex})   -> this is "base"
second colour:  {c2_name} ({c2_hex})   -> this is "accent"
observed build: {build or "(none given)"}
observed vibe:  {vibe or "(none given)"}

The two colours above were measured from a real photo, so the sprite MUST read
as a {c1_name} {species} with {c2_name} markings. Make the {species} instantly
recognisable from its silhouette alone. JSON only."""


def design(species, color1_hex, color2_hex, color1_name, color2_name,
           build="", vibe="", retries: int = 2) -> dict:
    """Claude draws the anatomy when reachable; otherwise a pre-authored template
    for this species. Either way the COLOURS are the ones measured from the photo,
    so the sprite still reflects the real animal."""
    if not backends.CURRENT.claude:
        spec = templates.spec_for(species)
        print(f"[avatar] offline -> '{spec.get('_template')}' template, "
              f"recoloured {color1_hex} + {color2_hex}")
        return spec

    last = None
    for attempt in range(retries + 1):
        try:
            raw = llm.ask(
                config.ARTIST_MODEL,
                SYSTEM,
                _prompt(species, color1_name, color2_name, color1_hex, color2_hex, build, vibe),
                max_tokens=2400,
                temperature=0.85 if attempt else 0.7,
                prefill="{",
            )
            spec = llm.extract_json(raw)
            parts = spec.get("parts") or spec.get("shapes") or []
            if len(parts) >= 5:
                spec["parts"] = parts
                return spec
            last = ValueError(f"only {len(parts)} shapes returned")
        except Exception as e:      # noqa: BLE001 - we genuinely want any failure
            last = e
            time.sleep(0.6)
    print(f"[avatar] artist failed ({last}); using the {species} template instead")
    return templates.spec_for(species)


def make(species, color1_hex, color2_hex, color1_name, color2_name,
         build="", vibe="", stem="critter") -> tuple[str, dict]:
    """Design + rasterise. Returns (png_path, spec)."""
    spec = design(species, color1_hex, color2_hex, color1_name, color2_name, build, vibe)
    (config.SPEC_DIR / f"{stem}.json").write_text(json.dumps(spec, indent=2))
    png = config.AVATAR_DIR / f"{stem}.png"
    sprite.render(spec, color1_hex, color2_hex, png)
    return str(png), spec
