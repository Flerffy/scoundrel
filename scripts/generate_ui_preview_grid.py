"""Generate a clearer grid preview for a UI atlas.
Reads `scoundrel/assets/ui/BlackGreyUISheet.json` and `BlackGreyUISheet.png`
and writes `BlackGreyUISheet_preview_grid.png` where each detected tile
is shown as a thumbnail with its tile name and metadata below. This
avoids overlapping labels in the original preview.

Run from workspace root.
"""
from pathlib import Path
import json
import math
import pygame

ROOT = Path('scoundrel')
ASSET_DIR = ROOT / 'assets' / 'ui'
IMG = ASSET_DIR / 'BlackGreyUISheet.png'
DESC = ASSET_DIR / 'BlackGreyUISheet.json'
OUT = ASSET_DIR / 'BlackGreyUISheet_preview_grid.png'

# grid params
COLS = 6
THUMB_SCALE = 3  # scale each tile up this factor for clarity
PADDING = 8
LABEL_HEIGHT = 18
BG_COLOR = (20, 20, 20)
BORDER_COLOR = (200, 60, 60)
TEXT_COLOR = (230, 230, 230)


def ensure_pygame_display():
    pygame.init()
    # ensure display initialized and a tiny mode set so surfaces support convert_alpha
    try:
        if not pygame.display.get_init():
            pygame.display.init()
    except Exception:
        pass
    try:
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
    except Exception:
        pass


def build_preview():
    if not IMG.exists() or not DESC.exists():
        raise FileNotFoundError('Missing image or descriptor')
    ensure_pygame_display()
    img = pygame.image.load(str(IMG)).convert_alpha()
    desc = json.loads(DESC.read_text())
    tiles = desc.get('tiles', {})
    items = list(tiles.items())
    count = len(items)
    rows = math.ceil(count / COLS)

    # compute thumbnail sizes and final canvas size
    thumbs = []
    max_tw = 0
    max_th = 0
    for name, info in items:
        w = info['w']
        h = info['h']
        max_tw = max(max_tw, w)
        max_th = max(max_th, h)
    thumb_w = max_tw * THUMB_SCALE
    thumb_h = max_th * THUMB_SCALE

    canvas_w = COLS * (thumb_w + PADDING) + PADDING
    canvas_h = rows * (thumb_h + LABEL_HEIGHT + PADDING) + PADDING

    canvas = pygame.Surface((canvas_w, canvas_h))
    canvas.fill(BG_COLOR)

    font = pygame.font.Font(None, 16)

    for idx, (name, info) in enumerate(items):
        col = idx % COLS
        row = idx // COLS
        rx = PADDING + col * (thumb_w + PADDING)
        ry = PADDING + row * (thumb_h + LABEL_HEIGHT + PADDING)
        # extract tile
        rect = pygame.Rect(info['x'], info['y'], info['w'], info['h'])
        sub = img.subsurface(rect).copy()
        # scale up
        sw = max(1, int(info['w'] * THUMB_SCALE))
        sh = max(1, int(info['h'] * THUMB_SCALE))
        sub_s = pygame.transform.scale(sub, (sw, sh))
        # center inside thumb box
        tx = rx + (thumb_w - sw) // 2
        ty = ry + (thumb_h - sh) // 2
        canvas.blit(sub_s, (tx, ty))
        # border
        pygame.draw.rect(canvas, BORDER_COLOR, (rx, ry, thumb_w, thumb_h), 1)
        # label
        meta = info.get('type', '')
        label = f"{name} {meta} {info.get('w')}x{info.get('h')}"
        txt = font.render(label, True, TEXT_COLOR)
        canvas.blit(txt, (rx, ry + thumb_h + 2))

    try:
        pygame.image.save(canvas, str(OUT))
        print('Wrote', OUT)
    except Exception as e:
        print('Failed to save preview:', e)


if __name__ == '__main__':
    build_preview()
