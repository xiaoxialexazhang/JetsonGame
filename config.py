"""Central config. Everything tweakable lives here."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------- paths
DATA = ROOT / "data"
INPUT_DIR = DATA / "input"        # raw webcam snapshots
CROP_DIR = DATA / "crops"         # cropped subject (debug)
AVATAR_DIR = DATA / "avatars"     # generated sprite PNGs
SPEC_DIR = DATA / "specs"         # raw shape-primitive JSON from Claude (debug)
ROSTER = DATA / "critters.json"   # persisted list of everyone we've caught

for _d in (INPUT_DIR, CROP_DIR, AVATAR_DIR, SPEC_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- api
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

VISION_MODEL = os.getenv("VISION_MODEL", "claude-sonnet-4-5")
ARTIST_MODEL = os.getenv("ARTIST_MODEL", "claude-sonnet-4-5")
CHAT_MODEL = os.getenv("CHAT_MODEL", "claude-haiku-4-5-20251001")

# Set OFFLINE=1 to force the fully-local path even when a key and wifi exist.
# Use this to rehearse the demo exactly as it will run if the venue wifi dies.
OFFLINE = os.getenv("OFFLINE", "0").strip().lower() in ("1", "true", "yes", "on")

# ---------------------------------------------------------------- local models
# on-device species recognition (optional -- falls back to a generic critter)
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "mobilenet_v3_large")
LOCAL_CONF = float(os.getenv("LOCAL_CONF", "0.22"))   # folded-bucket threshold

# local dialogue
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60"))

# ---------------------------------------------------------------- camera
CAM_INDEX = int(os.getenv("CAM_INDEX", "0"))
CAM_W = int(os.getenv("CAM_W", "1280"))
CAM_H = int(os.getenv("CAM_H", "720"))

# ---------------------------------------------------------------- sprite
SPRITE_PX = 32          # logical pixel-art canvas (32x32, Stardew-ish)
SPRITE_SCALE = 5        # nearest-neighbour upscale -> 160px png on disk
DRAW_SIZE = 64          # how big a critter is drawn in the world

# ---------------------------------------------------------------- window
SCREEN_W = int(os.getenv("SCREEN_W", "1280"))
SCREEN_H = int(os.getenv("SCREEN_H", "800"))
FPS = 60
CHAT_BAR_H = 116        # bottom conversation bar
TILE = 32               # grass tile size

# ---------------------------------------------------------------- world
WALK_SPEED = 22.0       # px / second -- deliberately slow & cozy
IDLE_MIN, IDLE_MAX = 1.2, 4.5

# ---------------------------------------------------------------- palette (Stardew-ish)
GRASS_A = (110, 168, 62)
GRASS_B = (98, 154, 54)
GRASS_C = (122, 180, 70)
DIRT_A = (150, 110, 74)
DIRT_B = (134, 96, 64)
FENCE = (140, 96, 58)
FENCE_D = (96, 62, 36)
BLOSSOM = (238, 160, 196)
BLOSSOM_D = (214, 126, 168)
TRUNK = (110, 74, 48)
UI_BG = (54, 40, 34)
UI_BG2 = (76, 56, 46)
UI_EDGE = (222, 198, 158)
INK = (44, 32, 28)
CREAM = (250, 240, 214)
