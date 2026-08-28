"""Offline avatar path: a shape spec per species, recoloured with the colours
actually measured from the photo.

This is what runs when Claude is unreachable. It is NOT a static sprite sheet --
the two colours still come from the real animal in front of the camera, so the
capture -> extract -> generate story still holds up on stage with the wifi off.
Only the *anatomy* is pre-authored instead of invented per-animal.

Specs are in exactly the format pipeline/avatar.py gets back from Claude, so
pipeline/sprite.py renders them through the identical code path.
"""
from __future__ import annotations

from tools.demo_specs import CAT, CHICKEN, DOG, FISH, GOAT, PERSON

_NOTCH = {"shape": "rect", "x": 15, "y": 26, "w": 2, "h": 4, "fill": "outline", "z": 9}

# ---------------------------------------------------------------- extra species
RABBIT = {"species": "rabbit", "parts": [
    {"shape": "rect", "x": 10, "y": 24, "w": 4, "h": 6, "fill": "shade", "z": 2, "mirror": True},
    {"shape": "ellipse", "cx": 10, "cy": 8, "rx": 3, "ry": 8, "fill": "base", "z": 4, "mirror": True},
    {"shape": "ellipse", "cx": 10, "cy": 8, "rx": 2, "ry": 6, "fill": "pink", "z": 5, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 20, "rx": 9, "ry": 8, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 15, "rx": 7, "ry": 5, "fill": "base", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 24, "rx": 6, "ry": 4, "fill": "accent", "z": 7},
    {"shape": "pixel", "x": 12, "y": 14, "w": 2, "h": 3, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 15, "y": 18, "w": 2, "h": 1, "fill": "pink", "z": 9},
    {"shape": "ellipse", "cx": 25, "cy": 24, "rx": 3, "ry": 3, "fill": "light", "z": 5},
    _NOTCH,
]}

COW = {"species": "cow", "parts": [
    {"shape": "rect", "x": 9, "y": 24, "w": 4, "h": 6, "fill": "hoof", "z": 2, "mirror": True},
    {"shape": "poly", "points": [[7, 7], [4, 2], [10, 6]], "fill": "cream", "z": 3, "mirror": True},
    {"shape": "ellipse", "cx": 4, "cy": 12, "rx": 4, "ry": 2, "fill": "base", "z": 4, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 20, "rx": 11, "ry": 8, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 12, "rx": 8, "ry": 6, "fill": "base", "z": 7},
    {"shape": "ellipse", "cx": 9, "cy": 22, "rx": 4, "ry": 3, "fill": "accent", "z": 7},
    {"shape": "ellipse", "cx": 23, "cy": 19, "rx": 3, "ry": 3, "fill": "accent", "z": 7},
    {"shape": "ellipse", "cx": 20, "cy": 9, "rx": 3, "ry": 2, "fill": "accent", "z": 8},
    {"shape": "ellipse", "cx": 16, "cy": 16, "rx": 4, "ry": 3, "fill": "pink", "z": 8},
    {"shape": "pixel", "x": 12, "y": 10, "w": 2, "h": 2, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 14, "y": 16, "w": 1, "h": 1, "fill": "dark", "z": 10, "mirror": True},
    _NOTCH,
]}

HORSE = {"species": "horse", "parts": [
    {"shape": "rect", "x": 9, "y": 24, "w": 4, "h": 6, "fill": "hoof", "z": 2, "mirror": True},
    {"shape": "poly", "points": [[24, 18], [30, 12], [27, 26]], "fill": "accent_shade", "z": 3},
    {"shape": "poly", "points": [[10, 9], [12, 2], [15, 10]], "fill": "base", "z": 4, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 21, "rx": 10, "ry": 8, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 12, "rx": 6, "ry": 7, "fill": "base", "z": 7},
    {"shape": "poly", "points": [[10, 5], [16, 3], [16, 15], [11, 13]], "fill": "accent", "z": 8},
    {"shape": "ellipse", "cx": 16, "cy": 17, "rx": 4, "ry": 3, "fill": "accent_light", "z": 8},
    {"shape": "pixel", "x": 12, "y": 11, "w": 2, "h": 2, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 14, "y": 17, "w": 1, "h": 1, "fill": "dark", "z": 10, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 24, "rx": 5, "ry": 3, "fill": "shade", "z": 7},
    _NOTCH,
]}

