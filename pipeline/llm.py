"""Thin LLM client, plus a forgiving JSON extractor.

Talks to an OpenAI-compatible *or* Anthropic-compatible endpoint, so the same
code works against api.anthropic.com directly and against a corporate gateway
like https://inference-api.nvidia.com that fronts Bedrock.

Which shape the endpoint speaks is detected once, lazily, on the first call and
cached -- or pinned explicitly with API_STYLE=openai / anthropic in .env.

Only `requests` is needed; the anthropic SDK is no longer a dependency.
"""
from __future__ import annotations

import base64
import io
import json
import re
import threading

import requests
from PIL import Image

import config


class LLMError(RuntimeError):
    """An API call failed. The message carries the server's own error body."""


# --------------------------------------------------------------- endpoints
def _base() -> str:
    """Endpoint root with any trailing /v1 stripped, so we can append paths."""
    url = config.API_ENDPOINT.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url


def _url(style: str) -> str:
    if style == "anthropic":
        return f"{_base()}/v1/messages"
    return f"{_base()}/v1/chat/completions"


def _headers(style: str) -> dict:
    if not config.API_KEY:
        raise LLMError(
            "No API key set. Copy .env.example to .env and fill in INFERENCE_API_KEY."
        )
    # Bearer is what the NVIDIA gateway wants; api.anthropic.com wants x-api-key.
    # Sending both is harmless and means one config works against either.
    h = {
        "content-type": "application/json",
        "authorization": f"Bearer {config.API_KEY}",
    }
    if style == "anthropic":
        h["x-api-key"] = config.API_KEY
        h["anthropic-version"] = "2023-06-01"
    return h


# --------------------------------------------------------------- style probe
_style: str | None = None
_style_lock = threading.Lock()


def style() -> str:
    """Which request shape does the endpoint speak? Probed once, then cached."""
    global _style
    with _style_lock:
        if _style is not None:
            return _style
        pinned = (config.API_STYLE or "auto").strip().lower()
        if pinned in ("openai", "anthropic"):
            _style = pinned
            return _style

        probe = {"max_tokens": 4, "messages": [{"role": "user", "content": "hi"}]}
        for cand in ("openai", "anthropic"):
            try:
                r = requests.post(
                    _url(cand),
                    headers=_headers(cand),
                    json=dict(probe, model=config.model_for(cand)),
                    timeout=20,
                )
            except requests.RequestException:
                continue
            # 2xx obviously works. 400 means the route exists and parsed our
            # body but disliked a field -- still the right shape. 404/405 means
            # wrong route entirely; 401/403 means the auth header is wrong.
            if r.status_code < 300 or r.status_code == 400:
                _style = cand
                print(f"[llm] endpoint speaks {cand}-style (probe HTTP {r.status_code})")
                return _style

        _style = "openai"
        print("[llm] could not probe endpoint; assuming openai-style")
        return _style


def reset_style() -> None:
    """Forget the cached probe (the in-game C key re-checks connectivity)."""
    global _style
    with _style_lock:
        _style = None


# --------------------------------------------------------------- content
def image_block(path, max_edge: int = 1024):
    """Downscale + base64 an image into a content block.

    Always returns the Anthropic shape; `_to_openai` rewrites it when needed,
    so callers never have to care which endpoint is in play.
    """
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


def _to_openai(content):
    """Anthropic content blocks -> OpenAI content parts."""
    if isinstance(content, str):
        return content
    parts = []
    for b in content:
        if b.get("type") == "text":
            parts.append({"type": "text", "text": b["text"]})
        elif b.get("type") == "image":
            src = b["source"]
            parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{src['media_type']};base64,{src['data']}"
                },
            })
    return parts


# --------------------------------------------------------------- requests
def _post(style_: str, payload: dict, timeout: float) -> dict:
    try:
        r = requests.post(_url(style_), headers=_headers(style_),
                          json=payload, timeout=timeout)
    except requests.RequestException as e:
        raise LLMError(f"could not reach {_url(style_)}: {e}") from e

    if r.status_code >= 300:
        body = r.text[:500].replace("\n", " ")
        hint = ""
        if r.status_code in (401, 403):
            hint = "  -> key rejected; check INFERENCE_API_KEY"
        elif r.status_code == 404:
            hint = f"  -> no such route; check API_ENDPOINT (and model '{payload.get('model')}')"
        elif r.status_code == 400:
            hint = f"  -> bad request; model '{payload.get('model')}' may not exist on this endpoint"
        raise LLMError(f"HTTP {r.status_code} from {_url(style_)}: {body}{hint}")

    try:
        return r.json()
    except json.JSONDecodeError as e:
        raise LLMError(f"non-JSON response: {r.text[:300]}") from e


def _text_from(style_: str, body: dict) -> str:
    if style_ == "anthropic":
        return "".join(b.get("text", "") for b in body.get("content", [])
                       if b.get("type") == "text")
    choices = body.get("choices") or []
    if not choices:
        raise LLMError(f"no choices in response: {json.dumps(body)[:300]}")
    msg = choices[0].get("message") or {}
    out = msg.get("content") or ""
    # Some gateways return content as a list of parts rather than a string.
    if isinstance(out, list):
        out = "".join(p.get("text", "") for p in out if isinstance(p, dict))
    return out


def converse(model, system, messages, max_tokens=1600, temperature=0.6,
             timeout=90.0) -> str:
    """Multi-turn call. `messages` is a list of {role, content} dicts."""
    st = style()
    if st == "anthropic":
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        }
    else:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": ([{"role": "system", "content": system}] if system else []) +
                        [{"role": m["role"], "content": _to_openai(m["content"])}
                         for m in messages],
        }
    return _text_from(st, _post(st, payload, timeout))


def ask(model, system, content, max_tokens=1600, temperature=0.6, prefill=None,
        timeout=90.0) -> str:
    """Single-turn call. `content` is a string or a list of content blocks.

    `prefill` seeds the assistant's reply (we use "{" to force bare JSON). Not
    every gateway accepts a trailing assistant turn, so if it's rejected we
    retry without it -- extract_json is forgiving enough to cope either way.
    """
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    msgs = [{"role": "user", "content": content}]

    dropped = False
    if prefill:
        try:
            out = converse(model, system, msgs + [{"role": "assistant", "content": prefill}],
                           max_tokens, temperature, timeout)
            return prefill + out
        except LLMError as e:
            if "HTTP 400" not in str(e):
                raise
            print("[llm] endpoint rejected the prefill turn; retrying without it")
            dropped = True

    out = converse(model, system, msgs, max_tokens, temperature, timeout)
    # Without the prefill the model normally emits the opening brace itself.
    # If it didn't, put it back rather than failing the parse downstream.
    if dropped and prefill.strip() == "{" and "{" not in out:
        out = prefill + out
    return out


# --------------------------------------------------------------- json
def extract_json(text: str):
    """Models sometimes wrap JSON in prose or a fence. Dig it out."""
    text = (text or "").strip()
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


def list_models() -> list:
    """Ask the endpoint what it offers. Returns [] if it has no /v1/models."""
    try:
        r = requests.get(f"{_base()}/v1/models", headers=_headers(style()), timeout=20)
        if r.status_code >= 300:
            return []
        body = r.json()
    except (requests.RequestException, json.JSONDecodeError):
        return []
    data = body.get("data", body if isinstance(body, list) else [])
    out = []
    for m in data:
        name = m.get("id") or m.get("name") if isinstance(m, dict) else str(m)
        if name:
            out.append(name)
    return sorted(out)
