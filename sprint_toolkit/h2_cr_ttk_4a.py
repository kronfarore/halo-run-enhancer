"""Step 4a / 5b for the Halo 2 CONCUSSION RIFLE (B5, 2026-11-26): direct hits = impact + the full blast (the core),
Halo 2 legendary, each part through its own damage group, shield first (h2_gl_ttk_4a.py's model; h2_role_compare
counts impact damage only). The pace of fire is Halo 2's 30 Hz reset rule on a recovery-limited latch: a shot every
ceil(recovery x 30) ticks, a reload whenever the magazine empties. Cited by reports/h2_concussion_rifle_4a.md.

    python h2_cr_ttk_4a.py"""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ttk_halo2 as t2
import h2_role_compare as rc

g = t2.Globals({})
T = rc.enemies(g)

GROUPS = ('collision', 'plasma_fast', 'plasma_slow', 'explosion_large', 'explosion_largw', 'explosion_small',
          'bullet_fast')
for label, sh, bo, shm, bom in T:
    print('%-12s shield %6.1f (%s)  body %6.1f (%s)' % (label, sh, shm, bo, bom))
    for grp in GROUPS:
        known = '' if grp in g.table else '   (no such group in matg: x1 everywhere)'
        print('     %-16s shield x%-6g body x%g%s' % (grp, g.multiplier((grp,), shm)[0] if shm else 0,
                                                       g.multiplier((grp,), bom)[0], known))

# the Hunter: every material of its model, by group (Halo 1's B5 rule: Hunters a yardstick makes immune)
hm = t2.Tag(r'objects\characters\hunter\hunter.model', {})
print('\nHunter materials (model):')
for i in range(hm.count('materials')):
    m = hm.s('materials/[%d]/global material name' % i, False)
    n = hm.s('materials/[%d]/material name' % i, False)
    print('   %-22s %-24s ' % (n, m) + '  '.join('%s x%g' % (grp, g.multiplier((grp,), m)[0])
                                                for grp in ('collision', 'plasma_fast', 'explosion_large',
                                                            'explosion_small')))

# (name, impact, impact group, blast, blast group, recovery s, magazine, reload s)
SETS = [
    ('Reach own (Original)', 21.5, 'collision', 21.5, 'plasma_fast', 1 / 3., 6, 100 / 30.),
    ('Fuel Rod ratio (prov.)', 21.5, 'collision', 32.25, 'plasma_fast', 1 / 3., 6, 5.0 * 100 / 90.),
    ('Fuel Rod ratio, H2 grp', 21.5, 'explosion_large', 32.25, 'explosion_large', 1 / 3., 6, 5.0 * 100 / 90.),
    ('Rocket ratio', 16.125, 'collision', 17.92, 'plasma_fast', 1 / 3., 6, 5.0 * 100 / 116.),
    ('Plasma Grenade ratio', 0.0, 'collision', 10.32, 'plasma_fast', 1 / 3., 6, 100 / 30.),
    ('Fuel Rod (H2, peer)', 100, 'explosion_large', 90, 'explosion_largw', 0.4, 5, 5.0),
    ('Rocket (H2, peer)', 150, 'explosion_large', 200, 'explosion_large', 0.8, 2, 5.0),
    ('Brute Shot (H2, peer)', 20, 'bullet_fast', 50, 'explosion_small', 0.3, 4, 2.0),
]


def shots(sh, bo, shm, bom, parts):
    """parts: [(damage, group)] per shot; shield first, the overflow does not carry (Halo 2)."""
    n, s, b = 0, sh, bo
    while n < 80:
        n += 1
        for d, grp in parts:
            if s > 0 and shm:
                s -= d * g.multiplier((grp,), shm)[0]
                if s > 0:
                    continue
                s = 0
                continue
            b -= d * g.multiplier((grp,), bom)[0]
        if b <= 0:
            return n
    return None


def seconds(n, rec, mag, reload_s):
    """the first shot at t 0; a shot every ceil(rec x 30) ticks; a reload after each full magazine."""
    if n is None:
        return None
    step = math.ceil(round(rec * 30.0, 6)) / 30.0
    reloads = (n - 1) // mag
    return (n - 1 - reloads) * step + reloads * reload_s


print()
print('%-26s' % 'direct hits to kill' + ''.join('%16s' % t[0] for t in T))
for name, imp, ig, bl, bg, rec, mag, rl in SETS:
    parts = [(imp, ig), (bl, bg)]
    cells = []
    for _, sh, bo, shm, bom in T:
        n = shots(sh, bo, shm, bom, parts)
        t = seconds(n, rec, mag, rl)
        cells.append('%s / %s' % (n, '%.2f s' % t if t is not None else '-'))
    print('%-26s' % name + ''.join('%16s' % c for c in cells))
print('\npace: a shot every ceil(recovery x 30) ticks (0.333 s -> 10 ticks = 3.0/s; 0.4 -> 12 = 2.5/s; 0.8 -> 24;'
      ' 0.3 -> 9); a reload after each full magazine')
