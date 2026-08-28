"""What can we actually reach right now?

Detected once at startup and re-checkable at runtime (the C key in game).
Every pipeline stage asks this module which implementation to use, so the whole
app degrades cleanly from "full Claude" down to "no network at all" without any
stage needing to know about the others.

    stage        online (Claude)              offline (local)
    ---------------------------------------------------------------------
    species      Claude vision, any animal    torchvision ImageNet + Haar face
    colours      numpy k-means                numpy k-means        (same, local)
    avatar       Claude draws shapes          species template, recoloured
    persona      Claude invents one           name/persona tables
    dialogue     Claude Haiku                 Ollama, else canned lines
"""
from __future__ import annotations

import socket
import urllib.request
from dataclasses import dataclass

import config


@dataclass
class Backends:
    claude: bool = False
    ollama: bool = False
    torch: bool = False
    note: str = ""

    @property
    def can_chat(self) -> bool:
        return self.claude or self.ollama

    def summary(self) -> str:
        bits = [
            f"claude={'yes' if self.claude else 'no'}",
            f"ollama={'yes' if self.ollama else 'no'}",
            f"torch={'yes' if self.torch else 'no'}",
        ]
        return "  ".join(bits)


def _tcp_reachable(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _claude_ok(timeout: float) -> bool:
    if config.OFFLINE:
        return False
    if not config.ANTHROPIC_API_KEY:
        return False
    return _tcp_reachable("api.anthropic.com", 443, timeout)


def _ollama_ok(timeout: float) -> bool:
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_URL}/api/tags", timeout=timeout) as r:
            return r.status == 200
    except Exception:      # noqa: BLE001
        return False


def _torch_ok() -> bool:
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
        return True
    except Exception:      # noqa: BLE001
        return False


def detect(timeout: float = 2.0) -> Backends:
    b = Backends(
        claude=_claude_ok(timeout),
        ollama=_ollama_ok(min(timeout, 1.5)),
        torch=_torch_ok(),
    )
    if config.OFFLINE:
        b.note = "OFFLINE=1, Claude disabled by config"
    elif not config.ANTHROPIC_API_KEY:
        b.note = "no ANTHROPIC_API_KEY"
    elif not b.claude:
        b.note = "api.anthropic.com unreachable"
    print(f"[backends] {b.summary()}" + (f"   ({b.note})" if b.note else ""))
    return b


# module-level singleton, refreshed on demand
CURRENT = Backends()


def refresh(timeout: float = 2.0) -> Backends:
    global CURRENT
    CURRENT = detect(timeout)
    return CURRENT
