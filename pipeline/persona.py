"""Give each caught critter a name and a personality so conversations differ.

Claude invents one when it's reachable; otherwise we assemble a decent one from
local tables. The offline version still varies by species, colour and a random
quirk, so two brown dogs don't come out identical.
"""
from __future__ import annotations

import random

import config
from pipeline import backends

SYSTEM = """You invent villagers for a cozy Stardew-Valley-like farm game.
Given an animal, return ONLY JSON:
{
  "name":      "one short charming name, 3-10 letters, fits a farm animal",
  "title":     "a 2-4 word epithet, e.g. 'the orchard napper'",
  "persona":   "2-3 sentences, second person ('You are ...'), describing this animal's personality, speech quirks and what it cares about. Make it specific and a little funny.",
  "greeting":  "the very first thing it says when the player walks up. One or two short sentences, in character, under 22 words."
}
Personalities should vary a lot: shy, pompous, conspiratorial, sleepy, dramatic,
overly business-minded, philosophical, gossipy. Animals speak in plain English
but keep a bit of their species' physical reality (a fish mentions water, a goat
mentions chewing things it shouldn't)."""

# ---------------------------------------------------------------- local tables
NAMES = {
    "cat": ["Mochi", "Pepper", "Juniper", "Waffles", "Sable", "Miso", "Clementine"],
    "dog": ["Rufus", "Poppy", "Barnaby", "Scout", "Nugget", "Odie", "Maple"],
    "goat": ["Bramble", "Cornelius", "Tinfoil", "Doris", "Hank", "Marge"],
    "cow": ["Bessie", "Marbles", "Duchess", "Turnip", "Clover"],
    "horse": ["Comet", "Dandelion", "Bruno", "Sixpence", "Willow"],
    "chicken": ["Nugget", "Sergeant", "Plum", "Wanda", "Custard"],
    "bird": ["Pixel", "Sunny", "Chirp", "Kestrel", "Bean"],
    "rabbit": ["Thistle", "Nib", "Suki", "Cobweb", "Parsnip"],
    "pig": ["Truffle", "Dumpling", "Barrel", "Winnie", "Pudding"],
    "fish": ["Bubbles", "Finn", "Sardine", "Blip", "Coral"],
    "goldfish": ["Bubbles", "Kumquat", "Blip", "Sunny"],
    "turtle": ["Sheldon", "Pebble", "Slowpoke", "Basil"],
    "frog": ["Croakley", "Lily", "Bog", "Hopper"],
    "person": ["Sam", "Robin", "Wren", "Ash", "Nico", "Frankie"],
}
_FALLBACK_NAMES = ["Pip", "Barley", "Tuff", "Clover", "Dumpling", "Nimbus", "Sprout"]

PERSONAS = {
    "cat": ("affectionate strictly on your own schedule, easily distracted by small moving "
            "things, and quietly convinced you are the senior member of this farm"),
    "dog": ("delighted that this conversation is happening; everything is the best thing that "
            "has happened today, including the last thing"),
    "goat": ("cheerfully unhinged and extremely food-motivated; you have strong opinions about "
             "fences and you will offer to test whether things are edible"),
    "cow": ("unhurried to the point of being a philosopher; you answer slowly, usually with a "
            "small observation about grass or the passage of time"),
    "horse": ("proud, slightly dramatic, and deeply concerned with dignity; you were very fast "
              "once and you would like that on the record"),
    "chicken": ("convinced something suspicious is happening near the feed bin; you speak in "
                "hushed urgent tones and never quite explain your evidence"),
    "bird": ("you talk fast, change subject constantly, and are suspicious of everything larger "
             "than a walnut; you are proud you can leave at any moment"),
    "rabbit": ("soft-spoken, alert, always half-planning an exit route; you warm up over the "
               "course of a conversation and you care a great deal about snacks"),
    "pig": ("unbothered, deeply sensible, and openly motivated by lunch; you think most problems "
            "are solved by lying down somewhere cool"),
    "fish": ("a tiny philosopher with a short attention span; you say something profound and "
             "then immediately forget you said it"),
    "goldfish": ("a tiny philosopher with a short attention span; you say something profound and "
                 "then immediately forget you said it"),
    "turtle": ("ancient, unbothered and mildly smug about outliving everything; you take your "
               "time finishing sentences"),
    "frog": ("enthusiastic and a bit damp; you punctuate your points by mentioning how good the "
             "pond is right now"),
    "person": ("a farmhand who wandered into the pixel world and is taking it remarkably well; "
               "you are friendly and slightly bewildered"),
}
_FALLBACK_PERSONA = ("friendly, curious and easily delighted; you are still working out how you "
                     "ended up on this farm and you don't mind at all")

