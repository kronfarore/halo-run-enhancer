r"""Two Halo 1 tag views a port's template check needs (HCEEK, read-only):

  effect <tag>   every event of an effect: its delay / duration / skip, its parts (sound,
                 damage ...) and particles with their location -- what a `sound_effects`
                 copy would carry (the Mauler: the shotgun firing effect plays its fire
                 sound in TWO identical events, the casing in a third at 0.5 s)
  hud <tag>      a weapon HUD interface's static / meter / number elements (state, bitmap,
                 sequence, meter multiplier / bias), its flash cutoffs and crosshair
                 sequences -- which sheet a port's ammo readout replaces

    python h1_tag_inspect.py effect "weapons\shotgun\effects\shotgun firing"
    python h1_tag_inspect.py hud "weapons\shotgun\shotgun"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.effe import effe_def  # noqa: E402
from reclaimer.hek.defs.wphi import wphi_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')


def effect(rel):
    d = effe_def.build(filepath=os.path.join(TAGS, rel + '.effect')).data.tagdata
    print('locations %s' % [l.marker_name for l in d.locations.STEPTREE])
    for i, ev in enumerate(d.events.STEPTREE):
        print('event %d  skip %g  delay %s  duration %s'
              % (i, ev.skip_fraction, list(ev.delay_bounds), list(ev.duration_bounds)))
        for p in ev.parts.STEPTREE:
            print('   part      %-14s %s  (location %d)' % (p.type.tag_class.enum_name, p.type.filepath, p.location))
        for q in ev.particles.STEPTREE:
            print('   particle  %s  (location %d)' % (q.particle_type.filepath, q.location))


def hud(rel):
    d = wphi_def.build(filepath=os.path.join(TAGS, rel + '.weapon_hud_interface')).data.tagdata
    print('child %s' % d.child_hud.filepath)
    for name in ('static_elements', 'meter_elements', 'number_elements', 'overlay_elements'):
        for e in getattr(d, name).STEPTREE:
            bm = next((getattr(e, f).filepath for f in ('interface_bitmap', 'meter_bitmap') if hasattr(e, f)), '')
            extra = ' seq %s' % e.sequence_index if hasattr(e, 'sequence_index') else ''
            if name == 'meter_elements':
                extra += ' multiplier %s bias %s value scale %s' % (e.alpha_multiplier, e.alpha_bias, e.value_scale)
            if name == 'number_elements':
                extra += ' digits %s' % e.maximum_number_of_digits
            print('%-16s %-14s %s%s' % (name, e.state_attached_to.enum_name, bm, extra))
    fc = d.flash_cutoffs
    print('flash cutoffs loaded %s total %s' % (fc.loaded_ammo_cutoff, fc.total_ammo_cutoff))
    for c in d.crosshairs.STEPTREE:
        print('crosshair %-6s %s %s' % (c.crosshair_type.enum_name, c.crosshair_bitmap.filepath,
                                        [o.sequence_index for o in c.crosshair_overlays.STEPTREE]))


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('effect', 'hud'):
        raise SystemExit(__doc__)
    {'effect': effect, 'hud': hud}[sys.argv[1]](sys.argv[2])
