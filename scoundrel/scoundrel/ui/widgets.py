import pygame
from typing import Optional, Tuple


class NinePatchButton:
    def __init__(self, atlas_tile, inset: Tuple[int, int, int, int], pos, size, font=None, text=""):
        """atlas_tile may be either a Surface containing the 9-patch source
        or a mapping of state->Surface (e.g. {'normal': surf, 'hover': surf2}).
        inset = (L, T, R, B) in pixels.
        pos = (x,y) in virtual coords, size=(w,h)
        """
        # atlas_tile can be a dict mapping state names to surfaces
        if isinstance(atlas_tile, dict):
            # store mapping and use 'normal' as fallback
            self._src_map = atlas_tile
            self.src = self._src_map.get("normal")
        else:
            self._src_map = None
            self.src = atlas_tile
        self.inset = inset
        self.pos = pos
        self.size = size
        self.font = font
        self.text = text
        self.state = "normal"
        # cache keyed by (state, size)
        self._cache = {}
        self.rect = pygame.Rect(pos[0], pos[1], size[0], size[1])

    def _slice_nine(self):
        x = 0
        y = 0
        src = self.src
        # if we have a state map, pick the current state's surface if available
        if self._src_map is not None:
            src = self._src_map.get(self.state, self._src_map.get("normal", self.src))
        if src is None:
            return {k: None for k in ["tl", "t", "tr", "l", "c", "r", "bl", "b", "br"]}
        w, h = src.get_size()
        L, T, R, B = self.inset
        pieces = {}
        coords = {
            "tl": (x, y, L, T),
            "t": (x + L, y, w - L - R, T),
            "tr": (x + w - R, y, R, T),
            "l": (x, y + T, L, h - T - B),
            "c": (x + L, y + T, w - L - R, h - T - B),
            "r": (x + w - R, y + T, R, h - T - B),
            "bl": (x, y + h - B, L, B),
            "b": (x + L, y + h - B, w - L - R, B),
            "br": (x + w - R, y + h - B, R, B),
        }
        for k, rc in coords.items():
            sx, sy, sw, sh = rc
            if sw <= 0 or sh <= 0:
                pieces[k] = None
            else:
                pieces[k] = src.subsurface(pygame.Rect(sx, sy, sw, sh)).copy().convert_alpha()
        return pieces

    def _build_surface(self, size):
        # cache per-state and size because different state surfaces may exist
        state = self.state
        key = (state, size)
        if key in self._cache:
            return self._cache[key]
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pieces = self._slice_nine()
        L, T, R, B = self.inset
        # corners
        if pieces["tl"]:
            surf.blit(pieces["tl"], (0, 0))
        if pieces["tr"]:
            surf.blit(pieces["tr"], (w - R, 0))
        if pieces["bl"]:
            surf.blit(pieces["bl"], (0, h - B))
        if pieces["br"]:
            surf.blit(pieces["br"], (w - R, h - B))
        # edges & center — scale nearest
        def blit_scaled(src, dx, dy, dw, dh):
            if src is None:
                return
            s = pygame.transform.scale(src, (dw, dh))
            surf.blit(s, (dx, dy))

        if pieces["t"]:
            blit_scaled(pieces["t"], L, 0, w - L - R, T)
        if pieces["b"]:
            blit_scaled(pieces["b"], L, h - B, w - L - R, B)
        if pieces["l"]:
            blit_scaled(pieces["l"], 0, T, L, h - T - B)
        if pieces["r"]:
            blit_scaled(pieces["r"], w - R, T, R, h - T - B)
        if pieces["c"]:
            blit_scaled(pieces["c"], L, T, w - L - R, h - T - B)

        # draw text
        if self.text and self.font:
            txt = self.font.render(self.text, False, (255, 255, 255))
            surf.blit(txt, ((w - txt.get_width()) // 2, (h - txt.get_height()) // 2))
        self._cache[key] = surf
        return surf

    def draw(self, dest_surf):
        s = self._build_surface(self.size)
        dest_surf.blit(s, self.rect.topleft)

    def handle_event(self, ev):
        # simple hover/press handling using virtual coords
        if ev.type == pygame.MOUSEMOTION:
            mx, my = ev.pos
            if self.rect.collidepoint(mx, my):
                if self.state == "normal":
                    self.state = "hover"
            else:
                if self.state != "pressed":
                    self.state = "normal"
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.state = "pressed"
                return True
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if self.state == "pressed":
                clicked = self.rect.collidepoint(ev.pos)
                self.state = "hover" if clicked else "normal"
                return clicked
        return False


class ThreeSliceButton:
    def __init__(self, left_surf, center_surf, right_surf, pos, size, font=None, text=""):
        self.left = left_surf
        self.center = center_surf
        self.right = right_surf
        self.pos = pos
        self.size = size
        self.font = font
        self.text = text
        self.rect = pygame.Rect(pos[0], pos[1], size[0], size[1])
        self._cache = {}
        self.state = "normal"

    def _build(self, size):
        key = size
        if key in self._cache:
            return self._cache[key]
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        lw = self.left.get_width()
        rw = self.right.get_width()
        cw = w - lw - rw
        if cw < 0:
            cw = 0
        surf.blit(self.left, (0, 0))
        if cw > 0:
            center_scaled = pygame.transform.scale(self.center, (cw, h))
            surf.blit(center_scaled, (lw, 0))
        surf.blit(self.right, (lw + cw, 0))
        if self.text and self.font:
            txt = self.font.render(self.text, False, (255, 255, 255))
            surf.blit(txt, ((w - txt.get_width()) // 2, (h - txt.get_height()) // 2))
        self._cache[key] = surf
        return surf

    def draw(self, dest_surf):
        s = self._build(self.size)
        dest_surf.blit(s, self.rect.topleft)

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(ev.pos):
                if self.state == "normal":
                    self.state = "hover"
            else:
                if self.state != "pressed":
                    self.state = "normal"
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.state = "pressed"
                return True
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if self.state == "pressed":
                clicked = self.rect.collidepoint(ev.pos)
                self.state = "hover" if clicked else "normal"
                return clicked
        return False