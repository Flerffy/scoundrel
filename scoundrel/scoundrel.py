import pygame
from pathlib import Path
import importlib
import types
import sys


def _import_package_main():
    """Import the package's `main` module in a robust way.

    Create a lightweight package module entry in sys.modules with its __path__ set to the
    package directory, then use importlib.import_module to load `scoundrel.main`. This
    keeps the import machinery happy and allows relative imports inside the package.
    """
    base = Path(__file__).resolve().parent
    pkg_dir = base / "scoundrel"
    if not pkg_dir.exists():
        raise FileNotFoundError(f"Package directory not found: {pkg_dir}")

    pkg_name = "scoundrel"
    created_pkg = False
    pkg_mod = sys.modules.get(pkg_name)
    if not pkg_mod or not getattr(pkg_mod, "__path__", None) or str(pkg_dir) not in pkg_mod.__path__:
        pkg_mod = types.ModuleType(pkg_name)
        pkg_mod.__path__ = [str(pkg_dir)]
        sys.modules[pkg_name] = pkg_mod
        created_pkg = True

    try:
        module = importlib.import_module(f"{pkg_name}.main")
    except Exception:
        # If import fails, and we created the temporary package entry, remove it to avoid
        # leaving a broken module in sys.modules.
        if created_pkg and pkg_name in sys.modules:
            del sys.modules[pkg_name]
        raise
    return module


def main():
    pygame.init()
    pygame.display.set_caption("Scoundrel")

    # import and run the package main (avoids name collisions)
    pkg_main = _import_package_main()
    if hasattr(pkg_main, "main"):
        pkg_main.main()

    pygame.quit()


if __name__ == "__main__":
    main()