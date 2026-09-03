r"""Drop weapons and equipment in a circle at any coordinate on a Reach map.

The Halo 3 / ODST equivalent is odst_kikowani_test.py, which answers "did it spawn"
separately from "could I find it" by ringing items on a measured position. This is the
same idea, general over Reach's ten maps and driveable from the command line, because
finding a spot Reach will actually spawn at is turning into a per-map search.

WHAT THIS SESSION ESTABLISHED, so it does not have to be rediscovered:

  * appending a placement works, and so does growing the palette -- both confirmed in
    game on m20 (jet_pack and active_camouflage were appended to the palette and
    both appeared)
  * Reach's placement element is 0xB4 and moved every field: Type 0x42 sits where
    Halo 3 keeps Editor Folder, so Halo 3's offsets silently produce Type 0xFFFF and
    an object the engine will not spawn
  * Can Attach To BSP Flags is 0x54 (Halo 3: 0x50); Zone Set Flags is a SEPARATE
    field at 0x34 where 0 means unrestricted
  * a template placement must have a valid Type -- m50 ships an all-zero one with
    Type -1 that an "any auto placement" scan picks by mistake
  * Hologram and Drop Shield do not spawn from a placement anywhere tested, despite
    an identical model chain to three abilities that do
  * items ring at 0.8 units in the shipped patcher, which buries them inside scenery;
    2-3 units is the useful range

The open question this exists to answer: several coordinates spawn nothing at all,
including the measured player start, while the m20 supply cluster works. The leading
theory is that the tags are not STREAMED in those zones.

    # what can this map place, and where does it start?
    python reach_place.py --map m20 --list

    # ring five abilities on a coordinate
    python reach_place.py --map m20 --at -57.3 34.7 13.1 --radius 2.5 \
        --equipment "Armor Lock,Sprint,Jet Pack,Active Camouflage"

    # weapons too, and put it on the scenario's own starting location
    python reach_place.py --map m20 --at-spawn --weapons "magnum,shotgun" --lift 0.3

    # walk a trail from a spot that WORKS back to one that does not: whichever
    # marker is the last one you can see is the boundary
    python reach_place.py --map m20 --at -57.3 34.7 13.1 --steps 12 \
        --toward -39.59 -70.68 15.48

    # put the map back to vanilla (only needed when you are FINISHED -- every run
    # already starts by copying the .bak over the live map)
    python reach_place.py --map m20 --restore

Patches FROM <map>.bak and never modifies it, so the GUI's baseline is untouched and
a normal patch restores everything. Every run starts by copying that baseline over the
live map, so tests never stack and there is no need to --restore between them.

MCC can stay running. It only locks the file while that MAP is loaded, so patching
from the main menu (or while a different mission is up) works fine.
"""
import argparse
import math
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP                                          # noqa: E402
import map_vault as V                                            # noqa: E402

GAME = 'Halo Reach'
S = chr(92)
# Reach's object-placement element. Shared by the Weapons and Equipment blocks.
OFF = {'pal': 0x0, 'name': 0x2, 'flags': 0x4, 'pos': 0x8, 'zone': 0x34,
       'uid': 0x3C, 'type': 0x42, 'folder': 0x44, 'attach': 0x54}
NOT_AUTO, NEVER = 1 << 0, 1 << 6
DEFAULT_MASK = 0xFFFF          # every BSP; the narrow alternative is a per-area guess


def _db():
    # load_data prints a checkmark, and on a redirected cp1252 stream that raises --
    # which load_data swallows, leaving every pool empty and every lookup a miss.
    # Only halo_enhancer.main() guards this, and this is not that entry point.
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    import halo_enhancer as he
    he.load_settings()
    return he, he.ModifierDatabase()


