r"""A SIZE test copy of a Halo 1 level: the map grown past Custom Edition's old 384 MiB cap
the way the ports grow it -- by `tool` building extra resident data in -- to settle whether
MCC loads a classic map that large (H1_PORT_PLAN.md 0.1: MCC's limit is 2 GiB by c20, but
no map over 384 MiB had been booted; a10/d40 reach it around wave B's 7th port).

  KIT (temporary; the scenario is copied first and ALWAYS put back):
    * `test\size_pad\bitmaps\pad_<n>`: N patterned 2048x2048 bitmaps in 32-bit colour
      with mipmaps (~21.3 MiB each, stored raw) -- made once, kept in the kit;
    * `test\size_pad\size_pad`: a copy of the Assault Rifle whose HUD
      (`test\size_pad\size_pad` weapon_hud_interface) names every pad bitmap as a static
      element -- nothing else references them;
    * that weapon in the level's weapons palette + one resident-only placement (the SAW's,
      `not placed automatically`): built in, never spawned, never drawn.
  Built with h1_rebuild_all --no-ship, copied to HCEEK\maps\size_test\<level>.map, kit
  restored, normal level rebuilt (HCEEK\maps\<level>.map byte-identical again).
  The copy is then reported: file size, where the pad bitmaps landed, and which real data
  (sounds, model vertices, tag data) now lies beyond 384 MiB.
  --stage: h1_port_test_map.stage (live map backed up to E:\HaloBackups\h1_port_test,
  `python h1_port_test_map.py --restore <level>` puts it back).

    python h1_size_test_map.py --level a10 --pads 5 [--stage]
"""
import argparse
import copy
import os
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import port_env  # noqa: E402,F401
import paths  # noqa: E402
import h1_enemy_test_map as E  # noqa: E402

HCEEK = paths.HCEEK
TAGS = os.path.join(HCEEK, 'tags')
PAD = r'test\size_pad'
WEAPON = PAD + r'\size_pad'
AR = r'weapons\assault rifle\assault rifle'
SAW = r'weapons\saw\saw'
SIZE = 2048
CAP = 384 * 1024 * 1024


def tool(*args):
    r = subprocess.run([paths.TOOL_EXE] + list(args), cwd=HCEEK, capture_output=True,
                       text=True, errors='replace')
    return r.stdout + r.stderr


