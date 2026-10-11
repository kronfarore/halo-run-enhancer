r"""Halo 1: the CLASSIC Grunt Birthday Party confetti, `effects\grunt birthday party.effect`.

h1_birthday_party.py (halo1.dll) spawns this effect on a Grunt killed by a headshot while the
Grunt Birthday Party skull is on -- when the loaded map holds it; else the two stock fallbacks
(needle burst + plasma sparks). MCC's own confetti (`sfx_konfetti`) is Anniversary-only.

The effect is built ONLY from tags that ship with HCEEK, and has NO damage part:
  * confetti flakes in six colours: an own particle `effects\particles\solid\confetti` = a copy
    of `debris shirt` (a near-white fluttering cloth sprite on light, wind-damped point physics,
    so the effect tint gives clean colours) that lives 2.5-3.5 s and does not die at rest
  * pink needler spike debris, green plasma sparks, blue shield sparks
  * a short warm flash and the needler's detonation pop (sound)
All particles start at the Grunt's origin + 0.3 wu up (about head height), shot upward in a
wide cone; gravity and air friction bring the flakes down around the body.

In the maps: a never-called static script in sprint.hsc (`gbp_confetti_ref`) names the effect,
and global_scripts.hsc is compiled into every level, so tool's next build of each campaign map
(h1_rebuild_all.py) carries it. Nothing gameplay-side references it.

    python h1_confetti_effect.py           # dry run: print what would be written
    python h1_confetti_effect.py --write   # write the two tags into HCEEK\tags
"""
import argparse
import copy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.effe import effe_def  # noqa: E402
from reclaimer.hek.defs.part import part_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
EFFECT = r'effects\grunt birthday party'
FLAKE = r'effects\particles\solid\confetti'
FLAKE_SRC = r'effects\particles\solid\debris shirt'
TEMPLATE = r'weapons\needler\effects\needle detonate'   # structure + the pop sound
POP = r'sound\sfx\weapons\needler\expl'

UP = math.pi / 2          # relative_direction pitch: up in the Grunt's frame
HEAD = 0.3                # wu above the origin (feet)
# (particle, count, radius, velocity, cone rad, tint RGB or None = the particle's own)
COLOURS = [(1.0, 0.25, 0.6), (0.3, 1.0, 0.3), (0.25, 0.5, 1.0),
           (1.0, 0.95, 0.2), (1.0, 0.55, 0.1), (0.7, 0.3, 1.0)]
SPRAY = [(FLAKE, (6, 9), (0.02, 0.035), (1.2, 2.6), 0.9, c) for c in COLOURS] + [
    (r'effects\particles\solid\needler spike debris', (6, 10), (0.015, 0.05), (1.0, 2.2), 1.2, None),
    (r'effects\particles\energy\plasma overcharge spark', (5, 8), (0.03, 0.05), (0.8, 1.8), 1.4,
     (0.3, 1.0, 0.35)),
    (r'effects\particles\energy\shield jackal sparks', (5, 8), (0.03, 0.05), (0.8, 1.8), 1.4,
     (0.3, 0.55, 1.0)),
    (r'effects\particles\flash\flash h pistol detonate', (1, 1), (0.2, 0.25), (0.0, 0.0), 0.0,
     (1.0, 0.85, 0.4)),
]


def tag(rel, ext):
    return os.path.join(TAGS, rel + ext)


def flake(write):
    t = part_def.build(filepath=tag(FLAKE_SRC, '.particle'))
    d = t.data.tagdata
    d.flags.dies_at_rest = False
    d.lifespan[0], d.lifespan[1] = 2.5, 3.5
    d.fade_out_time = 0.6
    if write:
        t.serialize(filepath=tag(FLAKE, '.particle'), temp=False, backup=False)


def effect(write):
    t = effe_def.build(filepath=tag(TEMPLATE, '.effect'))
    d = t.data.tagdata
    locs = d.locations.STEPTREE
    del locs[1:]
    locs[0].marker_name = ''
    evs = d.events.STEPTREE
    del evs[1:]
    ev = evs[0]
    ev.delay_bounds[0] = ev.delay_bounds[1] = 0.0
    parts = ev.parts.STEPTREE
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].type.filepath != POP:
            parts.pop(i)           # the decal goes; only the pop stays
    if len(parts) != 1 or parts[0].type.tag_class.enum_name != 'sound':
        raise SystemExit('%s: no %s sound part' % (TEMPLATE, POP))
    parts[0].location = 0
    pts = ev.particles.STEPTREE
    proto = copy.deepcopy(pts[0])
    del pts[:]
    for path, n, r, v, cone, tint in SPRAY:
        pts.append(copy.deepcopy(proto))
        q = pts[len(pts) - 1]
        q.particle_type.filepath = path
        q.location = 0
        q.relative_direction[0], q.relative_direction[1] = 0.0, UP
        q.relative_offset.i, q.relative_offset.j, q.relative_offset.k = 0.0, 0.0, HEAD
        q.created_count[0], q.created_count[1] = n
        q.distribution_radius[0], q.distribution_radius[1] = 0.02, 0.05
        q.velocity[0], q.velocity[1] = v
        q.velocity_cone_angle = cone
        q.radius[0], q.radius[1] = r
        q.flags.tint_as_hsv = False
        for bd in (q.tint_lower_bound, q.tint_upper_bound):
            bd.a = 1.0
            bd.r, bd.g, bd.b = tint or (1.0, 1.0, 1.0)
    bad = [p.type.filepath for e in d.events.STEPTREE for p in e.parts.STEPTREE
           if p.type.tag_class.enum_name == 'damage_effect']
    if bad:
        raise SystemExit('damage parts left: %s' % bad)
    for e in d.events.STEPTREE:
        for p in e.parts.STEPTREE:
            print('  part      %-14s %s' % (p.type.tag_class.enum_name, p.type.filepath))
        for q in e.particles.STEPTREE:
            print('  particle  %-48s x%d-%d  tint %s' % (q.particle_type.filepath, q.created_count[0],
                  q.created_count[1], tuple(round(x, 2) for x in (q.tint_lower_bound.r,
                  q.tint_lower_bound.g, q.tint_lower_bound.b))))
    if write:
        t.serialize(filepath=tag(EFFECT, '.effect'), temp=False, backup=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--write', action='store_true', help='write the tags (default: dry run)')
    a = ap.parse_args()
    for rel in (TEMPLATE, FLAKE_SRC) + tuple(p for p, *_ in SPRAY if p != FLAKE):
        ext = '.effect' if rel == TEMPLATE else '.particle'
        if not os.path.isfile(tag(rel, ext)):
            raise SystemExit('missing source tag: %s%s' % (rel, ext))
    flake(a.write)
    print(('wrote ' if a.write else 'would write ') + FLAKE + '.particle')
    print(('wrote ' if a.write else 'would write ') + EFFECT + '.effect')
    effect(a.write)


if __name__ == '__main__':
    main()
