r"""Every PARTICLE of Halo 1 effects, side by side -- closing check 10, THE MUZZLE-FLASH RULE
(user 2026-10-10, the DMR): the port's first-person flash is compared with the source weapon's
before boot 1. Per particle: event, tag, location marker, created count, radius, direction
(yaw / pitch, rad), offset (forward / left / up wu), velocity cone and camera mode.

The source side (Halo 3 / Reach) is the firing effect's first-person particle systems: their
location markers and emitter `bounding radius estimate` in the kit export (the DMR's Reach
flash: 0.06-0.11 wu at the muzzle_flash markers; the sniper template's: two sideways fans of
15-20 sprites up to 0.125 wu). Also lists the shield-hit effects THE HIT-EFFECT RULE sizes.

    python h1_effect_particles.py "weapons\dmr\effects\fire bullet" "weapons\battle rifle\effects\fire bullet"
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.effe import effe_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')


def particles(rel):
    """[(event, tag, marker, (count lo, hi), (radius lo, hi), (yaw, pitch), (fwd, left, up),
    cone deg, camera mode)] of one effect tag (no extension)."""
    e = effe_def.build(filepath=os.path.join(TAGS, rel + '.effect')).data.tagdata
    locs = [l.marker_name for l in e.locations.STEPTREE]
    out = []
    for i, ev in enumerate(e.events.STEPTREE):
        for q in ev.particles.STEPTREE:
            o = q.relative_offset
            out.append((i, q.particle_type.filepath.split('\\')[-1],
                        locs[q.location] if q.location < len(locs) else q.location,
                        tuple(q.created_count), (q.radius[0], q.radius[1]),
                        (q.relative_direction[0], q.relative_direction[1]), (o.i, o.j, o.k),
                        math.degrees(q.velocity_cone_angle), q.create_in_camera.enum_name))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('effects', nargs='+', help=r'effect tags under HCEEK tags, no extension')
    a = ap.parse_args()
    for rel in a.effects:
        print('==', rel)
        for ev, tag, loc, cnt, rad, d, off, cone, cam in particles(rel):
            print('  ev%d %-32s %-16s count %-8s radius %.3f-%.3f dir %+.2f/%+.2f off %+.3f/%+.3f/%+.3f '
                  'cone %4.1f  %s' % (ev, tag, loc, '%d-%d' % cnt, rad[0], rad[1], d[0], d[1],
                                      off[0], off[1], off[2], cone, cam))


if __name__ == '__main__':
    main()