def make_bitmaps(n):
    """N pattern TIFFs -> bitmap tags, then 32-bit colour + mipmaps and re-imported."""
    from reclaimer.hek.defs.bitm import bitm_def
    data = os.path.join(HCEEK, 'data', PAD, 'bitmaps')
    os.makedirs(data, exist_ok=True)
    names = ['pad_%d' % i for i in range(n)]
    rng = np.random.default_rng(384)
    fresh = []
    for nm in names:
        if os.path.exists(os.path.join(TAGS, PAD, 'bitmaps', nm + '.bitmap')):
            continue
        # a compressible pattern: tool keeps the SOURCE plate compressed in the tag and
        # refuses noise ('failed to compress color plate'); 32-bit pixels are stored raw
        # in the map whatever they show, so a pattern pads exactly as much
        y, x = np.mgrid[0:SIZE, 0:SIZE]
        k = int(rng.integers(1, 255))
        a = np.stack([(x // 8 + k) % 256, (y // 8) % 256, ((x + y) // 16) % 256,
                      np.full_like(x, 255)], axis=-1).astype(np.uint8)
        Image.fromarray(a, 'RGBA').save(os.path.join(data, nm + '.tif'))
        fresh.append(nm)
    if not fresh:
        return names
    tool('bitmaps', PAD + '\\bitmaps')                       # first import (DXT)
    for nm in fresh:
        p = os.path.join(TAGS, PAD, 'bitmaps', nm + '.bitmap')
        t = bitm_def.build(filepath=p)
        t.data.tagdata.format.set_to('color_32bit')
        t.data.tagdata.mipmap_levels = 0                     # all of them
        t.serialize(temp=False, backup=False)
    tool('bitmaps', PAD + '\\bitmaps')                       # re-import keeps the format
    for nm in names:
        t = bitm_def.build(filepath=os.path.join(TAGS, PAD, 'bitmaps', nm + '.bitmap'))
        d = t.data.tagdata
        print('   %s: %s, %d bytes of pixels' % (nm, d.format.enum_name,
                                                 len(d.processed_pixel_data.data)))
    return names


def make_weapon(names):
    from reclaimer.hek.defs.weap import weap_def
    from reclaimer.hek.defs.wphi import wphi_def
    h = wphi_def.build(filepath=os.path.join(TAGS, AR + '.weapon_hud_interface'))
    st = h.data.tagdata.static_elements.STEPTREE
    tmpl = copy.deepcopy(st[0])
    st[:] = []
    for nm in names:
        st.append(copy.deepcopy(tmpl))
        st[len(st) - 1].interface_bitmap.filepath = PAD + '\\bitmaps\\' + nm
    h.filepath = os.path.join(TAGS, WEAPON + '.weapon_hud_interface')
    os.makedirs(os.path.dirname(h.filepath), exist_ok=True)
    h.serialize(temp=False, backup=False)
    w = weap_def.build(filepath=os.path.join(TAGS, AR + '.weapon'))
    w.data.tagdata.weap_attrs.interface.hud_interface.filepath = WEAPON
    w.filepath = os.path.join(TAGS, WEAPON + '.weapon')
    w.serialize(temp=False, backup=False)


def edit_kit(level):
    from reclaimer.hek.defs.scnr import scnr_def
    sp = E.scenario_path(level)
    t = scnr_def.build(filepath=sp)
    d = t.data.tagdata
    pal = d.weapons_palette.STEPTREE
    names = [e.name.filepath.lower() for e in pal]
    pal.append()
    pal[-1].name.filepath = WEAPON
    idx = len(pal) - 1
    places = d.weapons.STEPTREE
    src = [x for x in places if x.type == names.index(SAW) and x.not_placed.automatically]
    places.append(copy.deepcopy(src[0]))
    places[len(places) - 1].type = idx
    t.filepath = sp
    t.serialize(temp=False, backup=False)
    print('kit: %s palette #%d + resident-only placement (temporary)' % (WEAPON, idx))


def report(path, pads):
    import halo_patch
    m = halo_patch.open_map(path, 'Halo 1')
    size = os.path.getsize(path)
    print('\n%s: %.1f MiB (%s the 384 MiB cap by %.1f MiB)'
          % (path, size / 1048576.0, 'OVER' if size > CAP else 'under', abs(size - CAP) / 1048576.0))
    d = m.data
    # bitmap pixel data: each bitmap block's pixels offset (+0x18) and size (+0x1C), file offsets
    beyond, pad_at = 0, []
    for (cls, name), off in m.tags.items():
        if cls != 'bitm':
            continue
        n, ptr = struct.unpack_from('<II', d, off + 0x60)
        arr = (ptr - m.magic) & 0xFFFFFFFF
        for i in range(n):
            e = arr + i * 0x30
            po, ps = struct.unpack_from('<II', d, e + 0x18)
            if po + ps > CAP:
                beyond += 1
            if name.lower().startswith(PAD.lower()):
                pad_at.append((name.rsplit('\\', 1)[-1], po / 1048576.0))
    print('pad bitmaps at MiB: %s' % ', '.join('%s %.0f' % x for x in sorted(pad_at)))
    print('bitmap blocks whose pixels end past 384 MiB: %d' % beyond)
    tag_off = struct.unpack_from('<I', d, 0x10)[0]
    print('tag data starts at %.1f MiB (%s 384)' % (tag_off / 1048576.0,
                                                    'PAST' if tag_off > CAP else 'before'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--level', default='a10')
    ap.add_argument('--pads', type=int, default=5)
    ap.add_argument('--stage', action='store_true')
    a = ap.parse_args()
    print('pad bitmaps:')
    names = make_bitmaps(a.pads)
    make_weapon(names)
    sp = E.scenario_path(a.level)
    keep = sp + '.before_sizetest'
    shutil.copy2(sp, keep)
    try:
        edit_kit(a.level)
        E.build(a.level)
        out_dir = os.path.join(HCEEK, 'maps', 'size_test')
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, a.level + '.map')
        shutil.copy2(os.path.join(HCEEK, 'maps', a.level + '.map'), out)
    finally:
        shutil.copy2(keep, sp)
        os.remove(keep)
    print('kit scenario restored; rebuilding the normal %s' % a.level)
    E.build(a.level)
    report(out, names)
    if a.stage:
        import h1_port_test_map
        h1_port_test_map.stage(a.level, out, 'SIZE TEST %s (%d pad bitmaps)' % (a.level, a.pads))


if __name__ == '__main__':
    main()
