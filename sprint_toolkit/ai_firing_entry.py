r"""A source game's ai\generic firing entry for ANY weapon (read-only) -- the BALANCED DROP RULE needs the
YARDSTICK's source values beside the port's (the Binary Rifle, C6 2026-10-16: Halo 4's sniper on m020).
ai_firing_profile.build(..., write=False) never saves; ai_firing_profile.py itself writes without --port
(the C4 trap), so this is the safe reader. Map path relative to the MCC folder.

    python ai_firing_entry.py <map> <game> <source weapon tag> [--char ai\generic]
    e.g. python ai_firing_entry.py halo4\maps\m020.map "Halo 4" objects\weapons\rifle\storm_sniper_rifle\storm_sniper_rifle
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ai_firing_profile as A  # noqa: E402

MCC = os.path.dirname(os.path.dirname(HERE))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('game')
    ap.add_argument('weapon')
    ap.add_argument('--char', default='ai\\generic')
    a = ap.parse_args()
    mp = a.map if os.path.isabs(a.map) else os.path.join(MCC, a.map)
    p = A.build(mp, a.game, a.weapon, 'weapons\\(read only)', char=a.char, write=False)
    print(p['source'])
    for k, v in sorted(p['fields'].items(), key=lambda kv: int(kv[0], 16)):
        print('  %-6s %-32s %s' % (k, v[2], round(v[1], 4)))


if __name__ == '__main__':
    main()
