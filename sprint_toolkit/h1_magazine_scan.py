r"""Which Halo 1 weapons take ammo from a pickup, and what they take.

Halo 1 is the only game that works this way: a weapon's magazine names an EQUIPMENT tag
and how many rounds walking over one gives. Every later game hands ammo over with the
weapon itself, so this control only makes sense here.

Scans every campaign map so the list is the union, not whatever one level happens to
carry, and records which missions each weapon appears in.

    python h1_magazine_scan.py [--write]      # --write updates the catalog
"""
import argparse, contextlib, io, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection', 'tool')
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
GAME = 'Halo 1'
OUT = os.path.join(TOOL, 'h1_magazine_catalog.json')
# weap Magazines @0x4F0 (elem 0x70) -> Magazine Items @0x64 (elem 0x1C):
# Rounds i16@0, Equipment tagRef@0xC (ident at +0xC)
MAG, MAG_EL, ITEM, ITEM_EL, EQUIP = 0x4F0, 0x70, 0x64, 0x1C, 0xC


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    he.load_settings()
    weapons, items = {}, {}
    for mission in he.CONFIG['h1_campaign_maps']:
        src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo1', mission), GAME)
        if not os.path.exists(src):
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            m = hp.open_map(src, GAME)
        for path, base in m.find_tags('weap', '*'):
            for mag in m.follow_all(base, [MAG], [MAG_EL], 'all'):
                for it in m.follow_all(mag, [ITEM], [ITEM_EL], 'all'):
                    rounds = struct.unpack_from('<h', m.data, it)[0]
                    datum = m.u32(it + EQUIP + 0xC)
                    name = hp._tag_name_by_id(m, datum) if datum != 0xFFFFFFFF else None
                    e = weapons.setdefault(path, {'rounds': rounds, 'item': name,
                                                  'maps': set()})
                    e['maps'].add(mission)
                    if isinstance(name, str) and name:
                        items.setdefault(name, set()).add(mission)
        del m

    print('%-46s %-8s %s' % ('weapon', 'rounds', 'pickup item'))
    for w in sorted(weapons):
        e = weapons[w]
        print('%-46s %-8s %s' % (w.rsplit(B, 1)[-1], e['rounds'],
                                 (e['item'] or '(none)').rsplit(B, 1)[-1]))
    print('\n%d weapon(s) with a magazine, %d pickup item(s)' % (len(weapons), len(items)))

    if a.write:
        missions = he.CONFIG['h1_campaign_maps']
        data = {'game': GAME,
                'weapons': [{'tag': w, 'rounds': e['rounds'], 'item': e['item'],
                             'maps': sorted(e['maps'])}
                            for w, e in sorted(weapons.items())],
                'items': [{'tag': t,
                           'label': t.rsplit(B, 1)[-1].title(),
                           **({} if set(ms) == set(missions) else {'maps': sorted(ms)})}
                          for t, ms in sorted(items.items())]}
        json.dump(data, open(OUT, 'w', encoding='utf-8'), indent=1)
        print('wrote %s' % OUT)


if __name__ == '__main__':
    main()
