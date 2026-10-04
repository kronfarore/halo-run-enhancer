r"""The Halo 1 SAW's OWN firing sounds -- Halo 4's SAW audio (saw_port_audio.py) through
the HCEEK's sound import. CLASSIC ONLY (user, 2026-10-03: every H1/H2 rebuild is classic).

WHAT IT PLAYED (port_sound_refs.py, 2026-10-03): the Assault Rifle's own firing effect
`weapons\assault rifle\effects\fire bullet` (AR fire + the pistol's casing eject) and its
`empty` effect (AR dry fire) -- SHARED with the real AR, so the SAW gets OWN copies:

    weapons\saw\effects\fire bullet.effect   AR fire -> the SAW's, the casing eject kept
    weapons\saw\effects\empty.effect         AR dry fire -> the SAW's

and the weapon names them (in place here; saw_weapon.py does the same on a regeneration).

HOW CLASSIC HALO 1 PLAYS (measured on a10): the map carries the sound, Xbox ADPCM, the
AR fire 22 kHz mono. The SAW audio (48 kHz stereo) is resampled to 44.1 kHz mono and
imported UNCOMPRESSED (`tool sounds <data dir> wav` -> compression none): the kit's
`xbox` route encodes through a Windows ACM codec this machine lacks -- it printed
"MM: couldn't open stream (ACMERR_NOTPOSSIBLE)", still wrote the tag, with EMPTY
permutations, and the first build shipped a silent SAW (2026-10-03; the user heard only
the casing click and called it a pea shooter). Every permutation is now checked for
samples. The playback fields (distances, pitch, cone, random gain) are copied from the
AR's sound so it carries like the AR.

VOLUME (port_volume.py): a Halo 1 sound tag holds its own gains -- there is no shared
pool and no marker. The knob scales the permutations' GAIN (a linear fraction; 0 in a
tag means 1.0 in the map). HEADROOM RULE as elsewhere: built at -3 dB (0.708) with the
audio soft-limited +3 dB (saw_port_sounds.boosted), so the as-built level is the plain
import's and the knob has +3 up before 1.0.

    python h1_saw_sounds.py [--write]

Then rebuild the maps (all ten carry the SAW): h1_rebuild_all.py --maps a10 for a test.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env                                                          # noqa: E402,F401
from reclaimer.hek.defs.effe import effe_def                        # noqa: E402
from reclaimer.hek.defs.snd_ import snd__def                        # noqa: E402
from reclaimer.hek.defs.weap import weap_def                        # noqa: E402
from saw_port_sounds import AUDIO, boosted                          # noqa: E402
import h1_saw_tone as tone_mod                                      # noqa: E402
sys.path.insert(0, os.path.dirname(HERE))
import h1_fsb                                                       # noqa: E402

HCEEK = r'F:\SteamLibrary\steamapps\common\HCEEK'
TAGS = os.path.join(HCEEK, 'tags')
B = '\\'
# NOT under sound\sfx (2026-10-04): there the game CRASHED the moment the SAW became
# active (halo1.dll+0xB3605D) -- with the stock bank, with our classic and Anniversary
# index entries, and with stock-shaped 22 kHz ADPCM tags alike (tests 2-4); outside it
# (tests 0-1) it never crashed. Working theory: MCC pairs every sound\sfx tag with an
# Anniversary counterpart by path, and a new one has none.
SND_DIR = B.join(['sound', 'weapons', 'saw_port'])
AR_SND = B.join(['sound', 'sfx', 'weapons', 'assault rifle'])
#: own sound -> (audio folder, the AR sound whose playback fields it takes)
SOUNDS = {'saw_fire': ('fire', AR_SND + B + 'fire'),
          'saw_dryfire': ('dryfire', AR_SND + B + 'dryfire')}
AR_FX = B.join(['weapons', 'assault rifle', 'effects'])
OWN_FX = B.join(['weapons', 'saw', 'effects'])
#: own effect -> (the AR's, [(sound it names, own sound)])
EFFECTS = {'fire bullet': (AR_FX + B + 'fire bullet', [(AR_SND + B + 'fire', SND_DIR + B + 'saw_fire')]),
           'empty': (AR_FX + B + 'empty', [(AR_SND + B + 'dryfire', SND_DIR + B + 'saw_dryfire')])}
WEAPON = B.join(['weapons', 'saw', 'saw.weapon'])
RATE = 44100
#: 'wav' = uncompressed (compression none); 'xbox' needs an ACM codec this machine lacks
FORMAT = 'wav'
#: the fire's TONE (h1_saw_tone.py candidates A-D; the user picks by ear): None = the plain
#: import (thin and bright next to the H1 AR -- "a Pea Shooter")
TONE = 'D'          # user's pick 2026-10-04 (A, the plain import, was still 'a Pea Shooter')
HEADROOM_DB = 0.0          # the map tag gain is not what plays (the FMOD bank is); stock-like 1.0
BACKUP = r'E:\HaloBackups\HCEEK_saw_before_sounds'
#: playback fields copied from the AR's sound tag
COPY = ('flags', 'sound_class', 'minimum_distance', 'maximum_distance', 'skip_fraction',
        'random_pitch_bounds', 'inner_cone_angle', 'outer_cone_angle', 'outer_cone_gain',
        'gain_modifier', 'maximum_bend_per_second')


def mono_44k(src, dst):
    """48 kHz stereo 16-bit -> 44.1 kHz mono (FFT resample, padded so the wrap is silent)."""
    with wave.open(src, 'rb') as r:
        ch, rate, n = r.getnchannels(), r.getframerate(), r.getnframes()
        a = np.frombuffer(r.readframes(n), dtype=np.int16).astype(np.float64).reshape(-1, ch)
    x = a.mean(1)
    pad = rate // 10
    x = np.concatenate([x, np.zeros(pad)])
    m = int(round(len(x) * RATE / rate))
    X = np.fft.rfft(x)
    keep = m // 2 + 1
    Y = np.zeros(keep, dtype=complex)
    k = min(keep, len(X))
    Y[:k] = X[:k]
    y = np.fft.irfft(Y, m) * (m / len(x))
    y = y[:int(round(n * RATE / rate))]
    y = np.clip(np.round(y), -32768, 32767).astype(np.int16)
    with wave.open(dst, 'wb') as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(RATE)
        o.writeframes(y.tobytes())


def tool(*args):
    r = subprocess.run([os.path.join(HCEEK, 'tool.exe')] + list(args), cwd=HCEEK,
                       capture_output=True, text=True, errors='replace')
    return r.stdout + r.stderr


def backup():
    if os.path.exists(BACKUP):
        print('backup exists: %s' % BACKUP)
        return
    d = os.path.join(BACKUP, WEAPON)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copyfile(os.path.join(TAGS, WEAPON), d)
    print('backup: %s' % BACKUP)


def import_sounds():
    shutil.rmtree(os.path.join(TAGS, SND_DIR), ignore_errors=True)
    shutil.rmtree(os.path.join(HCEEK, 'data', SND_DIR), ignore_errors=True)
    gain = 10 ** (-HEADROOM_DB / 20)
    for name, (src, ar) in SOUNDS.items():
        d = os.path.join(HCEEK, 'data', SND_DIR, name)
        os.makedirs(d)
        pcm = []
        for w in sorted(glob.glob(os.path.join(AUDIO, src, '*.wav'))):
            # the SAME audio the bank carries (processed(): 22 kHz mono, the fire in TONE)
            y = processed(name, w)
            tone_mod.write(os.path.join(d, os.path.basename(w)), y, BANK_RATE)
            pcm.append(np.clip(np.round(y * 32767), -32768, 32767).astype(np.int32))
        out = tool('sounds', SND_DIR + B + name, FORMAT)
        path = os.path.join(TAGS, SND_DIR, name + '.sound')
        if not os.path.exists(path) or 'MM:' in out:
            print(out[-1500:])
            raise SystemExit('import failed: %s' % name)
        t = snd__def.build(filepath=path)
        arT = snd__def.build(filepath=os.path.join(TAGS, ar + '.sound')).data.tagdata
        dd = t.data.tagdata
        for f in COPY:
            setattr(dd, f, getattr(arT, f))
        perms = [p for pr in dd.pitch_ranges.STEPTREE for p in pr.permutations.STEPTREE]
        if len(perms) != len(pcm):
            raise SystemExit('%s: %d permutations for %d wavs' % (name, len(perms), len(pcm)))
        # STOCK-SHAPED: every stock classic sound is 22 kHz XBOX ADPCM, and a sound\sfx
        # tag left as 44 kHz PCM ('none') CRASHED the game the moment the SAW became active
        # (2026-10-04, halo1.dll+0xB3605D) -- the kit's own xbox route cannot encode here
        # (missing ACM codec), so the permutations get h1_fsb's encoder output: the same
        # 36-byte XBOX IMA blocks the stock tags carry.
        dd.sample_rate.data = 0                       # khz_22
        dd.compression.data = 1                       # xbox_adpcm
        for p, x in zip(perms, pcm):
            blob, _ns = h1_fsb.encode_xbox_ima(x)
            p.samples.data = bytearray(blob)
            p.compression.data = 1
            p.gain = gain
        t.serialize(temp=False, backup=False)
        t = snd__def.build(filepath=path).data.tagdata
        sizes = [len(p.samples.data) for pr in t.pitch_ranges.STEPTREE for p in pr.permutations.STEPTREE]
        if not sizes or min(sizes) == 0:
            raise SystemExit('%s: a permutation has NO samples %s -- the import failed' % (name, sizes))
        print('   %-12s samples %s bytes' % (name, sizes))
        print('   %-12s %d permutation(s), %s %s %s, class %s, gain %s' % (
            name, len(perms), t.sample_rate.enum_name, t.encoding.enum_name,
            t.compression.enum_name, t.sound_class.enum_name,
            sorted({round(p.gain, 4) for pr in t.pitch_ranges.STEPTREE for p in pr.permutations.STEPTREE})))


def own_effects():
    for name, (src, pairs) in EFFECTS.items():
        dst = os.path.join(TAGS, OWN_FX, name + '.effect')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(TAGS, src + '.effect'), dst)
        t = effe_def.build(filepath=dst)
        hits = 0
        for ev in t.data.tagdata.events.STEPTREE:
            for p in ev.parts.STEPTREE:
                for old, new in pairs:
                    if p.type.filepath.lower() == old.lower():
                        p.type.filepath = new
                        hits += 1
        if hits != len(pairs):
            raise SystemExit('%s: repointed %d of %d sounds' % (name, hits, len(pairs)))
        t.serialize(temp=False, backup=False)
        print('   effect %-12s own copy, %d sound(s) -> own' % (name, hits))


def repoint_weapon():
    path = os.path.join(TAGS, WEAPON)
    t = weap_def.build(filepath=path)
    n = 0
    for trig in t.data.tagdata.weap_attrs.triggers.STEPTREE:
        for fe in trig.firing_effects.STEPTREE:
            for field, name in (('firing_effect', 'fire bullet'), ('empty_effect', 'empty')):
                ref = getattr(fe, field)
                if ref.filepath.lower() in ((AR_FX + B + name).lower(), (OWN_FX + B + name).lower()):
                    ref.filepath = OWN_FX + B + name
                    n += 1
    t.serialize(temp=False, backup=False)
    print('   weapon: %d effect reference(s) -> own' % n)


#: MCC PLAYS HALO 1 SOUNDS FROM FMOD BANKS, NOT FROM THE MAP (2026-10-04, h1_fsb.py): the
#: classic view's sounds_adpcm.fsb, found by tag path through lst\sounds_adpcm.lst.bin.
#: A port's sound tag is silent until its audio is in that bank under its path -- every
#: build before this played only the casing click ("a Pea Shooter", A and D alike). The
#: bank audio ships with the tool (port_sounds\halo1) and tool\port_sounds.py puts it in
#: (patch time / by hand); the map's own copy of the audio is never played.
BANK_DIR = os.path.join(os.path.dirname(HERE), 'port_sounds', 'halo1')
BANK_RATE = 22050            # the stock classic bank: 22 kHz mono XBOX IMA ADPCM
#: the ANNIVERSARY index (sounds_debug, CELT -- not writable here) must name a sound tag
#: under sound\sfx too: with only the classic entry the game CRASHED the moment the SAW
#: became active (2026-10-04, halo1.dll+0xB3605D, a garbage tag pointer; also with the
#: stock bank). Classic only, so its entry borrows a stock Anniversary sound's subsongs
#: (the first `perms` of them) -- never heard in classic view.
REMASTERED_FROM = {'saw_fire': B.join(['sound', 'sfx', 'weapons', 'rocket launcher', 'fire']),
                   'saw_dryfire': B.join(['sound', 'sfx', 'weapons', 'assault rifle', 'dryfire'])}


def processed(name, w):
    """One SAW wav as Halo 1 carries it: 22 kHz mono float, the fire in TONE at the H1
    AR's shot level. The map's tags and the FMOD bank both get exactly this."""
    x, r = tone_mod.read(w)
    x = tone_mod.resample(x, r, 44100)
    if name == 'saw_fire' and TONE:
        x = tone_mod.level(tone_mod.tone(x, 44100, TONE), 44100, tone_mod.AR_RMS_DB)
    return tone_mod.resample(x, 44100, BANK_RATE)


def bank_wavs():
    """The SAW's bank audio, 22 kHz mono, the fire in TONE at the H1 AR's level, plus the
    manifest port_sounds.py reads: each sound's tag path, the index ALIASES (how classic
    view maps a path outside sound\\sfx is not known yet -- the plain path and an `old_`
    form are both listed), and its permutations in order."""
    import json
    shutil.rmtree(BANK_DIR, ignore_errors=True)
    os.makedirs(BANK_DIR)
    sounds = []
    for name, (src, _ar) in SOUNDS.items():
        perms = []
        for i, w in enumerate(sorted(glob.glob(os.path.join(AUDIO, src, '*.wav')))):
            y = processed(name, w)
            f = '%s_%d.wav' % (name, i + 1)
            tone_mod.write(os.path.join(BANK_DIR, f), y, BANK_RATE)
            perms.append(f)
        tag = SND_DIR + B + name
        sfx = B.join(['sound', 'sfx', ''])
        if tag.startswith(sfx):
            # classic index form sound\old_sfx\..., and the Anniversary index entry
            old = tag.replace(sfx, B.join(['sound', 'old_sfx', '']), 1)
            entry = {'tag': tag, 'aliases': [old, tag], 'perms': perms,
                     'remastered_from': REMASTERED_FROM[name]}
        else:
            # outside sound\sfx: the plain path (as the stock levels\test\... entries) and
            # an old_ form; no Anniversary entry (tests 0-1 ran without one, no crash)
            entry = {'tag': tag, 'perms': perms,
                     'aliases': [tag, tag.replace('sound' + B, 'sound' + B + 'old_', 1)]}
        sounds.append(entry)
        print('   bank audio %-12s %d permutation(s) at %d Hz' % (name, len(perms), BANK_RATE))
    json.dump({'game': 'Halo 1', 'weapon': 'SAW', 'rate': BANK_RATE, 'sounds': sounds},
              open(os.path.join(BANK_DIR, 'port_saw.json'), 'w'), indent=1)
    print('   wrote %s' % BANK_DIR)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--bank-only', action='store_true',
                    help='only rewrite the bank audio (port_sounds\\halo1); no tags, no rebuild')
    a = ap.parse_args()
    if not a.write:
        print('(dry run -- pass --write)')
        return
    if a.bank_only:
        bank_wavs()
        print('done -- install with: python ..\\port_sounds.py --write')
        return
    backup()
    import_sounds()
    own_effects()
    repoint_weapon()
    bank_wavs()
    print('done -- rebuild (h1_rebuild_all.py --maps a10 for a test), then '
          'python ..\\port_sounds.py --write')


if __name__ == '__main__':
    main()
