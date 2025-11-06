"""Stable static launcher for PyInstaller builds.

This does a straight static import of the package module so relative imports
inside the package work, and PyInstaller will detect the dependency during
analysis.
"""
from scoundrel.scoundrel import main as _pkg_main

if __name__ == '__main__':
    if hasattr(_pkg_main, 'main'):
        _pkg_main.main()
