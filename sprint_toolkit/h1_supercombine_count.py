r"""Halo 1: the supercombine needle count PER PROJECTILE instead of the engine's 7.

Halo 2 on carry `Super Detonation Projectile Count` in the projectile tag; Halo 1 hardcodes 7
(the Needle Rifle port wants Reach's 3, the stock needler keeps 7). halo1.dll compares the
number of same-tag needles stuck in one object against the constant 6 (= the 6 OTHERS of 7)
at four places, all for projectiles whose proj flags carry bit 3 `has super combining
explosion` (proj +0x17C):
  ATTACH_A  +0xBC72C5  cmp r8w,6 / jge  -> bts [new proj +0x1F8], 7   (rdi = proj tag)
  ATTACH_B  +0xBC8442  cmp r10w,6 / jge -> bts [proj +0x1F8], 7       (r13 = proj tag)
  DET_COUNT +0xBC8EC4  cmp r8w,6 / jle skip  -- the detonation: >= 7 same-tag needles
                       in the parent -> super_detonation (proj +0x198 = its effe index)
  DET_SPLIT +0xBC8F4C  cmp r8w,6 / jg   -- the same routine, the per-sibling loop
                       (rsi = proj tag at both detonation sites)
(rva at image base 0x180000000; MCC halo1.dll of 2026-06-22.) Each `cmp ...,6` (5 bytes)
becomes a call to a 20/21-byte cave that compares against (count - 1) read from the
projectile's OWN tag:

    proj +0x1F2  int16  'Super Detonation Projectile Count'  (0 or less = the engine's 7)

+0x1F2 is the HEK pad(2) after `detonation noise` (Assembly: hidden int16 'Unknown'); zero in
all 772 proj tags of the 29 stock/built Halo 1 maps (2026-10-10), read by nothing in
halo1.dll. With the patch on and every count at 0 the game is exactly stock.
The count is total needles, like Halo 2+'s field: 3 = the third stuck needle combines.

Caves: .text has no section slack left (overheat + melee caves), so these sit in int3
padding between functions: 21-byte runs after a `ret`, outside every .pdata range and
relocation, unreferenced. eax is dead at all four sites (overwritten before any read on
every path), so the caves use it without touching the stack:
    movsx eax, word [T+0x1F2] ; dec eax ; jns +4 ; mov ax,6 ; cmp R, ax ; ret

Same LIVE / FILE handling as h1_melee_blocks_fire.py, copied (verified sites, caves first,
rename swap while MCC runs, .prepatch.bak). In co-op BOTH machines need it.

    python sprint_toolkit/h1_supercombine_count.py --show
    python sprint_toolkit/h1_supercombine_count.py --on           # live + file
    python sprint_toolkit/h1_supercombine_count.py --on --live    # the running MCC only
    python sprint_toolkit/h1_supercombine_count.py --off          # back to stock (--restore)
TEST helpers (the count is TAG data, read live from the loaded map):
    python sprint_toolkit/h1_supercombine_count.py --count                   # list live
    python sprint_toolkit/h1_supercombine_count.py --count "weapons\needler\needle" 3
    python sprint_toolkit/h1_supercombine_count.py --map <file.map> --count <proj> 3
"""
import argparse
import os
import shutil
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402
from h1_melee_blocks_fire import _live  # noqa: E402
from h1_overheat_unzoom import DLL, _classify, _cleanup_inuse, _file_reader, _write_file  # noqa: E402

H = bytes.fromhex
NAME = 'Supercombine needle count per projectile'
FIELD = 'Super Detonation Projectile Count'
FIELD_OFFSET = 0x1F2          # proj tag, int16; 0 = the engine's 7
ENGINE_COUNT = 7


def _rel(next_ip, target):
    return struct.pack('<i', target - next_ip)


def _cave(tag_load, cmp_reg):
    return (tag_load                     # movsx eax, word [T+0x1F2]
            + H('ffc8')                  # dec eax                 count - 1
            + H('7904')                  # jns +4                  count >= 1: keep it
            + H('66b80600')              # mov ax, 6               0 / negative = engine 7
            + cmp_reg                    # cmp r8w|r10w, ax        (the replaced compare)
            + H('c3'))


CAVE_RDI_R8 = 0x139561B       # int3 padding (21 bytes) after +0x1395600's ret
CAVE_R13_R10 = 0x139576B      # int3 padding (21 bytes) after a ret
CAVE_RSI_R8 = 0x1397BAB       # int3 padding (21 bytes) after a ret
CODE_RDI_R8 = _cave(H('0fbf87f2010000'), H('664139c0'))
CODE_R13_R10 = _cave(H('410fbf85f2010000'), H('664139c2'))
CODE_RSI_R8 = _cave(H('0fbf86f2010000'), H('664139c0'))
assert max(map(len, (CODE_RDI_R8, CODE_R13_R10, CODE_RSI_R8))) <= 21


