r"""Halo 4 port: the Focus Rifle's own BEAM LOOK, on the path a player weapon draws.

WHAT EXISTS (measured 2026-10-02). Halo 4 has no beam_system tags; Bungie converted the
Focus Rifle's beam into the Sentinel's tracers, and the Sentinel's 3p tracer IS that
beam: a `center` core on energy_trail plus two `plasma` layers blending plasma_trail_a
and plasma_trail_b noise through a colour palette -- the Reach beam's own textures, only
the palette swapped for a blue Forerunner gradient. Crossed ribbons, double-sided, and
~10x the Beam Rifle streak's size (0.035-0.4 against 0.01-0.025).

WHY IT NEVER DREW, AND WHY UNPINNING IT DREW NOTHING. A point-to-point tracer in a firing
effect does not draw from a player's weapon (boots 2-8); a player's beam rides the
PROJECTILE (the Beam Rifle's streak, boots 9-10). Clearing point-to-point (boot 12) left
the Sentinel's tracers with LENGTH functions driven by "profile position" -- along a line
between two points that no longer existed -- so they had no length. The Beam Rifle's
streak drives its length by "profile age", along the trail behind the projectile.

SO, per tracer of the port's own copy of the Sentinel tracer:
  * look       kept: materials, shape (cross), profile size -- the Focus Rifle's beam
  * behaviour  copied from the Beam Rifle streak's first tracer: length, offset, profile
               lifespan, profile self acceleration (functions, field by field, data blobs
               and their input/range/modifier enums)
  * colour     palette -> fx\reach\bitmaps\contrails\_gradients\focus_rifle_plasma (Reach)
  * system     point-to-point cleared
and the port's own copy of the Beam Rifle's projectile effect carries it.
h4_make_port_weapon.py attaches that effect to the port's projectile.

Run inside the portable Blender on F: (H4EK is bound through an absolute path):

    blender --background --python h4_beam_look.py [-- --write]
"""
import importlib
import os
import shutil
import struct
import sys

import bpy

KEY = 'bl_ext.user_default.io_scene_foundry'
H4EK_TAGS = r'F:\SteamLibrary\steamapps\common\H4EK\tags'
B = '\\'
SB_TRACER = B.join(['objects', 'weapons', 'pistol', 'storm_sentinel_beam', 'fx', 'friendly_beam',
                    'projectile_3p'])
BR_TRACER = B.join(['objects', 'weapons', 'rifle', 'storm_beam_rifle', 'fx', 'projectile'])
BR_EFFECT = BR_TRACER
OWN_TRACER = B.join(['objects', 'weapons', 'rifle', 'focus_rifle', 'fx', 'beam'])
OWN_EFFECT = B.join(['objects', 'weapons', 'rifle', 'focus_rifle', 'fx', 'beam_projectile'])
PALETTE = B.join(['fx', 'reach', 'bitmaps', 'contrails', '_gradients', 'focus_rifle_plasma'])
BEHAVIOUR = ('length', 'offset', 'profile lifespan', 'profile self acceleration')
#: boot 15 (user): "very 2 dimensional" -> a TUBE: Reach's own 1p beam used an n-gon
#: profile; "lifespan a bit too long" -> the streak's profile lifespan (0.35..1.0 s,
#: floats at +4/+8 of the function data) scaled down.
SHAPE, SIDES = 'n-gon', 6
LIFESPAN_SCALE = 0.5


def field(fields, name):
    for f in fields:
        if f.FieldName == name:
            return f
        if str(f.FieldType) == 'Struct':
            got = field(f.Elements[0].Fields, name)
            if got is not None:
                return got
    return None


def copy_fields(src_fields, dst_fields):
    """Copy every value field by position (same definition on both sides)."""
    n = 0
    for s, d in zip(src_fields, dst_fields):
        ft = str(s.FieldType)
        if s.FieldName != d.FieldName:
            raise SystemExit('field mismatch %r vs %r' % (s.FieldName, d.FieldName))
        if ft == 'Struct':
            n += copy_fields(s.Elements[0].Fields, d.Elements[0].Fields)
        elif ft == 'Data':
            d.SetData(s.GetData())
            n += 1
        elif 'Enum' in ft:
            d.Value = s.Value
            n += 1
        elif 'Flags' in ft:
            d.RawValue = s.RawValue
            n += 1
        elif hasattr(s, 'GetStringData') and ft not in ('Block', 'Reference'):
            d.SetStringData(s.GetStringData())
            n += 1
    return n


