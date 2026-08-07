"""Read and write Run Enhancer script globals in a BUILT Halo 2 cache map.

The H2 counterpart of sprint_tune.py: it edits the compiled globals in place, so
tuning a value takes a second instead of a rebuild-scripts + build-cache-file
round trip. Point it at the DEPLOYED map and relaunch the level.

    python h2_tune.py "<map>" --show
    python h2_tune.py "<map>" --shield 0.0267
    python h2_tune.py "<map>" --kind 4 --vit-max 75 --rate 0.5

Layout, verified against known values on 03a_oldmombasa: the scnr Globals block
(0x1C0, elem 0x28) holds Name[0x20], Type@0x20 and an Initialization Expression
datum@0x24 whose low 16 bits index the script syntax node table. Nodes are 20
bytes with the value at +0x10, as in Halo 1.

The node table pointer is at **scnr+0x23C** (size at 0x238). NOTE the Assembly
Halo2MCC plugin lists "Script Syntax Data" at 0x1A8, which is wrong for this MCC
build -- following it lands ~0x11890 short and silently reads garbage. The
offset here was derived by locating known global values in the file and solving
for the base, then checked against all nine.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as hp    # noqa: E402

GLOBALS_BLOCK = 0x1C0
GLOBALS_ELEM = 0x28
SYNTAX_PTR = 0x23C
NODE_SIZE = 20
NODE_VALUE = 0x10
TYPE_REAL, TYPE_SHORT, TYPE_LONG, TYPE_BOOL = 6, 7, 8, 5

# Every knob the ability script exposes, with the flag that drives it. Names track
# sprint.hsc (Halo 1) since the per-player rewrite -- ability0/ability1 rather than one
# shared ab_kind, and a cooldown per ability rather than one ab_cooldown.
KNOBS = [
    ('ability0', '--p1', int, 'player 1: 0 none, 1 sprint, 2 overshield, 3 camo, '
                              '4 regeneration'),
    ('ability1', '--p2', int, 'player 2: same ids (needs the p2-vision-trigger '
                              'halo2.dll patch to be triggerable)'),
    ('os_shield', '--shield', float, 'overshield magnitude, engine units'),
    ('os_ticks', '--os-duration', int, 'overshield window before the cooldown starts'),
    ('vit_max', '--vit-max', float, 'engine vitality scale (75 in Halo 1)'),
    ('medi_ticks', '--duration', int, 'regeneration duration, ticks (30/sec)'),
    ('medi_rate', '--rate', float, 'health added per tick, vitality units'),
    ('sprint_ticks', '--sprint-duration', int, 'sprint window, ticks (30/sec)'),
    ('sprint_cooldown', '--sprint-cooldown', int, 'ticks before sprint re-arms'),
    ('os_cooldown', '--os-cooldown', int, 'ticks before overshield re-arms'),
    ('medi_cooldown', '--medi-cooldown', int, 'ticks before regeneration re-arms'),
    ('camo_cooldown', '--camo-cooldown', int, 'ticks before camo re-arms'),
    ('camo_ticks', '--camo-duration', int, 'total camo duration in ticks (30/sec)'),
    ('camo_reapply', '--camo-reapply', int,
     'ticks between camo re-applications; must stay under the ~4s engine cap'),
    ('fx_every', '--fx-every', int, 'ticks between regeneration shimmer pulses'),
    ('fx_kind', '--fx-kind', int, '1 Chief shield recharge, 2 Elite recharge, '
                                  '4 co-op teleport, 8 Regret teleport'),
    ('fx_ready', '--fx-ready', int, 'effect fired when a cooldown expires; 0 off'),
    ('fx_ready_n', '--fx-ready-n', int, 'how many flashes the ready cue fires'),
    ('fx_ready_gap', '--fx-ready-gap', int, 'ticks between those flashes'),
    ('no_native_camo', '--no-native-camo', int,
     "1 = cancel the Arbiter's engine camo every tick (Arbiter levels)"),
]


def _globals(m):
    """name -> (type, node index). Raises if the map has no scenario globals."""
    scnr = hp._scnr_base(m)
    n = m.i32(scnr + GLOBALS_BLOCK)
    b = hp._block_base(m, scnr + GLOBALS_BLOCK)
    out = {}
    for i in range(n if b else 0):
        e = b + i * GLOBALS_ELEM
        name = m.data[e:e + 0x20].split(b'\0')[0].decode('latin-1')
        vtype, = struct.unpack_from('<h', m.data, e + 0x20)
        datum, = struct.unpack_from('<I', m.data, e + 0x24)
        out[name] = (vtype, datum & 0xFFFF)
    return out


def _addr(m, node):
    scnr = hp._scnr_base(m)
    return m.meta_offset + m.u32(scnr + SYNTAX_PTR) + node * NODE_SIZE + NODE_VALUE


def read_global(m, name):
    g = _globals(m).get(name)
    if g is None:
        return None
    vtype, node = g
    at = _addr(m, node)
    if vtype == TYPE_REAL:
        return struct.unpack_from('<f', m.data, at)[0]
    if vtype == TYPE_LONG:
        return struct.unpack_from('<i', m.data, at)[0]
    if vtype == TYPE_BOOL:
        return m.data[at]
    return struct.unpack_from('<h', m.data, at)[0]


def write_global(m, name, value):
    g = _globals(m).get(name)
    if g is None:
        raise KeyError('%s is not a global in this map' % name)
    vtype, node = g
    at = _addr(m, node)
    if vtype == TYPE_REAL:
        struct.pack_into('<f', m.data, at, float(value))
    elif vtype == TYPE_LONG:
        struct.pack_into('<i', m.data, at, int(value))
    elif vtype == TYPE_BOOL:
        m.data[at] = 1 if value else 0
    else:
        struct.pack_into('<h', m.data, at, int(value))
    return read_global(m, name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('--show', action='store_true', help='print current values and exit')
    ap.add_argument('--out', help='write elsewhere instead of in place')
    for name, flag, kind, helptext in KNOBS:
        ap.add_argument(flag, type=kind, help='%s (%s)' % (helptext, name))
    a = ap.parse_args(argv)

    m = hp.open_map(a.map, 'Halo 2')
    present = _globals(m)
    if 'ability0' not in present and 'ab_kind' not in present:
        raise SystemExit('%s has no ability script -- is it a Run Enhancer build?'
                         % os.path.basename(a.map))
    if 'ability0' not in present:
        raise SystemExit('%s was built before per-player abilities (it carries ab_kind, '
                         'not ability0/ability1). Rebuild it with h2_batch.py.'
                         % os.path.basename(a.map))

    if a.show or not any(getattr(a, f.lstrip('-').replace('-', '_')) is not None
                         for _, f, _, _ in KNOBS):
        for name, flag, _, helptext in KNOBS:
            print('  %-16s %-10s %s' % (name, read_global(m, name), helptext))
        return

    changed = False
    for name, flag, _, _ in KNOBS:
        val = getattr(a, flag.lstrip('-').replace('-', '_'))
        if val is None:
            continue
        before = read_global(m, name)
        after = write_global(m, name, val)
        print('  %-16s %s -> %s' % (name, before, after))
        changed = True

    if changed:
        m.update_checksum()
        m.save(a.out or a.map)
        print('wrote %s' % (a.out or a.map))


if __name__ == '__main__':
    main()
