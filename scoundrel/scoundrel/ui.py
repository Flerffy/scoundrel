import pygame
import json
from pathlib import Path
from typing import Optional

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
    def __init__(self, rect, text, enabled=True, action: Optional[str] = None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.enabled = enabled
        self.hover = False
        # explicit action attribute to keep static checkers happy
        self.action: Optional[str] = action

    def draw(self, surf, font):
        base = (60, 60, 60) if self.enabled else (40, 40, 40)
        hover_color = (100, 100, 100)
        color = hover_color if (self.enabled and self.hover) else base
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        # border
        pygame.draw.rect(surf, (200, 200, 200), self.rect, width=2, border_radius=8)
        # text
        txt = font.render(self.text, False, (240, 240, 240) if self.enabled else (160, 160, 160))
        txt_rect = txt.get_rect(center=self.rect.center)
        surf.blit(txt, txt_rect)
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
        # try to load background tile for the menu
        try:
            bg_path = Path(__file__).resolve().parents[1] / "assets" / "backgrounds" / "ClassicBackground.png"
            if bg_path.exists():
                self._bg_tile = pygame.image.load(str(bg_path)).convert()
            else:
                self._bg_tile = None
        except Exception:
            self._bg_tile = None
        # cache for scaled tiles (keyed by integer scale) so menu and engine
        # can reuse similarly-sized scaled tiles and avoid re-sampling differences
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
                            btn = MenuAtlasButton(rect, text, enabled, action, NinePatchButton, sm, n_inset)
                        else:
                            btn = MenuAtlasButton(rect, text, enabled, action, NinePatchButton, n_surf, n_inset)
                    else:
                        btn = Button(rect, text, enabled=enabled, action=action)
                except Exception:
                    btn = Button(rect, text, enabled=enabled, action=action)
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
                            result = btn.action
                            running = False
                            break

            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                btn.update_hover(mouse_pos)

            self._draw()
            pygame.display.flip()
        return result

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
            scale = min(max(1, w // virtual_w), max(1, h // virtual_h)) if virtual_w and virtual_h else 1

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

    def update_score_display(self, score, high_score):
        score_surface = self.font.render(f"Score: {score}  High Score: {high_score}", False, (255, 255, 255))
        self.screen.blit(score_surface, (10, 10))


class MenuAtlasButton:
    def __init__(self, rect, text, enabled, action, NPClass, atlas_tile, inset):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.enabled = enabled
        self.action = action
        # create NinePatchButton instance; NPClass expects (tile, inset, pos, size, font, text)
        try:
            pos = (self.rect.left, self.rect.top)
            size = (self.rect.width, self.rect.height)
            self._np = NPClass(atlas_tile, inset, pos, size, font=None, text=text)
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
            txt = font.render(self.text, False, (240, 240, 240))
            surf.blit(txt, txt.get_rect(center=self.rect.center))

    def update_hover(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)
        if self._np is not None:
            try:
                self._np.state = "hover" if self.hover else "normal"
            except Exception:
                pass

    def clicked(self):
        return self.enabled