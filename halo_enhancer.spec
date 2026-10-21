# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller --noconfirm halo_enhancer.spec
# Produces a single windowed executable at dist/halo_enhancer.exe with
# halo.json bundled alongside it.

block_cipher = None

a = Analysis(
    ['halo_enhancer.py'],
    pathex=['sprint_toolkit'],
    binaries=[],
    # the ports' catalog and the AI firing profiles are read from next to weapon_ports /
    # h1_enemy_weapons / h2_enemy_weapons -- in a onefile build that folder is _MEIPASS
    datas=[('halo.json', '.'), ('port_glyphs.json', '.'), ('port_sounds', 'port_sounds'),
           ('weapon_ports_catalog.json', '.'), ('ai_firing_profiles.json', '.')],   # bundle the data files next to the app
    hiddenimports=['h3_font_repack', 'port_glyphs', 'port_sounds', 'port_volume',
                   'h1_fsb', 'numpy',
                   # imported inside functions after a sys.path insert (halo3_reload)
                   'h3_move_speed', 'h3_anim_lengthen', 'h3_raw_residency', 'h3_zone_pools'],
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