def main(write):
    mb = importlib.import_module(KEY + '.managed_blam')
    if not mb.mb_active:
        mb.mb_init(os.path.join(H4EK_TAGS, 'globals', 'globals.globals'))
    if 'h4ek' not in str(mb.mb_path).lower():
        raise SystemExit('ManagedBlam is bound to %r, not H4EK' % mb.mb_path)

    class T(mb.Tag):
        pass

    src = os.path.join(H4EK_TAGS, SB_TRACER + '.tracer_system')
    dst = os.path.join(H4EK_TAGS, OWN_TRACER + '.tracer_system')
    if write:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    with T(path=os.path.join(H4EK_TAGS, BR_TRACER + '.tracer_system')) as br, \
            T(path=dst if write else src) as own:
        donor = br.tag.SelectField('tracers').Elements[0]
        flags = own.tag.SelectField('tracer system flags')
        flags.SetBit('point-to-point', False)
        tracers = own.tag.SelectField('tracers')
        for i in range(tracers.Elements.Count):
            e = tracers.Elements[i]
            name = e.SelectField('tracer name').GetStringData()
            copied = 0
            for fn in BEHAVIOUR:
                copied += copy_fields(field(donor.Fields, fn).Elements[0].Fields,
                                      field(e.Fields, fn).Elements[0].Fields)
            sh = e.SelectField('profile shape')
            sh.Value = [x.EnumName for x in sh.Items].index(SHAPE)
            e.SelectField('number of n-gon sides').SetStringData(str(SIDES))
            life = field(field(e.Fields, 'profile lifespan').Elements[0].Fields, 'data')
            raw = bytearray(life.GetData())
            lo, hi = struct.unpack_from('<ff', raw, 4)
            struct.pack_into('<ff', raw, 4, lo * LIFESPAN_SCALE, hi * LIFESPAN_SCALE)
            life.SetData(bytes(raw))
            print('   shape %s/%d sides, lifespan %.3f..%.3f -> %.3f..%.3f s'
                  % (SHAPE, SIDES, lo, hi, lo * LIFESPAN_SCALE, hi * LIFESPAN_SCALE))
            params = field(e.Fields, 'material parameters')
            pal = 0
            for j in range(params.Elements.Count):
                p = params.Elements[j]
                if p.SelectField('parameter name').GetStringData() == 'palette':
                    p.SelectField('bitmap').Path = own._TagPath_from_string(PALETTE + '.bitmap')
                    pal += 1
            print('tracer %d %-8s behaviour fields copied %d, palette -> focus_rifle_plasma %d'
                  % (i, name, copied, pal))
        own.tag_has_changes = bool(write)
    if write:
        shutil.copyfile(os.path.join(H4EK_TAGS, BR_EFFECT + '.effect'),
                        os.path.join(H4EK_TAGS, OWN_EFFECT + '.effect'))
        with T(path=os.path.join(H4EK_TAGS, OWN_EFFECT + '.effect')) as fx:
            ev = fx.tag.SelectField('events')
            hit = 0
            for i in range(ev.Elements.Count):
                parts = ev.Elements[i].SelectField('parts')
                for j in range(parts.Elements.Count):
                    t = parts.Elements[j].SelectField('type')
                    if fx.get_path_str(t.Path).lower().endswith('.tracer_system'):
                        t.Path = fx._TagPath_from_string(OWN_TRACER + '.tracer_system')
                        hit += 1
            if hit != 1:
                raise SystemExit('expected one tracer part in the effect, found %d' % hit)
            fx.tag_has_changes = True
        print('wrote %s.tracer_system and %s.effect' % (OWN_TRACER, OWN_EFFECT))
    else:
        print('(dry run on the Sentinel tracer in memory -- pass --write)')


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    main('--write' in argv)
