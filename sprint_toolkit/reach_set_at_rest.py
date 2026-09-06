# -*- coding: utf-8 -*-
r"""Set Create At Rest on the enhancer's own marker placements, in built maps.

Without the flag an object is spawned falling rather than set down, so it tumbles,
sinks into the floor, or ends up somewhere the player never looks -- which reads
exactly like a spawn that never happened. It is a single bit in the placement record,
so a map that is otherwise finished does not need rebuilding to gain it.

Only placements that are BOTH inert (Not Automatically -- the marker convention) and
close to an enhancer marker are touched. Shipped maps leave the bit clear all over the
place: untouched m50 has 54 such placements, all Bungie's script spawns, and flipping
those would change how the level behaves.

Both the live map and its patch baseline are edited, separately rather than by copying
one over the other, so a live map that currently holds a patch keeps it.

    python reach_set_at_rest.py            # dry run
    python reach_set_at_rest.py --write
"""
import argparse
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP                                          # noqa: E402
import map_vault as V                                            # noqa: E402

GAME = 'Halo Reach'
SEP = chr(92)
CREATE_AT_REST = 1 << 8
NOT_AUTOMATICALLY = 1 << 0
NEVER_PLACED = 1 << 6
#: A marker cluster is a couple of metres across; anything further off is the level's.
NEAR = 8.0


def targets(m):
    """[(kind, index, name, flags, distance)] for placements that should be at rest."""
    scnr = HP._scnr_base(m)
    mk = HP.reach_named_markers(m, GAME)
    E = HP._MAP_EQUIPMENT[GAME]
    eoff, ees = E['items']
    eb = HP._block_base(m, scnr + eoff)
    anchors = [struct.unpack_from('<fff', m.data, eb + i * ees + 0x8)
               for i in mk.values()]
    if not anchors:
        return []
    out = []
    for kind, lay in (('weapons', HP._MAP_WEAPONS[GAME]), ('equipment', E)):
        off, es = lay['items' if kind == 'equipment' else 'weapons']
        poff, pes = lay['palette']
        pb = HP._block_base(m, scnr + poff)
        pal = [str(HP._tag_name_by_id(m, m.u32(pb + i * pes + lay['pal_id_at'])))
               .split(SEP)[-1] for i in range(max(0, m.i32(scnr + poff)))]
        b = HP._block_base(m, scnr + off)
        for i in range(max(0, m.i32(scnr + off))) if b else []:
            e = b + i * es
            fl = struct.unpack_from('<I', m.data, e + 0x4)[0]
            if fl & (NEVER_PLACED | CREATE_AT_REST):
                continue
            if not (fl & NOT_AUTOMATICALLY):
                continue                       # live placement, the level's own
            pos = struct.unpack_from('<fff', m.data, e + 0x8)
            d = min(sum((pos[k] - a[k]) ** 2 for k in range(3)) ** 0.5 for a in anchors)
            if d > NEAR:
                continue
            pi = struct.unpack_from('<h', m.data, e)[0]
            out.append((kind, i, pal[pi] if 0 <= pi < len(pal) else '?', fl, d,
                        e + 0x4))
    return out


def fix(path, write):
    if not path or not os.path.exists(path):
        return 0
    m = HP.open_map(path, GAME)
    hits = targets(m)
    for kind, i, nm, fl, d, at in hits:
        struct.pack_into('<I', m.data, at, fl | CREATE_AT_REST)
        print('      %-10s #%-3d %-22s 0x%04X -> 0x%04X  (%.2fu from a marker)'
              % (kind, i, nm, fl, fl | CREATE_AT_REST, d))
    if hits and write:
        m.save(path)
    return len(hits)


def forget_pool_cache(names):
    """Drop these missions' remembered pools, so the next look re-derives them.

    Belt and braces. The pool stamp is now an exact digest, so this edit IS visible to
    it and the entries would be refreshed anyway -- but that was not true when this
    tool was written: the stamp was the map's own XOR checksum, and flipping the same
    bit an even number of times cancels, which is exactly what this tool does. Both
    maps came out of the first run byte-changed and stamp-identical.

    Kept because a tool that edits a map in place should not have to reason about how
    good someone else's change detection is.
    """
    try:
        import halo_enhancer as he
    except Exception as ex:
        print('could not reach the pool cache (%s); run reach_ek_build --warm' % ex)
        return
    want = set(names)
    try:
        entries = he._pool_disk()
        gone = [k for k in list(entries) if k.split('|')[1:2] and k.split('|')[1] in want]
        if not gone:
            return
        for k in gone:
            entries.pop(k, None)
        target = he.app_data_dir() / he.POOL_CACHE_FILE
        tmp = str(target) + '.tmp'
        with io.open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'version': he.POOL_CACHE_VERSION, 'entries': entries},
                      f, indent=1, sort_keys=True)
        os.replace(tmp, str(target))
        print('dropped %d pool cache entr(ies); they will be re-derived' % len(gone))
    except Exception as ex:
        print('could not update the pool cache (%s); run reach_ek_build --warm' % ex)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--write', action='store_true', help='save; otherwise a dry run')
    ap.add_argument('--maps', help='comma-separated subset')
    a = ap.parse_args(argv)
    tool = os.path.dirname(HERE)
    with io.open(os.path.join(tool, 'halo.json'), encoding='utf-8') as f:
        names = list(json.load(f)['Missions'][GAME])
    if a.maps:
        names = [x.strip() for x in a.maps.split(',')]
    total = 0
    for name in names:
        live = V.resolve(GAME, name)
        if not live:
            continue
        base = V.baseline_for(GAME, live)
        n = 0
        for label, path in (('live', live), ('baseline', base)):
            if not os.path.exists(path):
                continue
            print('   %s %s' % (name, label))
            try:
                n += fix(path, a.write)
            except PermissionError:
                print('      %s is in use -- leave the mission and retry' % name)
        if n:
            print('   %s: %d placement(s)%s' % (name, n, '' if a.write else ' (dry run)'))
        total += n
    print()
    print('%d placement(s) %s' % (total, 'updated' if a.write else 'would change'))
    if total and a.write:
        forget_pool_cache(names)
    if total and not a.write:
        print('pass --write to apply')
    return 0


if __name__ == '__main__':
    sys.exit(main())
