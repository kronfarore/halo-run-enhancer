r"""Spawn-count test maps: multiply the counts of every squad a Spawn Count card would grow.

Uses enemy_count's own squad reading and growth (grow_all: one slack reservation for
every Halo 3 block) (counts + copied on-foot locations), so the
test exercises the patcher's code; only the share is fixed per squad (x --mult) instead of
a percentage spread over the level. Squads that spawn by script or into a vehicle, bosses,
vehicle squads and the other side are left alone -- exactly the cards' exclusions.

    python squad_count_test.py --game "Halo 1" --map <map> --show
    (Halo 3: `normal` = fire-teams playing on Normal, `insane` = Legendary-only teams)
    python squad_count_test.py --game "Halo 1" --map <in> --out <out> --mult 2 [--side ally]
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import enemy_count as ec  # noqa: E402
import halo_patch as hp  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('--map', required=True)
    ap.add_argument('--out')
    ap.add_argument('--mult', type=float, default=2.0)
    ap.add_argument('--side', default='enemy', choices=('enemy', 'ally'))
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()
    m = hp.open_map(a.map, a.game)
    rows = ec.squads(m, a.game)
    side = [s for s in rows if s[a.side] and s['chars']]
    grow = [s for s in side if not s['vehicle'] and not s['boss'] and ec._takes_extras(s)]
    why = {'vehicle squad': lambda s: s['vehicle'], 'boss/story': lambda s: s['boss'],
           'spawns by script': lambda s: s['script'], 'put into a vehicle': lambda s: s['bound'],
           'never placed': lambda s: not s['placed'], 'count 0 / no locations':
           lambda s: s['foot'] <= 0 or (s['normal'] <= 0 and s['insane'] <= 0)}
    print('%d squads, %d on the %s side, %d to grow' % (len(rows), len(side), a.side, len(grow)))
    for k, f in why.items():
        hit = [s['name'] for s in side if s not in grow and f(s)]
        if hit:
            print('  left alone (%s): %d  %s' % (k, len(hit), ', '.join(hit[:6]) + (' ...' if len(hit) > 6 else '')))
    before, after, plan = [0, 0], [0, 0], []
    for s in grow:
        sp = '+'.join(sorted({ec.species(c) for c in s['chars']}))
        n = int(math.ceil(s['normal'] * a.mult)) if s['normal'] > 0 else 0
        i = int(math.ceil(s['insane'] * a.mult)) if s['insane'] > 0 else 0
        before[0] += max(s['normal'], 0)
        before[1] += max(s['insane'], 0)
        after[0] += n
        after[1] += i
        if a.show:
            print('  %-44s %-26s normal %2d insane %2d locs %2d' % (s['name'], sp, s['normal'], s['insane'], s['locs']))
            continue
        plan.append((s, n, i))
        print('  %-44s %-26s normal %2d->%2d insane %2d->%2d locs %2d' % (
            s['name'], sp, s['normal'], n, s['insane'], i, s['locs']))
    added = 0 if a.show else ec.grow_all(m, a.game, plan)
    print('actors (grown squads): normal %d -> %d, insane %d -> %d, %d new locations' % (
        before[0], after[0], before[1], after[1], added))
    if a.show:
        return
    if not a.out:
        sys.exit('--out is required to write')
    m.save(a.out)
    print('written:', a.out)


if __name__ == '__main__':
    main()
