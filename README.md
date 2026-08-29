# Critter World

Point a USB webcam at a living thing on a Jetson Orin Nano. It becomes a
Stardew-Valley-style pixel villager that walks around a farm and talks back.

```
webcam ──▶ 1. species           what is it?
       ──▶ 2. colours           its two dominant colours   (always local)
       ──▶ 3. three text params (species, color1, color2)
       ──▶ 4. avatar            shape spec ──▶ rasteriser ──▶ sprite.png
       ──▶ 5. persona           name, personality, opening line
       ──▶ 6. pygame world      it walks around; click it to talk
```

**It runs with or without a network.** Every stage has a local implementation
and an optional Claude upgrade, chosen at startup by `pipeline/backends.py`:

| stage | online (Claude) | offline (on-device) |
|---|---|---|
| 1 species | Claude vision, any creature, tight bbox | torchvision ImageNet → 17 buckets, + Haar face cascade → `person` |
| 2 colours | *(local either way)* | numpy k-means in the bbox, background-suppressed |
| 4 avatar | Claude invents the anatomy per animal | pre-authored template for that species |
| 5 persona | Claude writes name + personality | local name/persona/greeting tables |
| dialogue | Claude Haiku | Ollama `llama3.2:3b`, else canned in-character lines |

The colours are measured from the real photo in **both** paths, so the
capture → extract → generate story holds up on stage even with the wifi off.
Only the *anatomy* falls back from invented to pre-authored.

Rehearse the offline path deliberately with `python3 main.py --offline`
(or `OFFLINE=1`), which ignores the API key even when it would work.

## Hardware

Jetson Orin Nano · monitor · USB webcam · keyboard + mouse.

## Running it on a Mac first

You do not need the Jetson to develop this. The Mac's built-in webcam works,
and it's a much faster loop.

```bash
cd ~/JetsonGame
bash setup_mac.sh             # venv + deps, creates .env
nano .env                     # paste INFERENCE_API_KEY + DEFAULT_ENDPOINT
source .venv/bin/activate
python3 main.py               # webcam + Claude, the full thing
```

The one macOS gotcha: the terminal app running python needs camera permission
under **System Settings → Privacy & Security → Camera**, and you have to
restart the terminal after granting it. If the preview panel is black, that's
why. `python3 main.py --no-camera` sidesteps it entirely.

## Which API endpoint

The client in `pipeline/llm.py` talks to **either** an OpenAI-compatible or an
Anthropic-compatible endpoint, so the same code works against a corporate
gateway and against Anthropic directly. Two lines in `.env` decide:

```
INFERENCE_API_KEY='sk-...'
DEFAULT_ENDPOINT=https://inference-api.nvidia.com     # NVIDIA gateway (Bedrock)
```

```
INFERENCE_API_KEY=sk-ant-api03-...
DEFAULT_ENDPOINT=https://api.anthropic.com            # Anthropic direct
```

Auth goes out as `Authorization: Bearer` (plus `x-api-key` on the Anthropic
shape, so one config satisfies both). The request shape is **probed once** on
the first call and cached — pin it with `API_STYLE=openai` or `anthropic` to
skip the probe.

Model names differ by endpoint. The gateway prefixes them
(`aws/anthropic/bedrock-claude-opus-5`); Anthropic direct does not
(`claude-opus-5`). Every stage falls back to `DEFAULT_MODEL`, so one line gets
you running, and you override per stage once you know what's available:

```
DEFAULT_MODEL=aws/anthropic/bedrock-claude-opus-5
#VISION_MODEL=...     # identify the animal
#ARTIST_MODEL=...     # draw it (spend here — it decides how the sprite looks)
#CHAT_MODEL=...       # dialogue, wants to be fast
```

`python3 tools/test_api.py --models` lists what your endpoint actually offers,
which is the fastest way to fix a `400`.

## Setup on the Jetson

```bash
git clone git@github.com:xiaoxialexazhang/JetsonGame.git && cd JetsonGame
bash setup_jetson.sh          # apt deps, venv, pip, camera check
nano .env                     # paste INFERENCE_API_KEY + DEFAULT_ENDPOINT (optional)
```

For the on-device recognizer, also install torch + torchvision from NVIDIA's
JetPack wheels (not from PyPI — the PyPI build has no CUDA on aarch64). Without
them the game still runs; faces still resolve to `person` via OpenCV, and
anything else becomes a generic critter in its real colours.

The previous fully-local implementation is preserved untouched under
`legacy/jetson_critters/` — its DeepLabV3 + CIELAB coat/eye extraction is more
sophisticated than the k-means used here and is worth revisiting.

