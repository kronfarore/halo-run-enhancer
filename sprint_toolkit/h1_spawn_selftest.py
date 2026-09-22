r"""Does Halo 1's placed-starting-weapons path actually work?

The markers only reach a map when it is REBUILT, so this does not wait for that: it
names an existing equipment placement `enhancer_marker1` in a scratch copy of the map,
runs the placer, and reads the result back out of the weapon block. That exercises every
part the rebuild will rely on -- the Object Names lookup, the marker's coordinates, the
palette match, growing the block and the flags -- without needing the rebuild first.

Nothing is written to a live map: the copy lives in the scratch directory.

    python h1_spawn_selftest.py [--map b30] [--weapon shotgun]
"""
import argparse, contextlib, io, os, struct, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
GAME = 'Halo 1'
OBJ_NAMES, OBJ_ES = 0x204, 0x24


def name_a_marker(m, scnr, which=0, name='enhancer_marker1'):
    """Point an Object Names entry at equipment placement `which` and name it, the way
    a rebuilt map's Sapien-placed marker would look."""
    E = hp._MAP_EQUIPMENT[GAME]
    eoff, ees = E['items']
    ecount = max(0, m.i32(scnr + eoff))
    ebase = hp._block_base(m, scnr + eoff)
    if not ebase or ecount <= which:
        return None
    ncount = max(0, m.i32(scnr + OBJ_NAMES))
    nbase = hp._block_base(m, scnr + OBJ_NAMES)
    if not nbase or not ncount:
        return None
    slot = ncount - 1                       # reuse the last entry rather than grow
    e = nbase + slot * OBJ_ES
    m.data[e:e + 0x20] = name.encode('latin1').ljust(0x20, b'\0')
    struct.pack_into('<hh', m.data, e + 0x20, 4, which)
    struct.pack_into('<h', m.data, ebase + which * ees + 0x2, slot)   # placement -> name
    return struct.unpack_from('<fff', m.data, ebase + which * ees + 0x8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='b30')
    ap.add_argument('--weapon', default='shotgun')
    a = ap.parse_args()
    he.load_settings()

    src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo1', a.map), GAME)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))
    scnr = hp._scnr_base(m)
    lay = hp._MAP_WEAPONS[GAME]
    woff, wes = lay['weapons']
    before = max(0, m.i32(scnr + woff))
    print('%s: %d weapon placement(s) before' % (a.map, before))

    print('markers as shipped: %s' % (hp.reach_named_markers(m, GAME) or '(none)'))
    pos = name_a_marker(m, scnr)
    if pos is None:
        raise SystemExit('could not stage a marker on this map')
    print('staged enhancer_marker1 on equipment placement 0 at (%.1f, %.1f, %.1f)' % pos)
    named = hp.reach_named_markers(m, GAME)
    print('markers now: %s' % named)
    if 'enhancer_marker1' not in named:
        raise SystemExit('the marker lookup did not find it -- Object Names offset wrong')

    # what the level actually stocks, so the test asks for something placeable
    poff, pes = lay['palette']
    pbase = hp._block_base(m, scnr + poff)
    stock = []
    for i in range(max(0, m.i32(scnr + poff))):
        nm = hp._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        if isinstance(nm, str):
            stock.append(nm)
    print('weapon palette: %s' % ', '.join(n.rsplit(B, 1)[-1] for n in stock))
    pick = next((n for n in stock if a.weapon in n.lower()), stock[0] if stock else None)
    if not pick:
        raise SystemExit('this level stocks no weapons at all')
    print('placing: %s' % pick)

    res = hp._apply_spawn_weapons(m, GAME, {'groups': [[pick]], 'radius': 0.5}, reg)
    for r in res:
        print('   %s' % r)

    after = max(0, m.i32(scnr + woff))
    base = hp._block_base(m, scnr + woff)
    print('\n%d weapon placement(s) after (+%d)' % (after, after - before))
    ok = after == before + 1
    for i in range(before, after):
        e = base + i * wes
        pi, ni = struct.unpack_from('<hh', m.data, e)
        flags = struct.unpack_from('<I', m.data, e + 0x4)[0]
        p = struct.unpack_from('<fff', m.data, e + 0x8)
        left, loaded = struct.unpack_from('<hh', m.data, e + lay['rounds_left'])
        print('   [%d] palette=%d name=%d flags=%#x pos=(%.1f, %.1f, %.1f) rounds %d/%d'
              % (i, pi, ni, flags, p[0], p[1], p[2], loaded, left))
        if flags & 0x1:
            print('       !! NOT AUTOMATICALLY is set -- this would never spawn')
            ok = False
        if abs(p[0] - pos[0]) > 1.0 or abs(p[1] - pos[1]) > 1.0:
            print('       !! not at the marker')
            ok = False

    out = os.path.join(os.environ.get('TEMP', '.'), 'h1_spawn_selftest_%s.map' % a.map)
    m.save(out)
    reopened = hp.open_map(out, GAME)
    n2 = max(0, reopened.i32(hp._scnr_base(reopened) + woff))
    print('\nsaved and reopened: %d placement(s)%s'
          % (n2, '' if n2 == after else '   !! count did not survive the round trip'))
    ok = ok and n2 == after
    print('\n%s' % ('PASS' if ok else 'FAIL'))


if __name__ == '__main__':
    main()
