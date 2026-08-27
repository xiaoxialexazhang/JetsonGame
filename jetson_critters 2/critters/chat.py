"""Talking to your critters, via a local LLM served by Ollama on the Jetson.

Requests run on a worker thread and results arrive through a queue, so the game
loop never stalls waiting on a token.
"""

from __future__ import annotations

import queue
import threading
from typing import List, Optional

import requests

from .world import Critter, Message

SYSTEM_TEMPLATE = """You are {name}, a {species} living in a small sanctuary on someone's desk.

Your nature: {persona}

A personal quirk of yours: you are {trait}.

Rules for how you speak:
- You are an animal, not an assistant. Never offer help, lists, or advice unless it's animal advice.
- Keep replies to 1-3 short sentences. This is a chat bubble, not an essay.
- Stay in character no matter what the human says.
- You may use one short physical action in *asterisks* per reply, at most.
- You know the human found you with a camera and brought you here. You're fine with it.
"""


class ChatError(Exception):
    pass


class OllamaChat:
    def __init__(self, base_url: str, model: str, timeout: float = 60.0, max_history: int = 12):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_history = max_history
        self.results: "queue.Queue[tuple[str, str, bool]]" = queue.Queue()
        self.status: str = "unchecked"
        self._inflight: set[str] = set()
        self._lock = threading.Lock()

    # -- health ---------------------------------------------------------
    def check(self) -> bool:
        """Ping Ollama and confirm the configured model is pulled."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=4)
            resp.raise_for_status()
            names = [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception as exc:
            self.status = f"offline ({type(exc).__name__})"
            return False

        base = self.model.split(":")[0]
        if any(n == self.model or n.split(":")[0] == base for n in names):
            self.status = f"ready · {self.model}"
            return True
        self.status = f"model '{self.model}' not pulled"
        return False

    # -- prompting -------------------------------------------------------
    def _system_prompt(self, critter: Critter) -> str:
        sp = critter.species
        return SYSTEM_TEMPLATE.format(
            name=critter.name,
            species=sp.display.lower(),
            persona=sp.persona,
            trait=critter.trait or "unremarkable, and a bit sensitive about it",
        )

    def _messages(self, critter: Critter) -> List[dict]:
        msgs = [{"role": "system", "content": self._system_prompt(critter)}]
        recent = [m for m in critter.history if m.role in ("user", "assistant")][-self.max_history :]
        for m in recent:
            msgs.append({"role": m.role, "content": m.text})
        return msgs

    # -- sending ---------------------------------------------------------
    def send(self, critter: Critter, text: str) -> bool:
        """Queue a user message. Returns False if this critter is already replying."""
        with self._lock:
            if critter.id in self._inflight:
                return False
            self._inflight.add(critter.id)

        critter.history.append(Message("user", text))
        critter.thinking = True
        payload = {
            "model": self.model,
            "messages": self._messages(critter),
            "stream": False,
            "options": {"temperature": 0.85, "num_predict": 160},
        }
        threading.Thread(
            target=self._worker, args=(critter.id, payload), name=f"chat-{critter.id}", daemon=True
        ).start()
        return True

    def _worker(self, critter_id: str, payload: dict) -> None:
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "").strip()
            if not content:
                raise ChatError("empty response from model")
            self.results.put((critter_id, content, True))
        except Exception as exc:
            self.results.put((critter_id, self._fallback(exc), False))
        finally:
            with self._lock:
                self._inflight.discard(critter_id)

    @staticmethod
    def _fallback(exc: Exception) -> str:
        name = type(exc).__name__
        if name in ("ConnectionError", "ConnectTimeout"):
            return "*stares blankly* (no local model reachable — is `ollama serve` running?)"
        if "Timeout" in name:
            return "*slow blink* (the model took too long to answer)"
        return f"*confused noise* ({name}: {exc})"

    # -- draining ---------------------------------------------------------
    def drain(self, lookup) -> None:
        """Move finished replies into the right critter's history. Call once per frame."""
        while True:
            try:
                critter_id, text, ok = self.results.get_nowait()
            except queue.Empty:
                return
            critter: Optional[Critter] = lookup(critter_id)
            if critter is None:
                continue
            critter.history.append(Message("assistant", text))
            critter.thinking = False
            if not ok:
                self.status = "error on last reply"
