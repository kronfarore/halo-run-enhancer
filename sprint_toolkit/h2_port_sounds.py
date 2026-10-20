r"""Step 10 of a Halo 2 port: its OWN sounds, CLASSIC (Opus 48 kHz, as the stock classic sounds),
and every tag that names a borrowed sound repointed (generalized from h2_saw_sounds.py, the SAW
2026-10-03/04 -- its notes stand: import = `sounds-single-layer <dir> <class>` then
`reimport-sounds-to-opus <dir>`; the VOLUME MARKER (port_volume) builds each sound a hair below
its gain so it owns its gestalt entry and the enhancer's knob can shift it).

The config's `sounds` section:
    weapon, fire_fx          the port's weapon and firing effect (kit-relative, with extension)
    audio                    the folder of source wavs (<audio>\<src>\*.wav)
    audio_key                port_volume.MARKER_DB key
    foley_module             a module with mix()/count()/RATE and cue lists ('foley:<CUES>[@stretch]')
    sounds                   {own sound: (audio folder or 'foley:CUES', sound class)}
    repoint_fx, repoint_weapon   (the sound named now, the own sound) on the effect / the weapon
    graph_sounds, graph_sound_dir   ((donor sound, own sound), ...) on both FP graphs
    h3_bank                  {audio folder: [Halo 3 bank source folders]} -- rendered into
                             <audio> first (render_h3_bank; a Halo 3 source, the AR)
    gain, boost              per sound (dB)
    backup, graph_backup     first-run backups (E:)
The sound folder is the config's `reservations['sound_dir']`, the graphs its `fp_graph`.

    python h2_port_sounds.py <key> [--write]
"""
import argparse
import glob
import importlib
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import h2_tagref                                                    # noqa: E402
import port_volume                                                  # noqa: E402
import ports_h2                                                     # noqa: E402
from saw_port_sounds import boosted                                 # noqa: E402

H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
TAGS = os.path.join(H2EK, 'tags')
B = '\\'
# set from the config by setup()
SND_DIR = WEAPON = FIRE_FX = AUDIO = AUDIO_KEY = FOLEY = BACKUP = GRAPH_BACKUP = None
SOUNDS, GAIN, BOOST, REPOINT, GRAPHS = {}, {}, {}, [], []


def setup(key):
    global SND_DIR, WEAPON, FIRE_FX, AUDIO, AUDIO_KEY, FOLEY, BACKUP, GRAPH_BACKUP
    global SOUNDS, GAIN, BOOST, REPOINT, GRAPHS
    cfg = ports_h2.load(key)
    c, r = ports_h2.get(key, 'sounds'), cfg['reservations']
    SND_DIR, WEAPON, FIRE_FX = r['sound_dir'], c['weapon'], c['fire_fx']
    AUDIO = c.get('audio') or __import__('saw_port_sounds').AUDIO
    AUDIO_KEY, FOLEY = c['audio_key'], c.get('foley_module', 'saw_port_foley')
    SOUNDS, GAIN, BOOST = dict(c['sounds']), dict(c.get('gain', {})), dict(c.get('boost', {}))
    BACKUP, GRAPH_BACKUP = c['backup'], c['graph_backup']
    GRAPHS = [B.join(['objects', 'characters', sp, 'fp', r['fp_graph'] + '.model_animation_graph'])
              for sp in ports_h2.SPECIES]
    rp = []
    if c.get('repoint_fx'):
        rp.append((FIRE_FX, c['repoint_fx'][0], SND_DIR + B + c['repoint_fx'][1]))
    if c.get('repoint_weapon'):
        rp.append((WEAPON, c['repoint_weapon'][0], SND_DIR + B + c['repoint_weapon'][1]))
    rp += [(g, c['graph_sound_dir'] + s, SND_DIR + B + n) for g in GRAPHS
           for s, n in c.get('graph_sounds', ())]
    REPOINT = rp


def tool(*args):
    r = subprocess.run([os.path.join(H2EK, 'tool.exe')] + list(args), cwd=H2EK,
                       capture_output=True, text=True, errors='replace')
    return r.stdout + r.stderr


def read_tag(name):
    """(gain base, compression) of an own sound tag, through the kit's XML export. H2's
    export wants ABSOLUTE paths for both files (a relative output is written empty) and
    writes `<field name="gain base" type="real">-3.000000</field>`."""
    x = os.path.join(H2EK, 'temp', '_h2port_snd_%d.xml' % os.getpid())
    os.makedirs(os.path.dirname(x), exist_ok=True)
    if os.path.exists(x):
        os.remove(x)
    tool('export-tag-to-xml', os.path.join(TAGS, SND_DIR, name + '.sound'), x)
    txt = open(x, encoding='utf-8', errors='replace').read() if os.path.exists(x) else ''
    g = re.search(r'<field name="gain base"[^>]*>([^<]*)<', txt, re.I)
    c = re.findall(r'<field name="compression"[^>]*>([^<]*)<', txt, re.I)
    return (float(g.group(1)) if g else None), sorted(set(c))


def backup():
    if os.path.exists(BACKUP):
        print('backup exists: %s' % BACKUP)
        return
    for rel in (WEAPON, FIRE_FX):
        d = os.path.join(BACKUP, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(os.path.join(TAGS, rel), d)
    print('backup: %s' % BACKUP)


def render_foley(name, cues_name, d):
    """One wav per variation set of the Halo 4 foley mix (48 kHz mono, as recorded)."""
    import wave
    import numpy as np
    foley = importlib.import_module(FOLEY)
    cues_name, _at, stretch = cues_name.partition('@')
    stretch = float(stretch or 1.0)
    cues = getattr(foley, cues_name)
    for k in range(foley.count(cues)):
        x = foley.mix(cues, k, stretch)
        if np.abs(x).max() > 0.95:
            x = 0.95 * np.tanh(x / 0.95)
        with wave.open(os.path.join(d, '%s_%d.wav' % (name, k + 1)), 'wb') as o:
            o.setnchannels(1)
            o.setsampwidth(2)
            o.setframerate(foley.RATE)
            o.writeframes(np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16).tobytes())


