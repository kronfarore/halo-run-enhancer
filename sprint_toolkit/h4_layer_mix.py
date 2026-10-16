r"""Candidate MIXES of a Halo 4 event's layers as WAVs for the user to listen to, read-only for the kit (the
Sticky Detonator, C8, 2026-10-16: 'the firing sound is the wrong kind of sound'). Each candidate = a set of
extract indices (one sound per layer, h4_event_layers.py lists them), summed, levelled like h1_port_sounds
(active RMS to --level dB, then the 0.95 tanh soft limit) or peak-normalised (--peak).

THE LESSON: mixes of the SAME layers at different levels were indistinguishable to the user; candidates from
DIFFERENT material (subsets without some layers, another event's recordings) found the bad layers in one
round. Make the candidates differ in WHAT plays.

    python h4_layer_mix.py sticky_detonator_player play_weapons_storm_sticky_detonator_player_fire <out dir> ^
        all=0,4,6,9,12,13,14,17,19 without_12_13=0,4,6,9,14,17,19 only_12_13=12,13 [--level -12.8 | --peak]
"""
import argparse
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
H4_WORK = os.path.join(HERE, 'out', 'h4_sounds')


def load(path):
    with wave.open(path) as w:
        n, sr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(float) / 32768
    return x.reshape(-1, ch).mean(1), sr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bank')
    ap.add_argument('event')
    ap.add_argument('out')
    ap.add_argument('candidates', nargs='+', help='name=k,k,...')
    ap.add_argument('--level', type=float, default=-12.8)
    ap.add_argument('--peak', action='store_true', help='peak-normalise to 0.95 instead of the level')
    a = ap.parse_args()
    d = os.path.join(H4_WORK, a.bank, a.event)
    files = {int(f.split('_')[0]): os.path.join(d, f) for f in os.listdir(d) if f.endswith('.wav')}
    os.makedirs(a.out, exist_ok=True)
    for spec in a.candidates:
        name, ids = spec.split('=')
        parts = [load(files[int(k)]) for k in ids.split(',')]
        sr = parts[0][1]
        y = np.zeros(max(len(p) for p, _ in parts))
        for p, _ in parts:
            y[:len(p)] += p
        if a.peak:
            y *= 0.95 / np.abs(y).max()
        else:
            act = y[np.abs(y) > 0.01]
            y *= 10 ** ((a.level - 20 * np.log10(np.sqrt((act ** 2).mean()))) / 20)
            peak = np.abs(y).max()
            y = 0.95 * np.tanh(y / 0.95)
            print('%-24s peak before the limiter %.2f' % (name, peak))
        out = os.path.join(a.out, name + '.wav')
        with wave.open(out, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
        print(out)


if __name__ == '__main__':
    main()