def _copy_baseline(bak, live):
    """Start every run from the pristine map.

    This is also why there is no need to --restore between tests: each run discards
    the previous patch by overwriting the live map from the baseline. --restore only
    exists to leave the map vanilla when you are finished.

    MCC does NOT have to be closed -- it only holds the file while that map is
    LOADED, so patching from the menu or another mission is fine. The old version
    refused whenever the process existed, which denied far more than it needed to.
    The file lock is the real test, so let the copy fail and say what it means.
    """
    try:
        shutil.copy2(bak, live)
        return True
    except PermissionError:
        print('cannot write %s -- the map is open in MCC.' % os.path.basename(live))
        print('Leave the mission (the main menu is enough); MCC itself can stay up.')
        return False


def _palette(m, scnr, lay):
    poff, pes = lay['palette']
    out = {}
    for i in range(max(0, m.i32(scnr + poff))):
        e = HP._block_base(m, scnr + poff) + i * pes
        nm = HP._tag_name_by_id(m, m.u32(e + lay['pal_id_at']))
        if nm:
            out[str(nm).replace('/', S).lower()] = i
    return out


def _template(m, base, N, esz):
    """A placement that spawns on its own AND has a valid Type. Type first: m50 ships
    an all-zero placement with Type -1 that is the only non-scripted one it has."""
    for i in range(N):
        e = base + i * esz
        fl = struct.unpack_from('<I', m.data, e + OFF['flags'])[0]
        ty = struct.unpack_from('<h', m.data, e + OFF['type'])[0]
        if ty >= 0 and not (fl & (NOT_AUTO | NEVER)):
            return i
    for i in range(N):
        if struct.unpack_from('<h', m.data, base + i * esz + OFF['type'])[0] >= 0:
            return i
    return 0 if N else None


def _resolve(db, he, kind, name, m):
    """(tag path, already-resident datum or None) for a display name OR a basename."""
    if kind == 'equipment':
        tag = db.eqip_tag_for(name, GAME)
    else:
        tag = db.weap_tag_for(name, GAME)
    if tag:
        return tag.split(' ', 1)[1].split('&')[0].strip()
    # fall back to a raw basename match against what the map carries
    cls = 'eqip' if kind == 'equipment' else 'weap'
    for t in (m.tags or []):
        if t.get('class') == cls and t.get('name'):
            if t['name'].rsplit(S, 1)[-1].lower() == name.strip().lower():
                return t['name']
    return None


