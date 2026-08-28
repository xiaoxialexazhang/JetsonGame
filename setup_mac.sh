#!/usr/bin/env bash
# Run Critter World on a Mac -- the fastest way to see it working before the
# Jetson is involved. Uses the built-in webcam.
set -e

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null; then
  echo "python3 not found. Install it with: brew install python@3.12"
  exit 1
fi

echo "==> venv"
python3 -m venv .venv
source .venv/bin/activate

echo "==> deps"
pip install --upgrade pip -q
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "==> created .env -- open it and paste your ANTHROPIC_API_KEY"
fi

cat <<'EOF'

==> done. Next:

  source .venv/bin/activate

  # 1. no key, no camera needed -- proves the renderer and the game loop work
  python3 tools/seed_demo.py --reset
  python3 main.py --no-camera --offline

  # 2. add your key to .env, then check what's reachable
  python3 -c "from pipeline import backends; backends.refresh()"

  # 3. one real capture through Claude, no game window
  python3 tools/test_pipeline.py path/to/a/photo.jpg

  # 4. the whole thing, using your Mac's webcam
  python3 main.py

macOS camera note: the first time you run step 4, macOS must grant camera
access to whatever is running python -- Terminal, iTerm, or VS Code. If the
preview panel stays black, check
  System Settings > Privacy & Security > Camera
and restart the terminal app after enabling it.

EOF
