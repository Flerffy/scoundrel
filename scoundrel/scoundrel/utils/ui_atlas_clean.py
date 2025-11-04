import json
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Union, Any

import pygame


class UIAtlas:
    """Load an image atlas and (optionally) a JSON descriptor.

    Also provides an automatic-slicing helper that scans non-transparent
    regions and returns bounding boxes.
    """

    def __init__(self, image_path: Union[str, Path], descriptor: Optional[Union[str, Path]] = None):
        # accept str or Path for convenience
        self.image_path = Path(image_path)
        self.descriptor_path = Path(descriptor) if descriptor is not None else None
        self.image = None  # loaded Surface
        # tiles map: tile_id -> dict with mixed value types (ints, strings, lists)
        self.tiles: Dict[str, Dict[str, Any]] = {}

    def load_image(self):
        # Ensure pygame and a video mode are available for convert_alpha()
        pygame.init()
        if not pygame.display.get_init():
            try:
                pygame.display.init()
            except Exception:
                pass
        # Some SDL builds require a display mode before convert_alpha; set a tiny dummy mode
        try:
            if pygame.display.get_surface() is None:
                pygame.display.set_mode((1, 1))
        except Exception:
            # best-effort; if this fails, image loading may still work without convert_alpha
            pass
        if not self.image_path.exists():
            raise FileNotFoundError(f"Atlas image not found: {self.image_path}")
        self.image = pygame.image.load(str(self.image_path)).convert_alpha()
        return self.image

    def save_descriptor(self, out_path: Path):
        data = {"image": self.image_path.name, "tiles": self.tiles}
        # ensure parent directory exists
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def load_descriptor(self, desc_path: Path):
        # accept Path or str
        p = Path(desc_path)
        data = json.loads(p.read_text())
        tiles = data.get("tiles", {})
        self.tiles = tiles
        self.descriptor_path = desc_path

    # --- Auto-slice helpers ---
    def autoslice(self, min_area: int = 40) -> List[Tuple[int, int, int, int]]:
        """Detect non-transparent connected regions and return list of bboxes.

        This performs a flood-fill over non-transparent pixels. It's robust
        for most UI sprite sheets where sprites are separated by transparent
        gutters.
        """
        surf = self.image if self.image is not None else self.load_image()
        w, h = surf.get_size()
        visited = [[False] * w for _ in range(h)]
        bboxes: List[Tuple[int, int, int, int]] = []

        def alpha_at(x, y):
            try:
                return surf.get_at((x, y))[3]
            except Exception:
                return 0

        for y in range(h):
            for x in range(w):
                if visited[y][x]:
                    continue
                if alpha_at(x, y) == 0:
                    visited[y][x] = True
                    continue
                minx = x
                maxx = x
                miny = y
                maxy = y
                stack = [(x, y)]
                visited[y][x] = True
                while stack:
                    sx, sy = stack.pop()
                    if sx < minx:
                        minx = sx
                    if sx > maxx:
                        maxx = sx
                    if sy < miny:
                        miny = sy
                    if sy > maxy:
                        maxy = sy
                    for nx, ny in ((sx - 1, sy), (sx + 1, sy), (sx, sy - 1), (sx, sy + 1)):
                        if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                            if alpha_at(nx, ny) > 0:
                                visited[ny][nx] = True
                                stack.append((nx, ny))
                            else:
                                visited[ny][nx] = True
                area = (maxx - minx + 1) * (maxy - miny + 1)
                if area >= min_area:
                    bboxes.append((minx, miny, maxx - minx + 1, maxy - miny + 1))
        return bboxes

    def analyze_and_build_descriptor(self, out_json: Path, out_preview: Path | None = None):
        surf = self.load_image()
        w, h = surf.get_size()
        bboxes = self.autoslice(min_area=30)
        bboxes.sort(key=lambda r: (r[1], r[0]))
        tiles = {}
        for i, (x, y, tw, th) in enumerate(bboxes):
            name = f"tile_{i:03d}"
            cx = x + tw // 2
            cy = y + th // 2
            try:
                center_alpha = surf.get_at((cx, cy))[3]
            except Exception:
                center_alpha = 255
            # tile dict may contain ints, strings or lists (ninepatch insets)
            tile: Dict[str, Any] = {"x": int(x), "y": int(y), "w": int(tw), "h": int(th)}
            if center_alpha < 16:
                tile["type"] = "ninepatch"
                L = max(1, tw // 4)
                T = max(1, th // 4)
                R = max(1, tw // 4)
                B = max(1, th // 4)
                tile["ninepatch"] = [L, T, R, B]
            else:
                if tw > th * 2:
                    tile["type"] = "threeslice"
                else:
                    tile["type"] = "icon"
            tiles[name] = tile
        self.tiles = tiles
        self.save_descriptor(out_json)

        if out_preview is not None:
            try:
                out_preview_path = Path(out_preview)
                out_preview_path.parent.mkdir(parents=True, exist_ok=True)
                pv = pygame.Surface((w, h + 120), pygame.SRCALPHA)
                pv.blit(surf, (0, 0))
                font = pygame.font.Font(None, 18)
                for name, tile in tiles.items():
                    rx, ry, rw, rh = tile["x"], tile["y"], tile["w"], tile["h"]
                    pygame.draw.rect(pv, (255, 0, 0), (rx, ry, rw, rh), 1)
                    txt = font.render(name, False, (255, 255, 255))
                    pv.blit(txt, (rx, ry - 18))
                pygame.image.save(pv, str(out_preview_path))
            except Exception:
                # preview generation is best-effort
                pass
        return {"image": self.image_path.name, "tiles": tiles}
