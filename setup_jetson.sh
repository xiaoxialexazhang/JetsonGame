#!/usr/bin/env bash
# One-shot bring-up on a fresh Jetson Orin Nano (JetPack 5 or 6).
set -e

echo "==> apt deps"
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-opencv v4l-utils libsdl2-2.0-0

echo "==> venv (with system opencv visible)"
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

echo "==> python deps"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> cameras found:"
ls -1 /dev/video* 2>/dev/null || echo "  (none -- plug the USB webcam in)"
v4l2-ctl --list-devices 2>/dev/null || true

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "==> created .env -- open it and paste your ANTHROPIC_API_KEY"
fi

echo ""
echo "next:"
echo "  source .venv/bin/activate"
echo "  python3 tools/seed_demo.py       # offline sanity check"
echo "  python3 main.py --no-camera      # see the world"
echo "  python3 tools/test_camera.py     # then the camera"
echo "  python3 main.py                  # the whole thing"