PIG = {"species": "pig", "parts": [
    {"shape": "rect", "x": 10, "y": 24, "w": 4, "h": 6, "fill": "hoof", "z": 2, "mirror": True},
    {"shape": "poly", "points": [[6, 12], [9, 3], [14, 12]], "fill": "accent", "z": 4, "mirror": True},
    {"shape": "poly", "points": [[8, 11], [10, 6], [13, 11]], "fill": "pink", "z": 5, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 19, "rx": 11, "ry": 9, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 12, "rx": 7, "ry": 6, "fill": "base", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 17, "rx": 5, "ry": 4, "fill": "pink", "z": 8},
    {"shape": "pixel", "x": 14, "y": 16, "w": 2, "h": 2, "fill": "dark", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 12, "y": 10, "w": 2, "h": 2, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "ellipse", "cx": 26, "cy": 22, "rx": 2, "ry": 2, "fill": "accent", "z": 5},
    _NOTCH,
]}

BIRD = {"species": "bird", "parts": [
    {"shape": "rect", "x": 13, "y": 26, "w": 2, "h": 4, "fill": "hoof", "z": 2, "mirror": True},
    {"shape": "poly", "points": [[23, 14], [30, 10], [25, 24]], "fill": "accent_shade", "z": 3},
    {"shape": "ellipse", "cx": 16, "cy": 18, "rx": 9, "ry": 9, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 10, "rx": 6, "ry": 5, "fill": "base", "z": 7},
    {"shape": "ellipse", "cx": 9, "cy": 19, "rx": 4, "ry": 6, "fill": "accent", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 22, "rx": 5, "ry": 4, "fill": "light", "z": 7},
    {"shape": "poly", "points": [[20, 10], [26, 12], [20, 14]], "fill": "cream", "z": 8},
    {"shape": "pixel", "x": 13, "y": 9, "w": 2, "h": 2, "fill": "eye", "z": 9, "mirror": True},
]}

TURTLE = {"species": "turtle", "parts": [
    # stubby legs poking out from under the shell
    {"shape": "ellipse", "cx": 8, "cy": 25, "rx": 4, "ry": 3, "fill": "accent_shade", "z": 2, "mirror": True},
    # head on the right, so the silhouette isn't a symmetric disc
    {"shape": "ellipse", "cx": 26, "cy": 20, "rx": 5, "ry": 4, "fill": "accent", "z": 3},
    {"shape": "pixel", "x": 27, "y": 18, "w": 2, "h": 2, "fill": "eye", "z": 9},
    {"shape": "pixel", "x": 29, "y": 21, "w": 2, "h": 1, "fill": "dark", "z": 9},
    # tail
    {"shape": "poly", "points": [[6, 21], [2, 23], [6, 24]], "fill": "accent_shade", "z": 3},
    # shell: a squat dome, flat underside, sitting high on the body
    {"shape": "ellipse", "cx": 16, "cy": 22, "rx": 12, "ry": 5, "fill": "shade", "z": 5},
    {"shape": "ellipse", "cx": 16, "cy": 18, "rx": 12, "ry": 9, "fill": "base", "z": 6},
    {"shape": "rect", "x": 4, "y": 20, "w": 24, "h": 4, "fill": "base", "z": 6},
    # scute plates -- reads as a shell rather than a bullseye
    {"shape": "poly", "points": [[16, 10], [22, 15], [16, 19], [10, 15]], "fill": "light", "z": 7},
    {"shape": "poly", "points": [[8, 16], [12, 14], [13, 20], [8, 21]], "fill": "shade", "z": 7, "mirror": True},
    {"shape": "pixel", "x": 15, "y": 13, "w": 2, "h": 2, "fill": "accent_light", "z": 8},
    {"shape": "rect", "x": 4, "y": 23, "w": 24, "h": 1, "fill": "outline", "z": 8},
]}

FROG = {"species": "frog", "parts": [
    {"shape": "ellipse", "cx": 7, "cy": 26, "rx": 5, "ry": 3, "fill": "shade", "z": 2, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 20, "rx": 12, "ry": 8, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 24, "rx": 8, "ry": 4, "fill": "accent", "z": 7},
    # eyes sit ON TOP of the head as two small bumps, frog-style
    {"shape": "ellipse", "cx": 10, "cy": 12, "rx": 4, "ry": 4, "fill": "base", "z": 7, "mirror": True},
    {"shape": "ellipse", "cx": 10, "cy": 11, "rx": 2, "ry": 2, "fill": "cream", "z": 8, "mirror": True},
    {"shape": "pixel", "x": 10, "y": 10, "w": 2, "h": 2, "fill": "eye", "z": 9, "mirror": True},
    # wide grin across the whole face
    {"shape": "rect", "x": 8, "y": 20, "w": 16, "h": 1, "fill": "outline", "z": 9},
    {"shape": "pixel", "x": 8, "y": 19, "w": 1, "h": 1, "fill": "outline", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 11, "y": 17, "w": 2, "h": 1, "fill": "accent_light", "z": 9, "mirror": True},
]}

