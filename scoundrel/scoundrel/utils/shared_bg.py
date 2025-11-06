from pathlib import Path
from typing import Dict, Optional, Tuple
import pygame

# Module-level cache for a single shared background tile and scaled-cache
_shared_tile: Optional[pygame.Surface] = None
_shared_scaled_cache: Dict[int, pygame.Surface] = {}


def get_shared_bg_tile() -> Tuple[Optional[pygame.Surface], Dict[int, pygame.Surface]]:
    """Return (tile_surface_or_None, scaled_cache_dict).

    The scaled_cache dict is safe to share between callers; keys are integer
    scales and values are scaled Surface objects. This helper loads the
    bundled ClassicBackground.png from the package assets on first use.
    """
    global _shared_tile, _shared_scaled_cache
    if _shared_tile is not None:
        return _shared_tile, _shared_scaled_cache

    try:
        # assets lives two levels up from this utils package (package layout:
        # scoundrel/scoundrel/utils/shared_bg.py -> assets/ is at scoundrel/scoundrel/assets)
        bg_path = Path(__file__).resolve().parents[2] / "assets" / "backgrounds" / "ClassicBackground.png"
        if bg_path.exists():
            _shared_tile = pygame.image.load(str(bg_path))
            # If a display surface exists, convert the tile to the display
            # pixel format to accelerate blits. Use convert_alpha when the
            # image contains per-pixel alpha.
            try:
                if pygame.display.get_surface() is not None:
                    if _shared_tile.get_flags() & pygame.SRCALPHA:
                        try:
                            _shared_tile = _shared_tile.convert_alpha()
                        except Exception:
                            pass
                    else:
                        try:
                            _shared_tile = _shared_tile.convert()
                        except Exception:
                            pass
            except Exception:
                # If display queries fail, keep raw surface
                pass
        else:
            _shared_tile = None
    except Exception:
        _shared_tile = None

    # ensure a cache dict exists (shared)
    if _shared_scaled_cache is None:
        _shared_scaled_cache = {}
    return _shared_tile, _shared_scaled_cache
