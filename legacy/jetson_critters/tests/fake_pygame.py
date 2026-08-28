"""A minimal stand-in for pygame, used only so the smoke test can run on machines
where pygame is not installed (CI containers, headless build boxes).

It implements enough of the API that every draw call in ui.py/sprites.py actually
executes — so typos, bad attribute names and broken layout maths still surface.
It draws nothing. If real pygame is available the smoke test uses that instead.
"""

from __future__ import annotations

import sys
import types

# ---------------------------------------------------------------- constants
QUIT = 256
KEYDOWN = 768
MOUSEBUTTONDOWN = 1025
MOUSEWHEEL = 1027
SRCALPHA = 65536
HIDDEN = 128
K_ESCAPE = 27
K_BACKSPACE = 8
K_RETURN = 13
K_KP_ENTER = 1073741912
K_TAB = 9
K_0, K_1, K_2, K_3, K_4 = 48, 49, 50, 51, 52
K_5, K_6, K_7, K_8, K_9 = 53, 54, 55, 56, 57
K_r, K_s, K_c = 114, 115, 99
CAP_PROP_POS_FRAMES = 1


class Rect:
    def __init__(self, *args):
        if len(args) == 1:
            args = tuple(args[0])
        if len(args) == 2:
            (x, y), (w, h) = args
        else:
            x, y, w, h = args
        self.x, self.y, self.width, self.height = int(x), int(y), int(w), int(h)

    # aliases
    w = property(lambda s: s.width)
    h = property(lambda s: s.height)
    left = property(lambda s: s.x)
    top = property(lambda s: s.y)
    right = property(lambda s: s.x + s.width)
    bottom = property(lambda s: s.y + s.height)
    centerx = property(lambda s: s.x + s.width // 2)
    centery = property(lambda s: s.y + s.height // 2)
    center = property(lambda s: (s.centerx, s.centery))
    topleft = property(lambda s: (s.x, s.y))
    size = property(lambda s: (s.width, s.height))

    def collidepoint(self, *p):
        px, py = p[0] if len(p) == 1 else p
        return self.x <= px < self.right and self.y <= py < self.bottom

    def copy(self):
        return Rect(self.x, self.y, self.width, self.height)

    def __iter__(self):
        return iter((self.x, self.y, self.width, self.height))

    def __repr__(self):
        return f"Rect({self.x},{self.y},{self.width},{self.height})"


class Surface:
    def __init__(self, size, flags=0):
        self.width, self.height = int(size[0]), int(size[1])
        self._clip = None
        self.blits = 0

    def get_size(self):
        return (self.width, self.height)

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_rect(self, **kwargs):
        r = Rect(0, 0, self.width, self.height)
        if "center" in kwargs:
            cx, cy = kwargs["center"]
            r.x, r.y = int(cx - r.width / 2), int(cy - r.height / 2)
        if "topleft" in kwargs:
            r.x, r.y = map(int, kwargs["topleft"])
        return r

    def fill(self, colour, rect=None):
        _check_colour(colour)

    def blit(self, src, pos, area=None):
        assert isinstance(src, Surface), f"blit source must be a Surface, got {type(src)}"
        float(pos[0]), float(pos[1])
        self.blits += 1

    def set_clip(self, rect):
        self._clip = rect

    def get_clip(self):
        return self._clip

    def set_alpha(self, a):
        assert 0 <= int(a) <= 255, f"alpha out of range: {a}"

    def get_at(self, pos):
        return (60, 90, 60, 255)

    def convert(self):
        return self

    def convert_alpha(self):
        return self


def _check_colour(colour):
    assert 3 <= len(colour) <= 4, f"bad colour tuple: {colour}"
    for ch in colour:
        assert 0 <= int(ch) <= 255, f"colour channel out of range: {colour}"


def _pt(p):
    return (float(p[0]), float(p[1]))


class _Draw:
    @staticmethod
    def rect(surf, colour, rect, width=0, border_radius=0):
        _check_colour(colour)
        assert isinstance(rect, Rect)

    @staticmethod
    def ellipse(surf, colour, rect, width=0):
        _check_colour(colour)
        assert isinstance(rect, Rect)

    @staticmethod
    def line(surf, colour, start, end, width=1):
        _check_colour(colour)
        _pt(start), _pt(end)
        assert int(width) >= 1, f"line width must be >= 1, got {width}"

    @staticmethod
    def lines(surf, colour, closed, points, width=1):
        _check_colour(colour)
        assert len(points) >= 2
        for p in points:
            _pt(p)
        assert int(width) >= 1

    @staticmethod
    def polygon(surf, colour, points, width=0):
        _check_colour(colour)
        assert len(points) >= 3
        for p in points:
            _pt(p)

    @staticmethod
    def circle(surf, colour, centre, radius, width=0):
        _check_colour(colour)
        _pt(centre)


class Font:
    def __init__(self, name=None, size=14, bold=False):
        self.size_px = int(size)
        self.bold = bold

    def render(self, text, antialias, colour, background=None):
        _check_colour(colour)
        w, h = self.size(text)
        return Surface((w, h))

    def size(self, text):
        return (max(1, int(len(text) * self.size_px * 0.55)), self.size_px + 4)

    def get_height(self):
        return self.size_px + 4


class _FontModule(types.ModuleType):
    Font = Font

    @staticmethod
    def SysFont(name, size, bold=False, italic=False):
        return Font(name, size, bold)

    @staticmethod
    def init():
        pass


class _Clock:
    def tick(self, fps=60):
        return 16


def install() -> types.ModuleType:
    """Register this stub as the `pygame` module. Returns it."""
    mod = types.ModuleType("pygame")
    mod.Rect = Rect
    mod.Surface = Surface
    mod.draw = _Draw
    mod.error = RuntimeError

    for name, value in globals().items():
        if name.isupper() or name.startswith("K_"):
            setattr(mod, name, value)

    font_mod = _FontModule("pygame.font")
    mod.font = font_mod

    display = types.ModuleType("pygame.display")
    display.set_mode = lambda size, flags=0: Surface(size)
    display.set_caption = lambda *_: None
    display.flip = lambda: None
    display.update = lambda *_: None
    mod.display = display

    time_mod = types.ModuleType("pygame.time")
    time_mod.Clock = _Clock
    mod.time = time_mod

    event_mod = types.ModuleType("pygame.event")
    event_mod.queue = []
    event_mod.get = lambda: [event_mod.queue.pop(0)] if event_mod.queue else []
    event_mod.post = lambda e: event_mod.queue.append(e)
    mod.event = event_mod

    mouse = types.ModuleType("pygame.mouse")
    mouse.get_pos = lambda: (0, 0)
    mod.mouse = mouse

    transform = types.ModuleType("pygame.transform")
    transform.smoothscale = lambda surf, size: Surface(size)
    transform.scale = lambda surf, size: Surface(size)
    mod.transform = transform

    surfarray = types.ModuleType("pygame.surfarray")
    surfarray.make_surface = lambda arr: Surface((arr.shape[0], arr.shape[1]))
    mod.surfarray = surfarray

    mod.init = lambda: (0, 0)
    mod.quit = lambda: None

    sys.modules["pygame"] = mod
    sys.modules["pygame.font"] = font_mod
    sys.modules["pygame.display"] = display
    sys.modules["pygame.time"] = time_mod
    sys.modules["pygame.event"] = event_mod
    sys.modules["pygame.transform"] = transform
    sys.modules["pygame.surfarray"] = surfarray
    sys.modules["pygame.mouse"] = mouse
    return mod


class Event:
    """Simple event object matching pygame's attribute access."""

    def __init__(self, type_, **kwargs):
        self.type = type_
        self.__dict__.update(kwargs)
