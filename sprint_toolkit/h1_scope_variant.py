r"""TEST-ONLY scope variants of a Halo 1 port: two (or more) zoom masks judged in ONE boot.

The Carbine (2026-10-08): the BR's scope settings drew it too big and too wide; variant A
(the config) on the spawn primary, variant B (this tool) on the secondary
(`h1_port_test_map.py <key> --secondary <variant weapon>`), the user picked B. A variant is
a copy of the port's weapon tag + its HUD with the mask baked at other `aspect` / `span` /
`size` values, all under `<weapon dir>\test` -- never shipped: delete it after the test.

    python h1_scope_variant.py covenant_carbine b --aspect 1.667 [--span 828] [--size 1024] [--screen b.png]
    python h1_port_test_map.py covenant_carbine --secondary "weapons\covenant carbine\test\covenant carbine b" --stage
    python h1_scope_variant.py covenant_carbine --clean        (after the test)
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.wphi import wphi_def  # noqa: E402
import h1_h3_scope  # noqa: E402
import ports_h1  # noqa: E402

TAGS = h1_h3_scope.TAGS
B = '\\'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('port')
    ap.add_argument('name', nargs='?', help='variant suffix, e.g. b')
    ap.add_argument('--aspect', type=float)
    ap.add_argument('--span', type=float)
    ap.add_argument('--size', type=int)
    ap.add_argument('--screen', help='PNG of the variant as Halo 1 draws it')
    ap.add_argument('--clean', action='store_true', help='delete every test variant of the port')
    a = ap.parse_args()
    w = ports_h1.load(a.port)['pickable']
    wdir = w['weapon'].rsplit(B, 1)[0]
    test = wdir + B + 'test'
    if a.clean:
        p = os.path.join(TAGS, test)
        if os.path.isdir(p):
            shutil.rmtree(p)
            print('deleted', p)
        else:
            print('no test variants under', p)
        return
    if not a.name:
        ap.error('a variant name (or --clean)')
    S = dict(w['hud']['scope'])
    for k in ('aspect', 'span', 'size'):
        if getattr(a, k) is not None:
            S[k] = getattr(a, k)
    dark, blur, used = h1_h3_scope.bake_maps(S['chud'], size=S.get('size', 512), span=S.get('span', 640.0),
                                             aspect=S.get('aspect', 1.0), per_widget=S.get('per_widget'))
    base = w['weapon'].rsplit(B, 1)[1]
    mask = test + B + 'scope_mask_' + a.name
    print('mask', h1_h3_scope.write(dark, mask, alpha=S.get('alpha', 255), blur=blur))
    h = wphi_def.build(filepath=os.path.join(TAGS, w['hud']['out'] + '.weapon_hud_interface'))
    for se in h.data.tagdata.screen_effect.STEPTREE:
        se.mask.fullscreen_mask.filepath = se.mask.splitscreen_mask.filepath = mask
    hud = test + B + base + ' ' + a.name
    h.filepath = os.path.join(TAGS, hud + '.weapon_hud_interface')
    h.serialize(temp=False, backup=False)
    t = weap_def.build(filepath=os.path.join(TAGS, w['weapon'] + '.weapon'))
    t.data.tagdata.weap_attrs.interface.hud_interface.filepath = hud
    t.filepath = os.path.join(TAGS, hud + '.weapon')
    t.serialize(temp=False, backup=False)
    print('variant weapon  %s  (aspect %.3f, span %g, size %d)' % (hud, S['aspect'], S['span'], S['size']))
    if a.screen:
        print('screen', h1_h3_scope.screen(dark, blur, a.screen))


if __name__ == '__main__':
    main()
