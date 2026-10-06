r"""A weapon's OWN Halo 1 sounds, taken from Halo 3's FMOD bank -- generic, per weapon.

The SAW's Halo 1 sounds (h1_saw_sounds.py) came from Halo 4 and are hard-wired to it; this
is the same pipeline as data, for any weapon whose sounds exist in Halo 3:

  1. SOURCE. MCC's `halo3\fmod\pc\sfx.fsb` holds every Halo 3 sound; its `.info` has one
     280-byte entry per subsong naming the source file (`data\sound\weapons\energy_sword\
     energy_melee_1\melee_1.aif`). A sound = every subsong under its folder, decoded with
     vgmstream (F:\Tools\vgmstream). Halo 3 cues SEVERAL sounds on one frame where Halo 1
     cues one (the sword's lunge: hum + cloth at frame 0), so a port sound may MIX several
     Halo 3 sounds, permutation k with permutation k.
  2. SHAPE. 22 kHz mono, active RMS set to the level of the stock Halo 1 sound it stands in
     for (targets measured from the classic bank in the SAW work: melee -16.2 dBFS, ready
     -13.1), peaks soft-limited.
  3. TAGS. `tool sounds <dir> wav`, then the permutations re-encoded to 22 kHz XBOX ADPCM
     (h1_fsb) -- the shape of every stock classic sound; playback fields copied from the
     stock sound named `like`. NEVER under sound\sfx (PORTING.md / h1-fmod-bank-sounds: a
     new tag there crashes the game the moment the weapon is active).
  4. BANK. MCC plays Halo 1 audio from `sounds_adpcm.fsb` by tag path, never from the map:
     the same 22 kHz WAVs go to tool\port_sounds\halo1 with a manifest port_<weapon>.json,
     and `python port_sounds.py --write` appends them. Only THIS weapon's files are
     written or removed there -- the SAW's stay.

Why it exists (2026-10-06): the H1 sword cued the Elite's third-person swing, which is
SILENT for its first 0.45 s (peak at 0.48 s: it is timed to the Elite's long wind-up), so
the first-person slash and lunge were heard 0.3 s late. Halo 3's own first-person sword
sounds start at frame 0.

    python h1_port_sounds.py energy_sword            # show what it would do
    python h1_port_sounds.py energy_sword --write    # then: python ..\port_sounds.py --write
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import port_env                                       # noqa: E402,F401
from reclaimer.hek.defs.snd_ import snd__def          # noqa: E402
import h1_saw_tone as tone                            # noqa: E402  (read/write/resample)
import h1_fsb                                         # noqa: E402

MCC = os.path.dirname(os.path.dirname(HERE))
H3_FSB = os.path.join(MCC, 'halo3', 'fmod', 'pc', 'sfx.fsb')
VGMSTREAM = os.path.join('F:' + os.sep, 'Tools', 'vgmstream', 'vgmstream-cli.exe')
HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
TAGS = os.path.join(HCEEK, 'tags')
BANK_DIR = os.path.join(os.path.dirname(HERE), 'port_sounds', 'halo1')
WORK = os.path.join(HERE, 'out', 'h3_sounds')
RATE = 22050
B = '\\'
ANIMS = B.join(['sound', 'sfx', 'weapons', 'weapon_anims'])
COPY = ('flags', 'sound_class', 'minimum_distance', 'maximum_distance', 'skip_fraction',
        'random_pitch_bounds', 'inner_cone_angle', 'outer_cone_angle', 'outer_cone_gain',
        'gain_modifier', 'maximum_bend_per_second')

PR = B.join(['sound', 'sfx', 'weapons', 'plasma rifle'])
SG = B.join(['sentinel_gun', 'sent_gun', ''])
OH = B.join(['sentinel_beam_overheat', 'beam_overheat', ''])
IMPACTS = B.join(['sound', 'sfx', 'impulse', 'melee'])
#: weapon -> tag folder (never under sound\sfx) and its sounds:
#:   name -> (Halo 3 sound folders mixed together, stock H1 sound to copy playback from,
#:            active-RMS target dBFS[, sound class override])
#:   a folder given as a TUPLE is its pieces played one after another (permutation 1 of
#:   each): Halo 3's in/loop/out sound_looping parts as one Halo 1 one-shot
WEAPONS = {
    'energy_sword': {
        'dir': B.join(['sound', 'weapons', 'energy_sword_port']),
        'h3_dir': 'data\\sound\\weapons\\energy_sword\\',
        'sounds': {
            'sword_melee': (['energy_melee_1'], ANIMS + B + 'ball_melee', -16.2),
            'sword_lunge': (['energy_sword_lunge_hum', 'energy_sword_lunge_cloth'],
                            ANIMS + B + 'ball_melee', -16.2),
            'sword_ready': (['sword_ready'], ANIMS + B + 'ball_ready', -13.1),
            'sword_pose': (['energy_sword_pose'], ANIMS + B + 'ball_posing', -20.0),
            # the melee damage effect's sound, so a slash or lunge that HITS sounds like one
            'sword_hit': (['sword_impact_character'], IMPACTS + B + 'melee_impact_fleshy',
                          -14.0),
            # Halo 3's idle hum: the LOOP of a sound_looping the weapon carries always
            'sword_hum': (['sword_loop\\sword_loop\\loop'],
                          B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'charge']), -27.0,
                          'weapon_idle'),
        },
    },
    # Halo 3's fuel rod is the flak_cannon; every sound it cues sits on frame 0
    'fuel_rod': {
        'dir': B.join(['sound', 'weapons', 'fuel_rod_port']),
        'h3_dir': 'data\\sound\\weapons\\flak_cannon\\',
        'sounds': {
            'rod_ready': (['flak_cannon_ready'], ANIMS + B + 'plasrifle_ready', -13.1),
            'rod_reload': (['flak_cannon_reload'], ANIMS + B + 'rocket_reload_e', -20.9),
            'rod_pose': (['flak_cannon_posing_var1'], ANIMS + B + 'rocket_posing', -20.0),
            'rod_melee': (['flak_cannon_melee'], ANIMS + B + 'fuelrod_melee', -16.2),
            'rod_fire': (['flak_cannon_fire_animation'], ANIMS + B + 'rocket_fire', -18.0),
        },
    },
    # the Sentinel Beam (a full port): Halo 3's player weapon cues the Sentinel's own
    # sounds. The fire loop is a Halo 1 sound_looping (start/loop/end tracks), scaled by
    # the weapon's illumination; the overheat is in + loop + out as one 2.4 s one-shot on
    # the overheated effect (the vent is 2.2 s)
    'sentinel_beam': {
        'dir': B.join(['sound', 'weapons', 'sentinel_beam_port']),
        'h3_dir': 'data\\sound\\characters\\sentinel\\',
        'sounds': {
            'beam_ready': (['sentinel_ready'], ANIMS + B + 'plasrifle_ready', -13.1),
            'beam_pose': (['sentinel_posing'], ANIMS + B + 'plasrifle_posing', -20.0),
            'beam_melee': (['sentinel_melee'], ANIMS + B + 'plasrifle_melee', -16.2),
            'beam_fire_in': ([SG + 'in'], PR + B + 'fire', -16.0),
            'beam_fire_loop': ([SG + 'loop'], PR + B + 'fire', -16.0),
            'beam_fire_out': ([SG + 'out'], PR + B + 'fire', -16.0),
            'beam_overheat': ([tuple(OH + k for k in ('in', 'loop', 'out'))],
                              PR + B + 'overheat', -18.0),
        },
    },
}


def h3_index():
    """{source folder (lower case, ends in \\): [subsong index, ...]} of Halo 3's bank."""
    d = open(H3_FSB + '.info', 'rb').read()
    out = {}
    for i in range(len(d) // 280):
        path = d[i * 280 + 24:(i + 1) * 280].split(b'\0')[0].decode('latin1').lower()
        out.setdefault(path.rsplit('\\', 1)[0] + '\\', []).append((path, i))
    return {k: [i for _p, i in sorted(v)] for k, v in out.items()}


def decode(subsong):
    """One Halo 3 subsong as float mono at its own rate (vgmstream, cached)."""
    os.makedirs(WORK, exist_ok=True)
    wav = os.path.join(WORK, 'h3_%05d.wav' % subsong)
    if not os.path.exists(wav):
        subprocess.run([VGMSTREAM, '-s', str(subsong + 1), '-o', wav, H3_FSB],
                       capture_output=True, check=True)
    x, rate = tone.read(wav)
    return x, rate


def render(weapon):
    """{sound name: [22 kHz mono float per permutation]}"""
    w = WEAPONS[weapon]
    idx = h3_index()
    out = {}
    for name, (folders, _like, target, *_cls) in w['sounds'].items():
        sets = []
        for f in folders:
            pieces = []
            for g in (f if isinstance(f, tuple) else (f,)):
                key = (w['h3_dir'] + g + '\\').lower()
                subs = idx.get(key)
                if not subs:
                    raise SystemExit('%s: no %s in Halo 3\'s bank' % (name, key))
                pieces.append([tone.resample(*decode(s), RATE) for s in subs])
            sets.append([np.concatenate([p[0] for p in pieces])] if isinstance(f, tuple)
                        else pieces[0])
        perms = []
        for k in range(max(len(s) for s in sets)):
            parts = [s[k % len(s)] for s in sets]
            n = max(len(p) for p in parts)
            x = np.zeros(n)
            for p in parts:
                x[:len(p)] += p
            act = x[np.abs(x) > 0.01]
            rms = 20 * np.log10(np.sqrt((act ** 2).mean()) + 1e-12) if len(act) else -99
            x = x * 10 ** ((target - rms) / 20)
            if np.abs(x).max() > 0.95:
                x = 0.95 * np.tanh(x / 0.95)
            perms.append(x)
        out[name] = perms
    return out


def tool(*args):
    r = subprocess.run([os.path.join(HCEEK, 'tool.exe')] + list(args), cwd=HCEEK,
                       capture_output=True, text=True, errors='replace')
    return r.stdout + r.stderr


def write_tags(weapon, audio):
    w = WEAPONS[weapon]
    for name, perms in audio.items():
        like = w['sounds'][name][1]
        cls = (w['sounds'][name][3:] or [None])[0]
        rel = w['dir'] + B + name
        data = os.path.join(HCEEK, 'data', rel)
        shutil.rmtree(data, ignore_errors=True)
        os.makedirs(data)
        pcm = []
        for k, x in enumerate(perms):
            tone.write(os.path.join(data, '%s_%d.wav' % (name, k + 1)), x, RATE)
            pcm.append(np.clip(np.round(x * 32767), -32768, 32767).astype(np.int32))
        log = tool('sounds', rel, 'wav')
        path = os.path.join(TAGS, rel + '.sound')
        if not os.path.exists(path) or 'MM:' in log:
            print(log[-1500:])
            raise SystemExit('import failed: %s' % name)
        t = snd__def.build(filepath=path)
        dd = t.data.tagdata
        ref = snd__def.build(filepath=os.path.join(TAGS, like + '.sound')).data.tagdata
        for f in COPY:
            setattr(dd, f, getattr(ref, f))
        if cls:
            dd.sound_class.set_to(cls)
        tps = [p for pr in dd.pitch_ranges.STEPTREE for p in pr.permutations.STEPTREE]
        if len(tps) != len(pcm):
            raise SystemExit('%s: %d permutations for %d wavs' % (name, len(tps), len(pcm)))
        dd.sample_rate.data = 0                        # khz_22
        dd.compression.data = 1                        # xbox_adpcm, like every stock sound
        for p, x in zip(tps, pcm):
            blob, _ns = h1_fsb.encode_xbox_ima(x)
            p.samples.data = bytearray(blob)
            p.compression.data = 1
            p.gain = 1.0
        t.serialize(temp=False, backup=False)
        print('   tag  %-40s %d permutation(s), class %s' % (rel, len(tps), dd.sound_class.enum_name))


def write_bank(weapon, audio):
    """This weapon's WAVs + manifest in port_sounds\\halo1 (others untouched)."""
    w = WEAPONS[weapon]
    os.makedirs(BANK_DIR, exist_ok=True)
    for name in audio:
        for f in glob.glob(os.path.join(BANK_DIR, name + '_*.wav')):
            os.remove(f)
    sounds = []
    for name, perms in audio.items():
        files = []
        for k, x in enumerate(perms):
            f = '%s_%d.wav' % (name, k + 1)
            tone.write(os.path.join(BANK_DIR, f), x, RATE)
            files.append(f)
        tag = w['dir'] + B + name
        sounds.append({'tag': tag, 'perms': files, 'aliases': [tag]})
    man = os.path.join(BANK_DIR, 'port_%s.json' % weapon)
    json.dump({'game': 'Halo 1', 'weapon': weapon, 'rate': RATE, 'sounds': sounds},
              open(man, 'w'), indent=1)
    print('   bank %s (%d sounds)' % (man, len(sounds)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('weapon', choices=sorted(WEAPONS))
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    audio = render(a.weapon)
    for name, perms in audio.items():
        print('%-14s %d permutation(s), %s s' % (name, len(perms),
                                                 '/'.join('%.2f' % (len(x) / RATE) for x in perms)))
    if a.write:
        write_tags(a.weapon, audio)
        write_bank(a.weapon, audio)
        print('then: python ..\\port_sounds.py --write   (and rebuild the maps)')


if __name__ == '__main__':
    main()
