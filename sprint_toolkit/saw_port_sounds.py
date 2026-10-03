r"""The SAW ports' OWN firing sounds -- Halo 4's SAW audio (saw_port_audio.py) through each
Halo 3-family kit's sound import: Reach (HREK), Halo 3 (H3EK), ODST (H3ODSTEK).

    python saw_port_sounds.py --game reach|h3|odst --write

THE SAW BORROWED ITS DONOR'S EFFECTS (port_sound_refs.py, 2026-10-03): in all three it
fired through the ASSAULT RIFLE's own firing effect (shared with the real AR); the dry
fire comes from the AR's empty effect in Reach and the BATTLE RIFLE's in Halo 3 / ODST.
So the SAW gets OWN copies of those effects (saw\fx), its sounds repointed, and the
weapon names them. The distant-fire LOD sound stays the AR's for now.

THE IMPORT (all three kits): `tool sounds-single-layer <data folder> <sound class>
-bank:saw` = one sound tag per folder, one PERMUTATION per wav, plus an FMOD bank
`fmod\pc\sfx.saw.fsb` (+ .info) in the kit; a compiled sound tag carries the suffix
(`FMod Bank Suffix`, Reach snd! +0x30). The type argument is a SOUND CLASS. The AR's
tails are two tags by class (first_person_outside / _inside); the SAW tail is imported
twice so. Halo 3's AR firing effect has NO tails.

ENCODING ROUTE per game (see GAMES):
  * Reach, CONFIRMED IN GAME 2026-10-03: PC Reach plays the MS-ADPCM audio COMPILED INTO
    THE MAP. Boot 1 (xma2 only) was silent; `reimport-sounds <dir> adpcm no no stereo`
    re-encodes to MS-ADPCM only (test 1: same sound without XMA2) -- it clears the bank
    suffix, which reach_sound_suffix.py restores; with the bank file REMOVED from the game
    folder the SAW still plays (test 2). Nothing outside the map is needed.
  * Halo 3 / ODST, first test pending: the stock tags carry xma v2.0 ONLY, so PC must play
    stock sounds from FMOD (sfx.fsb); the H3 kits' adpcm reimport gives uncompressed PCM
    and also clears the suffix. So the first test mirrors stock: the import's XMA2 + the
    bank installed beside sfx.fsb in the game's fmod\pc (done automatically).

Then rebuild the map(s) that carry the SAW (Reach m20; ODST sc150; Halo 3 010_jungle ...).
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

MCC = os.path.dirname(os.path.dirname(HERE))
AUDIO = r'F:\SteamLibrary\steamapps\common\H4EK\temp\saw_port_audio'
B = '\\'
SUFFIX = 'saw'
SND_DIR = B.join(['sound', 'weapons', 'saw_port'])
WEAPON = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
OWN_FX = B.join(['objects', 'weapons', 'rifle', 'saw', 'fx'])
AR_FX = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'fx'])
BR_FX = B.join(['objects', 'weapons', 'rifle', 'battle_rifle', 'fx'])
AR_SND = B.join(['sound', 'weapons', 'assault_rifle'])
DRYFIRE = B.join(['sound', 'weapons', 'battle_rifle', 'dryfire'])
FIRE = {'saw_fire': ('fire', 'weapon_fire')}
TAILS = {'saw_tail_ext': ('tail', 'first_person_outside'), 'saw_tail_int': ('tail', 'first_person_inside')}
DRY = {'saw_dryfire': ('dryfire', 'weapon_empty')}
FIRE_PAIR = [(AR_SND + B + 'ar_fire', SND_DIR + B + 'saw_fire')]
TAIL_PAIRS = [(AR_SND + B + 'ar_tail_ext', SND_DIR + B + 'saw_tail_ext'),
              (AR_SND + B + 'ar_tail_int', SND_DIR + B + 'saw_tail_int')]
DRY_PAIR = [(DRYFIRE, SND_DIR + B + 'saw_dryfire')]
#: per game: kit, MCC game folder, the sounds (tag -> (wav folder, class)), the effects the
#: SAW borrows (own name -> (source effect, [(old sound, new sound)])), and the ENCODING
#: route: 'pc' = MS-ADPCM only, played from the map (Reach, confirmed in game: the FMOD
#: bank not needed); 'stock' = the import's XMA2 + the FMOD bank installed beside sfx.fsb,
#: as the stock Halo 3 / ODST sounds are (their tags carry xma v2.0 only; the H3 kits'
#: adpcm reimport gives uncompressed PCM and clears the bank suffix).
GAMES = {
    'reach': dict(ek='HREK', folder='haloreach', route='pc',
                  sounds=dict(FIRE, **TAILS, **DRY),
                  effects={'firing': (AR_FX + B + 'firing', FIRE_PAIR + TAIL_PAIRS),
                           'empty': (AR_FX + B + 'empty', DRY_PAIR)}),
    # Halo 3's AR firing effect has no tails: fire + distant fire only
    'h3': dict(ek='H3EK', folder='halo3', route='stock',
               sounds=dict(FIRE, **DRY),
               effects={'firing': (AR_FX + B + 'firing', FIRE_PAIR),
                        'empty': (BR_FX + B + 'empty', DRY_PAIR)}),
    'odst': dict(ek='H3ODSTEK', folder='halo3odst', route='stock',
                 sounds=dict(FIRE, **TAILS, **DRY),
                 effects={'firing': (AR_FX + B + 'firing', FIRE_PAIR + TAIL_PAIRS),
                          'empty': (BR_FX + B + 'empty', DRY_PAIR)}),
}
G = EK = TAGS = SOUNDS = None


def configure(game):
    global G, EK, TAGS, SOUNDS
    G = GAMES[game]
    EK = os.path.join(r'F:\SteamLibrary\steamapps\common', G['ek'])
    TAGS = os.path.join(EK, 'tags')
    SOUNDS = G['sounds']


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
    if G['route'] != 'pc':
        return
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
    """The PC encoding ONLY -- XMA2 dropped (the ports run on PC). Test 1, CONFIRMED in game
    2026-10-03: the SAW sounds the same as with both encodings.
    `reimport-sounds <dir> adpcm no no <filter>` REPLACES the encodings when the filter is
    not compression-append; the filter must match every tag (`weapons` misses the
    first_person_* tails, `stereo` takes all four). It also CLEARS the bank suffix, even
    with -bank:<suffix>, so reach_sound_suffix.py puts it back."""
    if G['ek'] != 'HREK':
        raise SystemExit('the pc route is measured for Reach only')
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
    for fx, (src_fx, pairs) in G['effects'].items():
        src = os.path.join(TAGS, src_fx + '.effect')
        dst = os.path.join(TAGS, OWN_FX, fx + '.effect')
        shutil.copyfile(src, dst)
        t = h3tag.Tag(dst)
        for old, new in pairs:
            n = t.repoint(old, new, 'snd!')
            print('   %s.effect: %-40s -> %s  x%d' % (fx, old.rsplit(B, 1)[-1], new.rsplit(B, 1)[-1], n))
            if n < 1:
                raise SystemExit('%s does not name %s' % (src_fx, old))
        t.save()
        if not h3tag.Tag(dst).check()[0]:
            raise SystemExit('%s no longer spans its file' % dst)
    w = h3tag.Tag(os.path.join(TAGS, WEAPON + '.weapon'))
    for fx, (src_fx, _pairs) in G['effects'].items():
        n = w.repoint(src_fx, OWN_FX + B + fx, 'effe')
        print('   weapon: %s -> own %s  x%d' % (src_fx, fx, n))
        if n < 1:
            raise SystemExit('the SAW does not name %s' % src_fx)
    w.save()
    if not h3tag.Tag(os.path.join(TAGS, WEAPON + '.weapon')).check()[0]:
        raise SystemExit('the weapon no longer spans its file')


def install():
    dst = os.path.join(MCC, G['folder'], 'fmod', 'pc')
    for f in glob.glob(os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb*' % SUFFIX)):
        shutil.copyfile(f, os.path.join(dst, os.path.basename(f)))
        print('   installed %s' % os.path.join(dst, os.path.basename(f)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', choices=sorted(GAMES), default='reach')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--install', action='store_true',
                    help='copy the FMOD bank into the game folder (automatic on the stock route; '
                         'Reach does not need it)')
    ap.add_argument('--both', action='store_true',
                    help='Reach: keep the Xbox XMA2 encoding beside MS-ADPCM (the default is PC '
                         'ONLY, confirmed in game 2026-10-03)')
    a = ap.parse_args()
    configure(a.game)
    if not glob.glob(os.path.join(AUDIO, 'fire', '*.wav')):
        raise SystemExit('run saw_port_audio.py first')
    print('%s: %s, route %s' % (a.game, G['ek'], G['route']))
    if a.write:
        import_sounds()
        own_effects()
        if G['route'] == 'pc' and not a.both:
            pc_only()
    if a.install or (a.write and G['route'] == 'stock'):
        install()
    if not (a.write or a.install):
        print('(dry run -- pass --write)')


if __name__ == '__main__':
    main()
