r"""What a Halo 3 sound folder actually holds, BEFORE it becomes a port sound: per subsong in
MCC's Halo 3 FMOD bank, its length and a 0.1 s RMS envelope (dBFS).

Written for the Beam Rifle (2026-10-08): `beam_rifle_first_person_fire` is SILENT for 0.3 s
and then two clicks -- only Halo 3's first-person LAYER; the shot is `beam_rifle_fire` (the
user: 'the firing sound is missing'). Its overheat in / loop / out (2.7 + 2.9 + 1.2 s) did not
fit a 2-3 s vent as one piece. Look at every candidate folder before choosing.

    python h3_sound_envelope.py data\sound\weapons\beam_rifle\ [--match fire] [--all]
    (a folder prefix from the bank's .info, as h1_port_sounds 'h3_dir'; lists every sound
     folder under it, with --match only those whose path holds the text)
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h1_port_sounds as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('prefix', help=r'e.g. data\sound\weapons\beam_rifle\ ')
    ap.add_argument('--match', help='only folders whose path holds this')
    ap.add_argument('--all', action='store_true', help='every subsong (default: the first two a folder)')
    ap.add_argument('--steps', type=int, default=30, help='envelope steps shown (0.1 s each)')
    a = ap.parse_args()
    pre = a.prefix.strip().lower()
    idx = S.h3_index()
    folders = sorted(k for k in idx if k.startswith(pre) and (not a.match or a.match.lower() in k))
    if not folders:
        raise SystemExit('no folder under %s in Halo 3\'s bank' % pre)
    for k in folders:
        print(k[len(pre):] or k)
        for sub in (idx[k] if a.all else idx[k][:2]):
            x, r = S.decode(sub)
            h = max(1, int(r * 0.1))
            env = [int(round(20 * np.log10(np.sqrt((x[i:i + h] ** 2).mean()) + 1e-9)))
                   for i in range(0, max(1, len(x) - h), h)]
            print('   #%-6d %5.2f s  %s' % (sub, len(x) / float(r), ' '.join('%4d' % e for e in env[:a.steps])))


if __name__ == '__main__':
    main()
