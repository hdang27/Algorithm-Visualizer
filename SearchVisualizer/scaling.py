import ctypes
import math
import os
import sys

import pygame

S = 1.0


def enable_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def system_scale():
    if sys.platform != "win32":
        return 1.0
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96
    except Exception:
        try:
            return ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        except Exception:
            return 1.0


def choose_scale(w, h):
    if os.environ.get("SV_SCALE"):
        return max(0.5, float(os.environ["SV_SCALE"]))
    s = system_scale()
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
        s = min(s, dw * 0.96 / w, dh * 0.90 / h)
    except Exception:
        pass
    return max(1.0, s)


def set_scale(s):
    global S
    S = s


def sc(v):
    return int(round(v * S))


def sc_rect(r):
    r = pygame.Rect(r)
    x0, y0 = sc(r.x), sc(r.y)
    return pygame.Rect(x0, y0, sc(r.right) - x0, sc(r.bottom) - y0)


def sc_width(w):
    return 0 if w == 0 else max(1, sc(w))


def unscale_pos(p):
    return int(p[0] / S), int(p[1] / S)


def mouse_pos():
    return unscale_pos(pygame.mouse.get_pos())


class HiSurf:

    def __init__(self, surf):
        self.surf = surf

    def get_size(self):
        w, h = self.surf.get_size()
        return math.ceil(w / S), math.ceil(h / S)

    def get_width(self):
        return self.get_size()[0]

    def get_height(self):
        return self.get_size()[1]

    def get_rect(self, **kw):
        r = pygame.Rect((0, 0), self.get_size())
        for k, v in kw.items():
            setattr(r, k, v)
        return r


class SFont:

    def __init__(self, name, size, bold=False):
        self.raw = pygame.font.SysFont(name, max(1, sc(size)), bold=bold)

    def render(self, text, aa, color, bg=None):
        return HiSurf(self.raw.render(text, aa, color, bg))

    def size(self, text):
        w, h = self.raw.size(text)
        return math.ceil(w / S), math.ceil(h / S)

    def get_linesize(self):
        return round(self.raw.get_linesize() / S)

    def get_height(self):
        return round(self.raw.get_height() / S)


class Canvas:

    def __init__(self, surf):
        self.surf = surf

    def fill(self, color, rect=None):
        self.surf.fill(color, sc_rect(rect) if rect is not None else None)

    def blit(self, src, dest):
        x, y = (dest.x, dest.y) if isinstance(dest, pygame.Rect) else dest[:2]
        pos = (sc(x), sc(y))
        if isinstance(src, HiSurf):
            self.surf.blit(src.surf, pos)
        else:
            w, h = src.get_size()
            self.surf.blit(pygame.transform.smoothscale(src, (sc(w), sc(h))), pos)

    def set_clip(self, rect):
        self.surf.set_clip(sc_rect(rect) if rect is not None else None)

    def get_size(self):
        w, h = self.surf.get_size()
        return int(w / S), int(h / S)


def rect(surf, color, r, width=0, border_radius=0):
    if isinstance(surf, Canvas):
        return pygame.draw.rect(surf.surf, color, sc_rect(r), sc_width(width),
                                border_radius=sc(border_radius))
    return pygame.draw.rect(surf, color, r, width, border_radius=border_radius)


def line(surf, color, a, b, width=1):
    if isinstance(surf, Canvas):
        return pygame.draw.line(surf.surf, color, (sc(a[0]), sc(a[1])),
                                (sc(b[0]), sc(b[1])), sc_width(width))
    return pygame.draw.line(surf, color, a, b, width)


def circle(surf, color, center, radius, width=0):
    if isinstance(surf, Canvas):
        return pygame.draw.circle(surf.surf, color, (sc(center[0]), sc(center[1])),
                                  max(1, sc(radius)), sc_width(width))
    return pygame.draw.circle(surf, color, center, radius, width)


def ellipse(surf, color, r, width=0):
    if isinstance(surf, Canvas):
        return pygame.draw.ellipse(surf.surf, color, sc_rect(r), sc_width(width))
    return pygame.draw.ellipse(surf, color, r, width)
