r"""Halo 1: the CLASSIC Grunt Birthday Party confetti, `effects\grunt birthday party.effect`.

h1_birthday_party.py (halo1.dll) spawns this effect on a Grunt killed by a headshot while the
Grunt Birthday Party skull is on -- the ONLY effect it names since 3e50a85 (a map without the
tag plays nothing). MCC's own confetti (`sfx_konfetti`) cannot be copied: it is a Saber3D
(Anniversary engine) text definition in halo1\prebuild\paks\initial_ps.s3dpak -- emitters on
`sfx_source_ak`, the `konfetti_16x1` 4x4 sprite sheet, a Saber `sfx` material -- which only the
Anniversary renderer draws; the classic engine reads Blam tags only. Its numbers are mirrored
here instead: pieces emitted UP (`dir y+`, speed 2), living 6 s, settling on the ground
(`CDT friction 15`), plus a flash (`sfx_expl_flash_02`).

Built ONLY from tags that ship with HCEEK, NO damage part. The container is a copy of the plasma
grenade's explosion (it DOES show on a dead Grunt spawned at the object origin, in game
2026-10-11; small spark effects did not) with EVERY part but its light removed -- no plasma
fireball, no damage, no decal; the light is an own warm copy (`effects\lights\grunt birthday
party`), the flash. Then, all with their own velocity and spread (no impact normal):
  * event 0, the LAUNCH (from the origin + 0.3 wu): confetti and pink needle debris shot
    straight up in a narrow cone, plus the needler's pop and the Grunt's own `celebration`
    dialogue line (14 permutations: the dead Grunt cheers)
  * event 1, the AIR BURST, 0.3 s later at the origin + 1.2 wu (about 3.6 m up): confetti in
    six colours in every direction, green and blue sparks; it rains down around the body
Confetti = an own particle `effects\particles\solid\confetti`: a copy of `debris shirt` (a
near-white fluttering cloth sprite on light, wind-damped point physics, so the tint gives
clean colours) that lives 4-6 s, fades over the last second and does not die at rest.

In the maps: a never-called static script in sprint.hsc (`gbp_confetti_ref`) names the effect,
and global_scripts.hsc is compiled into every level, so tool's next build of each campaign map
(h1_rebuild_all.py) carries it. Nothing gameplay-side references it.

    python h1_confetti_effect.py           # dry run: print what would be written
    python h1_confetti_effect.py --write   # write the tags into HCEEK\tags
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
from reclaimer.hek.defs.ligh import ligh_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
EFFECT = r'effects\grunt birthday party'
FLAKE = r'effects\particles\solid\confetti'
FLAKE_SRC = r'effects\particles\solid\debris shirt'
BASE = r'weapons\plasma grenade\effects\explosion'      # the container: only its light stays
BASE_LIGHT = r'weapons\plasma grenade\explosion'
OWN_LIGHT = r'effects\lights\grunt birthday party'
OLD_PCTL = r'effects\particle systems\grunt birthday party'  # v2's pink fireball, removed
PROTO = r'weapons\needler\effects\needle detonate'     # a particle entry to copy
POP = r'sound\sfx\weapons\needler\expl'
CHEER = r'sound\dialog\grunt\conditional\combat2\postcombatactions\celebration'
LIGHT_RGB = (1.0, 0.8, 0.4)                            # a warm flash

UP = math.pi / 2          # relative_direction pitch: up in the Grunt's frame
LAUNCH = 0.3              # wu above the origin (feet): about head height
BURST = 1.2               # wu above the origin: the air burst (~3.6 m)
BURST_DELAY = 0.3         # s after the launch
COLOURS = [(1.0, 0.25, 0.6), (0.3, 1.0, 0.3), (0.25, 0.5, 1.0),
           (1.0, 0.95, 0.2), (1.0, 0.55, 0.1), (0.7, 0.3, 1.0)]
# (event, particle, count, radius, velocity, cone rad, tint RGB or None = the particle's own)
SPRAY = ([(0, FLAKE, (4, 6), (0.05, 0.08), (3.0, 4.5), 0.35, c) for c in COLOURS] +
         [(0, r'effects\particles\solid\needler spike debris', (8, 12), (0.04, 0.09), (3.0, 4.5),
           0.35, None)] +
         [(1, FLAKE, (10, 14), (0.05, 0.08), (1.0, 2.5), math.pi, c) for c in COLOURS] + [
    (1, r'effects\particles\energy\plasma overcharge spark', (8, 12), (0.07, 0.12), (1.0, 2.5),
     math.pi, (0.3, 1.0, 0.35)),
    (1, r'effects\particles\energy\shield jackal sparks', (8, 12), (0.07, 0.12), (1.0, 2.5),
     math.pi, (0.3, 0.55, 1.0)),
])
HEIGHT = {0: LAUNCH, 1: BURST}


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
    d.lifespan[0], d.lifespan[1] = 4.0, 6.0
    d.fade_out_time = 1.0
    save(t, FLAKE, '.particle', write)


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
    evs = d.events.STEPTREE
    del evs[1:]
    ev = evs[0]
    parts = ev.parts.STEPTREE
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].type.tag_class.enum_name not in ('light', 'sound'):
            parts.pop(i)                       # fireball, both damage parts, decal
    if sorted(p.type.tag_class.enum_name for p in parts) != ['light', 'sound']:
        raise SystemExit('%s: unexpected parts %s' % (BASE, [p.type.filepath for p in parts]))
    for p in parts:
        p.type.filepath = OWN_LIGHT if p.type.tag_class.enum_name == 'light' else POP
    parts.append(copy.deepcopy(next(p for p in parts if p.type.tag_class.enum_name == 'sound')))
    parts[len(parts) - 1].type.filepath = CHEER
    del ev.particles.STEPTREE[:]
    # the air burst: its own event, the launch's copy without parts, BURST_DELAY s later
    evs.append(copy.deepcopy(ev))
    burst = evs[1]
    del burst.parts.STEPTREE[:]
    burst.delay_bounds[0] = burst.delay_bounds[1] = BURST_DELAY
    for e, path, n, r, v, cone, tint in SPRAY:
        pts = evs[e].particles.STEPTREE
        pts.append(copy.deepcopy(proto))
        q = pts[len(pts) - 1]
        q.particle_type.filepath = path
        q.location = 0
        q.relative_direction[0], q.relative_direction[1] = 0.0, UP
        q.relative_offset.i, q.relative_offset.j, q.relative_offset.k = 0.0, 0.0, HEIGHT[e]
        q.created_count[0], q.created_count[1] = n
        q.distribution_radius[0], q.distribution_radius[1] = 0.03, 0.08
        q.velocity[0], q.velocity[1] = v
        q.velocity_cone_angle = cone
        q.radius[0], q.radius[1] = r
        q.flags.tint_as_hsv = False
        for bd in (q.tint_lower_bound, q.tint_upper_bound):
            bd.a = 1.0
            bd.r, bd.g, bd.b = tint or (1.0, 1.0, 1.0)
    kinds = sorted(p.type.tag_class.enum_name for e in evs for p in e.parts.STEPTREE)
    if kinds != ['light', 'sound', 'sound']:
        raise SystemExit('unexpected parts: %s' % kinds)
    for i, e in enumerate(evs):
        print('  event %d, delay %.2f s' % (i, e.delay_bounds[0]))
        for p in e.parts.STEPTREE:
            print('    part      %-8s %s' % (p.type.tag_class.enum_name, p.type.filepath))
        for q in e.particles.STEPTREE:
            print('    particle  %-48s x%d-%d  +%.1f wu  v %.1f-%.1f  cone %.2f' % (
                q.particle_type.filepath, q.created_count[0], q.created_count[1],
                q.relative_offset.k, q.velocity[0], q.velocity[1], q.velocity_cone_angle))
    save(t, EFFECT, '.effect', write)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--write', action='store_true', help='write the tags (default: dry run)')
    a = ap.parse_args()
    need = [(BASE, '.effect'), (PROTO, '.effect'), (BASE_LIGHT, '.light'), (POP, '.sound'),
            (CHEER, '.sound'), (FLAKE_SRC, '.particle')]
    need += [(p, '.particle') for _, p, *_ in SPRAY if p != FLAKE]
    for rel, ext in need:
        if not os.path.isfile(tag(rel, ext)):
            raise SystemExit('missing source tag: %s%s' % (rel, ext))
    flake(a.write)
    light(a.write)
    for rel, ext in ((FLAKE, '.particle'), (OWN_LIGHT, '.light'), (EFFECT, '.effect')):
        print(('wrote ' if a.write else 'would write ') + rel + ext)
    effect(a.write)
    old = tag(OLD_PCTL, '.particle_system')
    if a.write and os.path.isfile(old):
        os.remove(old)
        print('removed ' + OLD_PCTL + '.particle_system (v2, no longer referenced)')


if __name__ == '__main__':
    main()
