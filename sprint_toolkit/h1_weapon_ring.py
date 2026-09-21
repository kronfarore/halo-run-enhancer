r"""Put one weapon of each kind in a ring, so a level that will not render in Sapien can
still be navigated by eye.

Stand in the ring, look at which weapon is nearest, and you know where you are -- which
is enough to place a marker by coordinate afterwards. Nothing is added to the map: the
level's existing weapon placements are MOVED, one per palette kind, so no block has to
grow. Everything comes back with --restore.

The ring's centre defaults to the midpoint of the two turrets nearest the player start,
which on b40 is the pair flanking the outer door at the beginning of the level.

    python h1_weapon_ring.py b40 --status
    python h1_weapon_ring.py b40 --apply [--radius 6] [--center X,Y,Z] [--z-offset 0.5]
    python h1_weapon_ring.py b40 --restore
"""
import argparse, contextlib, io, math, os, shutil, struct, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
GAME = 'Halo 1'
WEAPONS, WEAPON_ES, WEAPON_PAL = 0x270, 0x5C, 0x27C
VEHICLES, VEHICLE_ES, VEHICLE_PAL = 0x240, 0x78, 0x24C
PAL_ES, PAL_ID = 0x30, 0xC
START_BLOCK, START_ES = 0x354, 0x34
FLAGS_AT, POS_AT, ROT_AT = 0x4, 0x8, 0x14


def live_path(mission):
    return os.path.join(he.mcc_root(), 'halo1', 'maps', mission + '.map')


def baseline(mission):
    return he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo1', mission), GAME)


def palette(m, scnr, paloff):
    n = m.i32(scnr + paloff)
    if n <= 0:
        return {}
    base = hp._block_base(m, scnr + paloff)
    return {i: hp._tag_name_by_id(m, m.u32(base + i * PAL_ES + PAL_ID)) for i in range(n)}


def placements(m, scnr, off, esize):
    n = m.i32(scnr + off)
    return (n, hp._block_base(m, scnr + off)) if n > 0 else (0, None)


def player_start(m, scnr):
    n = m.i32(scnr + START_BLOCK)
    if n <= 0:
        return None
    base = hp._block_base(m, scnr + START_BLOCK)
    return struct.unpack_from('<3f', m.data, base)


def turret_pair(m, scnr, near):
    """The two turrets closest to `near` that sit at the same height as each other."""
    n, base = placements(m, scnr, VEHICLES, VEHICLE_ES)
    names = palette(m, scnr, VEHICLE_PAL)
    got = []
    for i in range(n):
        pi = struct.unpack_from('<h', m.data, base + i * VEHICLE_ES)[0]
        nm = (names.get(pi) or '')
        if 'turret' not in nm.lower():
            continue
        p = struct.unpack_from('<3f', m.data, base + i * VEHICLE_ES + POS_AT)
        d = math.dist(p, near) if near else 0.0
        got.append((d, i, p))
    got.sort()
    for a in range(len(got)):
        for b in range(a + 1, len(got)):
            if abs(got[a][2][2] - got[b][2][2]) < 1.0 and math.dist(got[a][2], got[b][2]) < 20:
                return got[a], got[b]
    return (got[0], got[1]) if len(got) > 1 else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mission', nargs='?', default='b40')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--radius', type=float, default=6.0)
    ap.add_argument('--center')
    ap.add_argument('--z-offset', type=float, default=0.3)
    a = ap.parse_args()
    he.load_settings()
    mission = a.mission

    if a.restore:
        shutil.copy2(baseline(mission), live_path(mission))
        print('restored %s from the baseline' % mission)
        return

    path = live_path(mission) if (a.status and os.path.exists(live_path(mission))) \
        else baseline(mission)
    if a.apply:
        shutil.copy2(baseline(mission), live_path(mission))
        path = live_path(mission)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(path, GAME)
    scnr = hp._scnr_base(m)

    start = player_start(m, scnr)
    print('%s: player start %s' % (mission, tuple(round(c, 2) for c in start) if start else '?'))
    if a.center:
        cx, cy, cz = [float(x) for x in a.center.replace(' ', '').split(',')]
        print('centre from --center: %.2f %.2f %.2f' % (cx, cy, cz))
    else:
        t1, t2 = turret_pair(m, scnr, start)
        if not t1 or not t2:
            raise SystemExit('no turret pair found; pass --center X,Y,Z')
        p1, p2 = t1[2], t2[2]
        cx, cy, cz = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (p1[2] + p2[2]) / 2)
        print('turrets  [%d] %s  and  [%d] %s  (%.1f apart, %.1f from the start)'
              % (t1[1], tuple(round(c, 2) for c in p1),
                 t2[1], tuple(round(c, 2) for c in p2), math.dist(p1, p2), t1[0]))
        print('centre   %.2f %.2f %.2f' % (cx, cy, cz))
    cz += a.z_offset

    names = palette(m, scnr, WEAPON_PAL)
    n, base = placements(m, scnr, WEAPONS, WEAPON_ES)
    kinds = sorted(names.items())
    print('\nweapon palette: %d kind(s), %d placement(s) to borrow' % (len(kinds), n))
    if len(kinds) > n:
        raise SystemExit('more kinds than placements')

    print('\n%-4s %-22s %-8s %s' % ('slot', 'weapon', 'bearing', 'position'))
    for k, (pi, nm) in enumerate(kinds):
        ang = 2 * math.pi * k / len(kinds)
        x = cx + a.radius * math.cos(ang)
        y = cy + a.radius * math.sin(ang)
        short = (nm or '?').rsplit(B, 1)[-1]
        had = struct.unpack_from('<I', m.data, base + k * WEAPON_ES + FLAGS_AT)[0]
        print('%-4d %-22s %5.0f deg  %8.2f %8.2f %8.2f%s'
              % (k, short, math.degrees(ang), x, y, cz,
                 '   (cleared flags %#x)' % had if had else ''))
        if a.apply:
            e = base + k * WEAPON_ES
            struct.pack_into('<h', m.data, e, pi)                  # palette index
            # Placement flags @4 decide whether the weapon appears at all: bit 0 is "not
            # automatically" and the next three are the per-difficulty suppressions. A
            # borrowed placement can carry any of them -- b40's did, and the ring simply
            # did not spawn until they were cleared.
            struct.pack_into('<I', m.data, e + FLAGS_AT, 0)
            struct.pack_into('<3f', m.data, e + POS_AT, x, y, cz)
            struct.pack_into('<3f', m.data, e + ROT_AT, 0.0, 0.0, 0.0)
    if a.apply:
        # park every other weapon far below, so only the ring is visible
        for k in range(len(kinds), n):
            e = base + k * WEAPON_ES
            struct.pack_into('<3f', m.data, e + POS_AT, cx, cy, cz - 500.0)
        m.save(live_path(mission))
        print('\nmoved %d weapon(s) into the ring, parked %d other(s) out of sight'
              % (len(kinds), n - len(kinds)))
        print('saved %s' % live_path(mission))
    else:
        print('\n(read-only -- pass --apply to write, --restore to undo)')


if __name__ == '__main__':
    main()