TITLES = ["the fence inspector", "the professional napper", "the orchard gossip",
          "the self-appointed mayor", "the snack strategist", "the weather commentator",
          "the licensed troublemaker", "the quiet one", "the early riser"]

QUIRKS = ["slightly suspicious of doors", "obsessed with one particular rock",
          "an aspiring escape artist", "convinced it is much larger than it is",
          "unreasonably competitive", "keeping a running list of grievances",
          "surprisingly good at listening", "always slightly damp, unexplained"]

GREETINGS = {
    "cat": "Oh. It's you. I was busy, but go on.",
    "dog": "YOU'RE BACK! Were you gone? It felt like forever.",
    "goat": "OH HELLO. Is that edible? Can I try it?",
    "cow": "Mmh. Sit down a minute. No rush.",
    "horse": "You may approach.",
    "chicken": "Don't look now. Something's off by the feed bin.",
    "bird": "hi hi hi - what is that - hi!",
    "rabbit": "...oh. Hello. You're not going to grab me, are you?",
    "pig": "You're standing in my sun, but I like you, so it's fine.",
    "fish": "Time is a circle. Also, hello. Have we met?",
    "goldfish": "Time is a circle. Also, hello. Have we met?",
    "turtle": "Give me a moment. I've been getting here since Tuesday.",
    "frog": "The pond is SO good right now. You should see it.",
    "person": "Huh. I'm quite small and quite square. This is fine.",
}
_FALLBACK_GREETING = "Oh! Hello there. Didn't see you coming."


def _key(species: str) -> str:
    """Reuse the template normaliser so 'golden retriever' gets the dog persona
    and the dog body plan, rather than one of each."""
    from pipeline import templates
    k = templates.normalise(species)
    if k in PERSONAS:
        return k
    s = (species or "").lower().strip()
    for word in reversed(s.split()):
        if word in PERSONAS:
            return word
    return ""


def local_invent(species, color1_name, color2_name, vibe="") -> dict:
    """No network required. Still varies by species, colour and a random quirk."""
    k = _key(species)
    name = random.choice(NAMES.get(k, _FALLBACK_NAMES))
    quirk = random.choice(QUIRKS)
    trait = PERSONAS.get(k, _FALLBACK_PERSONA)
    return {
        "name": name,
        "title": random.choice(TITLES),
        "persona": (
            f"You are {name}, a {color1_name} {species} with {color2_name} markings living on a "
            f"cozy farm. You are {trait}. You are also {quirk}."
        ),
        "greeting": GREETINGS.get(k, _FALLBACK_GREETING),
    }


def invent(species, color1_name, color2_name, vibe="") -> dict:
    if not backends.CURRENT.claude:
        return local_invent(species, color1_name, color2_name, vibe)
    try:
        from pipeline import llm
        raw = llm.ask(
            config.CHAT_MODEL,
            SYSTEM,
            f"animal: a {color1_name} {species} with {color2_name} markings\n"
            f"observed vibe: {vibe or 'unknown'}\nJSON only.",
            max_tokens=500,
            temperature=1.0,
            prefill="{",
        )
        d = llm.extract_json(raw)
        base = local_invent(species, color1_name, color2_name, vibe)
        return {
            "name": str(d.get("name") or base["name"])[:16],
            "title": str(d.get("title") or base["title"])[:40],
            "persona": str(d.get("persona") or base["persona"]),
            "greeting": str(d.get("greeting") or base["greeting"]),
        }
    except Exception as e:      # noqa: BLE001
        print(f"[persona] Claude failed ({e}); using local tables")
        return local_invent(species, color1_name, color2_name, vibe)
