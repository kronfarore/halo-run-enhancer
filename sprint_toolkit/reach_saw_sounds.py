r"""The Reach SAW port's OWN sounds -- Halo 4's SAW audio through the kit's FMOD route.

Before (port_sound_refs.py, 2026-10-03): the Reach SAW fired through the ASSAULT RIFLE's
own effects (objects\weapons\rifle\assault_rifle\fx\firing / empty) -- shared with the
real AR -- so it played ar_fire, ar_tail_ext/int and the Battle Rifle's dryfire.

THE KIT'S CUSTOM-SOUND ROUTE (HREK, measured):
  * `tool sounds-single-layer <data folder> <sound class> -bank:<suffix>` makes ONE sound
    tag per folder, one PERMUTATION per wav, and writes the audio into an FMOD bank
    `fmod\pc\sfx.<suffix>.fsb` (+ .info) beside the stock sfx.fsb.
  * a compiled Reach sound tag carries `FMod Bank Suffix` (snd! +0x30): stock sounds ''
    (sfx.fsb), these 'saw' -- so the game is expected to open
    haloreach\fmod\pc\sfx.saw.fsb (installed by this script; first in-game test pending).

What this does:
  0. (see import_sounds) every tag gets the PC encoding MS-ADPCM beside the XMA2 one;
  1. the audio from saw_port_audio.py into HREK data\sound\weapons\saw_port\:
        saw_fire      6 permutations  weapon_fire           (crack + body per shot)
        saw_tail_ext  3 permutations  first_person_outside  (the AR's tail classes, so the
        saw_tail_int  3 permutations  first_person_inside    engine picks one, as for the AR)
        saw_dryfire   1               weapon_empty
     imported with -bank:saw (a clean slate: old saw_port tags and the saw bank removed);
  2. the SAW's OWN firing / empty effects (copies of the AR's) with ar_fire -> saw_fire,
     ar_tail_ext/int -> saw_tail_ext/int, dryfire -> saw_dryfire; the distant-fire LOD
     sound stays the AR's;
  3. the SAW weapon names its own effects;
  4. --install copies sfx.saw.fsb + .info into MCC's haloreach\fmod\pc.
Then rebuild m20 (rebuild_reach.cmd m20).

    python reach_saw_sounds.py --write --install              (confirmed in game: xma2 + ms_adpcm)
    python reach_saw_sounds.py --write --pc-only --install    (test 1: ms_adpcm only)
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                        # noqa: E402

EK = r'F:\SteamLibrary\steamapps\common\HREK'
TAGS = os.path.join(EK, 'tags')
MCC = os.path.dirname(os.path.dirname(HERE))
AUDIO = r'F:\SteamLibrary\steamapps\common\H4EK\temp\saw_port_audio'
B = '\\'
SUFFIX = 'saw'
SND_DIR = B.join(['sound', 'weapons', 'saw_port'])
#: sound tag -> (source wav folder in AUDIO, sound class)
SOUNDS = {'saw_fire': ('fire', 'weapon_fire'),
          'saw_tail_ext': ('tail', 'first_person_outside'),
          'saw_tail_int': ('tail', 'first_person_inside'),
          'saw_dryfire': ('dryfire', 'weapon_empty')}
WEAPON = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
AR_FX = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'fx'])
OWN_FX = B.join(['objects', 'weapons', 'rifle', 'saw', 'fx'])
#: effect -> [(old sound, new sound)]
REPOINT = {'firing': [(B.join(['sound', 'weapons', 'assault_rifle', 'ar_fire']), SND_DIR + B + 'saw_fire'),
                      (B.join(['sound', 'weapons', 'assault_rifle', 'ar_tail_ext']), SND_DIR + B + 'saw_tail_ext'),
                      (B.join(['sound', 'weapons', 'assault_rifle', 'ar_tail_int']), SND_DIR + B + 'saw_tail_int')],
           'empty': [(B.join(['sound', 'weapons', 'battle_rifle', 'dryfire']), SND_DIR + B + 'saw_dryfire')]}


def tool(*args):
    r = subprocess.run([os.path.join(EK, 'tool.exe')] + list(args), cwd=EK, capture_output=True,
                       text=True, errors='replace')
    return r.stdout + r.stderr


def import_sounds():
    # clean slate: the saw bank and the port's sound tags (data wavs are rewritten below)
    for f in glob.glob(os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb*' % SUFFIX)):
        os.remove(f)
    shutil.rmtree(os.path.join(TAGS, SND_DIR), ignore_errors=True)
    shutil.rmtree(os.path.join(EK, 'data', SND_DIR), ignore_errors=True)
    for name, (src, cls) in SOUNDS.items():
        d = os.path.join(EK, 'data', SND_DIR, name)
        os.makedirs(d)
        for w in sorted(glob.glob(os.path.join(AUDIO, src, '*.wav'))):
            shutil.copyfile(w, os.path.join(d, os.path.basename(w)))
        out = tool('sounds-single-layer', SND_DIR + B + name, cls, '-bank:' + SUFFIX)
        perms = out.count('adding permutation')
        ok = os.path.exists(os.path.join(TAGS, SND_DIR, name + '.sound'))
        print('   %-13s %-22s %d permutation(s) %s' % (name, cls, perms, 'ok' if ok else 'FAILED'))
        if not ok:
            print(out[-1500:])
            raise SystemExit('import failed')
    bank = os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb' % SUFFIX)
    print('   bank %s: %d bytes' % (bank, os.path.getsize(bank)))
    # THE PC ENCODING (boot after the first build: the SAW was SILENT). A stock Reach sound
    # carries TWO encodings, `xma2,ms_adpcm`; the import writes xma2 only, the map then
    # compiles the sound with an XMA v2 codec (gestalt codec compression 7) where every
    # stock sound uses compression 8 -- the PC one. `reimport-sounds ... adpcm ...
    # compression-append` adds the MS-ADPCM encoding, as the stock tags have it.
    out = tool('reimport-sounds', SND_DIR, 'adpcm', 'no', 'no', 'compression-append')
    for name in SOUNDS:
        x = os.path.join(EK, 'temp', '_saw_snd.xml')
        if os.path.exists(x):
            os.remove(x)
        tool('export-tag-to-xml', os.path.join(TAGS, SND_DIR, name + '.sound'), x)
        comp = re.search(r'name="compression" value="([^"]*)"', open(x, encoding='utf-8', errors='replace').read())
        comp = comp.group(1) if comp else '?'
        print('   %-13s compression %s' % (name, comp))
        if 'ms_adpcm' not in comp:
            print(out[-1500:])
            raise SystemExit('%s has no PC (ms_adpcm) encoding' % name)


BLENDER = r'F:\Tools\blender-5.2.2-windows-x64\blender.exe'


def pc_only():
    """TEST 1 (user, 2026-10-03): the PC encoding ONLY -- drop XMA2 (the ports run on PC).
    `reimport-sounds <dir> adpcm no no <filter>` REPLACES the encodings when the filter is
    not compression-append; the filter must match every tag (`weapons` misses the
    first_person_* tails, `stereo` takes all four). It also CLEARS the bank suffix, even
    with -bank:<suffix>, so reach_sound_suffix.py puts it back."""
    tool('reimport-sounds', SND_DIR, 'adpcm', 'no', 'no', 'stereo')
    r = subprocess.run([BLENDER, '--background', '--python', os.path.join(HERE, 'reach_sound_suffix.py'),
                        '--', SUFFIX] + [SND_DIR + B + n for n in SOUNDS],
                       capture_output=True, text=True, errors='replace')
    if 'SUFFIX OK' not in r.stdout:
        print(r.stdout[-1500:])
        raise SystemExit('could not restore the bank suffix')
    for name in SOUNDS:
        x = os.path.join(EK, 'temp', '_saw_snd.xml')
        if os.path.exists(x):
            os.remove(x)
        tool('export-tag-to-xml', os.path.join(TAGS, SND_DIR, name + '.sound'), x)
        txt = open(x, encoding='utf-8', errors='replace').read()
        comp = re.search(r'name="compression" value="([^"]*)"', txt).group(1)
        suf = re.search(r'name="fmod bank suffix" value="([^"]*)"', txt).group(1)
        print('   %-13s compression %s, bank suffix %r' % (name, comp, suf))
        if comp != 'ms_adpcm' or suf != SUFFIX:
            raise SystemExit('%s is not PC-only with suffix %s' % (name, SUFFIX))


def own_effects():
    os.makedirs(os.path.join(TAGS, OWN_FX), exist_ok=True)
    for fx, pairs in REPOINT.items():
        src = os.path.join(TAGS, AR_FX, fx + '.effect')
        dst = os.path.join(TAGS, OWN_FX, fx + '.effect')
        shutil.copyfile(src, dst)
        t = h3tag.Tag(dst)
        for old, new in pairs:
            n = t.repoint(old, new, 'snd!')
            print('   %s.effect: %-40s -> %s  x%d' % (fx, old.rsplit(B, 1)[-1], new.rsplit(B, 1)[-1], n))
            if n < 1:
                raise SystemExit('%s does not name %s' % (fx, old))
        t.save()
        if not h3tag.Tag(dst).check()[0]:
            raise SystemExit('%s no longer spans its file' % dst)
    w = h3tag.Tag(os.path.join(TAGS, WEAPON + '.weapon'))
    for fx in REPOINT:
        n = w.repoint(AR_FX + B + fx, OWN_FX + B + fx, 'effe')
        print('   weapon: %s -> own  x%d' % (fx, n))
        if n < 1:
            raise SystemExit('the SAW does not name the AR %s effect' % fx)
    w.save()
    if not h3tag.Tag(os.path.join(TAGS, WEAPON + '.weapon')).check()[0]:
        raise SystemExit('the weapon no longer spans its file')


def install():
    dst = os.path.join(MCC, 'haloreach', 'fmod', 'pc')
    for f in glob.glob(os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb*' % SUFFIX)):
        shutil.copyfile(f, os.path.join(dst, os.path.basename(f)))
        print('   installed %s' % os.path.join(dst, os.path.basename(f)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--pc-only', action='store_true',
                    help='TEST 1: MS-ADPCM only, no XMA2 (confirmed in game so far: both)')
    a = ap.parse_args()
    if not glob.glob(os.path.join(AUDIO, 'fire', '*.wav')):
        raise SystemExit('run saw_port_audio.py first')
    if a.write:
        import_sounds()
        own_effects()
    if a.pc_only:
        pc_only()
    if a.install:
        install()
    if not (a.write or a.install):
        print('(dry run -- pass --write, then --install)')


if __name__ == '__main__':
    main()
