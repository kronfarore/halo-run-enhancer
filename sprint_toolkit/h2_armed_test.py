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
             'Flood Combat Form': 'floodcombat_elite', 'Marine': 'marine',
             'Sentinel': 'sentinel_aggressor'}
PER_SPECIES = 2


def replace_start(m, hp, enemies):
    """THE ARMED TEST LAYOUT (user, 2026-10-21: 'replace enemies to test them all quickly at the
    start'; memory halo-test-enemy-placement): the enemy squads nearest the first player starting
    location (on foot: no vehicle) become the tested types, round robin PER STARTING LOCATION until
    each has PER_SPECIES units --
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
    friends, char_team = E.side_of(m, hp, cp, hp._BETRAYAL['Halo 2'])
    cands = []
    for sq in m.follow_all(base, [0x160], [0x74], 'all'):
        if struct.unpack_from('<h', m.data, sq + 0x34)[0] >= 0:
            continue                                        # spawns in a vehicle
        team = struct.unpack_from('<h', m.data, sq + 0x24)[0]
        sc = struct.unpack_from('<h', m.data, sq + 0x36)[0]
        if team <= 0 and 0 <= sc < len(char_team):
            team = char_team[sc]
        if team in friends:
            continue                                        # the player's side (Arbiter levels)
        locs = m.follow_all(sq, [0x48], [0x64], 'all')
        if not locs:
            continue
        chars = [struct.unpack_from('<h', m.data, sq + 0x36)[0]] + \
            [struct.unpack_from('<h', m.data, l + 0x20)[0] for l in locs]
        chars = [c for c in chars if c >= 0]
        if not chars or not all(E.enemy_of(cnames[c]) for c in chars):
            continue
        d = min(math.dist(p0, struct.unpack_from('<fff', m.data, l + 4)) for l in locs)
        cands.append((d, sq, locs, team))
    cands.sort(key=lambda x: x[0])
    # PER LOCATION, not per squad (the AR pilot, 2026-10-21 -- 04a's first --armed all: whole
    # squads by distance gave the Brutes / Jackals / Drones squads the level's script places LATER,
    # and the user met only Elites and Grunts): the species are dealt round robin over the
    # STARTING LOCATIONS of the nearest squads, so the first squads to spawn carry the mix; every
    # location's character is written (one left at -1 would fall back to the squad's)
    rows, k, need = [], 0, PER_SPECIES * len(usable)
    for d, sq, locs, team in cands:
        if k >= need:
            break
        got = []
        for l in locs:
            e, ci = usable[k % len(usable)]
            if k == 0 or not got:
                struct.pack_into('<h', m.data, sq + 0x36, ci)
            struct.pack_into('<h', m.data, l + 0x20, ci)
            struct.pack_into('<I', m.data, l + 0x30, 0)
            got.append(e)
            k += 1
        # keep the squad on ITS side: a Team of 0 means 'the character's team', so a hostile
        # Sentinel squad turned into Elites would join the Arbiter -- write the team it had
        if team is not None and team > 0:
            struct.pack_into('<h', m.data, sq + 0x24, team)
        nm = m.data[sq:sq + 0x20].split(b'\0')[0].decode('latin-1')
        rows.append({'tag': 'scnr squads', 'field': 'Test layout: %s' % nm, 'ok': True,
                     'reason': '-> %s (%.0f wu from the start)' % (', '.join(got), d)})
    for e, i in want:
        if i is None:
            rows.append({'tag': 'scnr squads', 'field': 'Test layout: %s' % e, 'ok': True, 'skip': True,
                         'reason': 'not in this level\'s character palette'})
    return rows


CHEAT_DAMAGE = 'objects\\weapons\\rifle\\covenant_carbine\\damage_effects\\carbine_slug'
CHEAT_DAMAGE_X, CHEAT_SPEED_X = 1000.0, 2.0
CHEAT_DAMAGE_FIELDS = ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')
CHEAT_SPEED_FIELDS = ('Run Forward', 'Run Backward', 'Run Sideways', 'Run Acceleration',
                      'Sneak Forward', 'Sneak Backward', 'Sneak Sideways', 'Sneak Acceleration')


def _scale(m, tag, plugin, field, block, index, x):
    """Multiply one float field (plugin offsets, block element `index`); returns (old, new) or None."""
    fld = plugin.find(field, block, 0)
    if not fld:
        return None
    base = m.follow(tag, fld['block_offsets'], fld.get('block_sizes'), index) if fld['block_offsets'] else tag
    if base is None:
        return None
    v = struct.unpack_from('<f', m.data, base + fld['offset'])[0]
    struct.pack_into('<f', m.data, base + fld['offset'], v * x)
    return v, v * x


def cheat_map(m):
    """The Armed-test cheat (h2_port_test_map.CHEAT_WEAPON): the Carbine's slug damage x1000 and
    the player's matg Player Information run / sneak speeds + accelerations x2 (the 'Speed and
    Acceleration' card's fields, every element)."""
    sys.path.insert(0, HERE)
    import ai_firing_profile as A
    reg = A._plugins()('Halo 2')
    out = []
    jpt, matg = reg.get('jpt!'), reg.get('matg')
    for _n, t in m.find_tags('jpt!', CHEAT_DAMAGE):
        r = [_scale(m, t, jpt, f, None, 0, CHEAT_DAMAGE_X) for f in CHEAT_DAMAGE_FIELDS]
        out.append('carbine_slug damage %s' % ', '.join('%.3g -> %.4g' % x for x in r if x))
    for _n, t in m.find_tags('matg', 'globals' + chr(92) + 'globals'):
        n = m.i32(t + matg.find('Run Forward', 'Player Information', 0)['block_offsets'][0])
        for k in range(max(0, n)):
            r = [_scale(m, t, matg, f, 'Player Information', k, CHEAT_SPEED_X) for f in CHEAT_SPEED_FIELDS]
            run = r[0]
            out.append('player run x%g (Player Information #%d: run forward %.3g -> %.3g)'
                       % (CHEAT_SPEED_X, k, run[0], run[1]) if run else 'Player Information #%d: ?' % k)
    return out


def port_balance(m, weapon, balanced=True):
    """THE BALANCE SETTING on every port test (user 2026-10-22: 'This should be part of the normal
    test process'): the port's catalog entry through the enhancer's own path --
    weapon_ports.active_ports (Balanced on, or off = each row's `original`) into
    halo_patch.apply_weapon_ports (balance rows, ammo pick, animation retiming). The kit's tags
    hold the source game's own numbers, so without this no boot ever plays the Balanced weapon."""
    import halo_patch as hp
    import weapon_ports as W
    sys.path.insert(0, HERE)
    import ai_firing_profile as A
    port = next((p for p in W.ports_for('Halo 2')
                 if (W.weap_path(p) or '').lower() == (weapon or '').lower()), None)
    if port is None:
        return None
    cfg = {'weapon_ports': {'Halo 2': {port['weapon']: {'enabled': True, 'balanced': balanced}}}}
    entries = [e for e in W.active_ports('Halo 2', cfg) if e.get('weapon') == port['weapon']]
    return hp.apply_weapon_ports(m, 'Halo 2', A._plugins()('Halo 2'), entries)


def test_map(map_path, weapon=None, species=(), share=1.0, balanced=True, god=True, replace=True,
             cheat=False, also=()):
    """One open + save of a built test map: the port's Balanced (or Original) numbers, the Armed
    pass (if species; the nearest squads first replaced by the tested types unless
    replace=False) and the god shield."""
    import halo_patch as hp
    m = hp.open_map(map_path, 'Halo 2')
    if getattr(m, 'compressed', False):
        raise SystemExit('%s is compressed -- Halo2Map.save cannot write it' % map_path)
    if weapon:
        rows = port_balance(m, weapon, balanced)
        if rows is None:
            print("   %s: no catalog entry -- the kit's own numbers (no Balanced / Original test)" % weapon)
        for r in rows or ():
            print('   %s: %s %s -> %s%s' % ('BALANCED' if balanced else 'ORIGINAL', r.get('field'),
                                          r.get('old'), r.get('new'),
                                          '' if r.get('ok') else '  NOT OK: %s' % r.get('reason')))
    for w in also:              # another port in the player's hands (h2_port_test_map --secondary)
        for r in port_balance(m, w, balanced) or ():
            print('   %s %s: %s %s -> %s' % (w.rsplit(chr(92), 1)[-1], 'BALANCED' if balanced else 'ORIGINAL',
                                         r.get('field'), r.get('old'), r.get('new')))
    res = arm(map_path, weapon, species, share, balanced=balanced, m=m, replace=replace) \
        if species else None
    if god:
        print('   god shield (player body + shield 1e6, no stun): %s' % (', '.join(god_shield(m)) or 'NO player model found'))
    if cheat:
        print('   cheat: %s' % ('; '.join(cheat_map(m)) or 'NOTHING written (no carbine_slug / matg?)'))
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
