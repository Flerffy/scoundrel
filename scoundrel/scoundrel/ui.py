import pygame
from pathlib import Path
from typing import Optional


# Basic button + menu implementation for the title/menu screen.
# Usage: Menu(screen).run() -> returns "continue"|"new"|"settings"|"quit" or None

SCREEN_PADDING_TOP = 80
BUTTON_WIDTH = 420
BUTTON_HEIGHT = 56
BUTTON_SPACING = 14
TITLE_GAP = 36

FONT_NAME = None  # None uses default pygame font; set to a path in assets if you want


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
        txt = font.render(self.text, True, (240, 240, 240) if self.enabled else (160, 160, 160))
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
            if FONT_NAME:
                font_path = Path(FONT_NAME)
                self.title_font = pygame.font.Font(str(font_path), 64)
                self.btn_font = pygame.font.Font(str(font_path), 28)
            else:
                self.title_font = pygame.font.SysFont(None, 64)
                self.btn_font = pygame.font.SysFont(None, 28)
        except Exception:
            self.title_font = pygame.font.SysFont(None, 64)
            self.btn_font = pygame.font.SysFont(None, 28)
        # shared small font used for non-menu UI (game over / score display)
        try:
            self.font = pygame.font.Font(None, 36)
        except Exception:
            self.font = pygame.font.SysFont(None, 36)

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
        for text, enabled, action in labels:
            rect = (center_x - BUTTON_WIDTH // 2, y, BUTTON_WIDTH, BUTTON_HEIGHT)
            btn = Button(rect, text, enabled=enabled, action=action)
            self.buttons.append(btn)
            y += BUTTON_HEIGHT + BUTTON_SPACING

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
        title_surf = self.title_font.render(self.title, True, (235, 220, 120))
        title_rect = title_surf.get_rect(center=(w // 2, SCREEN_PADDING_TOP // 2 + 10))
        self.screen.blit(title_surf, title_rect)
        # Buttons
        for btn in self.buttons:
            btn.draw(self.screen, self.btn_font)

    def draw_game_over(self, score):
        self.screen.fill((0, 0, 0))
        game_over_surface = self.font.render("Game Over", True, (255, 0, 0))
        self.screen.blit(game_over_surface, (self.screen.get_width() // 2 - game_over_surface.get_width() // 2, 100))

        score_surface = self.font.render(f"Your Score: {score}", True, (255, 255, 255))
        self.screen.blit(score_surface, (self.screen.get_width() // 2 - score_surface.get_width() // 2, 200))

        restart_surface = self.font.render("SPACE to Return to Menu", True, (255, 255, 255))
        self.screen.blit(restart_surface, (self.screen.get_width() // 2 - restart_surface.get_width() // 2, 300))

        pygame.display.flip()

    def update_score_display(self, score, high_score):
        score_surface = self.font.render(f"Score: {score}  High Score: {high_score}", True, (255, 255, 255))
        self.screen.blit(score_surface, (10, 10))