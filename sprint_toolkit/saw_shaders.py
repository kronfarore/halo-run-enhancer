"""Halo 1 shader_model tags for the SAW, copied from the AR's first-person shaders with
the SAW's bitmaps in place of the AR's.

    python saw_shaders.py --dump      # print the AR shaders' fields
    python saw_shaders.py             # write tags\\weapons\\saw\\shaders\\*.shader_model
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.hek.defs.soso import soso_def

TAGS = r'F:\SteamLibrary\steamapps\common\HCEEK\tags'
AR = os.path.join(TAGS, 'weapons', 'assault rifle', 'fp', 'shaders')
OUT = os.path.join(TAGS, 'weapons', 'saw', 'shaders')
BM = 'weapons' + os.sep + 'saw' + os.sep + 'bitmaps' + os.sep
# SAW shader name: (AR template, base map, multipurpose map). Halo 1 multipurpose, read
# off the AR's own map: R = reflection mask, G = self-illumination, B unused. Without
# one the AR shader's reflection (0.8 / 1.0 brightness) covered the whole gun -- the
# "mostly white" first test.
PLAN = {'saw_body': ('gun', BM + 'saw_diff', BM + 'saw_mp'),
        'saw_display': ('display', BM + 'saw_display', BM + 'saw_display_mp'),
        'saw_display_depleted': ('display', BM + 'saw_display_depleted', BM + 'saw_display_mp')}


def main():
    if '--dump' in sys.argv:
        for n in ('gun', 'display'):
            t = soso_def.build(filepath=os.path.join(AR, n + '.shader_model'))
            print('==', n)
            print(str(t.data.tagdata)[:4000])
        return
    os.makedirs(OUT, exist_ok=True)
    for name, (tmpl, bitmap, mp) in PLAN.items():
        t = soso_def.build(filepath=os.path.join(AR, tmpl + '.shader_model'))
        m = t.data.tagdata.soso_attrs
        m.maps.diffuse_map.filepath = bitmap
        m.maps.multipurpose_map.filepath = mp
        t.filepath = os.path.join(OUT, name + '.shader_model')
        t.serialize(temp=False, backup=False)
        print('wrote', t.filepath)


if __name__ == '__main__':
    main()
