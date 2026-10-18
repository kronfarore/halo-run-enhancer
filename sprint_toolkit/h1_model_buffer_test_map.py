r"""A MODEL-BUFFER test copy of a Halo 1 level: built past the 32 MiB model-buffer cap with a
PATCHED COPY of tool, to settle whether MCC itself copes with more model data (2026-10-18).

THE CAP IS TOOL'S (found 2026-10-18 by disassembly, HCEEK tool.exe): the cache build
(0x4079d0) takes `HeapAlloc(GetProcessHeap(), 0, 0x2000000)` -- a fixed 32 MiB scratch
buffer -- and "streaming model vertex and index buffers..." (0x407330) writes every model's
vertices (x68) and then every model's strip indices (x2) into it with NO bounds check: the
access violation of memory h1-model-buffer-32mib-cap. Both `push 0x2000000` immediates (VA
0x4079e8, 0x4079f6) -> 0x8000000 (128 MiB) in `HCEEK\tool_mb128.exe`; tool.exe is untouched.
Builds use the copy only through the environment override `H1_TOOL_EXE` (paths.py).

  KIT (temporary; the scenario is copied first and ALWAYS put back):
    * `test\mb_pad\pad_<n>`: N copies of the Warthog's gbxmodel (0.70 MiB of the buffer each)
      as scenery tags -- made once, kept in the kit;
    * those sceneries appended to the level's scenery palette and PLACED in a 4-wide grid in
      front of the first player start (visible: if their data were cut off they would draw
      wrong or not at all).
  tool writes ALL vertices first, then ALL indices: past ~33 MiB of vertices every model's
  index data lies beyond 32 MiB, so a game that reads only 32 MiB breaks EVERY model in the
  level -- the test cannot pass by accident. The report prints where the regions lie.
  Built with the patched tool (--no-ship), copied to HCEEK\maps\mb_test\<level>.map, kit
  restored, the normal level rebuilt with the normal tool.

    python h1_model_buffer_test_map.py --level b30 --pads 16 [--stage]
"""
import argparse
import copy
import hashlib
import math
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import port_env  # noqa: E402,F401
import paths  # noqa: E402
import h1_enemy_test_map as E  # noqa: E402
import h1_model_buffer as MB  # noqa: E402

HCEEK = paths.HCEEK
TAGS = os.path.join(HCEEK, 'tags')
PAD = r'test\mb_pad'
SRC_MODEL = r'vehicles\warthog\warthog'
SRC_SCENERY = r'scenery\trees\tree_leafy\tree_leafy'
PATCHED = os.path.join(HCEEK, 'tool_mb128.exe')
IMM_OFFSETS = (0x4079e8, 0x4079f6)          # VAs of the two `push 0x2000000` immediates
OLD, NEW = 0x2000000, 0x8000000


