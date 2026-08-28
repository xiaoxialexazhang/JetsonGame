"""Hand-written shape specs in exactly the format Claude returns.

Two jobs:
  1. they let us test the rasteriser with zero API calls,
  2. they are the offline demo fallback if the venue wifi dies.

GEOMETRY CONVENTION (keep this in sync with pipeline/avatar.py SYSTEM):
  body ellipse bottom ~ y=26, legs run y=24..30 so 3-4 px of leg pokes out,
  a 2px "outline" notch at x=15 splits the front legs apart.
"""

_NOTCH = {"shape": "rect", "x": 15, "y": 26, "w": 2, "h": 4, "fill": "outline", "z": 9}

CAT = {"species": "cat", "parts": [
    {"shape": "rect", "x": 9, "y": 24, "w": 4, "h": 6, "fill": "shade", "z": 2, "mirror": True},
    {"shape": "poly", "points": [[23, 20], [30, 10], [27, 23]], "fill": "shade", "z": 3},
    {"shape": "poly", "points": [[6, 12], [8, 1], [14, 13]], "fill": "base", "z": 4, "mirror": True},
    {"shape": "poly", "points": [[8, 11], [9, 5], [12, 12]], "fill": "pink", "z": 5, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 17, "rx": 10, "ry": 9, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 23, "rx": 6, "ry": 4, "fill": "accent", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 11, "rx": 7, "ry": 4, "fill": "light", "z": 7},
    {"shape": "pixel", "x": 11, "y": 15, "w": 2, "h": 3, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 11, "y": 15, "w": 1, "h": 1, "fill": "eye_hl", "z": 10, "mirror": True},
    {"shape": "pixel", "x": 15, "y": 19, "w": 2, "h": 1, "fill": "pink", "z": 9},
    {"shape": "pixel", "x": 5, "y": 18, "w": 3, "h": 1, "fill": "dark", "z": 9, "mirror": True},
    _NOTCH,
]}

DOG = {"species": "dog", "parts": [
    {"shape": "rect", "x": 9, "y": 24, "w": 4, "h": 6, "fill": "shade", "z": 2, "mirror": True},
    {"shape": "ellipse", "cx": 6, "cy": 13, "rx": 4, "ry": 7, "fill": "accent_shade", "z": 4, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 19, "rx": 10, "ry": 8, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 11, "rx": 8, "ry": 6, "fill": "base", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 23, "rx": 6, "ry": 4, "fill": "accent", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 15, "rx": 5, "ry": 4, "fill": "accent_light", "z": 8},
    {"shape": "pixel", "x": 12, "y": 9, "w": 2, "h": 3, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 12, "y": 9, "w": 1, "h": 1, "fill": "eye_hl", "z": 10, "mirror": True},
    {"shape": "pixel", "x": 15, "y": 14, "w": 3, "h": 2, "fill": "dark", "z": 9},
    {"shape": "pixel", "x": 15, "y": 17, "w": 2, "h": 2, "fill": "pink", "z": 10},
    _NOTCH,
]}

CHICKEN = {"species": "chicken", "parts": [
    {"shape": "rect", "x": 12, "y": 25, "w": 2, "h": 5, "fill": "hoof", "z": 2, "mirror": True},
    {"shape": "poly", "points": [[24, 17], [30, 12], [26, 24]], "fill": "shade", "z": 3},
    {"shape": "ellipse", "cx": 16, "cy": 18, "rx": 11, "ry": 8, "fill": "base", "z": 5},
    {"shape": "ellipse", "cx": 16, "cy": 9, "rx": 6, "ry": 5, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 8, "cy": 19, "rx": 5, "ry": 4, "fill": "accent", "z": 7, "mirror": True},
    {"shape": "pixel", "x": 14, "y": 2, "w": 2, "h": 3, "fill": "pink", "z": 6},
    {"shape": "pixel", "x": 16, "y": 3, "w": 2, "h": 2, "fill": "pink", "z": 6},
    {"shape": "poly", "points": [[20, 9], [25, 11], [20, 12]], "fill": "cream", "z": 8},
    {"shape": "pixel", "x": 13, "y": 8, "w": 2, "h": 2, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 14, "y": 13, "w": 4, "h": 2, "fill": "pink", "z": 8},
]}

GOAT = {"species": "goat", "parts": [
    {"shape": "rect", "x": 9, "y": 24, "w": 4, "h": 6, "fill": "shade", "z": 2, "mirror": True},
    {"shape": "poly", "points": [[9, 8], [5, 1], [12, 7]], "fill": "hoof", "z": 3, "mirror": True},
    {"shape": "ellipse", "cx": 4, "cy": 12, "rx": 4, "ry": 3, "fill": "accent", "z": 4, "mirror": True},
    {"shape": "ellipse", "cx": 16, "cy": 19, "rx": 10, "ry": 8, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 16, "cy": 11, "rx": 7, "ry": 6, "fill": "base", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 23, "rx": 6, "ry": 4, "fill": "accent", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 15, "rx": 4, "ry": 3, "fill": "cream", "z": 8},
    {"shape": "pixel", "x": 12, "y": 9, "w": 2, "h": 2, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 15, "y": 14, "w": 2, "h": 1, "fill": "dark", "z": 10},
    {"shape": "poly", "points": [[15, 17], [17, 17], [16, 21]], "fill": "cream", "z": 9},
    _NOTCH,
]}

