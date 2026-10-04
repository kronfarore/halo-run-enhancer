r"""Halo 1 SAW: TONE toward the Halo 1 Assault Rifle (user, 2026-10-04: the H1 SAW "sounds
like a Pea Shooter. It needs to go a bit more into the direction of the rough sounding AR").

MEASURED (shot = first 0.25 s, as played in game; h1_saw_sounds.py imports):
    H1 AR fire      rms -10.8 dBFS, peaks at full scale, 26.6% of the energy < 250 Hz,
                    spectral centroid 2.3 kHz -- dark, heavy, hot
    SAW (imported)  rms -12.0 dBFS, 15.8% < 250 Hz, centroid 5.0 kHz -- thin and bright

CANDIDATES, each LEVEL-MATCHED to the AR's shot (what the game plays: the file at the
port's permutation gain 0.708), written to sound_compare\h1_rough for listening:
    A  the SAW as imported, only the level matched
    B  tilt toward the AR: +6 dB shelf below 250 Hz, -6 dB above 4 kHz
    C  B + saturation (tanh drive) for grit, at 22 kHz like the AR
    D  B + the H1 AR's own shot layered under it at -6 dB (literally "toward the AR")
    AR the Halo 1 AR fire itself, for reference

    python h1_saw_tone.py --compare          write the candidates
    (h1_saw_sounds.py TONE = 'A'..'D' imports the pick)
"""
import glob
import os
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'sound_compare', 'h1_rough')
AR_DECODED = os.path.join(OUT, 'decoded')
AR_RMS_DB = -10.8            # the H1 AR shot as played (decoded from its tag)
SHOT = 0.25


def read(p):
    with wave.open(p, 'rb') as r:
        ch, rate = r.getnchannels(), r.getframerate()
        a = np.frombuffer(r.readframes(r.getnframes()), dtype=np.int16).astype(np.float64)
    return a.reshape(-1, ch).mean(1) / 32768.0, rate


def write(p, x, rate):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with wave.open(p, 'wb') as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(rate)
        o.writeframes(np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16).tobytes())


def resample(x, rate, to):
    if rate == to:
        return x
    n = len(x)
    pad = np.concatenate([x, np.zeros(rate // 10)])
    m = int(round(len(pad) * to / rate))
    X = np.fft.rfft(pad)
    Y = np.zeros(m // 2 + 1, dtype=complex)
    k = min(len(Y), len(X))
    Y[:k] = X[:k]
    return (np.fft.irfft(Y, m) * (m / len(pad)))[:int(round(n * to / rate))]


def tilt(x, rate, low_db=6.0, low_hz=250.0, high_db=-6.0, high_hz=4000.0):
    """Zero-phase shelves in the spectrum (smooth 1-octave transitions)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / rate)
    lf = np.log2(np.maximum(f, 1.0))
    lo = 1.0 / (1.0 + np.exp((lf - np.log2(low_hz)) * 4.0))       # 1 below, 0 above
    hi = 1.0 / (1.0 + np.exp(-(lf - np.log2(high_hz)) * 4.0))     # 0 below, 1 above
    g_db = low_db * lo + high_db * hi
    return np.fft.irfft(X * 10 ** (g_db / 20.0), len(x))


def saturate(x, drive=3.0):
    return np.tanh(x * drive) / np.tanh(drive)


def shot_rms_db(x, rate):
    s = x[:int(rate * SHOT)]
    return 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-12)


def level(x, rate, want_db):
    """Soft-limited (0.95*tanh) to a shot RMS of want_db: binary search on the drive."""
    soft = lambda v: 0.95 * np.tanh(v / 0.95)                       # noqa: E731
    lo, hi = 1e-3, 100.0
    for _ in range(60):
        k = (lo * hi) ** 0.5
        if shot_rms_db(soft(x * k), rate) < want_db:
            lo = k
        else:
            hi = k
    return soft(x * (lo * hi) ** 0.5)


def ar_shot(rate):
    p = sorted(glob.glob(os.path.join(AR_DECODED, 'ar_?.wav')))[0]
    x, r = read(p)
    return resample(x, r, rate)


def tone(x, rate, which):
    """The candidate `which` of a mono SAW shot at `rate` (BEFORE levelling)."""
    if which == 'A':
        return x
    y = tilt(x, rate)
    if which == 'B':
        return y
    if which == 'C':
        y22 = resample(y, rate, 22050)
        return resample(saturate(y22 / (np.abs(y22).max() + 1e-12)), 22050, rate)
    if which == 'D':
        a = ar_shot(rate)
        a = np.pad(a, (0, max(0, len(y) - len(a))))[:len(y)]
        yn = y / (np.sqrt((y[:int(rate * SHOT)] ** 2).mean()) + 1e-12)
        an = a / (np.sqrt((a[:int(rate * SHOT)] ** 2).mean()) + 1e-12)
        return yn + an * 10 ** (-6 / 20.0)
    raise ValueError(which)


def main():
    import argparse
    import shutil
    from saw_port_sounds import AUDIO
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--compare', action='store_true')
    a = ap.parse_args()
    if not a.compare:
        print(__doc__)
        return
    src = sorted(glob.glob(os.path.join(AUDIO, 'fire', '*.wav')))[0]
    x, r = read(src)
    x = resample(x, r, 44100)
    for w in 'ABCD':
        y = level(tone(x, 44100, w), 44100, AR_RMS_DB)
        write(os.path.join(OUT, '%s_saw.wav' % w), y, 44100)
        print('%s  shot rms %.1f dBFS, peak %.1f dBFS' % (w, shot_rms_db(y, 44100),
                                                         20 * np.log10(np.abs(y).max())))
    shutil.copyfile(sorted(glob.glob(os.path.join(AR_DECODED, 'ar_?.wav')))[0],
                    os.path.join(OUT, 'AR_reference.wav'))
    print('written to %s' % OUT)


if __name__ == '__main__':
    main()
