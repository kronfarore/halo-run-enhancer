"""Step 4a / 5b for the Halo 2 GRENADE LAUNCHER (B4, 2026-11-24): direct hits = impact + the full blast (the core),
Halo 2 legendary, each part through its own damage group, shield first. h2_role_compare counts impact damage only
(its stated assumption: no splash), so an explosive port's blast is read here. Cited by
reports/h2_grenade_launcher_4a.md and reports/h2_grenade_launcher_5b.txt.

    python h2_gl_ttk_4a.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ttk_halo2 as t2
import h2_role_compare as rc

g = t2.Globals({})
T = rc.enemies(g)
for label, sh, bo, shm, bom in T:
    print('%-12s shield %6.1f (%s)  body %6.1f (%s)' % (label, sh, shm, bo, bom))
    for grp in ('explosion_small', 'explosion_large', 'collision', 'bullet_fast', 'emp'):
        print('     %-16s shield x%-5g body x%g' % (grp, g.multiplier((grp,), shm)[0] if shm else 0,
                                                     g.multiplier((grp,), bom)[0]))

# (name, impact, impact group, blast, blast group, seconds between shots)
SETS = [
    ('Reach own (Original)', 25, 'collision', 180, 'explosion_small', None),
    ('Frag + RL holes (prov.)', 18.75, 'collision', 168.75, 'explosion_small', None),
    ('Rocket Launcher ratio', 18.75, 'collision', 150, 'explosion_small', None),
    ('Brute Shot (H2, peer)', 20, 'bullet_fast', 50, 'explosion_small', 0.3),
    ('Rocket (H2, peer)', 150, 'explosion_large', 200, 'explosion_large', 0.8),
    ('Fuel Rod (H2, peer)', 100, 'explosion_large', 90, 'explosion_large', 0.4),
    ('Frag grenade (H2)', 0, 'collision', 150, 'explosion_small', None),
]


def shots(sh, bo, shm, bom, parts):
    """parts: [(damage, group)] per shot; shield first, the overflow does not carry (Halo 2)."""
    n, s, b = 0, sh, bo
    while n < 50:
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


print()
print('%-26s' % 'direct hits to kill' + ''.join('%14s' % t[0] for t in T))
for name, imp, ig, bl, bg, _ in SETS:
    parts = [(imp, ig), (bl, bg)]
    print('%-26s' % name + ''.join('%14s' % shots(sh, bo, shm, bom, parts) for _, sh, bo, shm, bom in T))