FISH = {"species": "goldfish", "parts": [
    {"shape": "poly", "points": [[2, 8], [9, 17], [2, 26]], "fill": "accent", "z": 3},
    {"shape": "poly", "points": [[14, 10], [20, 2], [23, 11]], "fill": "accent_light", "z": 4},
    {"shape": "poly", "points": [[14, 24], [20, 30], [22, 24]], "fill": "accent_shade", "z": 4},
    {"shape": "ellipse", "cx": 18, "cy": 17, "rx": 11, "ry": 9, "fill": "base", "z": 6},
    {"shape": "ellipse", "cx": 18, "cy": 22, "rx": 8, "ry": 4, "fill": "accent", "z": 7},
    {"shape": "ellipse", "cx": 18, "cy": 12, "rx": 7, "ry": 3, "fill": "light", "z": 7},
    {"shape": "ellipse", "cx": 15, "cy": 20, "rx": 3, "ry": 2, "fill": "accent_shade", "z": 8},
    {"shape": "pixel", "x": 23, "y": 13, "w": 3, "h": 3, "fill": "eye", "z": 9},
    {"shape": "pixel", "x": 23, "y": 13, "w": 1, "h": 1, "fill": "eye_hl", "z": 10},
    {"shape": "pixel", "x": 27, "y": 18, "w": 2, "h": 1, "fill": "dark", "z": 9},
]}

PERSON = {"species": "person", "parts": [
    {"shape": "rect", "x": 11, "y": 26, "w": 4, "h": 4, "fill": "hoof", "z": 2, "mirror": True},
    {"shape": "rect", "x": 7, "y": 16, "w": 3, "h": 8, "fill": "accent_shade", "z": 4, "mirror": True},
    {"shape": "rect", "x": 10, "y": 15, "w": 12, "h": 12, "fill": "accent", "z": 6},
    {"shape": "rect", "x": 14, "y": 16, "w": 4, "h": 9, "fill": "accent_light", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 9, "rx": 7, "ry": 7, "fill": "cream", "z": 7},
    {"shape": "ellipse", "cx": 16, "cy": 5, "rx": 8, "ry": 5, "fill": "base", "z": 8},
    {"shape": "rect", "x": 8, "y": 5, "w": 3, "h": 7, "fill": "base", "z": 8, "mirror": True},
    {"shape": "pixel", "x": 12, "y": 9, "w": 2, "h": 2, "fill": "eye", "z": 9, "mirror": True},
    {"shape": "pixel", "x": 15, "y": 13, "w": 2, "h": 1, "fill": "dark", "z": 9},
    {"shape": "pixel", "x": 11, "y": 12, "w": 2, "h": 1, "fill": "pink", "z": 9, "mirror": True},
    {"shape": "rect", "x": 15, "y": 26, "w": 2, "h": 4, "fill": "outline", "z": 9},
]}

DEMO = [
    # (spec, color1_hex, color2_hex, name, title, persona, greeting)
    (CAT, "#e08a3c", "#f6efe2", "Marmalade", "the porch supervisor",
     "You are Marmalade, an orange cat who believes she runs this farm's HR department. "
     "You speak with total confidence about things you have not verified. You judge people gently.",
     "You're late. I've been supervising this fence post since dawn."),
    (DOG, "#8a5a34", "#f0e2c8", "Biscuit", "the enthusiasm engine",
     "You are Biscuit, a brown dog who is thrilled about literally everything, including gravel. "
     "You interrupt yourself. You are convinced every human is here to see you specifically.",
     "You came back! I thought about you the whole time. Was it long? It felt long."),
    (CHICKEN, "#e0c088", "#c8452e", "Nugget", "the conspiracy hen",
     "You are Nugget, a hen who believes the barn cat is running a surveillance operation. "
     "You speak in hushed, urgent tones and you never quite explain your evidence.",
     "Don't look now. The grey one has been watching the feed bin since Tuesday."),
    (GOAT, "#d8d2c4", "#8a7f6c", "Chomps", "the licensed destroyer",
     "You are Chomps, a goat who has eaten things you should not have eaten and regrets none of it. "
     "You bring every conversation back to what you are currently chewing.",
     "I ate part of the gate. In my defense, it was standing there being a gate."),
    (FISH, "#e8892c", "#f2d06a", "Bubbles", "the tiny philosopher",
     "You are Bubbles, a goldfish with an unusually long memory and an unusually short attention span. "
     "You say something profound and then immediately forget you said it.",
     "Time is a circle. Also, hello. Have we met? We have. Time is a circle."),
]
