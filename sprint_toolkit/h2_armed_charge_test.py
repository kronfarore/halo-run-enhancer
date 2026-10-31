r"""TEST-MAP patches for an Armed melee weapon in Halo 2 (the Gravity Hammer, A5, 2026-10-30/31): run on a
staged map after h2_port_test_map.py --stage, never on a shipping one. The AI's closing in is the
enhancer's to ship; these are the values the user confirmed.

    python h2_armed_charge_test.py <map> [--allies] [--marines] [--tough]

    (always)    Charge Properties of ai\generic and of every species character (never Tartarus): Consider
                8, Chance 1, Attack 1.5, Abort 12, Timeout 8; style behaviour melee_charge on.
    --allies    the enhancer's ally teach, which test maps do not run: a class Marines lack.
    --marines   Marines harder: Consider 15, Abort 20, Timeout 15, Delay 0.5, style Aggressive.
    --tough     Marines 5000 body vitality: they live to be watched.
"""
import argparse
import os
import struct
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import halo2_map
import halo_patch as hp
import h2_enemy_weapons as E

CHAR_CHARGE, CHARGE_ES = 0x7C, 0x40
CHAR_VITALITY, VITALITY_ES = 0x3C, 0x70
STYL_ATTITUDE, STYL_ENGAGE, STYL_BEHAVIORS, MELEE_CHARGE = 0x24, 0x28, 0x38, 16
SPECIES = ('grunt', 'jackal', 'bugger', 'elite', 'brute', 'floodcombat', 'heretic', 'marine')


def charge(m, marines):
    rows = 0
    for t in m.tags_of_class('char'):
        name = t['name'] or ''
        if 'tartarus' in name or not (name.endswith('generic') or any(sp in name for sp in SPECIES)):
            continue
        hard = marines and 'marine' in name
        for e in m.follow_all(t['base'], [CHAR_CHARGE], [CHARGE_ES], 'all'):
            struct.pack_into('<ffff', m.data, e + 4, 15.0 if hard else 8.0, 1.0, 1.5, 20.0 if hard else 12.0)
            struct.pack_into('<f', m.data, e + 0x14, 15.0 if hard else 8.0)
            if hard:
                struct.pack_into('<f', m.data, e + 0x18, 0.5)
            rows += 1
    print('charge rows written', rows)
    for t in m.tags_of_class('styl'):
        name = t['name'] or ''
        if 'tartarus' in name or not any(sp in name for sp in SPECIES):
            continue
        v = struct.unpack_from('<I', m.data, t['base'] + STYL_BEHAVIORS)[0]
        struct.pack_into('<I', m.data, t['base'] + STYL_BEHAVIORS, v | (1 << MELEE_CHARGE))
        if marines and 'marine' in name:
            struct.pack_into('<H', m.data, t['base'] + STYL_ATTITUDE, 2)
            m.data[t['base'] + STYL_ENGAGE] = 3


def tough(m):
    for t in m.tags_of_class('char'):
        if 'marine' in (t['name'] or ''):
            for e in m.follow_all(t['base'], [CHAR_VITALITY], [VITALITY_ES], 'all'):
                struct.pack_into('<ffff', m.data, e + 4, 5000.0, 0.0, 5000.0, 0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('--allies', action='store_true')
    ap.add_argument('--marines', action='store_true')
    ap.add_argument('--tough', action='store_true')
    a = ap.parse_args()
    if a.allies:
        m = hp.open_map(a.map, 'Halo 2')
        for r in E.ally_teach(m, hp):
            print(r.get('field'), r.get('ok'), str(r.get('reason'))[:90])
        m.save(a.map)
    m = halo2_map.Halo2Map(a.map)
    charge(m, a.marines)
    if a.tough:
        tough(m)
    m.save(a.map)
    print('saved')


if __name__ == '__main__':
    main()