def _call(site, cave):
    return H('e8') + _rel(site + 5, cave)


# (rva, context before, stock, patched, context after) -- in "on" order: caves first
SITES = [
    (CAVE_RDI_R8, H('5fc3'), b'\xcc' * len(CODE_RDI_R8), CODE_RDI_R8, b''),
    (CAVE_R13_R10, H('5ec3'), b'\xcc' * len(CODE_R13_R10), CODE_R13_R10, b''),
    (CAVE_RSI_R8, H('5fc3'), b'\xcc' * len(CODE_RSI_R8), CODE_RSI_R8, b''),
    (0xBC72C5, H('c0448938'), H('664183f806'), _call(0xBC72C5, CAVE_RDI_R8), H('7d0d8b81')),
    (0xBC8442, H('4183cbff'), H('664183fa06'), _call(0xBC8442, CAVE_R13_R10), H('7d118b81')),
    (0xBC8EC4, H('8e010000'), H('664183f806'), _call(0xBC8EC4, CAVE_RSI_R8), H('0f8e8301')),
    (0xBC8F4C, H('4c0f44c8'), H('664183f806'), _call(0xBC8F4C, CAVE_RSI_R8), H('7f790f57')),
]


def _writes(state, want):
    if want and state in ('off', 'partial'):
        return [(r, pt) for r, _p, _st, pt, _po in SITES]
    if not want and state in ('on', 'partial'):
        return [(r, st) for r, _p, st, _pt, _po in reversed(SITES)]
    return []


def file_state(path=DLL):
    return _classify(_file_reader(path), SITES) if os.path.exists(path) else 'missing'


def live_state(h, base):
    return _classify(lambda rva, n: dp.read(h, base + rva, n), SITES)


def live_set(h, base, want):
    state = live_state(h, base)
    if state == 'unknown':
        return False, ('the running halo1.dll does not hold the expected bytes -- this MCC '
                       'build differs, refusing to write')
    for rva, blob in _writes(state, want):
        ok, err = dp.write(h, base + rva, blob)
        if not ok:
            return False, '+0x%X: %s' % (rva, err)
    return True, None


def file_set(want, path=DLL):
    """(ok, message). In place, or the swap by rename while MCC holds the dll."""
    _cleanup_inuse(path)
    state = file_state(path)
    if state == 'missing':
        return False, '%s not found' % path
    if state == 'unknown':
        return False, ('halo1.dll does not hold the expected bytes -- this MCC build '
                       'differs, refusing to write')
    writes = _writes(state, want)
    if not writes:
        return True, 'already as wanted'
    bak = path + '.prepatch.bak'
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
    try:
        _write_file(path, writes)
        return True, 'written in place'
    except PermissionError:
        pass                                    # loaded by MCC: swap instead
    new = path + '.new'
    shutil.copyfile(path, new)
    _write_file(new, writes)
    if file_state(new) != ('on' if want else 'off'):
        os.remove(new)
        return False, 'the patched copy did not verify'
    held = '%s.inuse-%d' % (path, int(time.time()))
    try:
        os.rename(path, held)
    except OSError as e:
        os.remove(new)
        return False, 'MCC holds halo1.dll and it could not be renamed: %s' % e
    try:
        os.rename(new, path)
    except OSError as e:
        os.rename(held, path)
        return False, 'could not put the patched halo1.dll in place: %s' % e
    return True, 'swapped in while MCC runs (applies at its next start)'


def sync(on, path=DLL, quiet=True, live_only=False):
    """One call for the GUI (h1_overheat_unzoom.sync's shape): the patch on (or back to
    stock) in the running MCC AND in halo1.dll on disk. Result rows; never raises."""
    target = 'on' if on else 'off'
    row = {'tag': 'halo1.dll', 'effect': NAME}
    out = []

    def add(field, ok, old, msg):
        if quiet and ok and old == target:
            return
        out.append({**row, 'field': field, 'ok': ok, 'old': old,
                    'new': target if ok else None,
                    'reason': None if ok else msg, **({'note': msg} if ok else {})})

    def live(h, base):
        old = live_state(h, base)
        ok, err = live_set(h, base, on)
        add('running MCC', ok, old, err)
    try:
        # the running MCC only when acting on ITS dll (not on a --dll copy)
        r = (_live(live) if os.path.normcase(os.path.abspath(path)) == os.path.normcase(DLL)
             else None)
        if isinstance(r, tuple):
            add('running MCC', False, None, r[1])
    except Exception as e:                      # never fatal to a map patch
        add('running MCC', False, None, str(e))
    if not live_only:
        try:
            old = file_state(path)
            ok, msg = file_set(on, path)
            add('halo1.dll file', ok, old, msg)
        except Exception as e:
            add('halo1.dll file', False, None, str(e))
    return out


