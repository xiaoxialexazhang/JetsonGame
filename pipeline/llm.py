"""Thin Anthropic wrapper: one shared client, plus a forgiving JSON extractor."""
from __future__ import annotations

import base64
import io
import json
import re

from PIL import Image

import config

# The anthropic SDK is imported lazily so the fully-local path runs on a Jetson
# where it was never pip-installed.
_client = None


def client():
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise RuntimeError(
                "the anthropic package is not installed (pip install anthropic)"
            ) from e
        _client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def image_block(path, max_edge: int = 1024):
    """Downscale + base64 an image into a Claude content block."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_edge, max_edge))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88)
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.b64encode(buf.getvalue()).decode(),
        },
    }


def extract_json(text: str):
    """Claude sometimes wraps JSON in prose or a fence. Dig it out."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # fall back to the outermost {...}
    start, depth = None, 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
    raise ValueError(f"no JSON found in model output:\n{text[:600]}")


def ask(model, system, content, max_tokens=1600, temperature=0.6, prefill=None):
    """Single-turn call. `content` is a string or a list of content blocks."""
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    messages = [{"role": "user", "content": content}]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})
    resp = client().messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=messages,
    )
    out = "".join(b.text for b in resp.content if b.type == "text")
    return (prefill + out) if prefill else out
