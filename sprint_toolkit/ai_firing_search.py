r"""Step 11, read-only: which maps of a game carry an ai\generic entry for a weapon -- ai_firing_entry.py over every
map (the Railgun, C7 2026-10-16: phase 0 searched only the MP tag and found none; the campaign tag
`storm_rail_gun_pve` has one in nine Halo 4 campaign maps, with different drop odds per map). Prints one line a
map and weapon: the entry's last field (or why there is none); run ai_firing_entry.py on a map it names for the
whole entry.

    python ai_firing_search.py "Halo 4" halo4\maps objects\weapons\rifle\storm_rail_gun\storm_rail_gun_pve ^
                               objects\weapons\rifle\storm_rail_gun\storm_rail_gun [--prefix m]
`--prefix`: only maps whose file name starts with it (Halo 4's campaign: m).
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MCC = os.path.dirname(os.path.dirname(HERE))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('game')
    ap.add_argument('maps', help='the maps folder, relative to the MCC folder (e.g. halo4\\maps)')
    ap.add_argument('weapons', nargs='+')
    ap.add_argument('--prefix', default='')
    a = ap.parse_args()
    folder = os.path.join(MCC, a.maps)
    for m in sorted(os.listdir(folder)):
        if not m.endswith('.map') or not m.startswith(a.prefix):
            continue
        for w in a.weapons:
            r = subprocess.run([sys.executable, os.path.join(HERE, 'ai_firing_entry.py'),
                                os.path.join(a.maps, m), a.game, w],
                               cwd=HERE, capture_output=True, text=True, errors='replace')
            out = (r.stdout + r.stderr).strip().splitlines()
            print('%-22s %-40s | %s' % (m, w.split('\\')[-1], out[-1].strip()[:110] if out else '(no output)'),
                  flush=True)


if __name__ == '__main__':
    main()
