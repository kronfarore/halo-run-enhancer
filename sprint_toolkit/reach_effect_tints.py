r"""Read the colours of a Reach effect's particles -- the function data that
`tool export-tag-to-xml` only reports as a size. Through HREK's ManagedBlam, in Blender.

Found the Focus Rifle's muzzle colour (2026-10-02): Reach's flash is ORANGE, particle tint
(255,98,42) -> (255,92,0), sparks (255,200,72) -> (238,83,31); its firing light
blue-violet (71,73,255) -- the target h4_muzzle_recolor.py moves the Halo 4 flash to.

    blender --background --python reach_effect_tints.py -- <tag path rel. HREK\tags> [...]

A colour function's data: byte 2 = colour count; colours as u32 ARGB at +4 + 4*slot
(a two-colour function uses slots 0 and 3). Printed as (r, g, b) per used slot.
"""
import importlib
import os
import sys

import bpy  # noqa: F401

KEY = 'bl_ext.user_default.io_scene_foundry'
HREK_TAGS = r'F:\SteamLibrary\steamapps\common\HREK\tags'
SLOTS = {1: (0,), 2: (0, 3), 3: (0, 1, 3), 4: (0, 1, 2, 3)}


def walk(fields, path, out):
    for f in fields:
        ft = str(f.FieldType)
        if ft == 'Block':
            for i in range(f.Elements.Count):
                walk(f.Elements[i].Fields, '%s/%s[%d]' % (path, f.FieldName, i), out)
        elif ft == 'Struct':
            walk(f.Elements[0].Fields, '%s/%s' % (path, f.FieldName), out)
        elif ft == 'Data' and ('tint' in path.lower() or 'color' in path.lower()):
            try:
                out.append((path, bytes(f.GetData())))
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
        with T(path=os.path.join(HREK_TAGS, rel)) as t:
            out = []
            walk(t.tag.Fields, '', out)
            for path, b in out:
                if len(b) < 20 or not b[2]:
                    continue
                cols = []
                for k in SLOTS.get(b[2], ()):
                    bb, gg, rr, _aa = b[4 + 4 * k:8 + 4 * k]
                    cols.append((rr, gg, bb))
                print('TINT %s %s %s' % (os.path.basename(rel), path[-70:], cols))


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:])
