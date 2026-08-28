"""data/critters.json read/write.

Deliberately imports nothing from the LLM stack so the offline tools
(seed_demo, contact_sheet) work with no anthropic SDK and no API key.
"""
from __future__ import annotations

import json

import config


def load() -> list[dict]:
    if not config.ROSTER.exists():
        return []
    try:
        data = json.loads(config.ROSTER.read_text())
        return data if isinstance(data, list) else []
    except Exception:      # noqa: BLE001 - a corrupt roster must not kill the demo
        print("[roster] could not parse critters.json, starting empty")
        return []


def save(items: list[dict]):
    config.ROSTER.write_text(json.dumps(items, indent=2))


def append(item: dict):
    items = load()
    items.append(item)
    save(items)
