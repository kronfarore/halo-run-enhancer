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
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')



def arm(map_path, weapon, species, share=1.0, out=None):
    """The enhancer's own pass (h2_enemy_weapons.arm) with one card per species at `share`."""
    import halo_patch as hp
    import h2_enemy_weapons as E
    m = hp.open_map(map_path, 'Halo 2')
    if getattr(m, 'compressed', False):
        raise SystemExit('%s is compressed -- Halo2Map.save cannot write it' % map_path)
    names = {s.lower(): e for e in E.ENEMY_CHARS for s in (e, e.split()[0])}
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
    rows, done = E.arm(m, hp, cards, salt=os.path.basename(map_path))
    m.save(out or map_path)
    return idx, {e: sum(ws.values()) for e, ws in done.items()}, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('weapon')
    ap.add_argument('--species', default='elite,grunt,jackal,brute')
    ap.add_argument('--share', type=float, default=1.0)
    a = ap.parse_args()
    report(*arm(a.map, a.weapon, a.species.split(','), a.share))


def report(idx, armed, rows):
    print('   armed (palette #%d): %s' % (idx, ', '.join('%s x%d' % kv for kv in sorted(armed.items()))
                                         or 'NOTHING'))
    for r in rows:
        if r.get('skip'):
            print('   skipped: %s (%s)' % (r['field'], r['reason']))


if __name__ == '__main__':
    main()