def patched_tool():
    import pefile
    import struct
    src = paths.TOOL_EXE_STOCK
    pe = pefile.PE(src, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    b = bytearray(open(src, 'rb').read())
    for va in IMM_OFFSETS:
        o = pe.get_offset_from_rva(va - base)
        if b[o - 1] != 0x68 or struct.unpack_from('<I', b, o)[0] != OLD:
            raise SystemExit('tool.exe is not the build this patch was read from (VA %#x)' % va)
        struct.pack_into('<I', b, o, NEW)
    if not os.path.exists(PATCHED) or open(PATCHED, 'rb').read() != bytes(b):
        open(PATCHED, 'wb').write(b)
    print('patched tool: %s (model buffer %d MiB; tool.exe sha1 %s untouched)'
          % (PATCHED, NEW >> 20, hashlib.sha1(open(src, 'rb').read()).hexdigest()[:12]))


def make_pads(n):
    from reclaimer.hek.defs.scen import scen_def
    os.makedirs(os.path.join(TAGS, PAD), exist_ok=True)
    names = []
    for i in range(n):
        nm = PAD + '\\pad_%02d' % i
        g = os.path.join(TAGS, nm + '.gbxmodel')
        if not os.path.exists(g):
            shutil.copy2(os.path.join(TAGS, SRC_MODEL + '.gbxmodel'), g)
        s = scen_def.build(filepath=os.path.join(TAGS, SRC_SCENERY + '.scenery'))
        s.data.tagdata.obje_attrs.model.filepath = nm
        s.data.tagdata.obje_attrs.collision_model.filepath = ''   # the tree's nodes are not the Warthog's
        s.filepath = os.path.join(TAGS, nm + '.scenery')
        s.serialize(temp=False, backup=False)
        names.append(nm)
    return names


def edit_kit(level, names):
    from reclaimer.hek.defs.scnr import scnr_def
    sp = E.scenario_path(level)
    t = scnr_def.build(filepath=sp)
    d = t.data.tagdata
    pal, places = d.sceneries_palette.STEPTREE, d.sceneries.STEPTREE
    start = d.player_starting_locations.STEPTREE[0]
    fx, fy = math.cos(start.facing), math.sin(start.facing)      # forward
    rx, ry = fy, -fx                                             # right
    tmpl = [x for x in places if not x.not_placed.data][0]
    for i, nm in enumerate(names):
        pal.append()
        pal[-1].name.filepath = nm
        places.append(copy.deepcopy(tmpl))
        p = places[len(places) - 1]
        p.type = len(pal) - 1
        p.name = -1
        p.desired_permutation = 0
        row, col = divmod(i, 4)
        ahead, side = 8.0 + 5.0 * row, 4.0 * (col - 1.5)
        p.position.x = start.position.x + fx * ahead + rx * side
        p.position.y = start.position.y + fy * ahead + ry * side
        p.position.z = start.position.z
        p.rotation.y, p.rotation.p, p.rotation.r = start.facing, 0.0, 0.0
    t.filepath = sp
    t.serialize(temp=False, backup=False)
    print('kit: %d pad sceneries in %s palette + placed in front of the player start (temporary)'
          % (len(names), level))


def report(path):
    import halo_patch
    m = halo_patch.open_map(path, 'Halo 1')
    rows = []
    for name, _b in m.find_tags('mod2', '*'):
        c = MB.cost(name)
        if c:
            rows.append((name, c[0], c[1]))
    tv, ti = sum(r[1] for r in rows), sum(r[2] for r in rows)
    vb, ib = tv * 68, ti * 2
    pads = [r for r in rows if r[0].lower().startswith(PAD.lower())]
    print('\n%s: %.1f MiB file; MODEL DATA %.2f MiB (cap was 32): vertices 0-%.2f MiB, '
          'indices %.2f-%.2f MiB' % (path, os.path.getsize(path) / 2 ** 20, (vb + ib) / 2 ** 20,
                                     vb / 2 ** 20, vb / 2 ** 20, (vb + ib) / 2 ** 20))
    print('%d models, %d of them pads; past 32 MiB: %s' % (
        len(rows), len(pads), 'ALL index data + the vertices of the models at the end'
        if vb < MB.CAP < vb + ib else ('the vertices past %.2f MiB and ALL index data' % 32
                                       if vb > MB.CAP else 'nothing')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--level', default='b30')
    ap.add_argument('--pads', type=int, default=16)
    ap.add_argument('--stage', action='store_true')
    a = ap.parse_args()
    patched_tool()
    names = make_pads(a.pads)
    sp = E.scenario_path(a.level)
    keep = sp + '.before_mbtest'
    shutil.copy2(sp, keep)
    os.environ['H1_TOOL_EXE'] = PATCHED
    try:
        edit_kit(a.level, names)
        E.build(a.level)
        out_dir = os.path.join(HCEEK, 'maps', 'mb_test')
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, a.level + '.map')
        shutil.copy2(os.path.join(HCEEK, 'maps', a.level + '.map'), out)
    finally:
        del os.environ['H1_TOOL_EXE']
        shutil.copy2(keep, sp)
        os.remove(keep)
    print('kit scenario restored; rebuilding the normal %s with the normal tool' % a.level)
    E.build(a.level)
    report(out)
    if a.stage:
        import h1_port_test_map
        h1_port_test_map.stage(a.level, out, 'MODEL BUFFER TEST %s (%d pads)' % (a.level, a.pads))


if __name__ == '__main__':
    import kit_lock   # the shared-kit lock: two port sessions in parallel (H1_PORT_PLAN.md)
    with kit_lock.script('h1_model_buffer_test_map'):
        main()
