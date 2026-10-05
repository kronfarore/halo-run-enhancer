r"""The LEVEL a port's own sound should have: the donor's, measured from the game itself.

Halo 3 / ODST / Reach play their stock sounds from the game's FMOD bank
(`<game>\fmod\pc\sfx.fsb`, entry k of sfx.fsb.info = subsong k+1). This decodes the
donor's permutations with vgmstream, takes their ACTIVE RMS (samples with |x| > 0.01, so
silence does not count) and adds the donor tag's gain base (kit XML export):
effective = active RMS + gain. The port's own mix is then rendered at the donor's active
RMS and built with the donor's gain (saw_port_sounds.py `foley` targets + `gain`). This
is how every SAW foley level was set (2026-10-04); the user then trimmed by ear
(H3 +5 dB, 2026-10-05).

    python port_sound_levels.py --game h3 ar_reload ar_ready ar_melee1
    python port_sound_levels.py --game reach --dir sound\weapons\assault_rifle ar_ready_hero
    python port_sound_levels.py --foley            the H4 SAW mixes (saw_port_foley.py)

Promoted from a scratch script (foley_levels.py), 2026-10-05. Needs vgmstream-cli
(VGM below).
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MCC = os.path.dirname(os.path.dirname(HERE))
VGM = r'F:\Tools\vgmstream\vgmstream-cli.exe'
B = '\\'
#: game -> (MCC folder, kit)
GAMES = {'h3': ('halo3', 'H3EK'), 'odst': ('halo3odst', 'H3ODSTEK'), 'reach': ('haloreach', 'HREK')}


def active_rms(x):
    a = x[np.abs(x) > 0.01]
    return 20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-12) if len(a) else -99.0


def read_wav(p):
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    return x.reshape(-1, w.getnchannels()).mean(1) / 32768


def gain_base(kit, tag):
    root = os.path.join(r'F:\SteamLibrary\steamapps\common', kit)
    out = os.path.join(root, 'temp', '_lv.xml')
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(root, 'tool.exe'), 'export-tag-to-xml',
                    os.path.join(root, 'tags', tag + '.sound'), out], capture_output=True, cwd=root)
    if not os.path.exists(out):
        return None
    m = re.search(r'name="gain base" value="([^"]*)"', open(out, encoding='utf-8', errors='replace').read())
    return float(m.group(1)) if m else None


def measure(game, folder, names, perms=4):
    mcc_dir, kit = GAMES[game]
    pc = os.path.join(MCC, mcc_dir, 'fmod', 'pc')
    info = open(os.path.join(pc, 'sfx.fsb.info'), 'rb').read()
    paths = [m.group(0).decode('latin-1').lower() for m in
             re.finditer(rb'data[\x5c][\x20-\x7e]+?\.(?:wav|aif|aiff)', info)]
    tmp = tempfile.mkdtemp()
    want = B + folder.strip(B).lower().split(B)[-1] + B
    for n in names:
        idx = [i for i, p in enumerate(paths) if (want + n.lower() + B) in p]
        vals = []
        for i in idx[:perms]:
            o = os.path.join(tmp, '%d.wav' % i)
            subprocess.run([VGM, '-s', str(i + 1), '-o', o, os.path.join(pc, 'sfx.fsb')], capture_output=True)
            if os.path.exists(o):
                vals.append(active_rms(read_wav(o)))
        g = gain_base(kit, folder.strip(B) + B + n)
        r = float(np.mean(vals)) if vals else None
        print('%-6s %-26s %2d perms  active rms %-6s gain %-6s -> effective %s' % (
            game, n, len(idx), None if r is None else round(r, 1), g,
            None if r is None or g is None else round(r + g, 1)))


def foley_levels():
    import saw_port_foley as foley
    for name in ('RELOAD', 'READY', 'MELEE1', 'MELEE2', 'POSE1', 'POSE2', 'READY_INITIAL'):
        cues = getattr(foley, name, None)
        if cues:
            print('H4 %-14s active rms %s' % (name, [round(float(active_rms(foley.mix(cues, k))), 1)
                                                    for k in range(foley.count(cues))]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', choices=sorted(GAMES))
    ap.add_argument('--dir', default=B.join(['sound', 'weapons', 'assault_rifle']),
                    help='the donor sounds\' tag folder (default: the AR\'s)')
    ap.add_argument('--foley', action='store_true')
    ap.add_argument('names', nargs='*', help='donor sound tag names in that folder')
    a = ap.parse_args()
    if a.foley:
        foley_levels()
    if a.game:
        measure(a.game, a.dir, a.names)
    if not (a.foley or a.game):
        ap.print_help()


if __name__ == '__main__':
    main()
