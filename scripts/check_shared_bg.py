import sys, traceback
# Ensure both the repository root and the inner package directory are importable
sys.path.insert(0, r'C:\Users\Erik\scoundrel')
sys.path.insert(0, r'C:\Users\Erik\scoundrel\scoundrel')
import pygame
print('Python', sys.version)
try:
    pygame.display.init()
except Exception as e:
    print('pygame display init failed', e)

try:
    from scoundrel.utils.shared_bg import get_shared_bg_tile
    tile, cache = get_shared_bg_tile()
    print('tile is None?', tile is None)
    print('cache is None?', cache is None)
    if tile is not None:
        try:
            print('tile size=', tile.get_size())
        except Exception as e:
            print('tile.get_size failed', e)
    print('cache keys:', list(cache.keys()))
except Exception:
    traceback.print_exc()
