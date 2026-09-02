r"""Which weapons can a level actually give the player? All five games.

The enhancer already had this for ODST alone (`halo_patch.odst_player_weapons`), and
that test does not generalise: it keys on the weap `First Person` block, which the
plugins never name and Halo 1 does not have at all. So this asks the scenario instead,
which every game answers the same way.

Four verdicts, strongest first:

  PLACED    the scenario places it -- a real pickup, or for a detached turret a
            VEHICLE placement. This is proof.
  PALETTE   it sits in a palette but nothing places it. Something else spawns it: a
            script, or a squad carrying it. Treat as likely, not proven -- Halo 3's
            The Storm carries the missile pod exactly this way and it is unmistakably
            there in play.
  RESIDENT  the tag is in the map but in no palette. Usually a shared dependency, or
            a weapon another tag references; rarely obtainable.
  ABSENT    not in the map at all. Inserting it means importing the tag first.

Turrets matter here: they are placed as VEHICLES, not weapon pickups, so a
Weapons-only reader reports 0 for a machinegun turret you can plainly rip off its
mount. The Vehicles palette is walked too, and an entry there is kept only when a
WEAPON of the same name is also in the map -- that admits the rippable turret while
leaving Falcons and forklifts out.

    python weapon_availability.py --game "Halo 1"
    python weapon_availability.py --game "Halo 1" --weapon flamethrower
    python weapon_availability.py --game "Halo 1" --map b30 --verbose
    python weapon_availability.py --all --missing        # what halo.json offers but
                                                         # the map cannot supply
Reads only; MCC may be running.
"""
import argparse
import collections
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import halo_patch as HP                                          # noqa: E402
import map_vault as V                                            # noqa: E402

S = chr(92)

# Placement blocks per game. The weapon entries come from halo_patch._MAP_WEAPONS so
# the two cannot drift; the rest are read off the scnr plugin.
# Every palette offset is stated OUTRIGHT rather than derived from the placement block.
# A tagblock is 12 bytes in Halo 1 and from Halo 3 on, but only 8 in Halo 2, so the
# fixed +0xC this used to assume would read Halo 2's LIGHTMAPS as its vehicle palette.
# The same trap is already called out for weapons below; it applies here identically.
# Only VEHICLES beyond the weapon list: that is where detached turrets live. Scenery
# and Crates carry hundreds of props and would bury the answer in furniture.
_EXTRA = {
    # Halo 1 and Halo 2 are here because without them this tool could not see a
    # vehicle placement in either game at all, so every turret verdict it gave for
    # them was meaningless -- a Shade read RESIDENT ("in no palette") when the level
    # plainly places it. Offsets from the scnr plugins; the palette shapes match the
    # weapon palettes of the same game, which is the cross-check that they are right.
    'Halo 1': {'Vehicles': dict(block=(0x240, 0x78), palette=(0x24C, 0x30),
                                pal_id_at=0xC, palette_index=0x0)},
    'Halo 2': {'Vehicles': dict(block=(0x70, 0x54), palette=(0x78, 0x28),
                                pal_id_at=0x4, palette_index=0x0)},
    'Halo 3': {'Vehicles': dict(block=(0xE4, 0xA8), palette=(0xF0, 0x10),
                                pal_id_at=0xC, palette_index=0x0)},
    'Halo 3: ODST': {'Vehicles': dict(block=(0x100, 0xA8), palette=(0x10C, 0x10),
                                      pal_id_at=0xC, palette_index=0x0)},
    'Halo Reach': {'Vehicles': dict(block=(0x12C, 0xD0), palette=(0x138, 0x10),
                                    pal_id_at=0xC, palette_index=0x0)},
}
# Reach is missing from _MAP_WEAPONS (nothing had needed to swap its weapons yet).
_REACH_WEAPONS = {'weapons': (0x15C, 0xD0), 'palette': (0x168, 0x10), 'pal_id_at': 0xC,
                  'palette_index': 0x0}


def _weapon_layout(game):
    if game == 'Halo Reach':
        return _REACH_WEAPONS
    return HP._MAP_WEAPONS.get(game)


def _tag_class(m, rid):
    """Tag class of a palette datum, or None. The Vehicles palette holds real vehicles
    as well as detached turrets; only the turrets are `weap` tags, so the class is what
    separates a rippable plasma cannon from a Falcon."""
    row = rid & 0xFFFF
    tags = getattr(m, 'tags', None)
    if isinstance(tags, dict):                      # H1: {(class, name): off}
        nm = HP._tag_name_by_id(m, rid)
        for (c, n) in tags:
            if n == nm:
                return c
        return None
    t = m.tag(row) if hasattr(m, 'tag') else None
    return str(t['class']).strip() if t and t.get('class') else None


