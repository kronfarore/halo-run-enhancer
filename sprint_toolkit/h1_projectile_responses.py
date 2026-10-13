r"""A Halo 1 projectile's per-MATERIAL responses (HCEEK tags, read-only): default response, potential
response with its skip fraction / impact angle / velocity window, the response effect -- per Halo 1
material index (the numbers `default_responses` / `reflect` / `impact_thin` take). Written for the
Focus Rifle (B7, 2026-10-12): its beam is a copy of Halo 1's Sentinel beam, which overpenetrated every
unit body and reflected off Jackal shields; set to Reach's (overpenetrate flesh / glass / liquid /
plants, stop on armour) from this listing. Also prints velocity, range and the detonation timer.

    python h1_projectile_responses.py "weapons\focus rifle\beam" "weapons\plasma rifle\bolt"
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.proj import proj_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
MATS = ('dirt sand stone snow wood metal_hollow metal_thin metal_thick rubber glass force_field '
        'grunt hunter_armor hunter_skin elite jackal jackal_energy_shield engineer_skin '
        'engineer_force_field flood_combat_form flood_carrier_form cyborg_armor cyborg_energy_shield '
        'human_armor human_skin sentinel moniter plastic water leaves elite_energy_shield ice '
        'hunter_shield').split()


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    for rel in argv:
        p = proj_def.build(filepath=os.path.join(TAGS, rel + '.projectile')).data.tagdata.proj_attrs
        print('== %s  velocity %g -> %g wu/s  range %g  timer starts %s %s  flags %s'
              % (rel, p.physics.initial_velocity, p.physics.final_velocity, p.detonation.maximum_range,
                 p.detonation_timer_starts.enum_name, tuple(p.detonation.timer),
                 [f for f in p.flags.NAME_MAP if p.flags.get(f)]))
        for i, r in enumerate(p.material_responses.STEPTREE):
            pr = r.potential_response
            print('%2d %-22s %-14s potential %-14s skip %.2f angle %s velocity %s  effect %s'
                  % (i, MATS[i] if i < len(MATS) else '?', r.response.enum_name, pr.response.enum_name,
                     pr.skip_fraction, tuple(round(math.degrees(x)) for x in pr.impact_angle),
                     tuple(pr.impact_velocity), r.effect.filepath or '-'))


if __name__ == '__main__':
    main(sys.argv[1:])