## Bring-up, in order

Do these one at a time. Each step isolates one thing that can break.

```bash
source .venv/bin/activate

# 0. what can this machine reach right now?
python3 tools/test_api.py            # endpoint, key, and all three models

# 1. rasteriser only -- no API, no camera. Look at data/contact_sheet.png.
python3 tools/contact_sheet.py

# 2. the game only -- no API, no camera. 5 hand-made critters walk around.
python3 tools/seed_demo.py --reset
python3 main.py --no-camera

# 3. the camera only -- no API, no game. S saves a snapshot.
python3 tools/test_camera.py

# 4. the API pipeline only -- no game. Runs on the newest file in data/input.
python3 tools/test_pipeline.py

# 5. everything.
python3 main.py
```

## Controls

| key / action | what it does |
|---|---|
| `SPACE` | snapshot whatever the camera sees → run the pipeline → new critter |
| click a critter | walk up and start talking; it says its opening line |
| type + `ENTER` | say something back |
| `ESC` | step away |
| `T` | re-run the pipeline on the newest image in `data/input/` (no camera needed) |
| `R` | reload the roster from disk |
| `C` | re-check what's reachable (use when the wifi comes back mid-demo) |
| `F11` | fullscreen |
| `Q` | quit |

Every API call runs on a worker thread, so the world keeps animating while a
critter is being drawn or is thinking.

## Layout

```
config.py                 every tunable in one file
pipeline/
  backends.py             what's reachable right now -- every stage asks this
  capture.py              threaded webcam grab -> data/input/*.jpg
  vision.py               stage 1  Claude -> species, bbox, build, vibe
  local_vision.py         stage 1  offline: ImageNet buckets + Haar face
  colors.py               stage 2  numpy k-means -> two hex colours + names
  avatar.py               stage 4  Claude -> shape-primitive JSON
  templates.py            stage 4  offline: per-species anatomy + synonym map
  sprite.py               stage 4  JSON -> palette ramps -> outline -> PNG
  persona.py              stage 5  Claude, or local name/persona tables
  roster.py               data/critters.json read/write (no LLM imports)
  orchestrator.py         runs 1-5, appends to the roster
  llm.py                  OpenAI/Anthropic-shape client + JSON extraction
game/
  world.py                main loop, input, job draining
  critter.py              a wandering, clickable sprite
  mapgen.py               procedural grass / path / fences / blossom trees
  ui.py                   speech bubbles, chat bar, camera panel, toasts
  chat.py                 per-critter conversation with history
  jobs.py                 thread -> queue -> main loop plumbing
tools/
  contact_sheet.py        render every demo spec x 6 palettes onto one PNG
  seed_demo.py            populate the farm offline (also the wifi-died fallback)
  test_camera.py          camera-only check
  test_pipeline.py        API-only check
  demo_specs.py           hand-written specs in Claude's output format
```

## How the art stays consistent

Claude never returns an image — it returns *anatomy as shapes* on a 32×32 grid:

```json
{"shape":"ellipse","cx":16,"cy":17,"rx":10,"ry":9,"fill":"base","z":6}
{"shape":"poly","points":[[6,12],[8,1],[14,13]],"fill":"base","z":4,"mirror":true}
```

`pipeline/sprite.py` owns everything that makes it look like Stardew, so the
style can't drift between animals:

- the two measured colours are expanded into a full ramp
  (`base` / `shade` / `light`, `accent` / `accent_shade` / `accent_light`),
- `"mirror": true` draws the left/right twin of ears and legs for free,
- a 1px dark outline is grown around the finished silhouette — this single step
  is most of the Stardew look,
- the sprite is trimmed, bottom-aligned so feet touch the ground, and upscaled
  with nearest-neighbour only.

If the artist call fails or returns garbage, `sprite.fallback_spec()` puts a
generic cute blob on the map rather than crashing the demo.

## Tuning

| symptom | fix |
|---|---|
| colours picked from the wall, not the animal | fill more of the frame; the bbox from stage 1 drives the crop |
| sprites too small on screen | `DRAW_SIZE` in `config.py` (keep it a multiple of 32) |
| critters wander too fast | `WALK_SPEED` |
| replies too long for the bubble | the word cap in `game/chat.py` `STYLE` |
| avatar looks like a blob | check `data/specs/*.json` — the body ellipse must end near y=26 |

## Cost

Roughly one Sonnet vision call + one Sonnet artist call + one Haiku persona
call per capture, then one Haiku call per line of dialogue. A demo session is
cents.