def _palette(m, scnr, pal_off, elem, id_at):
    """[(index, basename, class)] for one placement block's palette."""
    out = []
    for i, el in enumerate(m.follow_all(scnr, [pal_off], [elem], 'all')):
        rid = m.u32(el + id_at)
        nm = HP._tag_name_by_id(m, rid)
        out.append((i, str(nm).rsplit(S, 1)[-1] if nm else None, _tag_class(m, rid)))
    return out


def survey(m, game, weap_names=None):
    """{basename: {'placed': n, 'blocks': {block: n}}} for every palette in the map."""
    weap_names = weap_names if weap_names is not None else resident(m)
    tags = m.find_tags('scnr', '*')
    if not tags:
        return {}
    scnr = tags[0][1]
    lay = _weapon_layout(game)
    blocks = {}
    if lay:
        # The weapon palette's offset is given explicitly, never derived: a tagblock is
        # 12 bytes in Halo 1 and from Halo 3 on, but only 8 in Halo 2, so assuming a
        # fixed delta from the placement block reads Halo 2's LIGHTMAPS as weapons.
        blocks['Weapons'] = (lay['weapons'][0], lay['weapons'][1],
                             lay['palette'][0], lay['palette'][1], lay['pal_id_at'],
                             lay.get('palette_index', 0))
    for name, lay2 in (_EXTRA.get(game) or {}).items():
        blocks[name] = (lay2['block'][0], lay2['block'][1],
                        lay2['palette'][0], lay2['palette'][1],
                        lay2['pal_id_at'], lay2.get('palette_index', 0))
    out = {}
    for bname, (off, elem, pal_off, pal_elem, id_at, idx_at) in blocks.items():
        pal = _palette(m, scnr, pal_off, pal_elem, id_at)
        if not pal:
            continue
        cnt = collections.Counter()
        for el in m.follow_all(scnr, [off], [elem], 'all'):
            cnt[struct.unpack_from('<h', m.data, el + idx_at)[0]] += 1
        for i, nm, cls in pal:
            # Keep weapons, and keep a VEHICLE only when a weapon of the same name
            # is also in the map -- that is a mounted turret whose gun the player can
            # rip off. It is what admits the machinegun turret while leaving Falcons
            # and forklifts out.
            if not nm:
                continue
            cls = cls or 'weap'
            if cls != 'weap' and not (cls == 'vehi' and nm in weap_names):
                continue
            rec = out.setdefault(nm, {'placed': 0, 'blocks': {}})
            n = cnt.get(i, 0)
            rec['placed'] += n
            rec['blocks'][bname] = rec['blocks'].get(bname, 0) + n
    return out


def vehicle_survey(m, game):
    """{basename: {'placed': n, 'palette': True}} for the Vehicles palette, unfiltered.

    `survey` keeps a vehicle only when a WEAPON of the same basename is also in the map,
    which is the right rule for "can this level arm the player" -- it admits a rippable
    machinegun turret and leaves Falcons out. It is the wrong rule for asking what
    TURRETS a level places, and it fails on Halo 1 outright, where the Shade is the
    vehicle `c gun turret` while its gun is `c gun turret gun`: different basenames, so
    the filter dropped a turret the level places five of. This asks the palette
    directly and lets the caller decide what counts.
    """
    lay = (_EXTRA.get(game) or {}).get('Vehicles')
    tags = m.find_tags('scnr', '*')
    if not lay or not tags:
        return {}
    scnr = tags[0][1]
    pal = _palette(m, scnr, lay['palette'][0], lay['palette'][1], lay['pal_id_at'])
    if not pal:
        return {}
    cnt = collections.Counter()
    for el in m.follow_all(scnr, [lay['block'][0]], [lay['block'][1]], 'all'):
        cnt[struct.unpack_from('<h', m.data, el + lay.get('palette_index', 0))[0]] += 1
    out = {}
    for i, base, cls in pal:
        if not base:
            continue
        rec = out.setdefault(base, {'placed': 0, 'cls': cls})
        rec['placed'] += cnt.get(i, 0)
    return out


def resident(m):
    """Every weap tag basename physically in the map."""
    return {str(t).rsplit(S, 1)[-1] for t, _b in m.find_tags('weap', '*')}


