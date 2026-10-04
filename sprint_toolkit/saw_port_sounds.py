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
  * Reach: the tags are re-encoded to MS-ADPCM (`reimport-sounds <dir> adpcm no no
    stereo`, which clears the bank suffix; reach_sound_suffix.py restores it) -- AND the
    FMOD bank sfx.saw.fsb must be INSTALLED in haloreach\fmod\pc (2026-10-04: without it
    the SAW was silent; the 2026-10-03 "plays without the bank" test had heard the
    projectile / the AR's distant-fire layer, not the SAW's sound).
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
sys.path.insert(0, os.path.dirname(HERE))
import port_volume                                                  # noqa: E402

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
# RELOAD / READY (2026-10-04, user: "go ahead with reload and swap for all four games"):
# Halo 4's SAW foley mixed at its frame cues (saw_port_foley.py) -- every SAW graph here
# cues ONE sound per animation at frame 0, so one mix per animation. Halo 3 / ODST reload
# 128 frames = Halo 4's (1:1); Reach's port reload is the AR's length (empty 68, full 59),
# so the cues are compressed to it. Levelled to the GAME'S OWN donor (foley_levels, active
# RMS of the AR's reload/ready in that game's sfx.fsb) with the donor's tag gain -- the
# games mix these very differently (H3 reload -38 dB effective, ODST -21, Reach -26).
RELOAD = {'saw_reload': ('foley', 'weapon_reload')}
READY = {'saw_ready': ('foley', 'weapon_ready')}
RELOAD_REACH = {'saw_reload_empty': ('foley', 'weapon_reload'),
                'saw_reload_full': ('foley', 'weapon_reload')}
# SECOND BATCH (2026-10-04): melee, idle fidgets, Reach's first draw -- same frame-cued
# mixes (saw_port_foley MELEE1/2, POSE1/2, READY_INITIAL). Classes as the donors'.
MELEE = {'saw_melee1': ('foley', 'weapon_melee'), 'saw_melee2': ('foley', 'weapon_melee')}
POSE = {'saw_pose1': ('foley', 'weapon_idle'), 'saw_pose2': ('foley', 'weapon_idle')}
FIRST_DRAW = {'saw_ready_initial': ('foley', 'weapon_ready'),
              # Reach's first draw cues ar_ready_hero AND a second ar_ready reference (now
              # saw_ready); Halo 4 plays its ready_initial alone (+ a silent cue), so that
              # second reference points at this short silence (G['graph_last'])
              'saw_silence': ('silence', 'weapon_ready')}
FP = B.join(['objects', 'weapons', 'rifle', 'saw', 'fp', ''])
SAW_DIR = B.join(['objects', 'weapons', 'rifle', 'saw', ''])
GRAPH_PAIRS = [(AR_SND + B + 'ar_reload', SND_DIR + B + 'saw_reload'),
               (AR_SND + B + 'ar_ready', SND_DIR + B + 'saw_ready'),
               (AR_SND + B + 'ar_melee1', SND_DIR + B + 'saw_melee1'),
               (AR_SND + B + 'ar_melee2', SND_DIR + B + 'saw_melee2'),
               (AR_SND + B + 'assault_rifle_pose_var1', SND_DIR + B + 'saw_pose1'),
               (AR_SND + B + 'assault_rifle_pose_var2', SND_DIR + B + 'saw_pose2')]
