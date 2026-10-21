r"""Hand a port to Halo 2 ENEMIES in a built map -- the Armed test (H2_PORT_PLAN.md 0.5b).

Which weapon a Halo 2 squad spawns with is the scenario's: squad Initial Weapon / Initial
Secondary (+0x3C / +0x3E) and each starting location's own pair (+0x22 / +0x24) are int16
indices into the scnr Weapon Palette (+0x98, element 0x28; tagref datum at +0x4). This
rewrites them, for every squad unit whose character is one of the named species, to the
port's palette index (secondary -1) -- the shape halo_patch's Thunderstorm pass already writes
(_TS_LAYOUT['Halo 2'], _ts_units: vehicle-bound / script-loaded squads stay as they are).
`--share` < 1 arms a deterministic fraction (the enhancer card's 'Weapon share %'). It runs the
enhancer's own pass, h2_enemy_weapons.arm (tool root), with one card per species.
Species: elite, grunt, jackal, brute, flood (Flood Combat Form), marine.
The FIRING data is not touched here: it is in the kit's ai\generic (h2_ai_firing.py).

    python h2_armed_test.py <built map> <weapon tag> --species elite,grunt,jackal [--share 1]
    (h2_port_test_map.py <key> --armed elite,grunt,jackal runs it on the test map)
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


# the player's damage pool in Halo 2 = the MODEL (hlmt New Damage Info +0x60, 0xF8; memory
# halo-player-vitality-and-hud): Maximum Vitality +0x28, Maximum Shield Vitality +0x8C, shield
# Stun Time +0x98, shield Recharge Time +0x9C
PLAYER_MODELS = ('objects\\characters\\masterchief\\masterchief',
                 'objects\\characters\\dervish\\dervish')
HLMT_DAMAGE, HLMT_DAMAGE_ES = 0x60, 0xF8
GOD = ((0x28, 1e6), (0x8C, 1e6), (0x98, 0.0), (0x9C, 0.1))


def god_shield(m):
    """THE GOD SHIELD on every port test (user, Halo 1 2026-10-09: 'an increased shield in all
    the port testing'): the player models' body + shield 1e6, no shield stun, 0.1 s recharge."""
    out = []
    for path in PLAYER_MODELS:
        for _n, t in m.find_tags('hlmt', path):
            for e in m.follow_all(t, [HLMT_DAMAGE], [HLMT_DAMAGE_ES], 'all')[:1]:
                for off, v in GOD:
                    struct.pack_into('<f', m.data, e + off, v)
                out.append(path.rsplit(chr(92), 1)[-1])
    return out


#: the base character each enemy type is replaced with for the Armed test (must be in the level's
#: Character Palette -- a character absent there cannot be added at patch time)
_C = 'objects' + chr(92) + 'characters' + chr(92)
BASE_CHAR = {'Grunt': 'grunt', 'Jackal': 'jackal', 'Elite': 'elite', 'Brute': 'brute', 'Bugger': 'bugger',
             'Flood Combat Form': 'floodcombat_elite', 'Marine': 'marine'}
PER_SPECIES = 2


def replace_start(m, hp, enemies):
    """THE ARMED TEST LAYOUT (user, 2026-10-21: 'replace enemies to test them all quickly at the
    start'; memory halo-test-enemy-placement): the enemy squads nearest the first player starting
    location (on foot: no vehicle) become the tested types, round robin, PER_SPECIES squads each --
    the squad's character, every location's own character, location variants cleared (a variant
    is per species). Story characters, bosses, Hunters and Sentinels are never touched."""
    import math
    import h2_enemy_weapons as E
    base = hp._scnr_base(m)
    ps = m.follow_all(base, [0x100], [0x34], 'all')
    if not ps:
        return []
    p0 = struct.unpack_from('<fff', m.data, ps[0])
    cp = m.follow_all(base, [0x178], [0x8], 'all')
    cnames = [(hp._tag_name_by_id(m, m.u32(e + 4)) or '') for e in cp]
    want = []
    for e in enemies:
        path = '%s%s%sai%s%s' % (_C, BASE_CHAR.get(e, '?'), chr(92), chr(92), BASE_CHAR.get(e, '?'))
        idx = next((i for i, n in enumerate(cnames) if n.lower() == path.lower()), None)
        want.append((e, idx))
    usable = [(e, i) for e, i in want if i is not None]
    cands = []
    for sq in m.follow_all(base, [0x160], [0x74], 'all'):
        if struct.unpack_from('<h', m.data, sq + 0x34)[0] >= 0:
            continue                                        # spawns in a vehicle
        locs = m.follow_all(sq, [0x48], [0x64], 'all')
        if not locs:
            continue
        chars = [struct.unpack_from('<h', m.data, sq + 0x36)[0]] + \
            [struct.unpack_from('<h', m.data, l + 0x20)[0] for l in locs]
        chars = [c for c in chars if c >= 0]
        if not chars or not all(E.enemy_of(cnames[c]) for c in chars):
            continue
        d = min(math.dist(p0, struct.unpack_from('<fff', m.data, l + 4)) for l in locs)
        cands.append((d, sq, locs))
    cands.sort(key=lambda x: x[0])
    rows, k = [], 0
    for d, sq, locs in cands[:PER_SPECIES * len(usable)]:
        e, ci = usable[k % len(usable)]
        k += 1
        struct.pack_into('<h', m.data, sq + 0x36, ci)
        for l in locs:
            if struct.unpack_from('<h', m.data, l + 0x20)[0] >= 0:
                struct.pack_into('<h', m.data, l + 0x20, ci)
            struct.pack_into('<I', m.data, l + 0x30, 0)
        nm = m.data[sq:sq + 0x20].split(b'\0')[0].decode('latin-1')
        rows.append({'tag': 'scnr squads', 'field': 'Test layout: %s' % nm, 'ok': True,
                     'reason': '-> %s (%.0f wu from the start, %d locations)' % (e, d, len(locs))})
    for e, i in want:
        if i is None:
            rows.append({'tag': 'scnr squads', 'field': 'Test layout: %s' % e, 'ok': True, 'skip': True,
                         'reason': 'not in this level\'s character palette'})
    return rows


def test_map(map_path, weapon=None, species=(), share=1.0, balanced=True, god=True, replace=True):
    """One open + save of a built test map: the Armed pass (if species; the nearest squads first
    replaced by the tested types unless replace=False) and the god shield."""
    import halo_patch as hp
    m = hp.open_map(map_path, 'Halo 2')
    if getattr(m, 'compressed', False):
        raise SystemExit('%s is compressed -- Halo2Map.save cannot write it' % map_path)
    res = arm(map_path, weapon, species, share, balanced=balanced, m=m, replace=replace) \
        if species else None
    if god:
        print('   god shield (player body + shield 1e6, no stun): %s' % (', '.join(god_shield(m)) or 'NO player model found'))
    m.save(map_path)
    if res:
        report(*res)


def arm(map_path, weapon, species, share=1.0, out=None, balanced=True, m=None, replace=False):
    """The enhancer's own pass (h2_enemy_weapons.apply: arming, shieldless Jackals, the Grunt
    teach + half rate, Balanced AI rows) with one card per species at `share`. Balanced by
    default: an Armed test runs the balanced numbers (memory h1-armed-test-balanced-god)."""
    import halo_patch as hp
    import h2_enemy_weapons as E
    own = m is None
    if own:
        m = hp.open_map(map_path, 'Halo 2')
        if getattr(m, 'compressed', False):
            raise SystemExit('%s is compressed -- Halo2Map.save cannot write it' % map_path)
    names = {s.lower(): e for e in E.ENEMY_CHARS for s in (e, e.split()[0])}
    names.update({'drone': 'Bugger', 'drones': 'Bugger', 'flood': 'Flood Combat Form'})
    cards = {}
    for s in species:
        e = names.get(s.strip().lower())
        if not e:
            raise SystemExit('unknown species %r (have %s)' % (s, ', '.join(E.ENEMY_CHARS)))
        cards[e] = {weapon: share}
    wnames = E.palette(m, hp, hp._scnr_base(m))
    idx = next((i for i, n in enumerate(wnames) if (n or '').lower() == weapon.lower()), None)
    if idx is None:
        raise SystemExit('%s is not in the weapon palette of %s' % (weapon, map_path))
    sys.path.insert(0, HERE)
    import ai_firing_profile as A
    layout = replace_start(m, hp, list(cards)) if replace else []
    rows = layout + E.apply(m, hp, {'cards': cards, 'balanced': [weapon] if balanced else []},
                   registry=A._plugins()('Halo 2'), salt=os.path.basename(map_path))
    if own:
        m.save(out or map_path)
    return idx, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('weapon')
    ap.add_argument('--species', default='elite,grunt,jackal,brute')
    ap.add_argument('--share', type=float, default=1.0)
    ap.add_argument('--default', action='store_true', help='the default AI numbers, not Balanced')
    a = ap.parse_args()
    report(*arm(a.map, a.weapon, a.species.split(','), a.share, balanced=not a.default))


def report(idx, rows):
    print('   the port is weapon palette #%d' % idx)
    for r in rows:
        who = r['tag'].rsplit(chr(92), 1)[-1] if r['field'].startswith('Armed') else ''
        print('   %s %-40s %s' % ('SKIP' if r.get('skip') else 'ok  ' if r.get('ok') else 'FAIL',
                                  (r['field'] + (' (%s)' % who if who else ''))[:40], r.get('reason', '')))


if __name__ == '__main__':
    main()
