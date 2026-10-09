r"""Step 4a's HALO 1 side, raw: the values the ratio rule compares, read from HCEEK tags.

h1_role_compare.py turns them into time to kill; this prints the fields themselves, the
counterpart of h3_weapon_values.py: magazine (loaded / initial / maximum / reload time /
rounds reloaded / chamber), trigger (rounds per second, projectiles per shot, error and
error angle in degrees, distribution), aim assist, melee damage tag, the FP animation
lengths (frames), the projectile (velocity, air damage range = the distance FALLOFF,
maximum range) and its impact damage (lower bound, upper bounds, category, acceleration,
the per-material modifiers that differ from 1).

Written for the Mauler (2026-10-08): the shotgun's 15 x 18..25 pellets falling to 8 over
1.5 -> 3 wu, 0.4 s a shell, error 10 deg came from it.

    python h1_weapon_values.py "weapons\shotgun\shotgun" "weapons\pistol\pistol"
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.jpt_ import jpt__def  # noqa: E402
from reclaimer.hek.defs.antr import antr_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
deg = math.degrees


def tag(rel, ext):
    return os.path.join(TAGS, rel + ext)


def main(weapons):
    for w in weapons:
        d = weap_def.build(filepath=tag(w, '.weapon')).data.tagdata.weap_attrs
        print('=====', w)
        if len(d.magazines.STEPTREE):
            m = d.magazines.STEPTREE[0]
            print('magazine   loaded %d  initial %d  maximum %d  reload %.2f s  reloaded %d  chamber %.2f  flags %s'
                  % (m.rounds_loaded_maximum, m.rounds_total_initial, m.rounds_total_maximum,
                     m.reload_time, m.rounds_reloaded, m.chamber_time,
                     [f for f in m.flags.NAME_MAP if m.flags.get(f)]))
            print('           items %s' % [(i.rounds, i.equipment.filepath) for i in m.magazine_items.STEPTREE])
        tr = d.triggers.STEPTREE[0]
        f, p = tr.firing, tr.projectile
        print('trigger    rps %s  per shot %d  error %s deg  min error %.2f  error angle %s deg  dist %s'
              % (list(f.rounds_per_second), p.projectiles_per_shot,
                 [round(deg(x), 2) for x in f.error], deg(p.minimum_error),
                 [round(deg(x), 2) for x in p.error_angle], p.distribution_function.enum_name))
        for fe in tr.firing_effects.STEPTREE:
            print('           effects firing %s | misfire %s | empty %s'
                  % (fe.firing_effect.filepath, fe.misfire_effect.filepath, fe.empty_effect.filepath))
        a = d.aiming
        print('aim        auto %.1f deg / %g wu   magnet %.1f deg / %g wu'
              % (deg(a.autoaim_angle), a.autoaim_range, deg(a.magnetism_angle), a.magnetism_range))
        print('melee      %s   weapon type %s   label %s' % (d.melee.player_damage.filepath,
                                                           d.weapon_type.enum_name, d.label))
        fp = d.interface.first_person_animations.filepath
        if fp and os.path.exists(tag(fp, '.model_animations')):
            an = antr_def.build(filepath=tag(fp, '.model_animations')).data.tagdata
            print('fp frames  %s' % {x.name.replace('first-person ', ''): x.frame_count
                                     for x in an.animations.STEPTREE
                                     if any(k in x.name for k in ('reload', 'ready', 'put', 'melee', 'fire'))})
        pt = p.projectile.filepath
        if not pt:
            continue
        pp = proj_def.build(filepath=tag(pt, '.projectile')).data.tagdata.proj_attrs
        ph = pp.physics
        print('projectile %s  velocity %g -> %g wu/s  air damage range %s  range %g'
              % (pt, ph.initial_velocity, ph.final_velocity, list(ph.air_damage_range),
                 pp.detonation.maximum_range))
        j = ph.impact_damage.filepath
        if j:
            jd = jpt__def.build(filepath=tag(j, '.damage_effect')).data.tagdata
            dm, mods = jd.damage, jd.damage_modifiers
            print('damage     %s  lower %g  upper %s  category %s  acceleration %g'
                  % (j, dm.damage_lower_bound, list(dm.damage_upper_bound),
                     dm.category.enum_name, dm.instantaneous_acceleration))
            print('           materials != 1: %s' % {k: round(getattr(mods, k), 2) for k in mods.desc['NAME_MAP']
                                                     if getattr(mods, k) != 1.0})


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
