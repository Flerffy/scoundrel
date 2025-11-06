from pathlib import Path
import pygame
from typing import Tuple


# Simple card sprite-sheet loader.
# Assumptions:
# - Each sprite sheet contains 13 columns (ranks Ace..King) and 4 rows (suits).
# - Default suit order (rows) for the provided sheets is: hearts, spades, clubs, diamonds
# - Default rank order (columns) is: A,2,3,...,10,J,Q,K

ASSETS_CARDS_DIR = Path(__file__).resolve().parents[2] / "assets" / "cards"

PACK_FILES = {
    "ClassicCards": "ClassicCards.png",
    "ClassicCardsDark": "ClassicCardsDark.png",
    "FantasyCards": "FantasyCards.png",
    "ForestCards": "ForestCards.png",
}

DEFAULT_RANKS = ["A"] + [str(n) for n in range(2, 11)] + ["J", "Q", "K"]
# sprite rows: top->bottom
DEFAULT_SUITS = ["hearts", "spades", "clubs", "diamonds"]


class CardArtManager:
    def __init__(self, pack_name: str = "ClassicCards"):
        self.pack_name = pack_name
        self.sheet_path = ASSETS_CARDS_DIR / PACK_FILES.get(pack_name, "")
        self.sheet = None
        self.card_surfaces = {}
        self.card_size = None
        # load lazily when pygame is initialized

    def _ensure_loaded(self):
        if self.sheet is not None:
            return
        try:
            if not self.sheet_path.exists():
                raise FileNotFoundError(self.sheet_path)
            self.sheet = pygame.image.load(str(self.sheet_path)).convert_alpha()
            w, h = self.sheet.get_size()
            # Many sheets use fixed card pixels; user reported 23x35 per card, but some sheets
            # include 1px gutters between cards or small margins. We'll attempt to detect
            # a (cw, ch, gutter_x, gutter_y) combination that exactly fits the sheet:
            #   13*cw + 12*gutter_x == w
            #    4*ch  +  3*gutter_y == h
            # Try small gutter values and pick the cw/ch nearest to expected fixed size.
            FIXED_CW = 23
            FIXED_CH = 35
            found = None
            best_score = None
            for gx in range(0, 6):
                rem_w = w - 12 * gx
                if rem_w <= 0:
                    continue
                if rem_w % 13 != 0:
                    continue
                cw_try = rem_w // 13
                for gy in range(0, 6):
                    rem_h = h - 3 * gy
                    if rem_h <= 0:
                        continue
                    if rem_h % 4 != 0:
                        continue
                    ch_try = rem_h // 4
                    # score closeness to expected fixed size
                    score = abs(cw_try - FIXED_CW) + abs(ch_try - FIXED_CH)
                    if best_score is None or score < best_score:
                        best_score = score
                        found = (cw_try, ch_try, gx, gy)

            if found:
                cw, ch, gutter_x, gutter_y = found
                cols = 13
                rows = 4
                # no outer margins assumed; columns spaced by cw + gutter_x
                x_step = cw + gutter_x
                y_step = ch + gutter_y
                left_margin = 0
                top_margin = 0
            else:
                # fallback: equal division
                cols = 13
                rows = 4
                cw = w // cols
                ch = h // rows
                gutter_x = 0
                gutter_y = 0
                x_step = cw
                y_step = ch
                left_margin = 0
                top_margin = 0

            self.card_size = (cw, ch)
            # extract surfaces: iterate columns (ranks) left->right and rows (suits) top->bottom
            for r_idx in range(cols):
                rank = DEFAULT_RANKS[r_idx] if r_idx < len(DEFAULT_RANKS) else DEFAULT_RANKS[r_idx % len(DEFAULT_RANKS)]
                for s_idx in range(rows):
                    suit = DEFAULT_SUITS[s_idx] if s_idx < len(DEFAULT_SUITS) else DEFAULT_SUITS[s_idx % len(DEFAULT_SUITS)]
                    x = left_margin + r_idx * x_step
                    y = top_margin + s_idx * y_step
                    # Extract the subsurface directly from the loaded sheet and
                    # convert it to the display's pixel format with alpha so
                    # subsequent blits are fast. Use copy() to get an independent Surface.
                    try:
                        subs = self.sheet.subsurface(pygame.Rect(x, y, cw, ch)).copy()
                        try:
                            subs = subs.convert_alpha()
                        except Exception:
                            # If convert_alpha fails (rare), fall back to the copy
                            pass
                        key = (suit, rank)
                        self.card_surfaces[key] = subs
                    except Exception:
                        # Fallback to the previous approach if subsurface fails
                        surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
                        surf.blit(self.sheet, (0, 0), pygame.Rect(x, y, cw, ch))
                        self.card_surfaces[(suit, rank)] = surf
        except Exception:
            # failure to load sheet; keep sheet None to signal fallback
            self.sheet = None

    def get_card(self, suit: str, rank: str, size: Tuple[int, int] | None = None) -> pygame.Surface | None:
        """Return a Surface for the requested card. If the sheet isn't available, return None.

        size: optional target size (width, height). If provided, the returned surface is scaled.
        """
        # ensure pygame has been initialized before loading images
        try:
            self._ensure_loaded()
        except Exception:
            return None

        if not self.sheet:
            return None

        key = (suit, rank)
        surf = self.card_surfaces.get(key)
        if surf is None:
            return None
        if size and surf.get_size() != size:
            try:
                # Use nearest-neighbor scaling to preserve pixel art / sharp edges.
                scaled = pygame.transform.scale(surf, size)
                try:
                    scaled = scaled.convert_alpha()
                except Exception:
                    pass
                return scaled
            except Exception:
                return surf
        return surf

    def available_packs(self):
        return [k for k, v in PACK_FILES.items() if (ASSETS_CARDS_DIR / v).exists()]
