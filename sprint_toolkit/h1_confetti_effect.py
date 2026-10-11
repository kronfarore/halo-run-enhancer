r"""Halo 1: the CLASSIC Grunt Birthday Party confetti, `effects\grunt birthday party.effect`.

h1_birthday_party.py (halo1.dll) spawns this effect on a Grunt killed by a headshot while the
Grunt Birthday Party skull is on -- when the loaded map holds it; else the two stock fallbacks
(needle burst + plasma sparks). MCC's own confetti (`sfx_konfetti`) is Anniversary-only.

The effect is built ONLY from tags that ship with HCEEK, and has NO damage part. Its BASE is
the plasma grenade's explosion, which DOES show on a dead Grunt spawned at the object origin
(in game 2026-10-11; small spark effects like `charged bolt sparks` did not):
  * its two damage parts and the decal removed; its particle system x0.7 recoloured pink and
    its light warm, as own copies (`effects\particle systems\grunt birthday party`,
    `effects\lights\grunt birthday party`); the boom swapped for the needler's pop
  * BIG confetti flakes in six colours: an own particle `effects\particles\solid\confetti` =
    a copy of `debris shirt` (a near-white fluttering cloth sprite on light, wind-damped point
    physics, so the effect tint gives clean colours) that lives 2.5-3.5 s and does not die at
    rest; half go up in a cone, half in every direction
  * pink needler spike debris, green plasma sparks, blue shield sparks, all large
All particles carry their own velocity and spread (no impact normal) and start at the
Grunt's origin + 0.3 wu (about head height).

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
from reclaimer.hek.defs.pctl import pctl_def  # noqa: E402
from reclaimer.hek.defs.ligh import ligh_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
EFFECT = r'effects\grunt birthday party'
FLAKE = r'effects\particles\solid\confetti'
FLAKE_SRC = r'effects\particles\solid\debris shirt'
# the BASE: the plasma grenade's explosion, which DOES show on a dead Grunt spawned at the
# object origin (measured in game 2026-10-11; the small spark effects did not). Its two
# damage parts and the decal go; its particle system and light become own recoloured copies.
BASE = r'weapons\plasma grenade\effects\explosion'
BASE_PCTL = r'weapons\plasma grenade\effects\explosion'
BASE_LIGHT = r'weapons\plasma grenade\explosion'
OWN_PCTL = r'effects\particle systems\grunt birthday party'
OWN_LIGHT = r'effects\lights\grunt birthday party'
PROTO = r'weapons\needler\effects\needle detonate'     # a particle entry to copy
POP = r'sound\sfx\weapons\needler\expl'                # the boom becomes the needler's pop
DROP = ('damage_effect', 'decal')

BURST_SCALE = 0.7                                      # the plasma fireball, a bit smaller
BURST_ARGB = (1.0, 1.0, 0.3, 0.75)                     # ... and party pink
LIGHT_RGB = (1.0, 0.8, 0.4)                            # a warm flash

UP = math.pi / 2          # relative_direction pitch: up in the Grunt's frame
HEAD = 0.3                # wu above the origin (feet)
COLOURS = [(1.0, 0.25, 0.6), (0.3, 1.0, 0.3), (0.25, 0.5, 1.0),
           (1.0, 0.95, 0.2), (1.0, 0.55, 0.1), (0.7, 0.3, 1.0)]
# (particle, count, radius, velocity, cone rad, tint RGB or None = the particle's own).
# BIG and self-contained (visible from a few metres): own velocity and spread, no impact
# normal. Half the flakes go up in a cone, half in every direction (whatever the frame).
SPRAY = ([(FLAKE, (10, 14), (0.05, 0.08), (2.0, 3.5), 1.2, c) for c in COLOURS] +
         [(FLAKE, (6, 9), (0.05, 0.08), (1.5, 3.0), math.pi, c) for c in COLOURS] + [
    (r'effects\particles\solid\needler spike debris', (10, 14), (0.04, 0.09), (1.5, 3.0), 1.4, None),
    (r'effects\particles\energy\plasma overcharge spark', (8, 12), (0.07, 0.12), (1.5, 3.0), math.pi,
     (0.3, 1.0, 0.35)),
    (r'effects\particles\energy\shield jackal sparks', (8, 12), (0.07, 0.12), (1.5, 3.0), math.pi,
     (0.3, 0.55, 1.0)),
])


def tag(rel, ext):
    return os.path.join(TAGS, rel + ext)


def save(t, rel, ext, write):
    if write:
        os.makedirs(os.path.dirname(tag(rel, ext)), exist_ok=True)
        t.serialize(filepath=tag(rel, ext), temp=False, backup=False)


def flake(write):
    t = part_def.build(filepath=tag(FLAKE_SRC, '.particle'))
    d = t.data.tagdata
    d.flags.dies_at_rest = False
    d.lifespan[0], d.lifespan[1] = 2.5, 3.5
    d.fade_out_time = 0.6
    save(t, FLAKE, '.particle', write)


def burst(write):
    t = pctl_def.build(filepath=tag(BASE_PCTL, '.particle_system'))
    for pt in t.data.tagdata.particle_types.STEPTREE:
        pt.radius *= BURST_SCALE
        for st in pt.particle_states.STEPTREE:
            st.scale[0], st.scale[1] = st.scale[0] * BURST_SCALE, st.scale[1] * BURST_SCALE
            for blk in (st.color_1, st.color_2):
                blk.a, blk.r, blk.g, blk.b = BURST_ARGB
    save(t, OWN_PCTL, '.particle_system', write)


def light(write):
    t = ligh_def.build(filepath=tag(BASE_LIGHT, '.light'))
    c = t.data.tagdata.color
    for bd in (c.color_lower_bound, c.color_upper_bound):
        if bd.r or bd.g or bd.b:
            bd.r, bd.g, bd.b = LIGHT_RGB
    save(t, OWN_LIGHT, '.light', write)


def effect(write):
    t = effe_def.build(filepath=tag(BASE, '.effect'))
    d = t.data.tagdata
    proto = copy.deepcopy(effe_def.build(filepath=tag(PROTO, '.effect'))
                          .data.tagdata.events.STEPTREE[0].particles.STEPTREE[0])
    ev = d.events.STEPTREE[0]
    parts = ev.parts.STEPTREE
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].type.tag_class.enum_name in DROP:
            parts.pop(i)
    for p in parts:
        cls = p.type.tag_class.enum_name
        if cls == 'particle_system':
            p.type.filepath = OWN_PCTL
        elif cls == 'light':
            p.type.filepath = OWN_LIGHT
        elif cls == 'sound':
            p.type.filepath = POP
    if sorted(p.type.tag_class.enum_name for p in parts) != ['light', 'particle_system', 'sound']:
        raise SystemExit('%s: unexpected parts %s' % (BASE, [p.type.filepath for p in parts]))
    pts = ev.particles.STEPTREE
    for path, n, r, v, cone, tint in SPRAY:
        pts.append(copy.deepcopy(proto))
        q = pts[len(pts) - 1]
        q.particle_type.filepath = path
        q.location = 0
        q.relative_direction[0], q.relative_direction[1] = 0.0, UP
        q.relative_offset.i, q.relative_offset.j, q.relative_offset.k = 0.0, 0.0, HEAD
        q.created_count[0], q.created_count[1] = n
        q.distribution_radius[0], q.distribution_radius[1] = 0.03, 0.08
        q.velocity[0], q.velocity[1] = v
        q.velocity_cone_angle = cone
        q.radius[0], q.radius[1] = r
        q.flags.tint_as_hsv = False
        for bd in (q.tint_lower_bound, q.tint_upper_bound):
            bd.a = 1.0
            bd.r, bd.g, bd.b = tint or (1.0, 1.0, 1.0)
    bad = [p.type.filepath for e in d.events.STEPTREE for p in e.parts.STEPTREE
           if p.type.tag_class.enum_name in DROP]
    if bad:
        raise SystemExit('damage/decal parts left: %s' % bad)
    for e in d.events.STEPTREE:
        for p in e.parts.STEPTREE:
            print('  part      %-16s %s' % (p.type.tag_class.enum_name, p.type.filepath))
        for q in e.particles.STEPTREE:
            print('  particle  %-48s x%d-%d  r %.2f-%.2f  tint %s' % (
                q.particle_type.filepath, q.created_count[0], q.created_count[1], q.radius[0],
                q.radius[1], tuple(round(x, 2) for x in (q.tint_lower_bound.r,
                                                         q.tint_lower_bound.g, q.tint_lower_bound.b))))
    save(t, EFFECT, '.effect', write)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--write', action='store_true', help='write the tags (default: dry run)')
    a = ap.parse_args()
    need = [(BASE, '.effect'), (PROTO, '.effect'), (BASE_PCTL, '.particle_system'),
            (BASE_LIGHT, '.light'), (POP, '.sound'), (FLAKE_SRC, '.particle')]
    need += [(p, '.particle') for p, *_ in SPRAY if p != FLAKE]
    for rel, ext in need:
        if not os.path.isfile(tag(rel, ext)):
            raise SystemExit('missing source tag: %s%s' % (rel, ext))
    flake(a.write)
    burst(a.write)
    light(a.write)
    for rel, ext in ((FLAKE, '.particle'), (OWN_PCTL, '.particle_system'), (OWN_LIGHT, '.light'),
                     (EFFECT, '.effect')):
        print(('wrote ' if a.write else 'would write ') + rel + ext)
    effect(a.write)

if __name__ == '__main__':
    main()
