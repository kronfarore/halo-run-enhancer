r"""The LEVEL of stock Halo 1 sounds as MCC plays them -- the targets a port's sounds are set to.

MCC plays Halo 1 audio from halo1\sound\pc\sounds_adpcm.fsb by tag path (memory
h1-fmod-bank-sounds; the classic tags are listed as sound\old_sfx\...), never from the map.
This finds each named sound in the bank's lst, decodes every permutation with vgmstream
(cached in out\h1_bank) and prints per permutation: the ACTIVE RMS (samples above 0.01 --
the same measure h1_port_sounds.py's targets use), length and peak.

Written for the SMG pilot (2026-10-07): the levels in ports_h1/smg.py's sounds section
(AR fire -13.1/-12.2/-13.0/-13.8, dryfire -17.6, ar_reload -20.9, ...) came from it.

    python h1_stock_sound_levels.py "assault rifle\fire" "weapon_anims\ar_reload"
    (a path tail under sound\old_sfx\weapons; matched case-insensitively at the end)
"""
import argparse
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
import h1_fsb                    # noqa: E402
import h1_saw_tone as tone       # noqa: E402

MCC = os.path.dirname(TOOL)
SND = os.path.join(MCC, 'halo1', 'sound', 'pc')
VGMSTREAM = os.path.join('F:' + os.sep, 'Tools', 'vgmstream', 'vgmstream-cli.exe')
CACHE = os.path.join(HERE, 'out', 'h1_bank')


def levels(tail):
    """[(lst name, [(active rms dB, seconds, peak dB) per permutation])] for a path tail."""
    _ver, entries = h1_fsb.read_lst(os.path.join(SND, 'lst', 'sounds_adpcm.lst.bin'))
    want = '\\' + tail.lower().strip('\\')
    out = []
    os.makedirs(CACHE, exist_ok=True)
    for name, first, count in entries:
        if not name.lower().endswith(want):
            continue
        perms = []
        for k in range(count):
            wav = os.path.join(CACHE, '%d.wav' % (first + k))
            if not os.path.exists(wav):
                subprocess.run([VGMSTREAM, '-s', str(first + k + 1), '-o', wav,
                                os.path.join(SND, 'sounds_adpcm.fsb')], capture_output=True)
            x, rate = tone.read(wav)
            x = np.asarray(x)
            act = x[np.abs(x) > 0.01]
            rms = 20 * np.log10(np.sqrt((act ** 2).mean())) if len(act) else -99.0
            perms.append((rms, len(x) / float(rate), 20 * np.log10(np.abs(x).max() + 1e-12)))
        out.append((name, perms))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sounds', nargs='+')
    a = ap.parse_args()
    for tail in a.sounds:
        hits = levels(tail)
        if not hits:
            print('%-48s not in the bank' % tail)
        for name, perms in hits:
            print('%-48s perms %d  active rms %s  len %s  peak %s' % (
                name, len(perms), '/'.join('%.1f' % p[0] for p in perms),
                '/'.join('%.2f' % p[1] for p in perms), '/'.join('%.1f' % p[2] for p in perms)))


if __name__ == '__main__':
    main()
