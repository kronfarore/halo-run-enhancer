r"""Put the Halo 2 SAW in the player's hands, build the level and deploy it.

The cheapest possible test. `gpmg` is in no scenario's palette and neither is the port,
so something has to place it -- and the cheapest place in Halo 2 is the **player starting
profile**, whose primary weapon reference pulls the weapon tag into the build on its own.
No palette entry, no placement, no object name, and none of the scenario-resource
machinery that `h2_loosetag.py` exists for. The player simply starts the level holding it.

Profiles live in the SCENARIO tag and are NOT stomped by a scenario resource at build
time, which is exactly why the abilities work went through them
(see `halo2-loose-tag-format`).

    python h2_saw_place.py [--level 03a_oldmombasa] [--build] [--deploy]
    python h2_saw_place.py --restore

The scenario is copied to `<name>.before_saw` before anything is written, and `--restore`
puts it back. Outskirts is the default because the Chief starts it holding a battle rifle
and a submachine gun, with a fight a few seconds later -- and because 01b_spacestation is
spoken for by another test and must not be rebuilt.
"""
import argparse
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_batch
import h2_loosetag as lt

B = os.sep
H2EK = h2_batch.H2EK
MAPS_OUT = h2_batch.MAPS_OUT
MCC = os.path.join('C:' + B, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                   'Halo The Master Chief Collection', 'halo2', 'h2_maps_win64_dx11')
PORT = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
PROFILE = 'starting profile'
PRIMARY = 0x28              # the primary weapon tagref inside a profile element

#: never rebuild this one -- the user has it primed for a different test
RESERVED = ('01b_spacestation',)


def scenario_path(level):
    return os.path.join(H2EK, 'tags', 'scenarios', 'solo', level, level + '.scenario')


def profiles(data):
    """(array start, element count) of the player starting profile block."""
    chunk = lt.locate(data, lt.PROFILES, lt.PRS)
    count = struct.unpack_from('<I', data, chunk + 8)[0]
    return chunk + lt.CHUNK, count


def _refs(data, base, count):
    """Every profile's two weapon references, in the order their paths are pooled."""
    out = []
    for i in range(count):
        for off in (PRIMARY, 0x3C):
            at = base + i * lt.PRS + off
            cls, _ptr, length, _datum = struct.unpack_from('<4sIII', data, at)
            out.append((i, off, at, cls[::-1], length))
    return out


def point_at(data, level_name, new_path, profile=PROFILE):
    """Repoint one profile's primary weapon, pool and all."""
    base, count = profiles(data)
    names = [bytes(data[base + i * lt.PRS:base + i * lt.PRS + 0x20]).split(b'\0')[0]
             .decode('latin-1') for i in range(count)]
    if profile not in names:
        raise SystemExit('%s has no profile called %r -- it has %s'
                         % (level_name, profile, names))
    which = names.index(profile)

    refs = _refs(data, base, count)
    # Paths are pooled after the element array in element then field order, so the
    # target's string is preceded by exactly the non-empty references before it.
    cursor = base + count * lt.PRS
    target = None
    for i, off, at, cls, length in refs:
        if length == 0:
            continue
        if i == which and off == PRIMARY:
            target = (at, cursor, length)
            break
        cursor += length + 1
    if target is None:
        raise SystemExit('%s: %s has no primary weapon to replace' % (level_name, profile))

    at, pool, length = target
    was = bytes(data[pool:pool + length]).decode('latin-1')
    new = new_path.encode('latin-1')
    out = bytearray(data)
    out[pool:pool + length] = new
    struct.pack_into('<I', out, at + 8, len(new))
    return bytes(out), was


def check(level):
    data = bytearray(open(scenario_path(level), 'rb').read())
    base, count = profiles(data)
    cursor = base + count * lt.PRS
    for i, off, _at, _cls, length in _refs(data, base, count):
        if length == 0:
            continue
        name = bytes(data[base + i * lt.PRS:base + i * lt.PRS + 0x20]).split(b'\0')[0]
        print('   %-22s %-10s %s' % (name.decode('latin-1'),
                                     'primary' if off == PRIMARY else 'secondary',
                                     bytes(data[cursor:cursor + length]).decode('latin-1')))
        cursor += length + 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--level', default='03a_oldmombasa')
    ap.add_argument('--profile', default='starting profile,respawn profile',
                    help='comma separated; both start and respawn by default')
    ap.add_argument('--weapon', default=PORT)
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--deploy', action='store_true')
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()

    if a.level in RESERVED:
        raise SystemExit('%s is reserved for another test; pick a different level'
                         % a.level)
    path = scenario_path(a.level)
    backup = path + '.before_saw'

    if a.show:
        print('%s starting profiles:' % a.level)
        check(a.level)
        return

    if a.restore:
        if not os.path.exists(backup):
            raise SystemExit('no %s to restore from' % os.path.basename(backup))
        shutil.copy(backup, path)
        print('restored %s' % os.path.basename(path))
        check(a.level)
        return

    if not os.path.exists(backup):
        shutil.copy(path, backup)
        print('backed up %s' % os.path.basename(backup))
    data = bytearray(open(backup, 'rb').read())        # always edit from pristine
    # The respawn profile matters as much as the starting one: without it, dying hands
    # the tester a battle rifle back and the test quietly stops testing anything.
    for name in [x.strip() for x in a.profile.split(',') if x.strip()]:
        edited, was = point_at(data, a.level, a.weapon, name)
        data = bytearray(edited)
        print('%s: %s primary weapon %s -> %s' % (a.level, name, was, a.weapon))
    open(path, 'wb').write(bytes(data))
    check(a.level)

    if a.build:
        logs = os.path.join(HERE, 'logs')
        os.makedirs(logs, exist_ok=True)
        print('building %s ...' % a.level)
        ok, msg = h2_batch.build_cache(a.level, logs)
        print('   %s  %s' % ('built' if ok else 'FAILED', msg))
        if not ok:
            raise SystemExit(1)

    if a.deploy:
        src = os.path.join(MAPS_OUT, a.level + '.map')
        dest = os.path.join(MCC, a.level + '.map')
        keep = dest + '.og'
        if not os.path.exists(keep):
            shutil.copy(dest, keep)
            print('   kept the stock map as %s' % os.path.basename(keep))
        shutil.copy(src, dest)
        print('   deployed %.0f MB to %s' % (os.path.getsize(dest) / 1e6, MCC))


if __name__ == '__main__':
    main()
