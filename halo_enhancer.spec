# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller --noconfirm halo_enhancer.spec
# Produces a single windowed executable at dist/halo_enhancer.exe with
# halo.json bundled alongside it.

block_cipher = None

a = Analysis(
    ['halo_enhancer.py'],
    pathex=[],
    binaries=[],
    datas=[('halo.json', '.')],   # bundle the data file next to the app
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='halo_enhancer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='app.ico',       # uncomment and add app.ico for a custom icon
)