# ---- the per-projectile count (tag data) --------------------------------------------
# halo1.dll's tag_get (+0xA9B648): tag array qword at +0x1C34FB0 (32-byte entries: class
# +0, id +0xC, name ptr +0x10, data ptr +0x14); a pointer p translates to
# p - [+0x2EA3410] + [+0x2D9CE10]. Tag data is loaded once per level -- reverts keep it.
TAG_ARRAY_PTR = 0x1C34FB0
VBASE_PTR = 0x2EA3410
DBASE_PTR = 0x2D9CE10


def _q(h, addr):
    b = dp.read(h, addr, 8)
    return struct.unpack('<Q', b)[0] if b and len(b) == 8 else None


def live_projectiles(h, base):
    """[(path, data address)] of every proj tag in the loaded map."""
    arr, vb, db = (_q(h, base + o) for o in (TAG_ARRAY_PTR, VBASE_PTR, DBASE_PTR))
    if not arr or vb is None or db is None:
        return []
    hdr = dp.read(h, db, 16)             # the tag-data region opens with the index header
    count = struct.unpack_from('<I', hdr, 0xC)[0] if hdr and len(hdr) == 16 else 0
    out = []
    for i in range(min(count, 0xFFFF)):
        e = dp.read(h, arr + 32 * i, 32)
        if not e or len(e) < 32:
            break
        if e[:4][::-1] != b'proj':
            continue
        name_p, data_p = struct.unpack_from('<ii', e, 0x10)
        raw = dp.read(h, name_p - vb + db, 256) or b''
        out.append((raw.split(b'\0')[0].decode('latin1'), data_p - vb + db))
    return out


# ---- the supercombine GATES on the stuck-in object (read-only probe) ----------------
# Detonation +0xBC8E7A..+0xBC8EBE, before the count: the parent (needle object +0xD8) must
# have word +0x70 == 0, and dword +0x1F8 == -1 OR the game-engine pointer [+0x2E9F820]
# non-null (set by game_engine_new +0xA9E3B0 from the variant's game type: null in
# campaign). Objects: table qword +0x1C42248, data qword +0x2D9CDF8, object = data + 0x34 +
# entry offset; header entry byte +3 = type (0 biped); +0xD4 first child, +0xD0 next.
OBJ_TABLE_PTR = 0x1C42248
OBJ_DATA_PTR = 0x2D9CDF8
GAME_ENGINE_PTR = 0x2E9F820
PLAYER_CONTROL_PTR = 0x2D8FE70   # +0x10 = the local player's unit handle


