import pygame
import json
import math
from pathlib import Path
from typing import Optional, Callable, cast

# Attempt to import atlas-backed UI widgets when available
NinePatchButton = None
UIAtlas = None

# Prefer to use importlib if available to attempt package-relative imports
try:
    import importlib
except Exception:
    importlib = None

if importlib is not None:
    _mod = None
    # try relative import first (works when package context is set)
    try:
        if __package__:
            _mod = importlib.import_module(".utils.ui_atlas", package=__package__)
    except Exception:
        _mod = None

    if _mod is None:
        try:
            _mod = importlib.import_module("utils.ui_atlas")
        except Exception:
            _mod = None

    if _mod is not None:
        UIAtlas = getattr(_mod, "UIAtlas", None)

    # try to import NinePatchButton from ui.widgets
    try:
        _mod = importlib.import_module("ui.widgets")
    except Exception:
        _mod = None

    if _mod is not None:
        NinePatchButton = getattr(_mod, "NinePatchButton", None)

# Fallback to a direct relative import if the above failed
if UIAtlas is None:
    try:
        from .utils.ui_atlas import UIAtlas as _UIAtlas
        UIAtlas = _UIAtlas
    except Exception:
        UIAtlas = None


# Basic button + menu implementation for the title/menu screen.
# Usage: Menu(screen).run() -> returns "continue"|"new"|"settings"|"quit" or None

SCREEN_PADDING_TOP = 80
BUTTON_WIDTH = 420
BUTTON_HEIGHT = 56
BUTTON_SPACING = 14
TITLE_GAP = 36

FONT_NAME = None  # None uses default pygame font; set to a path in assets if you want

# Attempt to prefer bundled DungeonFont.ttf in assets/ui if present
try:
    DEFAULT_FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "ui" / "DungeonFont.ttf"
    if not DEFAULT_FONT_PATH.exists():
        DEFAULT_FONT_PATH = None
except Exception:
    DEFAULT_FONT_PATH = None


