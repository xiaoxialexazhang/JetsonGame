"""Sanctuary state: the critters you've captured, where they wander, what they remember."""

from __future__ import annotations

import json
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .species import SPECIES, random_name, random_trait


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    text: str
    ts: float = field(default_factory=time.time)


@dataclass
class Critter:
    species_key: str
    name: str
    trait: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    x: float = 0.0
    y: float = 0.0
    heading: float = field(default_factory=lambda: random.uniform(0, math.tau))
    speed: float = field(default_factory=lambda: random.uniform(12.0, 34.0))
    scale: float = field(default_factory=lambda: random.uniform(0.9, 1.15))
    facing: int = 1
    captured_at: float = field(default_factory=time.time)
    snapshot: Optional[str] = None
    history: List[Message] = field(default_factory=list)

    # transient, not persisted
    _pause: float = 0.0
    _bob: float = field(default_factory=lambda: random.uniform(0, math.tau))
    thinking: bool = False

    @property
    def species(self):
        return SPECIES[self.species_key]

    @property
    def radius(self) -> float:
        return 34.0 * self.scale

    def update(self, dt: float, bounds) -> None:
        self._bob += dt * 4.0
        if self._pause > 0:
            self._pause -= dt
            return

        self.x += math.cos(self.heading) * self.speed * dt
        self.y += math.sin(self.heading) * self.speed * dt * 0.5

        left, top, right, bottom = bounds
        pad = self.radius
        if self.x < left + pad or self.x > right - pad:
            self.heading = math.pi - self.heading
            self.x = min(max(self.x, left + pad), right - pad)
        if self.y < top + pad or self.y > bottom - pad:
            self.heading = -self.heading
            self.y = min(max(self.y, top + pad), bottom - pad)

        if math.cos(self.heading) != 0:
            self.facing = 1 if math.cos(self.heading) > 0 else -1

        if random.random() < dt * 0.35:
            self.heading += random.uniform(-0.9, 0.9)
        if random.random() < dt * 0.15:
            self._pause = random.uniform(0.6, 2.4)

    def hit(self, px: float, py: float) -> bool:
        return (px - self.x) ** 2 + (py - self.y * 1.0) ** 2 <= (self.radius * 1.4) ** 2

    # -- serialisation --------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "species_key": self.species_key,
            "name": self.name,
            "trait": self.trait,
            "x": self.x,
            "y": self.y,
            "scale": self.scale,
            "captured_at": self.captured_at,
            "snapshot": self.snapshot,
            "history": [{"role": m.role, "text": m.text, "ts": m.ts} for m in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Critter":
        c = cls(
            species_key=data["species_key"],
            name=data["name"],
            trait=data.get("trait", ""),
            id=data.get("id", uuid.uuid4().hex[:8]),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            scale=data.get("scale", 1.0),
            captured_at=data.get("captured_at", time.time()),
            snapshot=data.get("snapshot"),
        )
        c.history = [Message(m["role"], m["text"], m.get("ts", 0.0)) for m in data.get("history", [])]
        return c


class World:
    def __init__(self, bounds, save_path: Path):
        self.bounds = bounds  # (left, top, right, bottom)
        self.save_path = Path(save_path)
        self.critters: List[Critter] = []
        self.selected_id: Optional[str] = None
        self.last_capture_at: Dict[str, float] = {}
        self.toast: Optional[tuple[str, float]] = None

    # -- population -----------------------------------------------------
    def can_capture(self, species_key: str, cooldown: float) -> bool:
        last = self.last_capture_at.get(species_key, 0.0)
        return (time.time() - last) >= cooldown

    def add_critter(self, species_key: str, snapshot: Optional[str] = None) -> Critter:
        left, top, right, bottom = self.bounds
        taken = [c.name for c in self.critters]
        critter = Critter(
            species_key=species_key,
            name=random_name(species_key, taken),
            trait=random_trait(),
            x=random.uniform(left + 80, right - 80),
            y=random.uniform(top + 80, bottom - 80),
            snapshot=snapshot,
        )
        critter.history.append(Message("assistant", SPECIES[species_key].greeting))
        self.critters.append(critter)
        self.last_capture_at[species_key] = time.time()
        self.toast = (f"{critter.name} the {SPECIES[species_key].display.lower()} joined you!", time.time())
        return critter

    def release(self, critter_id: str) -> None:
        self.critters = [c for c in self.critters if c.id != critter_id]
        if self.selected_id == critter_id:
            self.selected_id = None

    # -- interaction ----------------------------------------------------
    def update(self, dt: float) -> None:
        for c in self.critters:
            if c.id != self.selected_id:
                c.update(dt, self.bounds)

    def pick(self, px: float, py: float) -> Optional[Critter]:
        # topmost (visually front-most) critter wins
        for critter in sorted(self.critters, key=lambda c: -c.y):
            if critter.hit(px, py):
                return critter
        return None

    @property
    def selected(self) -> Optional[Critter]:
        if self.selected_id is None:
            return None
        return next((c for c in self.critters if c.id == self.selected_id), None)

    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for c in self.critters:
            out[c.species_key] = out.get(c.species_key, 0) + 1
        return out

    # -- persistence ----------------------------------------------------
    def save(self) -> None:
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "saved_at": time.time(),
            "critters": [c.to_dict() for c in self.critters],
        }
        tmp = self.save_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self.save_path)

    def load(self) -> None:
        if not self.save_path.exists():
            return
        try:
            payload = json.loads(self.save_path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        self.critters = [
            Critter.from_dict(d)
            for d in payload.get("critters", [])
            if d.get("species_key") in SPECIES
        ]
