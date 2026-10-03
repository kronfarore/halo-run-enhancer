r"""The SAW ports' OWN audio, made from Halo 4's SAW (storm_lmg) -- for every target game.

Source (2026-10-03): Halo 4's player bank `light_machine_gun_player` in sfxbank.pck,
event names recovered from H4EK's sound tags, audio decoded with vgmstream by
`h4_wwise.py --extract` into H4EK\temp\saw_sounds\<event>\:
    play_wea_lmg_player_fire_in   6 stereo CRACK transients (~84 ms) + 11 mono BODY
                                  layers (0.645 s) + one 0.35 s layer -- Wwise plays a
                                  crack and a body together per shot
    play_wea_lmg_player_fire_out  3 stereo TAILS (2.4-2.7 s), on trigger release
    ..._player_dryfire            1 dry fire
    reload / ready / pose / sprint sets (reload and ready are cued at animation frames:
                                  a later step, matched to each port's retimed graphs)

The older engines play ONE sound per shot (with permutations) plus an optional tail, so
each per-shot permutation here = one crack + one body, mixed (body duplicated to both
channels), peak-limited to -1 dBFS. 48 kHz 16-bit stereo WAV.

    python saw_port_audio.py [--out <dir>]      -> <out>\fire\, tail\, dryfire\
"""
import argparse
import array
import glob
import os
import wave

SRC = r'F:\SteamLibrary\steamapps\common\H4EK\temp\saw_sounds'
OUT = r'F:\SteamLibrary\steamapps\common\H4EK\temp\saw_port_audio'
PEAK = int(32767 * 0.891)                      # -1 dBFS


def read(path):
    with wave.open(path, 'rb') as w:
        ch, sw, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        if sw != 2:
            raise SystemExit('%s: not 16-bit' % path)
        a = array.array('h', w.readframes(n))
    if ch == 1:                                 # mono -> both channels
        st = array.array('h', bytes(len(a) * 4))
        st[0::2] = a
        st[1::2] = a
        a = st
    return a, rate


def write(path, a, rate):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(a.tobytes())


def mix(x, y):
    n = max(len(x), len(y))
    acc = [0] * n
    for src in (x, y):
        for i, v in enumerate(src):
            acc[i] += v
    peak = max(1, max(abs(v) for v in acc))
    g = min(1.0, PEAK / peak)
    return array.array('h', (int(v * g) for v in acc))


def by_length(folder):
    out = []
    for p in sorted(glob.glob(os.path.join(SRC, folder, '*.wav'))):
        with wave.open(p, 'rb') as w:
            out.append((w.getnframes(), w.getnchannels(), p))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    fire = by_length('play_wea_lmg_player_fire_in')
    cracks = [p for n, ch, p in fire if ch == 2 and n < 6000]
    bodies = [p for n, ch, p in fire if ch == 1 and n > 25000]
    if not cracks or not bodies:
        raise SystemExit('run h4_wwise.py --extract first (no cracks/bodies in %s)' % SRC)
    for i, c in enumerate(cracks):
        x, rate = read(c)
        y, _r = read(bodies[i % len(bodies)])
        write(os.path.join(a.out, 'fire', 'saw_fire_%d.wav' % (i + 1)), mix(x, y), rate)
    for i, (_n, _c, p) in enumerate(by_length('play_wea_lmg_player_fire_out')):
        x, rate = read(p)
        write(os.path.join(a.out, 'tail', 'saw_tail_%d.wav' % (i + 1)), x, rate)
    for _n, _c, p in by_length('play_weapons_storm_light_machine_gun_player_dryfire'):
        x, rate = read(p)
        write(os.path.join(a.out, 'dryfire', 'saw_dryfire.wav'), x, rate)
    for d in ('fire', 'tail', 'dryfire'):
        print('%-8s %d wav(s) in %s' % (d, len(glob.glob(os.path.join(a.out, d, '*.wav'))), os.path.join(a.out, d)))


if __name__ == '__main__':
    main()