ELITE = AR_SND + B + 'ar_elite_fp' + B
GRAPH_PAIRS_REACH = [(AR_SND + B + 'ar_reload_empty', SND_DIR + B + 'saw_reload_empty'),
                     (AR_SND + B + 'ar_reload_full', SND_DIR + B + 'saw_reload_full'),
                     (AR_SND + B + 'ar_ready', SND_DIR + B + 'saw_ready'),
                     (ELITE + 'elite_ar_reload_empty', SND_DIR + B + 'saw_reload_empty'),
                     (ELITE + 'elite_ar_reload_full', SND_DIR + B + 'saw_reload_full'),
                     (ELITE + 'elite_ar_ready', SND_DIR + B + 'saw_ready'),
                     (AR_SND + B + 'ar_melee_1', SND_DIR + B + 'saw_melee1'),
                     (AR_SND + B + 'ar_melee_2', SND_DIR + B + 'saw_melee2'),
                     (AR_SND + B + 'ar_pose_1', SND_DIR + B + 'saw_pose1'),
                     (AR_SND + B + 'ar_pose_2', SND_DIR + B + 'saw_pose2'),
                     (ELITE + 'elite_ar_melee1', SND_DIR + B + 'saw_melee1'),
                     (ELITE + 'elite_ar_melee2', SND_DIR + B + 'saw_melee2'),
                     (ELITE + 'elite_ar_pose1', SND_DIR + B + 'saw_pose1'),
                     (ELITE + 'elite_ar_pose2', SND_DIR + B + 'saw_pose2'),
                     (AR_SND + B + 'ar_ready_hero', SND_DIR + B + 'saw_ready_initial')]
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
                  sounds=dict(FIRE, **TAILS, **DRY, **RELOAD_REACH, **READY, **MELEE, **POSE,
                              **FIRST_DRAW),
                  effects={'firing': (AR_FX + B + 'firing', FIRE_PAIR + TAIL_PAIRS),
                           'empty': (AR_FX + B + 'empty', DRY_PAIR)},
                  # the graphs the weapon USES (saw.weapon jmad refs) keep their sounds in a
                  # FRAME EVENT LIST too, as Halo 4 does; saw\fp\fp_saw_*.model_animation_graph
                  # are unused leftovers (a first build edited those: m20 kept the AR's).
                  graphs=[SAW_DIR + g + B + g + ext for g in ('fp_saw_spartans', 'fp_saw_elite')
                          for ext in ('.model_animation_graph', '.frame_event_list')],
                  graph_pairs=GRAPH_PAIRS_REACH,
                  # (cues, stretch, donor active RMS) -- the port's reload is retimed to Halo
                  # 4's own 128 frames (ready 24), so the cues fit 1:1
                  foley={'saw_reload_empty': ('RELOAD', 1.0, -14.7),
                         'saw_reload_full': ('RELOAD', 1.0, -16.6),
                         'saw_ready': ('READY', 1.0, -16.2),
                         'saw_melee1': ('MELEE1', 1.0, -17.0), 'saw_melee2': ('MELEE2', 1.0, -16.4),
                         'saw_pose1': ('POSE1', 1.0, -28.9), 'saw_pose2': ('POSE2', 1.0, -27.6),
                         'saw_ready_initial': ('READY_INITIAL', 1.0, -13.7)},
                  graph_last=[(SND_DIR + B + 'saw_ready', SND_DIR + B + 'saw_silence')],
                  gain={'saw_reload_empty': -11, 'saw_reload_full': -11, 'saw_ready': -17,
                        'saw_melee1': -12, 'saw_melee2': -12, 'saw_pose1': -17, 'saw_pose2': -17,
                        'saw_ready_initial': -17, 'saw_silence': -17}),
    # Halo 3's AR firing effect has no tails: fire + distant fire only
    'h3': dict(ek='H3EK', folder='halo3', route='stock',
               sounds=dict(FIRE, **DRY, **RELOAD, **READY, **MELEE, **POSE),
               effects={'firing': (AR_FX + B + 'firing', FIRE_PAIR),
                        'empty': (BR_FX + B + 'empty', DRY_PAIR)},
               graphs=[FP + 'fp_saw_masterchief', FP + 'fp_saw_dervish'],
               graph_pairs=GRAPH_PAIRS,
               # reload +4 dB over the H3 AR's own (-31): "could use a bit more volume" (user,
               # 2026-10-04) -- audio level only, so a bank reinstall, no rebuild
               foley={'saw_reload': ('RELOAD', 1.0, -27.0), 'saw_ready': ('READY', 1.0, -23.7),
                      'saw_melee1': ('MELEE1', 1.0, -18.8), 'saw_melee2': ('MELEE2', 1.0, -19.1),
                      'saw_pose1': ('POSE1', 1.0, -17.2), 'saw_pose2': ('POSE2', 109 / 106.0, -32.4)},
               foley_mono=True,
               # the H3EK's FSBank cannot add 6+ permutations to a non-empty bank
               # (fsb5_merge.py): every sound gets its own fresh bank, merged afterwards
               bank_merge=True,
               gain={'saw_reload': -7, 'saw_ready': -9, 'saw_melee1': -5, 'saw_melee2': -5,
                     'saw_pose1': -3, 'saw_pose2': -3}),
    # GAIN (user, 2026-10-03: "noticeably quieter in ODST"). The SAW's shot measures the same
    # in every game (-12 dBFS over the first 0.25 s, tag gain -3 = -15 effective), but the
    # games' own mixes differ: Halo 3's AR is -22 effective (the SAW stands 7 dB above it),
    # ODST's AR -14.6 and Carbine -13.0 (the SAW sat level with them). About +6 dB puts it
    # where the Halo 3 SAW stands in its mix (~5.5 dB over the AR). The tag's GAIN BASE IS
    # CAPPED AT 0 dB (`tool process-sounds <dir> <spec> gain= 4` stays 0, gain+ stops at
    # 0): -3 -> 0 gives +3; the other +3 is the AUDIO, soft-limited (boosted()).
    'odst': dict(ek='H3ODSTEK', folder='halo3odst', route='stock',
                 sounds=dict(FIRE, **TAILS, **DRY, **RELOAD, **READY, **MELEE, **POSE),
                 effects={'firing': (AR_FX + B + 'firing', FIRE_PAIR + TAIL_PAIRS),
                          'empty': (BR_FX + B + 'empty', DRY_PAIR)},
                 graphs=[FP + 'fp_saw_odst_recon'],
                 graph_pairs=GRAPH_PAIRS,
                 foley={'saw_reload': ('RELOAD', 1.0, -14.4), 'saw_ready': ('READY', 1.0, -8.3),
                        'saw_melee1': ('MELEE1', 1.0, -11.0), 'saw_melee2': ('MELEE2', 1.0, -14.3),
                        'saw_pose1': ('POSE1', 1.0, -22.8), 'saw_pose2': ('POSE2', 109 / 106.0, -24.8)},
                 foley_mono=True,
                 gain={'saw_reload': -7, 'saw_ready': -9, 'saw_melee1': -5, 'saw_melee2': -5,
                       'saw_pose1': -3, 'saw_pose2': -3},
                 # +6 total (boost 3.0) was too loud (user, 2026-10-03): "somewhere in-between";
                 # +4.5 (gain 0 + boost 1.5) CONFIRMED. HEADROOM RULE (boot 2026-10-03: the
                 # engine CLAMPS Gain Base at 0 dB in the map, +12 was unmoved, -20 near
                 # silent): every port ships at the import gain -3 so port_volume.py has +3 dB
                 # up; the same +4.5 is therefore -3 gain + 4.5 audio (limiter: 0.05% of
                 # samples near the ceiling, peak -0.8 dBFS).
                 boost={'saw_fire': 4.5, 'saw_tail_ext': 4.5, 'saw_tail_int': 4.5}),
}
G = EK = TAGS = SOUNDS = None
#: what `sounds-single-layer` gives every sound; G['gain'] overrides per sound
IMPORT_GAIN = -3.0
#: THE VOLUME MARKER (port_volume.py): every SAW sound is built this far BELOW its gain, a
#: value no stock sound has, so the cache builder cannot pool the SAW's gestalt Playbacks
#: entries with stock sounds (before: shared with 4598 sounds on 010_jungle) and the
#: enhancer can turn the port's volume up or down at patch time. Inaudible (0.01 dB).
MARKER = port_volume.MARKER_DB['SAW']


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
    shutil.rmtree(_parts_dir(), ignore_errors=True)
    shutil.rmtree(os.path.join(TAGS, SND_DIR), ignore_errors=True)
    shutil.rmtree(os.path.join(EK, 'data', SND_DIR), ignore_errors=True)
    for name, (src, cls) in SOUNDS.items():
        d = os.path.join(EK, 'data', SND_DIR, name)
        os.makedirs(d)
        if src == 'foley':
            render_foley(name, d)
        elif src == 'silence':
            render_silence(name, d)
        for w in sorted(glob.glob(os.path.join(AUDIO, src, '*.wav'))) if src not in ('foley', 'silence') else ():
            dst = os.path.join(d, os.path.basename(w))
            if G.get('boost', {}).get(name):
                boosted(w, dst, G['boost'][name])
            else:
                shutil.copyfile(w, dst)
        out = tool('sounds-single-layer', SND_DIR + B + name, cls, '-bank:' + SUFFIX)
        perms = out.count('adding permutation')
        ok = os.path.exists(os.path.join(TAGS, SND_DIR, name + '.sound'))
        print('   %-13s %-22s %d permutation(s) %s' % (name, cls, perms, 'ok' if ok else 'FAILED'))
        # '-ERROR-' too: a failed bank update still writes the tag (H3 melee, 2026-10-04)
        if not ok or '-ERROR-' in out:
            print(out[-1500:])
            raise SystemExit('import failed')
        if G.get('bank_merge'):
            park_bank(name)
    bank = os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb' % SUFFIX)
    if G.get('bank_merge'):
        merge_banks()
    check_bank_complete()
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


