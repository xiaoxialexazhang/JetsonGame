"""Talking to a critter. One Conversation per critter, history kept in memory.

Three backends, picked at send time so the demo survives the wifi dropping
mid-conversation:
    Claude Haiku  ->  Ollama (llama3.2:3b, local)  ->  canned in-character lines
"""
from __future__ import annotations

import json
import random
import urllib.error
import urllib.request

import config
from pipeline import backends

STYLE = """
You are a character in a cozy pixel farm game. Stay fully in character.

Rules:
- Reply in 1-2 SHORT sentences. Max 30 words. This goes in a small speech bubble.
- Speak plain, warm, playful English. No emoji, no asterisk actions, no narration.
- You are a real animal on this farm: reference your body, the grass, the weather,
  the other animals, food, naps. Never mention being an AI or a program.
- If asked something you couldn't know, answer the way an animal would guess.
"""

# Used only when there is no Claude and no Ollama. Deliberately vague so they
# fit almost any question, and varied so a demo doesn't repeat itself.
CANNED = [
    "Hm. I'd have to think about that after my nap.",
    "You know, nobody's ever asked me that out here.",
    "Probably. Most things are, if you wait long enough.",
    "I was going to say something clever, then I saw a bug.",
    "That depends entirely on whether there's food involved.",
    "Ask me again when the sun's over the fence.",
    "I've got a strong opinion on that and I've forgotten it.",
    "Sure. But keep it between us and the grass.",
]


class Conversation:
    def __init__(self, critter: dict):
        self.critter = critter
        self.history: list[dict] = []
        self.system = (
            f"{critter.get('persona', '')}\n\n"
            f"Your name is {critter['name']}, {critter.get('title', '')}. "
            f"You are a {critter['color1']} {critter['species']} with "
            f"{critter['color2']} markings. You were photographed by the farmer's "
            f"camera and now live on this farm.\n{STYLE}"
        )

    # ------------------------------------------------------------------
    def reply(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        text = ""
        b = backends.CURRENT

        if b.claude:
            try:
                text = self._claude()
            except Exception as e:      # noqa: BLE001
                print(f"[chat] Claude failed ({e}); trying Ollama")
        if not text and b.ollama:
            try:
                text = self._ollama()
            except Exception as e:      # noqa: BLE001
                print(f"[chat] Ollama failed ({e}); using canned line")
        if not text:
            text = random.choice(CANNED)

        text = _tidy(text)
        self.history.append({"role": "assistant", "content": text})
        return text

    # ------------------------------------------------------------------
    def _claude(self) -> str:
        from pipeline import llm
        resp = llm.client().messages.create(
            model=config.CHAT_MODEL,
            max_tokens=180,
            temperature=1.0,
            system=self.system,
            messages=self.history[-12:],
        )
        return "".join(bl.text for bl in resp.content if bl.type == "text").strip()

    def _ollama(self) -> str:
        payload = {
            "model": config.OLLAMA_MODEL,
            "stream": False,
            "options": {"temperature": 0.9, "num_predict": 120},
            "messages": [{"role": "system", "content": self.system}] + self.history[-12:],
        }
        req = urllib.request.Request(
            f"{config.OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT) as r:
            body = json.loads(r.read().decode())
        return (body.get("message") or {}).get("content", "").strip()


def _tidy(text: str) -> str:
    """Small local models like to narrate and over-explain. Trim it to bubble size."""
    text = (text or "").strip().strip('"')
    text = text.replace("*", "").replace("\n", " ").strip()
    if not text:
        return "..."
    words = text.split()
    if len(words) > 40:
        text = " ".join(words[:40]).rstrip(",;:") + "..."
    return text
