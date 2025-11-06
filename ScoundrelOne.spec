# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


a = Analysis(
    ['pyinstaller_launcher.py'],
    pathex=['.'],
    binaries=[],
    # Bundle the entire assets tree and package data directories so art,
    # audio, and fonts are available at runtime. The destination side
    # uses the same relative path so code can reference e.g. 'scoundrel/assets'.
    datas=[
        ('scoundrel/assets', 'scoundrel/assets'),
        ('scoundrel/data', 'scoundrel/data'),
        ('data', 'data'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ScoundrelOne',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