def _parts_dir():
    return os.path.join(EK, 'temp', 'saw_bank_parts')


def park_bank(name):
    """Move the bank the last import wrote (that sound alone) aside, so the next import
    starts a fresh one. Kept OUT of fmod\\pc: install() copies sfx.saw.fsb*."""
    os.makedirs(_parts_dir(), exist_ok=True)
    src = os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb' % SUFFIX)
    n = len(glob.glob(os.path.join(_parts_dir(), '*.fsb')))
    for ext in ('', '.info'):
        shutil.move(src + ext, os.path.join(_parts_dir(), '%02d_%s.fsb%s' % (n, name, ext)))


def merge_banks():
    """The parked one-sound banks -> sfx.saw.fsb (+ .info), in import order. Proven
    against the kit (2026-10-04): a merge of single banks is byte-identical to the bank
    the H3EK builds itself, but for the 16-byte build hash every kit build changes."""
    import fsb5_merge
    parts = sorted(glob.glob(os.path.join(_parts_dir(), '*.fsb')))
    n = fsb5_merge.merge(os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb' % SUFFIX), parts)
    shutil.rmtree(_parts_dir())
    print('   merged %d one-sound banks: %d entries' % (len(parts), n))


def check_bank_complete():
    """Every imported wav has its bank entry (the .info path ends in <sound>\\<wav>)."""
    import struct
    d = open(os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb.info' % SUFFIX), 'rb').read()
    have = set()
    for k in range(len(d) // 280):
        p = d[k * 280 + 24:(k + 1) * 280].split(b'\0')[0].decode('latin-1').lower()
        have.add(B.join(p.split(B)[-2:]))
    want = set(B.join([n, w]).lower() for n in SOUNDS
               for w in os.listdir(os.path.join(EK, 'data', SND_DIR, n)))
    if want - have:
        raise SystemExit('missing from the bank: %s' % sorted(want - have))
    print('   bank complete: %d entries for %d wavs' % (len(have), len(want)))


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
            # a re-run: the weapon already names its own effect
            if any(r[1] == 'effe' and r[2].lower() == (OWN_FX + B + fx).lower() for r in w.references()):
                print('   weapon: already names its own %s' % fx)
                continue
            raise SystemExit('the SAW does not name %s' % src_fx)
    w.save()
    if not h3tag.Tag(os.path.join(TAGS, WEAPON + '.weapon')).check()[0]:
        raise SystemExit('the weapon no longer spans its file')


def render_foley(name, d):
    """The Halo 4 SAW foley mix for `name` (G['foley']: cues, stretch, target active RMS),
    one wav per variation set, 48 kHz. Reach: dual-mono STEREO (its PC re-encode filter
    `stereo` must match every port tag). Halo 3 / ODST: MONO (G['foley_mono']) -- the
    stereo reload was 917 KB in the bank, over the engines' 0xC0000-byte (768 KB) chunk
    size, and with it in the bank NO SAW sound played in either game (boot 2026-10-04;
    the same bank cut back to the entries under the chunk size played; Reach plays the
    same long entries fine)."""
    import wave
    import numpy as np
    import saw_port_foley as foley
    cues_name, stretch, target = G['foley'][name]
    cues = getattr(foley, cues_name)
    for k in range(foley.count(cues)):
        x = foley.mix(cues, k, stretch)
        act = x[np.abs(x) > 0.01]
        x = x * 10 ** ((target - 20 * np.log10(np.sqrt((act ** 2).mean()) + 1e-12)) / 20)
        if np.abs(x).max() > 0.95:
            x = 0.95 * np.tanh(x / 0.95)                  # peaks soft-limited
        y = np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16)
        mono = G.get('foley_mono')
        with wave.open(os.path.join(d, '%s_%d.wav' % (name, k + 1)), 'wb') as o:
            o.setnchannels(1 if mono else 2)
            o.setsampwidth(2)
            o.setframerate(foley.RATE)
            o.writeframes((y if mono else np.repeat(y, 2)).tobytes())


def render_silence(name, d):
    """0.1 s of digital silence (stereo 48 kHz, like the Reach foley)."""
    import wave
    with wave.open(os.path.join(d, name + '.wav'), 'wb') as o:
        o.setnchannels(2)
        o.setsampwidth(2)
        o.setframerate(48000)
        o.writeframes(bytes(4 * 4800))


#: the Halo 3 engine's chunk size for bank entries (halo3.dll .info parse: ceil(bytes /
#: 0xC0000)); an entry over it broke the whole suffix bank in Halo 3 and ODST
CHUNK_BYTES = 0xC0000


def check_bank_entries():
    """Halo 3 / ODST: refuse a bank entry over CHUNK_BYTES (the .info byte size)."""
    import struct
    info = os.path.join(EK, 'fmod', 'pc', 'sfx.%s.fsb.info' % SUFFIX)
    d = open(info, 'rb').read()
    big = []
    for k in range(len(d) // 280):
        size = struct.unpack_from('<I', d, k * 280 + 4)[0]
        name = d[k * 280 + 24:(k + 1) * 280].split(b'\0')[0].decode('latin-1')
        if size > CHUNK_BYTES:
            big.append((name.rsplit('\\', 1)[-1], size))
    print('   bank entries: %d, largest %d bytes (limit %d)' % (
        len(d) // 280, max(struct.unpack_from('<I', d, k * 280 + 4)[0] for k in range(len(d) // 280)),
        CHUNK_BYTES))
    if big:
        raise SystemExit('bank entries over the %d-byte chunk size: %s' % (CHUNK_BYTES, big))


GRAPH_BACKUP = r'E:\HaloBackups\%s_saw_graphs_before_foley'


def own_graph_sounds():
    """The SAW's first-person graphs name its own reload/ready sounds (G['graph_pairs'])."""
    if not G.get('graphs'):
        return
    bk = GRAPH_BACKUP % G['ek']
    for g in G['graphs']:
        rel = g if os.path.splitext(g)[1] else g + '.model_animation_graph'
        path = os.path.join(TAGS, rel)
        keep = os.path.join(bk, rel)                  # full path: names repeat across folders
        if not os.path.exists(keep):
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copyfile(path, keep)
        t = h3tag.Tag(path)
        for old, new in G['graph_pairs']:
            n = t.repoint(old, new, 'snd!')
            if n:
                print('   %-22s %-28s -> %s  x%d' % (os.path.basename(g), old.rsplit(B, 1)[-1],
                                                   new.rsplit(B, 1)[-1], n))
        # one-occurrence repoints (the LAST reference), only while the target is not named
        # yet -- on a re-run the last `old` would be a different animation's
        for old, new in G.get('graph_last') or ():
            if any(r[1] == 'snd!' and r[2].lower() == new.lower() for r in t.references()):
                continue
            n = t.repoint(old, new, 'snd!', last=True)
            print('   %-22s last %-23s -> %s  x%d' % (os.path.basename(g), old.rsplit(B, 1)[-1],
                                                    new.rsplit(B, 1)[-1], n))
        t.save()
        if not h3tag.Tag(path).check()[0]:
            raise SystemExit('%s no longer spans its file' % path)
        left = [r[2] for r in h3tag.Tag(path).references() if r[1] == 'snd!'
                and r[2].lower() in {o.lower() for o, _n in G['graph_pairs']}]
        if left:
            raise SystemExit('%s still names %s' % (path, sorted(set(left))))


def boosted(src, dst, db):
    """The same sound, `db` louder: scaled, then a tanh soft limiter (the shots already peak
    near full scale, so plain scaling would clip). Same audio, more loudness."""
    import wave
    import numpy as np
    with wave.open(src, 'rb') as r:
        ch, sw, rate, n = r.getnchannels(), r.getsampwidth(), r.getframerate(), r.getnframes()
        a = np.frombuffer(r.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0
    def soft(x):                                # linear when quiet, peaks capped at 0.95
        return 0.95 * np.tanh(x / 0.95)

    def rms(x):
        return np.sqrt((x[:min(len(x), 12000 * ch)] ** 2).mean())   # the shot, ~0.25 s
    want = rms(a) * 10 ** (db / 20)
    lo, hi = 1.0, 10 ** ((db + 12) / 20)       # drive that raises the shot's RMS by `db`
    for _ in range(40):
        k = (lo + hi) / 2
        lo, hi = (k, hi) if rms(soft(a * k)) < want else (lo, k)
    a = soft(a * (lo + hi) / 2)
    with wave.open(dst, 'wb') as o:
        o.setnchannels(ch)
        o.setsampwidth(sw)
        o.setframerate(rate)
        o.writeframes((a * 32767).astype(np.int16).tobytes())


def set_gain():
    """Each sound's gain base (dB) from G['gain'] (default IMPORT_GAIN) minus the volume
    MARKER, through the kit's own verb; read back."""
    for name in SOUNDS:
        db = G.get('gain', {}).get(name, IMPORT_GAIN) - MARKER
        tool('process-sounds', SND_DIR, name, 'gain=', str(db))
        x = os.path.join(EK, 'temp', '_saw_snd.xml')
        if os.path.exists(x):
            os.remove(x)
        tool('export-tag-to-xml', os.path.join(TAGS, SND_DIR, name + '.sound'), x)
        txt = open(x, encoding='utf-8', errors='replace').read()
        got = float(re.search(r'name="gain base" value="([^"]*)"', txt).group(1))
        suf = re.search(r'name="fmod bank suffix" value="([^"]*)"', txt)
        print('   %-13s gain base %+g dB%s' % (name, got, '' if suf is None else ', bank suffix %r' % suf.group(1)))
        if abs(got - db) > 0.01:
            raise SystemExit('%s: gain base is %g, wanted %g' % (name, got, db))


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
                    help='copy the FMOD bank into the game folder (automatic with --write); '
                         'fails while MCC has that game loaded (the bank file is locked)')
    ap.add_argument('--boost', type=float, metavar='DB',
                    help="override the audio boost (dB) of every boosted sound of this game. "
                         "The boost lives in the BANK only, so on the stock route (H3/ODST) a "
                         "retune is this run + an MCC restart, no rebuild")
    ap.add_argument('--gain-only', action='store_true',
                    help="only (re)write the tags' gain + volume marker, no import (then rebuild)")
    ap.add_argument('--both', action='store_true',
                    help='Reach: keep the Xbox XMA2 encoding beside MS-ADPCM (the default is PC '
                         'ONLY, confirmed in game 2026-10-03)')
    a = ap.parse_args()
    configure(a.game)
    if a.boost is not None:
        G['boost'] = {k: a.boost for k in G.get('boost') or G['gain']}
    if not glob.glob(os.path.join(AUDIO, 'fire', '*.wav')):
        raise SystemExit('run saw_port_audio.py first')
    print('%s: %s, route %s' % (a.game, G['ek'], G['route']))
    if a.gain_only:
        set_gain()
        return
    if a.write:
        import_sounds()
        own_effects()
        own_graph_sounds()
        if G['route'] == 'pc' and not a.both:
            pc_only()
        set_gain()
    if a.write and G['route'] == 'stock':
        check_bank_entries()
    # EVERY route installs the bank: Reach plays from it too (boot 2026-10-04 -- with
    # sfx.saw.fsb installed for the first time the SAW's fire, reload and ready played;
    # the earlier "bank not needed" test heard the projectile / AR distant layer)
    if a.install or a.write:
        install()
    if not (a.write or a.install):
        print('(dry run -- pass --write)')


if __name__ == '__main__':
    main()
