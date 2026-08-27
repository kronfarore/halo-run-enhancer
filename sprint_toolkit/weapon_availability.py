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
# the two cannot drift; the rest are read off the scnr plugin. Every block's PALETTE
# sits 0xC after it, and a placement's first int16 is its palette index.
# Only VEHICLES beyond the weapon list: that is where detached turrets live. Scenery
# and Crates carry hundreds of props and would bury the answer in furniture.
_EXTRA = {
    'Halo 3': {'Vehicles': (0xE4, 0xA8)},
    'Halo 3: ODST': {'Vehicles': (0x100, 0xA8)},
    'Halo Reach': {'Vehicles': (0x12C, 0xD0)},
}
# Reach is missing from _MAP_WEAPONS (nothing had needed to swap its weapons yet).
_REACH_WEAPONS = {'weapons': (0x15C, 0xD0), 'palette': (0x168, 0x10), 'pal_id_at': 0xC,
                  'palette_index': 0x0}
PAL_DELTA = 0xC


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
    for name, (off, elem) in (_EXTRA.get(game) or {}).items():
        blocks[name] = (off, elem, off + PAL_DELTA, 0x10, 0xC, 0x0)
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', help='one game; default every game')
    ap.add_argument('--map', help='one mission id')
    ap.add_argument('--weapon', help='tag basename substring, e.g. flamethrower')
    ap.add_argument('--all', action='store_true', help='list every weapon per map')
    ap.add_argument('--missing', action='store_true',
                    help="only what halo.json's mission list offers but the map cannot")
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args(argv)

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
