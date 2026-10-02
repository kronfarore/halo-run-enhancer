r"""The ManagedBlam half of h4_muzzle_recolor.py (run by it, in Blender, bound to H4EK).

    blender --background --python h4_muzzle_tags.py -- --list <json>
        the donor effect's particle / lens flare parts and their palette bitmaps
    blender --background --python h4_muzzle_tags.py -- --write <json>
        copy the effect and its parts to the port's folder, drop the sound part, recolour
        every colour function, point palettes at the own copies the json names
"""
import colorsys
import importlib
import json
import os
import shutil
import sys

import bpy  # noqa: F401

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h4_muzzle_recolor import (DONOR_EFFECT, EXT, OWN_DIR, OWN_EFFECT,  # noqa: E402
                               recolour_rgb)

KEY = 'bl_ext.user_default.io_scene_foundry'
TAGS = r'F:\SteamLibrary\steamapps\common\H4EK\tags'
B = '\\'
PALETTE_PARAMS = ('palette', 'palettemap')
#: colour count (function byte 2) -> the u32 ARGB slots that hold its colours
SLOTS = {1: (0,), 2: (0, 3), 3: (0, 1, 3), 4: (0, 1, 2, 3)}


def walk(fields, visit, el=None):
    for f in fields:
        ft = str(f.FieldType)
        if ft == 'Block':
            for i in range(f.Elements.Count):
                walk(f.Elements[i].Fields, visit, f.Elements[i])
        elif ft == 'Struct':
            walk(f.Elements[0].Fields, visit, f.Elements[0])
        else:
            visit(f, ft, el)


def split(path):
    """'a\\b.particle' -> ('a\\b', 'particle')"""
    base, _, ext = path.rpartition('.')
    return base, ext


def recolour_function(b):
    b = bytearray(b)
    n = b[2] if len(b) >= 20 else 0
    hit = 0
    for k in SLOTS.get(n, ()):
        o = 4 + 4 * k
        bb, gg, rr, aa = b[o:o + 4]
        nr, ng, nb = recolour_rgb(rr, gg, bb)
        if (nr, ng, nb) != (rr, gg, bb):
            b[o:o + 4] = bytes((nb, ng, nr, aa))
            hit += 1
    return bytes(b), hit


def main(argv):
    mb = importlib.import_module(KEY + '.managed_blam')
    if not mb.mb_active:
        mb.mb_init(os.path.join(TAGS, 'globals', 'globals.globals'))
    if 'h4ek' not in str(mb.mb_path).lower():
        raise SystemExit('ManagedBlam is bound to %r, not H4EK' % mb.mb_path)

    class T(mb.Tag):
        pass
    mode, js = argv[0], argv[1]
    if mode == '--list':
        parts, palettes = [], set()
        with T(path=os.path.join(TAGS, DONOR_EFFECT + '.effect')) as t:
            def refs(f, ft, el):
                if ft == 'Reference':
                    p = t.get_path_str(f.Path)
                    if p and split(p)[1] in EXT.values() and p not in parts:
                        parts.append(p)
            walk(t.tag.Fields, refs)
        for p in parts:
            with T(path=os.path.join(TAGS, p)) as t:
                def pal(f, ft, el):
                    if ft == 'Reference' and f.FieldName == 'bitmap' and el is not None:
                        try:
                            pn = el.SelectField('parameter name').GetStringData()
                        except Exception:
                            return
                        q = t.get_path_str(f.Path)
                        if pn in PALETTE_PARAMS and q:
                            palettes.add(split(q)[0])
                walk(t.tag.Fields, pal)
        json.dump({'parts': parts, 'palettes': sorted(palettes)}, open(js, 'w'))
        for p in parts:
            print('   part %s' % p)
        print('MUZZLE OK list')
        return

    cfg = json.load(open(js))
    own = {}
    for p in cfg['parts']:
        base, ext = split(p)
        own[p] = OWN_DIR + B + base.rsplit(B, 1)[-1] + '.' + ext
    os.makedirs(os.path.join(TAGS, OWN_DIR), exist_ok=True)
    shutil.copyfile(os.path.join(TAGS, DONOR_EFFECT + '.effect'), os.path.join(TAGS, OWN_EFFECT + '.effect'))
    for p, q in own.items():
        shutil.copyfile(os.path.join(TAGS, p), os.path.join(TAGS, q))
    pal = {k + '.bitmap': v + '.bitmap' for k, v in cfg['palettes'].items()}
    with T(path=os.path.join(TAGS, OWN_EFFECT + '.effect')) as t:
        dropped = 0
        events = t.tag.SelectField('events')
        for ei in range(events.Elements.Count):
            partsb = events.Elements[ei].SelectField('parts')
            for i in reversed(range(partsb.Elements.Count)):
                ty = t.get_path_str(partsb.Elements[i].SelectField('type').Path)
                if ty and split(ty)[1] == 'sound':
                    partsb.RemoveElement(i)
                    dropped += 1
        n = [0]

        def rep(f, ft, el):
            if ft == 'Reference':
                p = t.get_path_str(f.Path)
                if p in own:
                    f.Path = t._TagPath_from_string(own[p])
                    n[0] += 1
        walk(t.tag.Fields, rep)
        t.tag_has_changes = True
    print('   effect %s: %d part reference(s) -> own copies, %d sound part(s) dropped'
          % (OWN_EFFECT, n[0], dropped))
    for q in own.values():
        with T(path=os.path.join(TAGS, q)) as t:
            c = [0, 0]

            def edit(f, ft, el):
                if ft == 'Data':
                    try:
                        b = bytes(f.GetData())
                    except Exception:
                        return
                    nb, hit = recolour_function(b)
                    if hit:
                        f.SetData(nb)
                        c[0] += hit
                elif ft == 'Reference':
                    p = t.get_path_str(f.Path)
                    if p in pal:
                        f.Path = t._TagPath_from_string(pal[p])
                        c[1] += 1
            walk(t.tag.Fields, edit)
            t.tag_has_changes = True
        print('   %-48s colours %d, palettes %d' % (q.rsplit(B, 1)[-1], c[0], c[1]))
    print('MUZZLE OK write')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:])
