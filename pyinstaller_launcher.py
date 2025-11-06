"""Launcher with extra startup diagnostics and robust static imports.

This file performs static imports that PyInstaller can detect and emits
console prints at startup so we can see exactly what the frozen app loads.
"""
import sys
import traceback

print("[launcher] starting", flush=True)

# Try a few static import paths so the frozen analysis includes the package
# code. These static imports are important for PyInstaller to collect files.
_pkg_main = None
try:
    # Primary (expected) layout: scoundrel/scoundrel/main.py
    from scoundrel.scoundrel import main as _pkg_main
    print("[launcher] imported scoundrel.scoundrel.main", flush=True)
except Exception:
    try:
        # alternative layout: scoundrel/main.py (if package flattened)
        from scoundrel import main as _pkg_main
        print("[launcher] imported scoundrel.main", flush=True)
    except Exception:
        try:
            # fallback: import package and look for attribute 'main'
            import scoundrel as _pkg_pkg
            _pkg_main = getattr(_pkg_pkg, "main", None)
            if _pkg_main is not None:
                print("[launcher] found main on scoundrel package", flush=True)
        except Exception:
            print("[launcher] failed to statically import package; will attempt dynamic imports", flush=True)


def _run():
    try:
        if _pkg_main is None:
            # Try to dynamically import common module names as a last resort.
            try:
                import importlib
                _pkg_main_mod = None
                for name in ("scoundrel.scoundrel.main", "scoundrel.main", "main"):
                    try:
                        _pkg_main_mod = importlib.import_module(name)
                        print(f"[launcher] dynamically imported {name}", flush=True)
                        break
                    except Exception:
                        continue
                if _pkg_main_mod is not None and hasattr(_pkg_main_mod, "main"):
                    _pkg_main_obj = getattr(_pkg_main_mod, "main")
                    if callable(_pkg_main_obj):
                        _pkg_main_obj()
                        return
            except Exception:
                print("[launcher] dynamic import attempt failed", flush=True)
                traceback.print_exc()
                return

        # If we have a statically imported module or object, call it.
        if hasattr(_pkg_main, "main") and callable(getattr(_pkg_main, "main")):
            print("[launcher] calling _pkg_main.main()", flush=True)
            getattr(_pkg_main, "main")()
        elif callable(_pkg_main):
            print("[launcher] calling _pkg_main()", flush=True)
            _pkg_main()
        else:
            print("[launcher] no callable main found; exiting", flush=True)
    except Exception:
        print("[launcher] exception while running main:", flush=True)
        traceback.print_exc()


if __name__ == "__main__":
    _run()