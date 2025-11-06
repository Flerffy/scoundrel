import importlib.util, pathlib
p = pathlib.Path('scoundrel/scoundrel/scoundrel/utils/shared_bg.py').resolve()
spec = importlib.util.spec_from_file_location('shared_bg_test', str(p))
if spec is None:
    raise ImportError(f"Cannot create module spec for {p}")
mod = importlib.util.module_from_spec(spec)
loader = spec.loader
if loader is None:
    raise ImportError(f"No loader available for module spec created from {p}")
loader.exec_module(mod)
print('module loaded', mod.__name__)
try:
    tile, cache = mod.get_shared_bg_tile()
    print('tile is None?', tile is None)
    if tile is not None:
        print('tile size:', tile.get_size())
    print('cache is dict?', isinstance(cache, dict))
except Exception as e:
    print('error calling get_shared_bg_tile:', e)