def verdict(name, pal, res):
    if name in pal and pal[name]['placed'] > 0:
        where = ', '.join('%s x%d' % (b, n) for b, n in sorted(pal[name]['blocks'].items())
                          if n)
        return 'PLACED', where
    if name in pal:
        return 'PALETTE', 'in %s, never placed' % ', '.join(sorted(pal[name]['blocks']))
    if name in res:
        return 'RESIDENT', 'tag present, in no palette'
    return 'ABSENT', 'not in this map'


def _vehicles_main(a):
    """--vehicles: every Vehicles-palette entry per map, with its placement count."""
    tool = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = json.load(open(os.path.join(tool, 'halo.json'), encoding='utf-8'))
    games = [a.game] if a.game else list(doc['Missions'])
    for game in games:
        if game not in doc['Missions']:
            continue
        if not (_EXTRA.get(game) or {}).get('Vehicles'):
            print('\n=== %s: no vehicle-placement layout' % game)
            continue
        print('\n=== %s' % game)
        totals = {}
        for mid in doc['Missions'][game]:
            if a.map and mid != a.map:
                continue
            path = V.resolve(game, mid)
            if not path:
                continue
            try:
                m = HP.open_map(path, game)
            except Exception as e:
                print('   %-10s could not open (%s)' % (mid, e))
                continue
            veh = vehicle_survey(m, game)
            for base, rec in veh.items():
                if a.weapon and a.weapon.lower() not in base.lower():
                    continue
                t = totals.setdefault(base, {'placed': 0, 'maps': [], 'cls': rec['cls']})
                t['placed'] += rec['placed']
                if rec['placed']:
                    t['maps'].append('%s x%d' % (mid, rec['placed']))
                elif a.verbose:
                    t['maps'].append('%s(palette only)' % mid)
        for base, t in sorted(totals.items(), key=lambda kv: -kv[1]['placed']):
            print('   %-30s %-5s %4d placement(s)   %s'
                  % (base[:30], t['cls'], t['placed'],
                     ', '.join(t['maps'][:8]) or 'palette only, never placed'))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', help='one game; default every game')
    ap.add_argument('--map', help='one mission id')
    ap.add_argument('--weapon', help='tag basename substring, e.g. flamethrower')
    ap.add_argument('--all', action='store_true', help='list every weapon per map')
    ap.add_argument('--missing', action='store_true',
                    help="only what halo.json's mission list offers but the map cannot")
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--vehicles', action='store_true',
                    help='list the Vehicles palette instead, unfiltered -- what a '
                         'level actually places, which is how you find turrets')
    a = ap.parse_args(argv)

    if a.vehicles:
        return _vehicles_main(a)

    tool = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = json.load(open(os.path.join(tool, 'halo.json'), encoding='utf-8'))
    games = [a.game] if a.game else list(doc['Missions'])

    for game in games:
        if game not in doc['Missions']:
            print('unknown game %r' % game)
            continue
        if not _weapon_layout(game):
            print('\n=== %s: no weapon-placement layout' % game)
            continue
        print('\n=== %s' % game)
        for mid, md in doc['Missions'][game].items():
            if a.map and mid != a.map:
                continue
            path = V.resolve(game, mid)
            if not path:
                print('   %-10s map not found' % mid)
                continue
            m = HP.open_map(path, game)
            res = resident(m)
            pal = survey(m, game, res)
            if a.weapon:
                hits = sorted(n for n in set(pal) | res if a.weapon.lower() in n.lower())
                if not hits:
                    v, why = verdict(a.weapon, pal, res)
                    print('   %-10s %-9s %s' % (mid, v, why))
                for n in hits:
                    v, why = verdict(n, pal, res)
                    print('   %-10s %-26s %-9s %s' % (mid, n, v, why))
                continue
            if a.all or a.verbose:
                print('   %s (%s)' % (mid, md.get('name', '')))
                for n in sorted(set(pal) | (res if a.verbose else set())):
                    v, why = verdict(n, pal, res)
                    print('      %-30s %-9s %s' % (n, v, why))
                continue
            placed = sorted(n for n in pal if pal[n]['placed'])
            palonly = sorted(n for n in pal if not pal[n]['placed'])
            print('   %-10s placed %-2d: %s' % (mid, len(placed), ', '.join(placed)[:96]))
            if palonly:
                print('   %-10s palette-only: %s' % ('', ', '.join(palonly)[:96]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
