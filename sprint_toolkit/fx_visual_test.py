r"""In-game check of fx_visual_scale (explosion visual size), one level per game.

Builds <level>_fxscale_test.map beside the live map from the CURRENT live map (so a
patched run stays patched): the frag grenade's own detonation effects drawn x3 through
the emitter route (function copies, Halo 3 GPU rows). Halo 4 also draws the PLASMA
grenade x3 through the other route, the effect's Global Size Scale, so one boot
compares both. Damage is not touched -- only how big the explosion looks.

    python fx_visual_test.py build "Halo 3"        (fx_visual_test.cmd deploy does this)

What to look for: throw a frag (Halo 4: a plasma grenade too) and compare it with an
enemy's -- AI grenades are the same tag, so the test is the whole explosion being
about three times wider than normal. Outcomes:
  * bigger            -> the route works in that game's engine
  * normal size       -> the engine does not read what was written (Halo 3: GPU rows
                         or function copies ignored; Halo 4 GSS: the Global Size Scale)
  * crash / no fx     -> a repointed copy is not reachable (slack / partition)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import explosion_fx_audit as A  # noqa: E402
import fx_visual_scale as F  # noqa: E402

B = chr(92)
H3G = B.join(['objects', 'weapons', 'grenade', 'frag_grenade', 'fx', ''])
H4G = B.join(['objects', 'weapons', 'grenade', 'storm_frag_grenade', 'fx', ''])
H4P = B.join(['objects', 'weapons', 'grenade', 'storm_plasma_grenade', 'fx', ''])
SCALE = 3.0
TESTS = {
    'Halo 2': ('03a_oldmombasa', [([B.join(['effects', 'impact', 'explosion_small', 'frag_grenade',
                                             'airborne_detonation'])], 'emitters')]),
    'Halo 3': ('010_jungle', [([H3G + 'detonation', H3G + 'airborne_detonation'], 'emitters')]),
    'Halo 3: ODST': ('sc100', [([H3G + 'detonation', H3G + 'airborne_detonation'], 'emitters')]),
    'Halo Reach': ('m10', [([H3G + 'detonation', H3G + 'airborne_detonation'], 'emitters')]),
    'Halo 4': ('m10_crash', [([H4G + 'detonation', H4G + 'airborne_detonation'], 'emitters'),
                             ([H4P + 'detonation', H4P + 'airborne_detonation'], 'gss')]),
}


def build(game):
    lvl, jobs = TESTS[game]
    d = os.path.join(A.MCC, A.MAP_DIRS[game])
    src = os.path.join(d, lvl + '.map')
    pre = src + '.pre_fxscale'
    if os.path.exists(pre):         # a test is deployed: build from the kept live map
        src = pre
    out = os.path.join(d, lvl + '_fxscale_test.map')
    m = A.load(game, src)
    before = F.snapshot(game, m)
    for effects, mode in jobs:
        print(mode, F.Fx(game, m).scale(effects, SCALE, mode))
    m.save(out)
    after = F.snapshot(game, A.load(game, out))
    names = [e for effects, _ in jobs for e in effects]
    bad = 0
    for effects, mode in jobs:
        v = F.verify(game, {k: x for k, x in before.items() if k[0].lower() in {e.lower() for e in effects}
                            or k[0].lower() not in {n.lower() for n in names}},
                     after, effects, SCALE, mode)
        print('verify', mode, v)
        bad += v['n_problems']
    if bad:
        os.remove(out)
        raise SystemExit('verification failed -- test map removed')
    print('built', out)


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != 'build' or sys.argv[2] not in TESTS:
        raise SystemExit('usage: fx_visual_test.py build "<game>"   games: %s' % ', '.join(TESTS))
    build(sys.argv[2])