# ---------------------------------------------------------------- registry
TEMPLATES: dict[str, dict] = {
    "cat": CAT,
    "dog": DOG,
    "fox": CAT,
    "chicken": CHICKEN,
    "bird": BIRD,
    "goat": GOAT,
    "sheep": GOAT,
    "cow": COW,
    "horse": HORSE,
    "pig": PIG,
    "rabbit": RABBIT,
    "person": PERSON,
    "fish": FISH,
    "goldfish": FISH,
    "turtle": TURTLE,
    "frog": FROG,
    "bear": DOG,
    "lizard": FROG,
    "snake": FISH,
}

# what to reach for when the species is a word we have no drawing for
_GENERIC = CAT

# Claude answers with real-world names ("golden retriever", "mallard duck"),
# so map the common ones onto a body plan we can actually draw.
SYNONYMS: dict[str, str] = {
    # dogs
    "retriever": "dog", "labrador": "dog", "poodle": "dog", "terrier": "dog",
    "shepherd": "dog", "husky": "dog", "corgi": "dog", "beagle": "dog",
    "dachshund": "dog", "chihuahua": "dog", "spaniel": "dog", "puppy": "dog",
    "hound": "dog", "collie": "dog", "pug": "dog", "bulldog": "dog",
    # cats
    "kitten": "cat", "tabby": "cat", "siamese": "cat", "persian": "cat",
    "calico": "cat", "feline": "cat",
    # birds
    "duck": "bird", "mallard": "bird", "goose": "bird", "parrot": "bird",
    "budgie": "bird", "cockatiel": "bird", "pigeon": "bird", "crow": "bird",
    "raven": "bird", "owl": "bird", "sparrow": "bird", "penguin": "bird",
    "hen": "chicken", "rooster": "chicken", "chick": "chicken",
    # farm
    "lamb": "goat", "ram": "goat", "ewe": "goat", "kid": "goat",
    "calf": "cow", "bull": "cow", "ox": "cow", "cattle": "cow", "buffalo": "cow",
    "pony": "horse", "foal": "horse", "donkey": "horse", "mule": "horse",
    "hog": "pig", "boar": "pig", "piglet": "pig", "swine": "pig",
    # water
    "koi": "goldfish", "carp": "goldfish", "guppy": "fish", "salmon": "fish",
    "trout": "fish", "tuna": "fish", "shark": "fish", "betta": "fish",
    "tortoise": "turtle", "terrapin": "turtle",
    "toad": "frog", "tadpole": "frog",
    # people
    "human": "person", "man": "person", "woman": "person", "boy": "person",
    "girl": "person", "child": "person", "baby": "person", "face": "person",
    # small mammals
    "bunny": "rabbit", "hare": "rabbit",
    "hamster": "rabbit", "guinea": "rabbit", "gerbil": "rabbit", "mouse": "rabbit",
    "rat": "rabbit", "squirrel": "cat", "ferret": "cat",
    "wolf": "dog", "coyote": "dog", "fox": "fox",
    "gecko": "lizard", "iguana": "lizard", "chameleon": "lizard",
}


def has(species: str) -> bool:
    return _norm(species) in TEMPLATES


def _lookup(word: str) -> str:
    if word in TEMPLATES:
        return word
    if word in SYNONYMS:
        return SYNONYMS[word]
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return _lookup(word[:-1])          # 'dogs' -> 'dog', 'puppies' is fine to miss
    return ""


def _norm(species: str) -> str:
    """'golden retriever' -> dog, 'tabby cat' -> cat, 'mallard duck' -> bird."""
    s = (species or "").lower().strip()
    hit = _lookup(s)
    if hit:
        return hit
    # last word first: 'golden retriever' and 'baby goat' both end in the noun
    for word in reversed(s.replace("-", " ").split()):
        hit = _lookup(word)
        if hit:
            return hit
    # last resort: substring anywhere
    for key in TEMPLATES:
        if key in s:
            return key
    for word, key in SYNONYMS.items():
        if word in s:
            return key
    return ""


def normalise(species: str) -> str:
    """Public: which body plan does this species name map onto? '' if none."""
    return _norm(species)


def spec_for(species: str) -> dict:
    """Best pre-authored anatomy for this species name. Never raises."""
    key = _norm(species)
    spec = TEMPLATES.get(key, _GENERIC)
    out = dict(spec)
    out["species"] = species or spec.get("species", "critter")
    out["_template"] = key or "generic"
    return out