class Button:
    def __init__(self, rect, text, enabled=True, action: Optional[str] = None, font=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.enabled = enabled
        self.hover = False
        # explicit action attribute to keep static checkers happy
        self.action: Optional[str] = action
        # pre-rendered label surfaces (enabled/disabled) to avoid per-frame rendering
        self._label_enabled = None
        self._label_disabled = None
        try:
            if font is not None:
                try:
                    self._label_enabled = font.render(self.text, False, (240, 240, 240))
                except Exception:
                    self._label_enabled = None
                try:
                    self._label_disabled = font.render(self.text, False, (160, 160, 160))
                except Exception:
                    self._label_disabled = None
        except Exception:
            self._label_enabled = None
            self._label_disabled = None

    def draw(self, surf, font):
        base = (60, 60, 60) if self.enabled else (40, 40, 40)
        hover_color = (100, 100, 100)
        color = hover_color if (self.enabled and self.hover) else base
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        # border
        pygame.draw.rect(surf, (200, 200, 200), self.rect, width=2, border_radius=8)
        # text (use cached surfaces if available)
        try:
            if self.enabled and self._label_enabled is not None:
                lbl = self._label_enabled
            elif (not self.enabled) and self._label_disabled is not None:
                lbl = self._label_disabled
            else:
                lbl = None
            if lbl is not None:
                surf.blit(lbl, lbl.get_rect(center=self.rect.center))
            else:
                txt = font.render(self.text, False, (240, 240, 240) if self.enabled else (160, 160, 160))
                txt_rect = txt.get_rect(center=self.rect.center)
                surf.blit(txt, txt_rect)
        except Exception:
            try:
                txt = font.render(self.text, False, (240, 240, 240) if self.enabled else (160, 160, 160))
                surf.blit(txt, txt.get_rect(center=self.rect.center))
            except Exception:
                pass
        # if disabled, draw strike-through
        if not self.enabled:
            y = self.rect.centery
            pygame.draw.line(surf, (220, 60, 60), (self.rect.left + 8, y), (self.rect.right - 8, y), 3)

    def update_hover(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)

    def clicked(self):
        return self.enabled


class Menu:
    def __init__(self, screen, title="Scoundrel"):
        self.screen = screen
        self.title = title
        self.clock = pygame.time.Clock()
        self._setup_fonts()
        self._create_buttons()
        # Attempt to use a shared background tile and scaled-cache so menu,
        # settings, and gameplay all tile and scale the same image.
        try:
            from .utils.shared_bg import get_shared_bg_tile
            try:
                self._bg_tile, self._bg_tile_scaled_cache = get_shared_bg_tile()
            except Exception:
                self._bg_tile = None
                self._bg_tile_scaled_cache = {}
        except Exception:
            # fallback to previous per-instance behavior if helper isn't available
            try:
                bg_path = Path(__file__).resolve().parents[1] / "assets" / "backgrounds" / "ClassicBackground.png"
                if bg_path.exists():
                    # Avoid convert() to be robust against initialization order.
                    self._bg_tile = pygame.image.load(str(bg_path))
                else:
                    self._bg_tile = None
            except Exception:
                self._bg_tile = None
            self._bg_tile_scaled_cache = {}

    def _setup_fonts(self):
        # Prefer bundled font if present, otherwise use pygame default
        try:
            # priority: explicit FONT_NAME -> bundled DungeonFont.ttf -> system font
            if FONT_NAME:
                font_path = Path(FONT_NAME)
                self.title_font = pygame.font.Font(str(font_path), 64)
                self.btn_font = pygame.font.Font(str(font_path), 28)
            elif DEFAULT_FONT_PATH:
                self.title_font = pygame.font.Font(str(DEFAULT_FONT_PATH), 64)
                self.btn_font = pygame.font.Font(str(DEFAULT_FONT_PATH), 28)
            else:
                self.title_font = pygame.font.Font(None, 64)
                self.btn_font = pygame.font.Font(None, 28)
        except Exception:
            self.title_font = pygame.font.Font(None, 64)
            self.btn_font = pygame.font.Font(None, 28)
        # shared small font used for non-menu UI (game over / score display)
        try:
            if DEFAULT_FONT_PATH:
                self.font = pygame.font.Font(str(DEFAULT_FONT_PATH), 36)
            else:
                self.font = pygame.font.Font(None, 36)
        except Exception:
            self.font = pygame.font.Font(None, 36)

    def _create_buttons(self):
        w, h = self.screen.get_size()
        center_x = w // 2
        start_y = SCREEN_PADDING_TOP + TITLE_GAP + 40

        labels = [
            ("New Game", True, "new"),
            ("Custom Game (placeholder)", False, None),  # disabled
            ("Settings", True, "settings"),
            ("Credits", True, "credits"),
            ("Quit", True, "quit"),
        ]

        self.buttons = []
        y = start_y
        # Try to create atlas-backed buttons when possible
        # Load atlas image and mapping if available
        atlas_img = Path(__file__).resolve().parents[1] / "assets" / "ui" / "BlackGreyUISheet.png"
        atlas_json = Path(__file__).resolve().parents[1] / "assets" / "ui" / "BlackGreyUISheet.json"
        mapping_json = Path(__file__).resolve().parents[1] / "assets" / "ui" / "BlackGreyUISheet_mapping.json"
        atlas = None
        mapping = {}
        inset = (4, 4, 4, 4)
        if UIAtlas is not None and atlas_img.exists():
            try:
                ua = UIAtlas(atlas_img, atlas_json if atlas_json.exists() else None)
                try:
                    ua.load_image()
                except Exception:
                    pass
                if atlas_json.exists():
                    try:
                        ua.load_descriptor(atlas_json)
                    except Exception:
                        pass
                atlas = ua
            except Exception:
                atlas = None
        if mapping_json.exists():
            try:
                mapping = json.loads(mapping_json.read_text())
            except Exception:
                mapping = {}

        for text, enabled, action in labels:
            rect = (center_x - BUTTON_WIDTH // 2, y, BUTTON_WIDTH, BUTTON_HEIGHT)
            if atlas is not None and NinePatchButton is not None:
                # assemble state surfaces if available
                try:
                    def _get_tile(name):
                        tid = mapping.get(name)
                        if not tid:
                            return None, None
                        tile = atlas.tiles.get(tid)
                        if not tile:
                            return None, None
                        tx = tile.get("x")
                        ty = tile.get("y")
                        tw = tile.get("w")
                        th = tile.get("h")
                        # ensure atlas.image exists and is usable and coordinates are present
                        atlas_image = getattr(atlas, "image", None)
                        if atlas_image is None or not hasattr(atlas_image, "subsurface"):
                            return None, None
                        # avoid passing None into int() / pygame.Rect
                        if tx is None or ty is None or tw is None or th is None:
                            return None, None
                        try:
                            rect = pygame.Rect(int(tx), int(ty), int(tw), int(th))
                            surf = atlas_image.subsurface(rect).copy().convert_alpha()
                        except Exception:
                            return None, None
                        inset = tuple(tile.get("ninepatch", [4, 4, 4, 4]))
                        return surf, inset

                    sm = {}
                    n_surf, n_inset = _get_tile("button_normal")
                    h_surf, _ = _get_tile("button_hover")
                    p_surf, _ = _get_tile("button_pressed")
                    if n_surf is not None:
                        if h_surf is not None or p_surf is not None:
                            # build map
                            if n_surf is not None:
                                sm["normal"] = n_surf
                            if h_surf is not None:
                                sm["hover"] = h_surf
                            if p_surf is not None:
                                sm["pressed"] = p_surf
                            btn = MenuAtlasButton(rect, text, enabled, action, NinePatchButton, sm, n_inset, font=self.btn_font)
                        else:
                            btn = MenuAtlasButton(rect, text, enabled, action, NinePatchButton, n_surf, n_inset, font=self.btn_font)
                    else:
                        btn = Button(rect, text, enabled=enabled, action=action)
                except Exception:
                    btn = Button(rect, text, enabled=enabled, action=action, font=self.btn_font)
            else:
                btn = Button(rect, text, enabled=enabled, action=action)
            self.buttons.append(btn)
            y += BUTTON_HEIGHT + BUTTON_SPACING
    # small adapter so Menu can use NinePatchButton-backed buttons with the
    # same minimal interface as the legacy Button class.
    def run(self):
        """Run the menu loop. Returns action string or None on window close."""
        running = True
        result = None
        while running:
            self.clock.tick(60)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.KEYDOWN:
                    # Do not map Escape to quitting the program; keep Quit button explicit.
                    pass
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for btn in self.buttons:
                        if btn.rect.collidepoint(ev.pos) and btn.clicked():
                            # Special-case credits: show credits screen and continue the menu
                            if btn.action == "credits":
                                try:
                                    self._show_credits()
                                except Exception:
                                    # swallow errors from credits display and continue
                                    pass
                                break
                            result = btn.action
                            running = False
                            break

            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                btn.update_hover(mouse_pos)

            self._draw()
            pygame.display.flip()
        return result

    def _show_credits(self):
        """Display the credits screen. Reads from assets/credits.txt (editable).
        Returns when the user presses any key or clicks the mouse.
        """
        # load credits text
        credits_path = Path(__file__).resolve().parents[1] / "assets" / "credits.txt"
        if credits_path.exists():
            try:
                raw = credits_path.read_text(encoding="utf-8")
            except Exception:
                raw = "(Unable to read credits file)"
        else:
            raw = "No credits file found. Please create assets/credits.txt to edit this screen."

        lines = []
        for l in raw.splitlines():
            if l.strip() == "":
                lines.append("")
            else:
                lines.append(l.rstrip())

        # simple credits display loop
        showing = True
        clock = pygame.time.Clock()
        while showing:
            clock.tick(60)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    # propagate quit by raising SystemExit to let caller handle
                    raise SystemExit()
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    showing = False

            # draw background similar to menu
            w, h = self.screen.get_size()
            tile = getattr(self, "_bg_tile", None)
            if tile is not None:
                tw, th = tile.get_size()
                # reuse cached scaled tile if available
                # compute scale like _draw to match tiling
                cw, ch = (120, 180)
                virtual_w = 16 + (cw + 16) * 4 + 16 + cw + 16
                virtual_h = max(640, 150 + ch + 200)
                # integer division to pick integer scale (may be 0)
                scale = min(w // virtual_w, h // virtual_h) if virtual_w and virtual_h else 0
                if scale >= 1:
                    cached = self._bg_tile_scaled_cache.get(scale)
                    if cached is None:
                        try:
                            cached = pygame.transform.scale(tile, (tw * scale, th * scale))
                        except Exception:
                            cached = tile
                        self._bg_tile_scaled_cache[scale] = cached
                    ttw, tth = cached.get_size()
                    dx = (w - virtual_w * scale) // 2
                    dy = (h - virtual_h * scale) // 2
                    off_x = dx % ttw
                    off_y = dy % tth
                    start_x = off_x
                    start_y = off_y
                    if start_x > 0:
                        start_x -= ttw
                    if start_y > 0:
                        start_y -= tth
                    for yy in range(start_y, h, tth):
                        for xx in range(start_x, w, ttw):
                            self.screen.blit(cached, (xx, yy))
                else:
                    for yy in range(0, h, th):
                        for xx in range(0, w, tw):
                            self.screen.blit(tile, (xx, yy))
            else:
                self.screen.fill((10, 10, 10))

            # title
            title = self.title_font.render("Credits", False, (235, 220, 120))
            self.screen.blit(title, title.get_rect(center=(w // 2, 72)))

            # render credits lines
            y = 120
            pad = 6
            for ln in lines:
                # wrap long lines crudely by clipping; user can insert line breaks
                surf = self.font.render(ln, False, (240, 240, 240)) if ln != "" else None
                if surf:
                    r = surf.get_rect(center=(w // 2, y))
                    self.screen.blit(surf, r)
                    y += surf.get_height() + pad
                else:
                    y += self.font.get_linesize() // 2

            # prompt
            prompt = self.btn_font.render("Press any key or click to return", False, (200, 200, 200))
            self.screen.blit(prompt, prompt.get_rect(center=(w // 2, h - 60)))

            pygame.display.flip()

    def _draw(self):
        w, h = self.screen.get_size()
        # background: tile if available
        tile = getattr(self, "_bg_tile", None)
        if tile is not None:
            tw, th = tile.get_size()
            # Compute a virtual render size and integer scale that matches
            # GameEngine's computation so menu tiling lines up with gameplay.
            # Use the same defaults as GameEngine: card_size (120x180) and
            # virtual layout math.
            cw, ch = (120, 180)
            virtual_w = 16 + (cw + 16) * 4 + 16 + cw + 16
            virtual_h = max(640, 150 + ch + 200)
            # integer division to pick integer scale (may be 0)
            scale = min(w // virtual_w, h // virtual_h) if virtual_w and virtual_h else 0
            if scale >= 1:
                # center offset for a scaled game-area like GameEngine would compute
                scaled_game_w = virtual_w * scale
                scaled_game_h = virtual_h * scale
                dx = (w - scaled_game_w) // 2
                dy = (h - scaled_game_h) // 2

                # use cached scaled tile for this integer scale
                cached = self._bg_tile_scaled_cache.get(scale)
                if cached is None:
                    try:
                        cached = pygame.transform.scale(tile, (tw * scale, th * scale))
                    except Exception:
                        cached = tile
                    # Convert cached scaled tile to display format to speed blits.
                    try:
                        if cached is not None:
                            if cached.get_flags() & pygame.SRCALPHA:
                                try:
                                    cached = cached.convert_alpha()
                                except Exception:
                                    pass
                            else:
                                try:
                                    cached = cached.convert()
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    self._bg_tile_scaled_cache[scale] = cached

                ttw, tth = cached.get_size()
                off_x = dx % ttw
                off_y = dy % tth
                start_x = off_x
                start_y = off_y
                if start_x > 0:
                    start_x -= ttw
                if start_y > 0:
                    start_y -= tth
                for yy in range(start_y, h, tth):
                    for xx in range(start_x, w, ttw):
                        self.screen.blit(cached, (xx, yy))
            else:
                for yy in range(0, h, th):
                    for xx in range(0, w, tw):
                        self.screen.blit(tile, (xx, yy))
        else:
            self.screen.fill((18, 18, 18))
        # Title
        title_surf = self.title_font.render(self.title, False, (235, 220, 120))
        title_rect = title_surf.get_rect(center=(w // 2, SCREEN_PADDING_TOP // 2 + 10))
        self.screen.blit(title_surf, title_rect)
        # Buttons
        for btn in self.buttons:
            btn.draw(self.screen, self.btn_font)

    def draw_game_over(self, score):
        self.screen.fill((0, 0, 0))
        game_over_surface = self.font.render("Game Over", False, (255, 0, 0))
        self.screen.blit(game_over_surface, (self.screen.get_width() // 2 - game_over_surface.get_width() // 2, 100))

        score_surface = self.font.render(f"Your Score: {score}", False, (255, 255, 255))
        self.screen.blit(score_surface, (self.screen.get_width() // 2 - score_surface.get_width() // 2, 200))

        restart_surface = self.font.render("SPACE to Return to Menu", False, (255, 255, 255))
        self.screen.blit(restart_surface, (self.screen.get_width() // 2 - restart_surface.get_width() // 2, 300))

        pygame.display.flip()

    def _show_settings(self):
        """Display a simple settings screen with 3 sliders: Master, BGM, SFX.

        Adjusts pygame.mixer.music volume for BGM and uses audio_settings
        to propagate changes to runtime sfx playback.
        """
        # lazy import of audio settings (best-effort) using dynamic import to avoid
        # static unresolved relative import errors in different run contexts.
        try:
            import importlib
        except Exception:
            importlib = None

        get_master_fn: Optional[Callable[[], float]] = None
        get_bgm_fn: Optional[Callable[[], float]] = None
        get_sfx_fn: Optional[Callable[[], float]] = None

        set_master_fn: Optional[Callable[[float], None]] = None
        set_bgm_fn: Optional[Callable[[float], None]] = None
        set_sfx_fn: Optional[Callable[[float], None]] = None

        if importlib is not None:
            _mod = None
            try:
                if __package__:
                    _mod = importlib.import_module(".utils.audio_settings", package=__package__)
            except Exception:
                _mod = None

            if _mod is None:
                try:
                    _mod = importlib.import_module("utils.audio_settings")
                except Exception:
                    _mod = None

            if _mod is not None:
                try:
                    get_master_fn = cast(Optional[Callable[[], float]], getattr(_mod, "get_master", None))
                    get_bgm_fn = cast(Optional[Callable[[], float]], getattr(_mod, "get_bgm", None))
                    get_sfx_fn = cast(Optional[Callable[[], float]], getattr(_mod, "get_sfx", None))
                    set_master_fn = cast(Optional[Callable[[float], None]], getattr(_mod, "set_master", None))
                    set_bgm_fn = cast(Optional[Callable[[float], None]], getattr(_mod, "set_bgm", None))
                    set_sfx_fn = cast(Optional[Callable[[float], None]], getattr(_mod, "set_sfx", None))
                except Exception:
                    get_master_fn = get_bgm_fn = get_sfx_fn = None
                    set_master_fn = set_bgm_fn = set_sfx_fn = None

        # last-resort attempt using builtin __import__ (no static import statement)
        if get_master_fn is None:
            try:
                mod = __import__("utils.audio_settings", fromlist=["get_master", "get_bgm", "get_sfx", "set_master", "set_bgm", "set_sfx"])
                get_master_fn = cast(Optional[Callable[[], float]], getattr(mod, "get_master", None))
                get_bgm_fn = cast(Optional[Callable[[], float]], getattr(mod, "get_bgm", None))
                get_sfx_fn = cast(Optional[Callable[[], float]], getattr(mod, "get_sfx", None))
                set_master_fn = cast(Optional[Callable[[float], None]], getattr(mod, "set_master", None))
                set_bgm_fn = cast(Optional[Callable[[float], None]], getattr(mod, "set_bgm", None))
                set_sfx_fn = cast(Optional[Callable[[float], None]], getattr(mod, "set_sfx", None))
            except Exception:
                pass

        # provide local fallbacks that do nothing if import failed
        if get_master_fn is None or get_bgm_fn is None or get_sfx_fn is None or set_master_fn is None or set_bgm_fn is None or set_sfx_fn is None:
            def _fm():
                return 1.0
            def _fb():
                return 0.5
            def _fs():
                return 0.9
            def _sm(v):
                pass
            def _sb(v):
                pass
            def _ss(v):
                pass
            get_master_fn = _fm
            get_bgm_fn = _fb
            get_sfx_fn = _fs
            set_master_fn = _sm
            set_bgm_fn = _sb
            set_sfx_fn = _ss

        # slider geometry in screen coords
        w, h = self.screen.get_size()
        box_w = min(680, w - 120)
        box_h = 360
        bx = (w - box_w) // 2
        by = (h - box_h) // 2

        # reserve space on the right of sliders for the numeric value
        value_area = 80

        def slider_rect(i):
            # three vertical positions
            pad_top = 96
            spacing = 64
            sx = bx + 36
            # leave room for value text inside the box
            sw = box_w - 72 - value_area
            sy = by + pad_top + i * spacing
            sh = 18
            return (sx, sy, sw, sh)

        dragging = None
        clock = pygame.time.Clock()
        running = True
        while running:
            dt = clock.tick(60) / 1000.0
            t = pygame.time.get_ticks() / 1000.0

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    # propagate quit by raising SystemExit to let caller handle
                    raise SystemExit()
                if ev.type == pygame.KEYDOWN:
                    # Any key returns to the menu/settings exit
                    running = False
                    break
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx, my = getattr(ev, 'pos', pygame.mouse.get_pos())
                    clicked_slider = False
                    for i, name in enumerate(("master", "bgm", "sfx")):
                        sx, sy, sw, sh = slider_rect(i)
                        r = pygame.Rect(sx, sy - 6, sw, sh + 12)
                        if r.collidepoint(mx, my):
                            dragging = name
                            clicked_slider = True
                            # update immediately on press
                            rel = (mx - sx) / sw if sw > 0 else 0.0
                            val = max(0.0, min(1.0, rel))
                            try:
                                if name == "master":
                                    set_master_fn(val)
                                elif name == "bgm":
                                    set_bgm_fn(val)
                                else:
                                    set_sfx_fn(val)
                            except Exception:
                                pass
                            break
                    # if click was not on a slider, return from settings
                    if not clicked_slider:
                        running = False
                        break
                if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                    dragging = None
                if ev.type == pygame.MOUSEMOTION and dragging is not None:
                    mx, my = getattr(ev, 'pos', pygame.mouse.get_pos())
                    i = ("master", "bgm", "sfx").index(dragging)
                    sx, sy, sw, sh = slider_rect(i)
                    rel = (mx - sx) / sw if sw > 0 else 0.0
                    val = max(0.0, min(1.0, rel))
                    try:
                        if dragging == "master":
                            set_master_fn(val)
                        elif dragging == "bgm":
                            set_bgm_fn(val)
                        else:
                            set_sfx_fn(val)
                    except Exception:
                        pass

            # draw background box
            # tile/canvas background like menu (use integer-scale tiling to match GameEngine)
            tile = getattr(self, "_bg_tile", None)
            if tile is not None:
                tw, th = tile.get_size()
                cw, ch = (120, 180)
                virtual_w = 16 + (cw + 16) * 4 + 16 + cw + 16
                virtual_h = max(640, 150 + ch + 200)
                # integer division to pick integer scale (may be 0)
                scale = min(w // virtual_w, h // virtual_h) if virtual_w and virtual_h else 0
                if scale >= 1:
                    cached = self._bg_tile_scaled_cache.get(scale)
                    if cached is None:
                        try:
                            cached = pygame.transform.scale(tile, (tw * scale, th * scale))
                        except Exception:
                            cached = tile
                        self._bg_tile_scaled_cache[scale] = cached
                    ttw, tth = cached.get_size()
                    dx = (w - virtual_w * scale) // 2
                    dy = (h - virtual_h * scale) // 2
                    off_x = dx % ttw
                    off_y = dy % tth
                    start_x = off_x
                    start_y = off_y
                    if start_x > 0:
                        start_x -= ttw
                    if start_y > 0:
                        start_y -= tth
                    for yy in range(start_y, h, tth):
                        for xx in range(start_x, w, ttw):
                            self.screen.blit(cached, (xx, yy))
                else:
                    for yy in range(0, h, th):
                        for xx in range(0, w, tw):
                            self.screen.blit(tile, (xx, yy))
            else:
                self.screen.fill((16, 16, 20))

            # title
            title = self.title_font.render("Settings", False, (235, 220, 120))
            self.screen.blit(title, title.get_rect(center=(w // 2, by + 40)))

            # draw box
            pygame.draw.rect(self.screen, (24, 24, 24), (bx, by, box_w, box_h))
            pygame.draw.rect(self.screen, (140, 140, 140), (bx, by, box_w, box_h), 2)

            # slider labels and values using the fetched getter functions
            labels = [("Master", get_master_fn()), ("BGM", get_bgm_fn()), ("SFX", get_sfx_fn())]
            for i, (lbl, val) in enumerate(labels):
                sx, sy, sw, sh = slider_rect(i)
                # label
                lab_surf = self.font.render(f"{lbl}", False, (220, 220, 220))
                self.screen.blit(lab_surf, (sx, sy - 28))
                # track background
                pygame.draw.rect(self.screen, (60, 60, 60), (sx, sy, sw, sh), border_radius=8)
                # filled
                fill_w = int(sw * max(0.0, min(1.0, val)))
                pygame.draw.rect(self.screen, (80, 160, 220), (sx, sy, fill_w, sh), border_radius=8)
                # knob animation (pulse)
                pulse = 1.0 + 0.15 * math.sin(t * 6.0 + i * 1.3)
                kx = sx + max(0, min(sw, fill_w))
                ky = sy + sh // 2
                kr = int(max(6, min(14, 8 * pulse)))
                pygame.draw.circle(self.screen, (220, 220, 220), (kx, ky), kr)
                # value text drawn inside the box on the right
                vtxt = self.font.render(f"{int(val*100)}%", False, (200, 200, 200))
                v_x = bx + box_w - value_area + 8
                v_y = sy - 6
                # center value vertically with the slider
                self.screen.blit(vtxt, (v_x, v_y))

            # prompt
            prompt = self.btn_font.render("Drag sliders or press any key / click to return", False, (200, 200, 200))
            self.screen.blit(prompt, prompt.get_rect(center=(w // 2, by + box_h - 28)))

            pygame.display.flip()

    def update_score_display(self, score, high_score):
        score_surface = self.font.render(f"Score: {score}  High Score: {high_score}", False, (255, 255, 255))
        self.screen.blit(score_surface, (10, 10))


class MenuAtlasButton:
    def __init__(self, rect, text, enabled, action, NPClass, atlas_tile, inset, font=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.enabled = enabled
        self.action = action
        # pre-render label surfaces for fallback drawing
        self._label_enabled = None
        self._label_disabled = None
        try:
            if font is not None:
                try:
                    self._label_enabled = font.render(self.text, False, (240, 240, 240))
                except Exception:
                    self._label_enabled = None
                try:
                    self._label_disabled = font.render(self.text, False, (160, 160, 160))
                except Exception:
                    self._label_disabled = None
        except Exception:
            self._label_enabled = None
            self._label_disabled = None
        # create NinePatchButton instance; NPClass expects (tile, inset, pos, size, font, text)
        try:
            pos = (self.rect.left, self.rect.top)
            size = (self.rect.width, self.rect.height)
            # pass the font into the NinePatchButton if available so it can
            # draw text itself when rendering via atlas-backed widget
            self._np = NPClass(atlas_tile, inset, pos, size, font=font, text=text)
        except Exception:
            self._np = None
        self.hover = False

    def draw(self, surf, font):
        if self._np is not None:
            # set font for text drawing if applicable
            try:
                self._np.font = font
                self._np.draw(surf)
            except Exception:
                # fallback to simple rect
                pygame.draw.rect(surf, (80, 80, 80), self.rect, border_radius=8)
        else:
            pygame.draw.rect(surf, (80, 80, 80), self.rect, border_radius=8)
            # use cached label surfaces when available
            try:
                if self.enabled and self._label_enabled is not None:
                    lbl = self._label_enabled
                elif (not self.enabled) and self._label_disabled is not None:
                    lbl = self._label_disabled
                else:
                    lbl = None
                if lbl is not None:
                    surf.blit(lbl, lbl.get_rect(center=self.rect.center))
                else:
                    txt = font.render(self.text, False, (240, 240, 240))
                    surf.blit(txt, txt.get_rect(center=self.rect.center))
            except Exception:
                try:
                    txt = font.render(self.text, False, (240, 240, 240))
                    surf.blit(txt, txt.get_rect(center=self.rect.center))
                except Exception:
                    pass

    def update_hover(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)
        if self._np is not None:
            try:
                self._np.state = "hover" if self.hover else "normal"
            except Exception:
                pass

    def clicked(self):
        return self.enabled