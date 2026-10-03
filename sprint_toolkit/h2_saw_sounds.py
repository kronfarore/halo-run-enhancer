r"""The Halo 2 SAW's OWN firing sounds -- Halo 4's SAW audio (saw_port_audio.py) through
the H2EK's sound import. CLASSIC ONLY (user, 2026-10-03: every H1/H2 rebuild is classic).

WHAT IT PLAYED (port_sound_refs.py, 2026-10-03): its own firing effect saw_fire (a copy
of the SMG's, h2_saw_weapon.py) still names the SMG's fire sound (plus a remastered-only
SMG fire_lod part, which classic never plays); the dry fire is the Battle Rifle's sound,
named straight from the weapon's barrel.

HOW CLASSIC HALO 2 PLAYS IN MCC (measured on the built 03a): the map carries the sound,
OPUS at 48 kHz (4039 of 4456 sounds; the SMG fire stereo). So the import is the kit's
`sounds-single-layer <dir> <class>` then `reimport-sounds-to-opus <dir>`.

THE VOLUME MARKER (port_volume.py): Halo 2's sound gestalt pools gains like Halo 3's
(the SMG fire's entry is shared by 871 sounds on 03a), so the SAW's sounds are built
port_volume.MARKER_DB['SAW'] below their gain (-3 -> -3.01, no stock gain is like that)
and own their entries; the enhancer's knob then shifts them.

    python h2_saw_sounds.py [--write]

Then rebuild the maps that carry the SAW -- 03a_oldmombasa (and 01b_spacestation, which
is reserved for another test: never stage a test build there).
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
sys.path.insert(0, os.path.dirname(HERE))
import h2_tagref                                                    # noqa: E402
import port_volume                                                  # noqa: E402
from saw_port_sounds import AUDIO, boosted                          # noqa: E402

H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
TAGS = os.path.join(H2EK, 'tags')
B = '\\'
SND_DIR = B.join(['sound', 'weapons', 'saw_port'])
WEAPON = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw.weapon'])
FIRE_FX = B.join(['effects', 'objects', 'weapons', 'rifle', 'saw', 'saw_fire.effect'])
#: own sound -> (audio folder, sound class)
SOUNDS = {'saw_fire': ('fire', 'weapon_fire'), 'saw_dryfire': ('dryfire', 'weapon_empty')}
#: (tag, the sound it names now, the own sound it should name)
REPOINT = [(FIRE_FX, B.join(['sound', 'weapons', 'smg', 'fire']), SND_DIR + B + 'saw_fire'),
           (WEAPON, B.join(['sound', 'weapons', 'battle_rifle', 'dryfire']), SND_DIR + B + 'saw_dryfire')]
#: gain base per sound (dB, before the marker); the import gives -3
GAIN = {'saw_fire': -3.0, 'saw_dryfire': -3.0}
#: audio boost (dB, soft-limited; saw_port_sounds.boosted) per sound -- none until heard
BOOST = {}
BACKUP = r'E:\HaloBackups\H2EK_saw_before_sounds'


def tool(*args):
    r = subprocess.run([os.path.join(H2EK, 'tool.exe')] + list(args), cwd=H2EK,
                       capture_output=True, text=True, errors='replace')
    return r.stdout + r.stderr


def read_tag(name):
    """(gain base, compression) of an own sound tag, through the kit's XML export. H2's
    export wants ABSOLUTE paths for both files (a relative output is written empty) and
    writes `<field name="gain base" type="real">-3.000000</field>`."""
    x = os.path.join(H2EK, 'temp', '_saw_snd.xml')
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


def import_sounds():
    shutil.rmtree(os.path.join(TAGS, SND_DIR), ignore_errors=True)
    shutil.rmtree(os.path.join(H2EK, 'data', SND_DIR), ignore_errors=True)
    for name, (src, cls) in SOUNDS.items():
        d = os.path.join(H2EK, 'data', SND_DIR, name)
        os.makedirs(d)
        for w in sorted(glob.glob(os.path.join(AUDIO, src, '*.wav'))):
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
    marker = port_volume.MARKER_DB['SAW']
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if not glob.glob(os.path.join(AUDIO, 'fire', '*.wav')):
        raise SystemExit('run saw_port_audio.py first')
    if not a.write:
        for rel, old, new in REPOINT:
            print('would repoint %s: %s -> %s' % (rel, old, new))
        print('(dry run -- pass --write)')
        return
    backup()
    import_sounds()
    set_gain()
    repoint()
    print('done -- rebuild 03a_oldmombasa (never stage a test on 01b_spacestation)')


if __name__ == '__main__':
    main()