def place(m, scnr, kind, names, spot, radius, lift, mask, db, he, start_angle=0.0):
    lay = HP._MAP_EQUIPMENT[GAME] if kind == 'equipment' else HP._MAP_WEAPONS[GAME]
    boff, esz = lay['items'] if kind == 'equipment' else lay['weapons']
    poff, pes = lay['palette']
    N = m.i32(scnr + boff)
    base = HP._block_base(m, scnr + boff)
    pc = m.i32(scnr + poff)
    pbase = HP._block_base(m, scnr + poff)
    pal = _palette(m, scnr, lay)
    cls = 'eqip' if kind == 'equipment' else 'weap'
    plan, new_pal = [], []
    for i, name in enumerate(names):
        path = _resolve(db, he, kind, name, m)
        if not path:
            print('   SKIP %-22s no %s tag resolves' % (name, cls))
            continue
        key = path.replace('/', S).lower()
        if key in pal:
            pi = pal[key]
        else:
            datum = HP._h3_tag_datum(m, cls, path)
            if datum is None:
                print('   SKIP %-22s tag not resident in this map' % name)
                continue
            pi = pc + len(new_pal)
            new_pal.append(datum)
            pal[key] = pi
        ang = start_angle + (2 * math.pi * i / max(1, len(names)))
        plan.append((pi, (spot[0] + radius * math.sin(ang),
                          spot[1] + radius * math.cos(ang),
                          spot[2] + lift), name, math.degrees(ang)))
    if not plan:
        return 0
    tmpl = _template(m, base, N, esz)
    if tmpl is None:
        print('   no template placement in the %s block' % kind)
        return 0
    uids = [m.u32(base + i * esz + OFF['uid']) for i in range(N)]
    salt = uids[tmpl] >> 16
    nxt = max(u & 0xFFFF for u in uids) + 1
    sizes = [(N + len(plan)) * esz] + ([(pc + len(new_pal)) * pes] if new_pal else [])
    got = HP._h3_reserve(m, sizes)
    if got is None:
        print('   no free run of %d bytes to grow the %s block' % (sum(sizes), kind))
        return 0
    dest = got[0]
    if new_pal:
        pdest = got[1]
        m.data[pdest:pdest + pc * pes] = m.data[pbase:pbase + pc * pes]
        ref = m.data[pbase:pbase + pes]
        for j, datum in enumerate(new_pal):
            e = pdest + (pc + j) * pes
            m.data[e:e + pes] = ref
            struct.pack_into('<I', m.data, e + lay['pal_id_at'], datum)
        struct.pack_into('<i', m.data, scnr + poff, pc + len(new_pal))
        struct.pack_into('<I', m.data, scnr + poff + 4, m.off2data(pdest))
    m.data[dest:dest + N * esz] = m.data[base:base + N * esz]
    for k, (pi, pos, name, deg) in enumerate(plan):
        e = dest + (N + k) * esz
        m.data[e:e + esz] = m.data[base + tmpl * esz: base + (tmpl + 1) * esz]
        struct.pack_into('<h', m.data, e + OFF['pal'], pi)
        struct.pack_into('<h', m.data, e + OFF['name'], -1)
        fl = struct.unpack_from('<I', m.data, e + OFF['flags'])[0] & ~(NOT_AUTO | NEVER)
        struct.pack_into('<I', m.data, e + OFF['flags'], fl)
        struct.pack_into('<fff', m.data, e + OFF['pos'], *pos)
        struct.pack_into('<H', m.data, e + OFF['zone'], 0)
        struct.pack_into('<H', m.data, e + OFF['attach'], mask)
        struct.pack_into('<h', m.data, e + OFF['folder'], -1)
        struct.pack_into('<I', m.data, e + OFF['uid'],
                         ((salt << 16) | (nxt + k)) & 0xFFFFFFFF)
        print('   %-9s %-22s %3.0f deg  (%8.2f, %8.2f, %7.2f)'
              % (kind, name, deg, pos[0], pos[1], pos[2]))
    struct.pack_into('<i', m.data, scnr + boff, N + len(plan))
    struct.pack_into('<I', m.data, scnr + boff + 4, m.off2data(dest))
    return len(plan)