def render_h3_bank(c):
    """`h3_bank` {sound folder under AUDIO: [Halo 3 bank folders]} (the AR, wave-A pilot,
    2026-10-20): every permutation of a HALO 3 sound decoded from MCC's halo3 sfx.fsb by its
    source folder (h1_port_sounds.h3_index / decode, Halo 1 wave A's), resampled to 48 kHz
    mono at its NATIVE level (peaks soft-limited at 0.95), one wav each -- several folders
    mixed permutation k with permutation k. Written fresh every run."""
    import wave
    import numpy as np
    import h1_port_sounds as P
    import h1_saw_tone as tone
    P.use_bank({})
    idx = P.h3_index()
    for name, folders in c['h3_bank'].items():
        sets = []
        for f in folders:
            subs = idx.get(f.lower().rstrip('\\') + '\\')
            if not subs:
                raise SystemExit('%s: no %s in Halo 3\'s bank' % (name, f))
            sets.append([tone.resample(*P.decode(s), 48000) for s in subs])
        d = os.path.join(AUDIO, name)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        for k in range(max(len(s) for s in sets)):
            parts = [s[k % len(s)] for s in sets]
            x = np.zeros(max(len(p) for p in parts))
            for p in parts:
                x[:len(p)] += p
            if np.abs(x).max() > 0.95:
                x = 0.95 * np.tanh(x / 0.95)
            with wave.open(os.path.join(d, '%s_%d.wav' % (name, k + 1)), 'wb') as o:
                o.setnchannels(1)
                o.setsampwidth(2)
                o.setframerate(48000)
                o.writeframes(np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16).tobytes())
        print('   %-14s %d permutation(s) from %s' % (name, max(len(s) for s in sets),
                                                    ', '.join(f.split('\\')[-1] for f in folders)))


def backup_graphs():
    for g in GRAPHS:
        keep = os.path.join(GRAPH_BACKUP, g)
        if not os.path.exists(keep):
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copyfile(os.path.join(TAGS, g), keep)


def import_sounds():
    shutil.rmtree(os.path.join(TAGS, SND_DIR), ignore_errors=True)
    shutil.rmtree(os.path.join(H2EK, 'data', SND_DIR), ignore_errors=True)
    for name, (src, cls) in SOUNDS.items():
        d = os.path.join(H2EK, 'data', SND_DIR, name)
        os.makedirs(d)
        if src.startswith('foley:'):
            render_foley(name, src.split(':', 1)[1], d)
        for w in sorted(glob.glob(os.path.join(AUDIO, src, '*.wav'))) if ':' not in src else ():
            dst = os.path.join(d, os.path.basename(w))
            if BOOST.get(name):
                boosted(w, dst, BOOST[name])
            else:
                shutil.copyfile(w, dst)
        out = tool('sounds-single-layer', SND_DIR + B + name, cls)
        ok = os.path.exists(os.path.join(TAGS, SND_DIR, name + '.sound'))
        print('   %-12s %-12s %d wav -> %s' % (name, cls, len(os.listdir(d)), 'ok' if ok else 'FAILED'))
        if not ok:
            print(out[-1500:])
            raise SystemExit('import failed')
    out = tool('reimport-sounds-to-opus', SND_DIR)
    for name in SOUNDS:
        _g, comp = read_tag(name)
        print('   %-12s compression %s' % (name, comp))
        if not any('opus' in c.lower() for c in comp):
            print(out[-1500:])
            raise SystemExit('%s is not Opus after the reimport' % name)


def set_gain():
    marker = port_volume.MARKER_DB[AUDIO_KEY]
    for name in SOUNDS:
        want = GAIN.get(name, -3.0) - marker
        tool('process-sounds', SND_DIR, name, 'gain=', str(want))
        got, _c = read_tag(name)
        print('   %-12s gain base %s dB (want %+.2f)' % (name, got, want))
        if got is None or abs(got - want) > 0.005:
            raise SystemExit('%s: gain base %s, wanted %s' % (name, got, want))


def repoint():
    for rel, old, new in REPOINT:
        path = os.path.join(TAGS, rel)
        have = h2_tagref.references(path)
        if ('snd!', new) in have and ('snd!', old) not in have:
            print('   %-16s already names %s' % (os.path.basename(rel), new))
            continue
        h2_tagref.set_reference(path, 'snd!', old, new)
        print('   %-16s %s -> %s' % (os.path.basename(rel), old, new))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    setup(a.key)
    c = ports_h2.get(a.key, 'sounds')
    if c.get('h3_bank') and a.write:
        print('the Halo 3 sounds, from MCC\'s halo3 bank:')
        render_h3_bank(c)
    plain = [src for src, _c in SOUNDS.values() if ':' not in src]
    if plain and not glob.glob(os.path.join(AUDIO, plain[0], '*.wav')):
        raise SystemExit('no source audio in %s -- extract it first' % os.path.join(AUDIO, plain[0]))
    if not a.write:
        for rel, old, new in REPOINT:
            print('would repoint %s: %s -> %s' % (rel, old, new))
        print('(dry run -- pass --write)')
        return
    backup()
    backup_graphs()
    import_sounds()
    set_gain()
    repoint()
    print('done -- rebuild the levels that carry the port')


if __name__ == '__main__':
    main()