def probe_gates(h, base):
    """Rows for every live biped: (handle, is_player, w70, d1f8, stuck children by tag)."""
    table, data = _q(h, base + OBJ_TABLE_PTR), _q(h, base + OBJ_DATA_PTR)
    if not table or not data:
        return None, []
    engine = _q(h, base + GAME_ENGINE_PTR)
    pc = _q(h, base + PLAYER_CONTROL_PTR)
    player = struct.unpack('<I', dp.read(h, pc + 0x10, 4))[0] if pc else None
    hdr = dp.read(h, table, 0x38)
    maximum = struct.unpack_from('<h', hdr, 0x20)[0]
    first = struct.unpack_from('<i', hdr, 0x34)[0]
    entries = dp.read(h, table + first, 12 * maximum) or b''

    def at(i):
        salt, typ, off = (struct.unpack_from('<H', entries, 12 * i)[0], entries[12 * i + 3],
                          struct.unpack_from('<i', entries, 12 * i + 8)[0])
        return salt, typ, (None if off == -1 else data + 0x34 + off)

    rows = []
    for i in range(len(entries) // 12):
        salt, typ, o = at(i)
        if not salt or typ != 0 or o is None:
            continue
        handle = (salt << 16) | i
        b = dp.read(h, o, 0x200)
        stuck, child, guard = {}, struct.unpack_from('<I', b, 0xD4)[0], 0
        while child != 0xFFFFFFFF and guard < 64:
            _s, _t, co = at(child & 0xFFFF)
            if co is None:
                break
            cb = dp.read(h, co, 0x1FC)
            stuck[struct.unpack_from('<I', cb, 0)[0]] = stuck.get(
                struct.unpack_from('<I', cb, 0)[0], 0) + 1
            child, guard = struct.unpack_from('<I', cb, 0xD0)[0], guard + 1
        rows.append(('%08x' % handle, handle == player, struct.unpack_from('<H', b, 0x70)[0],
                     struct.unpack_from('<i', b, 0x1F8)[0], stuck))
    return engine, rows


def live_count(h, base, proj=None, count=None):
    """Rows (path, flags, count) of the loaded proj tags; with `count`, sets `proj`'s."""
    rows = []
    for path, addr in live_projectiles(h, base):
        if proj and path.lower() != proj.lower():
            continue
        if count is not None:
            ok, err = dp.write(h, addr + FIELD_OFFSET, struct.pack('<h', count), 0x04)
            if not ok:
                raise SystemExit('write failed: %s' % err)
        flags = struct.unpack('<I', dp.read(h, addr + 0x17C, 4))[0]
        n = struct.unpack('<h', dp.read(h, addr + FIELD_OFFSET, 2))[0]
        rows.append((path, flags, n))
    return rows


def map_count(halo_map, proj, count=None):
    """Read (or set) one proj tag's count in a HaloMap (halo_map.HaloMap); saving is the
    caller's. Returns the value now held, None when the map has no such tag."""
    off = halo_map.get_tag_meta('proj', proj)
    if off is None:
        return None
    if count is not None:
        struct.pack_into('<h', halo_map.data, off + FIELD_OFFSET, count)
    return struct.unpack_from('<h', halo_map.data, off + FIELD_OFFSET)[0]


def _print_counts(rows):
    for path, flags, n in rows:
        if flags & 8 or n:
            print('%-50s combines=%s count=%d%s' % (
                path, 'yes' if flags & 8 else 'NO ', n,
                ' (engine %d)' % ENGINE_COUNT if n <= 0 else ''))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', '--restore', dest='off', action='store_true')
    g.add_argument('--show', action='store_true')
    g.add_argument('--count', nargs='*', metavar=('PROJ', 'N'),
                   help='list the supercombining projectiles (live, or --map), or set one')
    g.add_argument('--gates', action='store_true',
                   help='read-only: the detonation gates on every live biped (+ .jsonl log)')
    ap.add_argument('--note', default='', help='with --gates: the condition, for the log')
    ap.add_argument('--live', action='store_true', help='the running MCC only, not the file')
    ap.add_argument('--dll', default=DLL, help='a halo1.dll to act on (default: MCC\'s)')
    ap.add_argument('--map', help='with --count: a .map file instead of the running game')
    a = ap.parse_args(argv)
    if a.on or a.off:
        for r in sync(a.on, a.dll, quiet=False, live_only=a.live):
            print('%-16s %s %s' % (r['field'], 'OK  ' if r['ok'] else 'FAIL',
                                   r.get('note') or r.get('reason') or r.get('new')))
        return
    if a.gates:
        r = _live(probe_gates)
        if not r or isinstance(r, tuple) or r[0] is None and not r[1]:
            print('MCC / a level not running')
            return
        engine, rows = r
        print('game engine pointer: %s (null = campaign: a biped whose +0x1F8 is not -1 '
              'is never supercombined)' % ('%x' % engine if engine else 'null'))
        for handle, is_player, w70, d1f8, stuck in rows:
            print('%s%s  +0x70=%d  +0x1F8=%d  stuck=%s' % (
                handle, ' PLAYER' if is_player else '       ', w70, d1f8,
                {'%08x' % k: v for k, v in stuck.items()}))
        import json
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out',
                           'supercombine_gates.jsonl')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'note': a.note,
                                'engine': bool(engine),
                                'bipeds': [{'handle': x[0], 'player': x[1], 'w70': x[2],
                                            'd1f8': x[3], 'stuck': len(x[4])}
                                           for x in rows]}) + '\n')
        return
    if a.count is not None:
        proj = a.count[0] if a.count else None
        n = int(a.count[1]) if len(a.count) > 1 else None
        if a.map:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from halo_map import HaloMap
            m = HaloMap(a.map)
            names = [proj] if proj else [p for (c, p) in m.tags if c == 'proj']
            for p in names:
                v = map_count(m, p, n)
                if v is None:
                    print('%s: no such proj tag' % p)
                elif proj or v:
                    print('%-50s count=%d' % (p, v))
            if n is not None:
                m.save(a.map)
            return
        r = _live(lambda h, base: live_count(h, base, proj, n))
        if r is None:
            print('MCC / halo1.dll not running')
        elif isinstance(r, tuple):
            print(r[1])
        elif not r:
            print('no such proj tag loaded (or no level loaded)')
        elif proj:
            for p, _f, c in r:
                print('%-50s count=%d' % (p, c))
        else:
            _print_counts(r)
        return
    print('file  %s  (%s)' % (file_state(a.dll), a.dll))
    r = _live(lambda h, base: live_state(h, base))
    print('live  %s' % (r if r else 'MCC / halo1.dll not running'))


if __name__ == '__main__':
    main()
