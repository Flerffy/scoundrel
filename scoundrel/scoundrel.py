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

    # First try the straightforward import. In a frozen/bundled executable
    # the package modules are embedded and importlib.import_module should work
    # directly. If that fails (e.g. during local development when package is
    # not on sys.path), fall back to locating a filesystem package directory
    # and creating a temporary package entry in sys.modules.
    pkg_name = "scoundrel"
    # If the current running module is named 'scoundrel' (the launcher), it
    # may be present in sys.modules as a plain module (without __path__).
    # Temporarily remove it so importlib can load the real package from the
    # bundled archive; if the import fails we'll restore the launcher entry.
    launcher_mod = sys.modules.get(pkg_name)
    if launcher_mod and not getattr(launcher_mod, "__path__", None):
        del sys.modules[pkg_name]
        try:
            return importlib.import_module(f"{pkg_name}.main")
        except Exception:
            # restore and continue to the filesystem fallback
            sys.modules[pkg_name] = launcher_mod

    # Try a direct import first (works in many cases, including when the
    # package is already importable).
    try:
        return importlib.import_module(f"{pkg_name}.main")
    except Exception:
        # fall back to filesystem-based recovery below
        pass

    # Candidate locations to search for a 'scoundrel' package directory.
    candidate_paths = []
    candidate_paths.append(base / pkg_name)
    # parent/_internal/scoundrel (PyInstaller one-dir layout)
    candidate_paths.append(base / "_internal" / pkg_name)
    # script location (when run unpacked)
    try:
        script_parent = Path(sys.argv[0]).resolve().parent
        candidate_paths.append(script_parent / pkg_name)
        candidate_paths.append(script_parent / "_internal" / pkg_name)
    except Exception:
        pass
    # also check executable parent (just in case)
    try:
        exe_parent = Path(sys.executable).resolve().parent
        candidate_paths.append(exe_parent / pkg_name)
        candidate_paths.append(exe_parent / "_internal" / pkg_name)
    except Exception:
        pass

    pkg_dir = None
    for candidate in candidate_paths:
        if candidate.exists() and ((candidate / "__init__.py").exists() or (candidate / "main.py").exists()):
            pkg_dir = candidate
            break

    if pkg_dir is None:
        raise FileNotFoundError(f"Package directory not found while searching common locations (from {base})")

    # Create a package module entry and set its __path__ so importlib can
    # import submodules like 'scoundrel.main' from the located directory.
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
        # cleanup if we created the temporary package entry
        if created_pkg and pkg_name in sys.modules:
            del sys.modules[pkg_name]
        raise
    return module

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