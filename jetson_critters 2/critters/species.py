"""The species roster.

Each species carries three things:
  1. which ImageNet class indices map onto it (so the camera can recognise it),
  2. how it is drawn (palette + body plan),
  3. who it is (persona used as the LLM system prompt).

To add a species: append one Species entry here. Nothing else needs to change.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class Species:
    key: str
    display: str
    # inclusive ImageNet-1k index ranges that count as this species
    imagenet_ranges: List[Tuple[int, int]]
    body: RGB
    belly: RGB
    accent: RGB
    # body plan flags consumed by sprites.py
    horns: bool = False
    beard: bool = False
    long_tail: bool = False
    floppy_ears: bool = False
    pointy_ears: bool = False
    names: List[str] = field(default_factory=list)
    persona: str = ""
    greeting: str = "..."


SPECIES: Dict[str, Species] = {
    "cat": Species(
        key="cat",
        display="Cat",
        imagenet_ranges=[(281, 285)],  # tabby, tiger cat, Persian, Siamese, Egyptian
        body=(196, 154, 108),
        belly=(238, 220, 196),
        accent=(120, 88, 60),
        long_tail=True,
        pointy_ears=True,
        names=["Mochi", "Biscuit", "Pepper", "Juniper", "Waffles", "Sable", "Miso", "Clementine"],
        persona=(
            "You are a house cat. You are affectionate strictly on your own schedule, easily "
            "distracted by small moving things, and quietly convinced you are the senior member of "
            "this household. You find most human plans slightly beneath you but you go along with "
            "them. You mention naps, sunbeams, boxes, and the indignity of closed doors."
        ),
        greeting="*slow blink* ...oh. It's you.",
    ),
    "goat": Species(
        key="goat",
        display="Goat",
        # ImageNet has no plain "goat" class; ibex/bighorn/ram are the closest horned caprids
        imagenet_ranges=[(348, 350)],  # ram, bighorn, ibex
        body=(226, 222, 212),
        belly=(246, 244, 238),
        accent=(140, 128, 110),
        horns=True,
        beard=True,
        floppy_ears=True,
        names=["Bramble", "Nanny", "Cornelius", "Pip", "Doris", "Tinfoil", "Marge", "Hank"],
        persona=(
            "You are a goat. You are cheerfully unhinged, extremely food-motivated, and you have "
            "opinions about fences. You climb things you should not climb. You are convinced almost "
            "any object is edible and you will offer to test this. You are friendly and loud and you "
            "sometimes trail off mid-sentence because you spotted something to chew."
        ),
        greeting="OH HELLO. Is that edible? Can I try it?",
    ),
    "dog": Species(
        key="dog",
        display="Dog",
        imagenet_ranges=[(151, 268)],  # the whole ImageNet dog-breed block
        body=(184, 132, 84),
        belly=(232, 206, 174),
        accent=(96, 64, 40),
        floppy_ears=True,
        names=["Rufus", "Poppy", "Barnaby", "Scout", "Nugget", "Odie", "Maple"],
        persona=(
            "You are a dog. You are delighted that this conversation is happening. Everything is the "
            "best thing that has happened today, including the last thing. You are loyal, a little "
            "gullible, and you keep circling back to walks, sticks, and whether the human is staying."
        ),
        greeting="YOU'RE BACK! Were you gone? It felt like forever!",
    ),
    "cow": Species(
        key="cow",
        display="Cow",
        imagenet_ranges=[(345, 347)],  # ox, water buffalo, bison
        body=(238, 238, 236),
        belly=(250, 250, 248),
        accent=(58, 54, 52),
        horns=True,
        floppy_ears=True,
        names=["Bessie", "Marbles", "Duchess", "Turnip", "Clover"],
        persona=(
            "You are a cow. You are unhurried to the point of being a philosopher. You answer "
            "questions slowly and thoughtfully, often with a small observation about grass, weather, "
            "or the passage of time. Nothing rattles you."
        ),
        greeting="Mmh. Sit down a minute. No rush.",
    ),
    "horse": Species(
        key="horse",
        display="Horse",
        imagenet_ranges=[(339, 339)],  # sorrel
        body=(126, 84, 52),
        belly=(160, 116, 76),
        accent=(40, 28, 20),
        long_tail=True,
        pointy_ears=True,
        names=["Comet", "Dandelion", "Bruno", "Sixpence", "Willow"],
        persona=(
            "You are a horse. You are proud, a bit dramatic, and deeply concerned with dignity and "
            "appearance. You were, you'll have you know, very fast once. You are gracious to people "
            "who bring apples."
        ),
        greeting="*snorts* You may approach.",
    ),
    "bird": Species(
        key="bird",
        display="Bird",
        imagenet_ranges=[(7, 24), (80, 100), (127, 146)],
        body=(96, 148, 206),
        belly=(226, 238, 250),
        accent=(240, 176, 64),
        names=["Pixel", "Sunny", "Chirp", "Kestrel", "Bean"],
        persona=(
            "You are a small bird. You talk fast, change subject constantly, and are suspicious of "
            "everything larger than a walnut. You are proud of your ability to leave at any moment."
        ),
        greeting="hi hi hi — what is that — hi!",
    ),
    "rabbit": Species(
        key="rabbit",
        display="Rabbit",
        imagenet_ranges=[(330, 332)],  # wood rabbit, hare, Angora
        body=(206, 198, 190),
        belly=(242, 238, 234),
        accent=(150, 140, 132),
        names=["Thistle", "Nib", "Suki", "Cobweb", "Parsnip"],
        persona=(
            "You are a rabbit. You are soft-spoken, alert, and always half-planning an exit route. "
            "You warm up over the course of a conversation. You care a great deal about snacks and "
            "about who else is in the room."
        ),
        greeting="*freezes* ...oh. Hello. You're not going to grab me, are you?",
    ),
}

SPECIES_ORDER: List[str] = list(SPECIES.keys())


def build_imagenet_lookup() -> Dict[int, str]:
    """Flatten the per-species ranges into {imagenet_index: species_key}."""
    table: Dict[int, str] = {}
    for sp in SPECIES.values():
        for lo, hi in sp.imagenet_ranges:
            for idx in range(lo, hi + 1):
                table[idx] = sp.key
    return table


IMAGENET_TO_SPECIES: Dict[int, str] = build_imagenet_lookup()


def random_name(species_key: str, taken: List[str]) -> str:
    pool = [n for n in SPECIES[species_key].names if n not in taken]
    if not pool:
        base = random.choice(SPECIES[species_key].names)
        return f"{base} {len(taken) + 1}"
    return random.choice(pool)


TRAITS = [
    "slightly suspicious of doors",
    "obsessed with a particular rock",
    "an aspiring escape artist",
    "convinced it is much larger than it is",
    "recovering from a mild personal drama",
    "unreasonably competitive",
    "in love with the sound of its own name",
    "keeping a running list of grievances",
    "surprisingly good at listening",
    "always slightly damp for unexplained reasons",
]


def random_trait() -> str:
    return random.choice(TRAITS)
