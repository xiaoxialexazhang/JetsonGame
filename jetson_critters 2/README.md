# Jetson Critters

Point the Jetson's camera at an animal. It recognises the species, and that animal
appears in your sanctuary. Click it and talk to it — the reply comes from a local
LLM running on the Jetson, in character.

That's the whole thing. No coins, no trading, no economy.

## Scope

**In**

- Live camera capture (CSI via `nvarguscamerasrc`, or any USB camera)
- On-device species recognition, folded down to a small roster
- Captured animals wander around a sanctuary and persist between runs
- Click any animal → chat with it via a local LLM, each with its own persona

**Out** — removed deliberately

- Coins, currency, prices
- Trading, marketplace, inventory value
- Levelling, quests, breeding

## Species

`cat` · `goat` · `dog` · `cow` · `horse` · `bird` · `rabbit`

Everything about a species lives in one entry in `critters/species.py`: which
ImageNet classes map to it, how it's drawn, and who it is. Adding an eighth
species is one dict entry and no other edits.

A note on the goat: ImageNet-1k has no plain "goat" class, so the goat is matched
from the closest horned caprids — `ram`, `bighorn`, `ibex` (indices 348–350). It
recognises a real goat reliably in practice, but if you want it tighter, swap in a
fine-tuned head and update `imagenet_ranges`.

## Install

On the Jetson:

```bash
pip install pygame numpy requests
```

Do **not** `pip install opencv-python` on a Jetson — JetPack already ships an
OpenCV built with GStreamer, and the pip wheel will shadow it and break the CSI
pipeline. Confirm yours is the right one:

```bash
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep -i gstreamer
```

Then torch + torchvision from the NVIDIA wheel index that matches your JetPack
version (not PyPI — the PyPI wheels have no CUDA for aarch64):
<https://developer.download.nvidia.com/compute/redist/jp/>

Then the local model:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3.2:3b
```

`llama3.2:3b` is the default because it fits comfortably in Orin Nano memory
alongside the vision model. On an AGX, `qwen2.5:7b` gives noticeably better
in-character replies — pass `--ollama-model qwen2.5:7b`.

## Run

```bash
python run.py                          # CSI camera
python run.py --camera 0               # USB webcam
python run.py --camera clips/cat.mp4   # video file, for testing off-device
```

Point the camera at a cat. The bar under the preview fills as the classifier keeps
agreeing with itself; when it's full, the cat drops into the sanctuary and a toast
confirms it. Click the cat, click the text box, type, hit Enter.

### Controls

| Input | Action |
|---|---|
| Click a critter | Select it and focus the chat box |
| Enter | Send message |
| Tab | Cycle through critters |
| `1`–`7` | Spawn a species by hand (demo without a camera) |
| `R` | Release the selected critter |
| `S` | Save now (it also autosaves on capture and exit) |
| `C` | Re-check the Ollama connection |
| Esc | Unfocus the text box, then quit |

The three chips in the header show camera / vision / LLM status. Green means live.
If the LLM chip is red, `ollama serve` isn't running or the model isn't pulled —
the game still works, animals just reply with a confused noise.

## Tuning

Everything below is settable by flag or env var; see `critters/config.py`.

| What | Env var | Default |
|---|---|---|
| Confidence to count a frame | `CRITTERS_CONF` | `0.35` |
| Agreeing frames before capture | `CRITTERS_STREAK` | `8` |
| Seconds before re-capturing a species | `CRITTERS_COOLDOWN` | `12` |
| Run inference every N frames | `CRITTERS_INFER_EVERY` | `5` |
| Classifier | `CRITTERS_MODEL` | `mobilenet_v3_large` |
| Local model | `OLLAMA_MODEL` | `llama3.2:3b` |

If capture feels sluggish on an Orin Nano, raise `CRITTERS_INFER_EVERY` — the
render loop stays at 60 fps regardless, since inference and chat both run off the
main thread.

## Test

```bash
python smoke_test.py
```

Runs the full pipeline headless with a fake camera and fake recogniser: capture →
critter in world → chat message → reply → save → reload. Needs no camera, no
Jetson, and no Ollama. It falls back to a stubbed pygame if pygame isn't
installed, so it runs in CI too (that path checks logic, not pixels).

## Layout

```
run.py            entry point + CLI
smoke_test.py     end-to-end headless test
critters/
  config.py       every tunable, env-overridable
  camera.py       threaded CSI / USB / file capture
  vision.py       classifier + ImageNet→species folding + capture streak
  species.py      the roster: recognition, appearance, persona
  world.py        critters, wandering, selection, save/load
  chat.py         Ollama client, personas, threaded requests
  sprites.py      procedural critter drawing (no art assets)
  ui.py           sanctuary view, camera HUD, chat panel
save/             sanctuary.json + capture snapshots (created on first run)
```

## Known limits

- Recognition is whole-frame classification, not detection — one animal at a time,
  and it wants the animal filling a decent share of the frame. If you need several
  at once, swap `TorchRecognizer` for a detector; `RecognitionWorker` doesn't care
  what produces the `Detection`.
- Chat history is capped at the last 12 turns per critter. Older messages stay in
  the save file but aren't sent to the model.
- The persona holds well for a few turns on a 3B model, then drifts. Bigger model
  or a periodic system-prompt reinjection if that matters.
