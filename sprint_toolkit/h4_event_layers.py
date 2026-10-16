r"""A Halo 4 Wwise EVENT's LAYERS, read-only (the Sticky Detonator, C8, 2026-10-16): one line per action of
the event -- its target's HIRC type, its id, and the sounds under it as the extract's indices with their
length, active RMS and spectral centroid. A `random/sequence` line is ONE layer (Halo 4 picks one of its
sounds); several lines play together. That is exactly what an h1_port_sounds spec names:
`<event>:k,k,..` = one layer (its random choices), several specs = the layers mixed. A STOP action (type
0x01xx) is marked: its sounds are not a layer (the explosion's flight-loop stop).

The extract (h4_wwise.extract) numbers an event's sounds in walk order; this lists the same indices, so
the spec can be read straight off. Run h1_port_sounds once (or h4_wwise --extract) so the WAVs exist.

    python h4_event_layers.py sticky_detonator_player play_weapons_storm_sticky_detonator_player_fire
    python h4_event_layers.py proj_sticky_detonator play_proj_storm_sticky_detonator_nonplayer_explosion

Why it exists: the Sticky Detonator's fire event has 11 actions (10 layers); two loud short layers made the
'wrong kind of sound' -- found by mixing candidate SUBSETS of these layers for the user.
"""
import argparse
import os
import struct
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_wwise as W  # noqa: E402

H4_WORK = os.path.join(HERE, 'out', 'h4_sounds')        # h1_port_sounds' extract cache


def wav_stats(path):
    with wave.open(path) as w:
        n, sr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(float) / 32768
    x = x.reshape(-1, ch).mean(1)
    a = x[np.abs(x) > 0.01]
    rms = 20 * np.log10(np.sqrt((a ** 2).mean())) if len(a) else -99.0
    sp = np.abs(np.fft.rfft(x))
    fr = np.fft.rfftfreq(len(x), 1.0 / sr)
    cen = float((sp * fr).sum() / sp.sum()) if sp.sum() else 0.0
    return n / float(sr), rms, cen, ch


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bank')
    ap.add_argument('events', nargs='+')
    a = ap.parse_args()
    p = W.read_pck(W.BANKS)
    b = W.bank_bytes(W.BANKS, p['banks'][W.fnv(a.bank)])
    objs = W.hirc(b)
    byid = {o: (t, d) for t, o, d in objs}
    sounds = {o for t, o, _d in objs if t == 2}
    for ev in a.events:
        eid = W.fnv(ev)
        if eid not in byid:
            print('== %s: not in %s' % (ev, a.bank))
            continue
        idx = {sid: k for k, (_v, sid) in enumerate(W.event_sounds(b, objs, eid))}
        wav_dir = os.path.join(H4_WORK, a.bank, ev)
        files = {}
        if os.path.isdir(wav_dir):
            for f in os.listdir(wav_dir):
                if f.endswith('.wav'):
                    files[int(f.split('_')[0])] = os.path.join(wav_dir, f)
        print('== %s (%s)%s' % (ev, a.bank, '' if files else '  -- no WAVs yet: run the extract'))
        d = byid[eid][1]
        n = struct.unpack_from('<I', d, 0)[0]
        for aid in struct.unpack_from('<%dI' % n, d, 4):
            ad = byid.get(aid, (None, b''))[1]
            if not ad:
                continue
            kind, tgt = struct.unpack_from('<HI', ad, 0)
            if tgt in sounds:
                ks = [tgt]
            elif tgt in byid:
                body = byid[tgt][1]
                ks = list(dict.fromkeys(v for v in (struct.unpack_from('<I', body, i)[0]
                                                    for i in range(len(body) - 3)) if v in sounds))
            else:
                ks = []
            typ = W.HIRC_TYPES.get(byid.get(tgt, (None,))[0], 'missing')
            parts = []
            for s in ks:
                k = idx.get(s)
                if k in files:
                    sec, rms, cen, ch = wav_stats(files[k])
                    parts.append('%d (%.2fs %.1fdB %dHz%s)' % (k, sec, rms, cen, ' st' if ch > 1 else ''))
                else:
                    parts.append(str(k))
            verb = 'STOP ' if kind >> 8 == 0x01 else ''
            print('  %s%-16s %#010x  %s' % (verb, typ, tgt, ', '.join(parts) or '-'))


if __name__ == '__main__':
    main()
