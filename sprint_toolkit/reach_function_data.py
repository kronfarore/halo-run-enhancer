r"""Every FUNCTION-DATA value of an HREK tag, by field path -- what `tool export-tag-to-xml`
only reports as a size. Through HREK's ManagedBlam, in Blender (Foundry's managed_blam).

Written for the Needle Rifle (wave B2, 2026-10-11): Reach's shader parameters (self_illum_color
/ intensity, meter colours) live in the `animated parameters` function data, and a contrail
system's PROFILE (lifespan, size, colour, intensity) in its mappings -- the numbers that decided
the needle's glow colours and its trail (0.15 s, 0.03 -> 0.01 wu; the sniper trail the port had
borrowed lived ~1.4 s). reach_effect_tints.py reads only colour functions; this prints all.

    blender --background --python reach_function_data.py -- <tag rel HREK\tags> [...]
    (Blender: F:\Tools\blender-5.2.2-windows-x64\blender.exe)

Per value: the parameter / field path, the data size, the first 32 bytes as hex and as float32.
Reading a function (the layout seen so far):
  byte 0      function type (1 = basic, 2 / 3 = with a range, 8 / 9 = curves)
  byte 2      colour count (a COLOUR function: colours as u32 BGRA at +4 + 4 x slot; a
              two-colour function uses slots 0 and 3) -- e.g. 8f 0d 6a ff = (106, 13, 143)
  +4 / +8     a SCALAR function's two values (float32): e.g. 3.0, 2.0 = intensity 3 -> 2
"""
import importlib
import os
import struct
import sys

import bpy  # noqa: F401

KEY = 'bl_ext.user_default.io_scene_foundry'
HREK_TAGS = r'F:\SteamLibrary\steamapps\common\HREK\tags'


def walk(fields, path, out):
    for f in fields:
        ft = str(f.FieldType)
        if ft == 'Block':
            for i in range(f.Elements.Count):
                walk(f.Elements[i].Fields, '%s/%s[%d]' % (path, f.FieldName, i), out)
        elif ft == 'Struct':
            walk(f.Elements[0].Fields, '%s/%s' % (path, f.FieldName), out)
        elif ft == 'StringId' and f.FieldName == 'parameter name':
            out.append((path, 'NAME', str(f.GetStringData())))
        elif ft == 'Data':
            try:
                out.append((path, 'DATA', bytes(f.GetData())))
            except Exception:
                pass


def main(tags):
    mb = importlib.import_module(KEY + '.managed_blam')
    if not mb.mb_active:
        mb.mb_init(os.path.join(HREK_TAGS, 'globals', 'globals.globals'))
    if 'hrek' not in str(mb.mb_path).lower():
        raise SystemExit('ManagedBlam is bound to %r, not HREK' % mb.mb_path)

    class T(mb.Tag):
        pass
    for rel in tags:
        print('=====', rel)
        with T(path=os.path.join(HREK_TAGS, rel)) as t:
            out = []
            walk(t.tag.Fields, '', out)
            for p, kind, v in out:
                if kind == 'NAME':
                    print('PARAM', p[-40:], v)
                elif len(v):
                    fl = [round(x, 4) for x in struct.unpack('<%df' % (len(v) // 4), v[:len(v) // 4 * 4])][:10]
                    print('   DATA', p[-60:], len(v), v[:32].hex(), fl)


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