def cmd_list(m, scnr):
    print('Player Starting Locations:')
    for i, (pos, _bsp) in enumerate(HP.h3_player_spawns(m, GAME)):
        print('   %d  (%8.2f, %8.2f, %7.2f)' % (i, *pos))
    for kind in ('equipment', 'weapons'):
        lay = HP._MAP_EQUIPMENT[GAME] if kind == 'equipment' else HP._MAP_WEAPONS[GAME]
        pal = _palette(m, scnr, lay)
        print('%s palette (%d):' % (kind, len(pal)))
        print('   %s' % ', '.join(sorted(p.rsplit(S, 1)[-1] for p in pal)))
    for cls, label in (('eqip', 'equipment'), ('weap', 'weapon')):
        res = sorted({(t.get('name') or '').rsplit(S, 1)[-1]
                      for t in (m.tags or []) if t.get('class') == cls})
        print('resident %s tags (%d): %s' % (label, len(res), ', '.join(res[:24])))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', required=True, help='mission id, e.g. m20')
    ap.add_argument('--at', nargs=3, type=float, metavar=('X', 'Y', 'Z'))
    ap.add_argument('--at-spawn', action='store_true',
                    help="use the scenario's Player Starting Location 0")
    ap.add_argument('--equipment', default='', help='comma-separated names')
    ap.add_argument('--weapons', default='', help='comma-separated names')
    ap.add_argument('--toward', nargs=3, type=float, metavar=('X', 'Y', 'Z'),
                    help='lay a TRAIL of single markers from --at to here, instead '
                         'of a ring, so the point where they stop appearing is the '
                         'boundary of whatever is gating them')
    ap.add_argument('--steps', type=int, default=10,
                    help='markers along the trail (default 10)')
    ap.add_argument('--radius', type=float, default=2.5)
    ap.add_argument('--lift', type=float, default=0.0,
                    help='raise every drop by this much; guards against floor burial')
    ap.add_argument('--mask', default=hex(DEFAULT_MASK),
                    help='Can Attach To BSP Flags (default 0xFFFF = every BSP)')
    ap.add_argument('--list', action='store_true',
                    help='show spawns, palettes and resident tags, then exit')
    ap.add_argument('--restore', action='store_true', help='copy the .bak back')
    a = ap.parse_args(argv)

    live = V.resolve(GAME, a.map)
    if not live:
        raise SystemExit('no such Reach map: %s' % a.map)
    bak = live + '.bak'
    if not os.path.isfile(bak):
        raise SystemExit('no pristine baseline at %s -- refusing to touch the map' % bak)
    if a.restore:
        if not _copy_baseline(bak, live):
            return 1
        print('restored %s from its baseline' % live)
        return 0
    if a.list:
        # the BASELINE, not the live map: listing what a previous run of this tool
        # already appended would make the map look like it ships things it does not
        m = HP.open_map(bak, GAME)
        cmd_list(m, (m.find_tags('scnr', '*') or [(None, None)])[0][1])
        return 0
    if not (a.at or a.at_spawn):
        raise SystemExit('give --at X Y Z or --at-spawn')
    if not _copy_baseline(bak, live):
        return 1
    m = HP.open_map(live, GAME)
    scnr = (m.find_tags('scnr', '*') or [(None, None)])[0][1]
    spot = tuple(a.at) if a.at else HP.h3_player_spawns(m, GAME)[0][0]
    mask = int(str(a.mask), 0)
    he, db = _db()
    eq = [s.strip() for s in a.equipment.split(',') if s.strip()]
    wp = [s.strip() for s in a.weapons.split(',') if s.strip()]
    n = 0

    if a.toward:
        # TRAIL: markers along the line from a spot that WORKS to one that does not,
        # so the point where they stop appearing is the boundary. That is the shape
        # of the streaming question -- a ring at one coordinate can only ever say
        # yes or no about that coordinate.
        dest = tuple(a.toward)
        items = (eq + wp) or ['Armor Lock', 'Sprint', 'Jet Pack', 'Active Camouflage']
        kinds = (['equipment'] * len(eq)) + (['weapons'] * len(wp))
        if not kinds:
            kinds = ['equipment'] * 4
        span = sum((d - s) ** 2 for s, d in zip(spot, dest)) ** 0.5
        print('trail  (%8.2f, %8.2f, %7.2f) -> (%8.2f, %8.2f, %7.2f)'
              % (spot + dest))
        print('       %d step(s) over %.1f units, lift %.2f, attach 0x%04X'
              % (a.steps, span, a.lift, mask))
        for i in range(a.steps):
            f = i / float(max(1, a.steps - 1))
            at = tuple(s + (d - s) * f for s, d in zip(spot, dest))
            name = items[i % len(items)]
            kind = kinds[i % len(kinds)]
            print('   step %2d  %5.1f units out' % (i, span * f))
            n += place(m, scnr, kind, [name], at, 0.0, a.lift, mask, db, he)
    else:
        print('centre (%8.2f, %8.2f, %7.2f)  radius %.2f  lift %.2f  attach 0x%04X'
              % (spot[0], spot[1], spot[2], a.radius, a.lift, mask))
        if eq:
            n += place(m, scnr, 'equipment', eq, spot, a.radius, a.lift, mask, db, he)
        if wp:
            # offset half a step so weapons interleave with the equipment ring
            step = math.pi / max(1, len(wp))
            n += place(m, scnr, 'weapons', wp, spot, a.radius, a.lift, mask, db, he,
                       start_angle=step)
    if not n:
        print('nothing placed; map left at its baseline')
        return 1
    m.save(live)           # save() recomputes the cache checksum
    print()
    print('patched %s with %d placement(s)' % (live, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
