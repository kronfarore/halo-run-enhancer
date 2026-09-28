r"""Make an ODST scenario REFERENCE the ported SAW, so `tool` builds it into the map.

A weapon only reaches a cache if the scenario reaches it -- and on a rebuilt map a
Player Starting Profile's weapon reference is enough on its own: `tool` gathers the
model and animation data AND marks the tags resident in GLOBAL, with no zone-pool patch
afterwards (see `h3-import-weapon-recipe`, confirmed in game for the battle rifle).

Halo 3's port did this in Sapien. This does it headlessly, and the reason it can is a
size coincidence worth writing down: a tag reference in an Editing Kit tag is a `frgt`
chunk holding its own LENGTH, so a path can be swapped for another of exactly the same
length without a single chunk growing -- no ancestor lengths to fix, nothing to
desynchronise. h3tag cannot help here anyway: its forward scan does not finish on a 6.9
MB scenario inside ten minutes.

WHAT IT TAKES, AND WHY THAT ONE. sc150's profile block ends in rows pairing weapons the
level never reads at runtime; they exist so `tool` gathers those weapons' resources.
Several were added by hand to restore weapons ODST cut -- battle rifle, plasma rifle,
plain SMG, sniper rifle, magnum, energy blade -- and those must not be disturbed. The
rows after them pair MULTIPLAYER objects that an ODST campaign map has no use for at
all, and `objects\weapons\multiplayer\ball\ball` is 37 characters, which is why the
port's weapon tag is named to 37 characters too.

So the cost is: sc150 stops gathering the multiplayer BALL. Nothing else moves.

    python odst_saw_place.py                     # show what it would do
    python odst_saw_place.py --write
    python odst_saw_place.py --restore
"""
import argparse
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_kit                                                   # noqa: E402

B = os.sep
#: the reference this replaces, and the port's weapon tag -- SAME LENGTH, by construction
DONOR = B.join(['objects', 'weapons', 'multiplayer', 'ball', 'ball'])
PORT = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw_h4_port'])


def scenario(level):
    return os.path.join(h3_kit.TAGS, 'levels', 'atlas', level, level + '.scenario')


def refs(d, group='weap'):
    """[(offset of the path, path)] for every tag reference of `group`.

    Found by the chunk marker rather than by walking the tree: a `frgt` chunk is the
    marker, a u32 of flags, its u32 LENGTH, then the group 4CC stored backwards and the
    path with no terminator. That is enough to read and to overwrite, and it does not
    need the whole 6.9 MB to parse first.
    """
    want = group[::-1].encode('latin1')
    out = []
    for m in re.finditer(b'frgt', d):
        at = m.start()
        length = struct.unpack_from('<I', d, at + 8)[0]
        if not (4 <= length <= 250) or d[at + 12:at + 16] != want:
            continue
        path = d[at + 16:at + 12 + length]
        try:
            path = path.decode('latin1')
        except UnicodeDecodeError:
            continue
        if path and not re.match(r'^[ -~]*$', path):
            continue
        out.append((at + 16, path, at, length))
    return [(off, path) for off, path, _at, _ln in out]


def profile_slots(d, group='weap'):
    """The weapon references that belong to a PLAYER STARTING PROFILE, by structure.

    A weapon appears in an ODST scenario in two places and only one of them is the one
    that matters: the WEAPON PALETTE, and the profile block. The multiplayer ball is in
    both, which is why picking by name alone is ambiguous.

    They are told apart by shape, not by offset. A palette entry is one `frgt` alone
    inside its `tsgt`; a profile is a `tsgt` holding TWO weapon references back to back,
    the primary and the secondary. So a reference is a profile slot when another weapon
    reference follows it with no `tsgt` in between, or when it IS that second one.
    """
    want = group[::-1].encode('latin1')
    spans = []
    for m in re.finditer(b'frgt', d):
        at = m.start()
        length = struct.unpack_from('<I', d, at + 8)[0]
        if not (4 <= length <= 250) or d[at + 12:at + 16] != want:
            continue
        path = d[at + 16:at + 12 + length]
        try:
            path = path.decode('latin1')
        except UnicodeDecodeError:
            continue
        if path and not re.match(r'^[ -~]*$', path):
            continue
        spans.append((at, at + 12 + length, at + 16, path))

    out = set()
    for i, (start, end, off, _path) in enumerate(spans):
        if i + 1 < len(spans):
            gap = d[end:spans[i + 1][0]]
            if b'tsgt' not in gap:
                out.add(off)
                out.add(spans[i + 1][2])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--level', default='sc150')
    ap.add_argument('--donor', default=DONOR)
    ap.add_argument('--port', default=PORT)
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    print(h3_kit.banner())
    if not h3_kit.IS_ODST:
        raise SystemExit('this places into an ODST scenario; run it with PORT_EK=odst')

    p = scenario(a.level)
    if not os.path.exists(p):
        raise SystemExit('no %s' % p)
    backup = p + '.before_saw'

    if a.restore:
        if not os.path.exists(backup):
            raise SystemExit('no %s to restore from' % os.path.basename(backup))
        shutil.copy2(backup, p)
        print('restored %s' % os.path.basename(p))
        return

    if len(a.donor) != len(a.port):
        raise SystemExit('the paths must be the same length: %s is %d, %s is %d'
                         % (a.donor, len(a.donor), a.port, len(a.port)))
    tag = os.path.join(h3_kit.TAGS, a.port + '.weapon')
    if not os.path.exists(tag):
        raise SystemExit('no %s -- the port must be named to the donor\'s length' % tag)

    d = bytearray(open(backup if os.path.exists(backup) else p, 'rb').read())
    got = refs(d)
    prof = profile_slots(bytes(d))
    all_hits = [off for off, path in got if path == a.donor]
    # BOTH, and the first build proved why. A profile slot alone brought every TAG in --
    # weapon, both models, the animation graph, the projectile, the HUD -- and NOT ONE
    # chunk of raw geometry, which is the "no geometry" state h3-import-weapon-recipe
    # describes: the weapon exists, and there is nothing to draw.
    #
    # The evidence for the palette came out of that same map. sc150's cut weapons (plain
    # SMG, magnum, battle rifle, energy blade, sentinel gun) sit only in profile rows and
    # DO carry geometry, so profiles are not useless -- but the ball, whose profile row
    # had just been taken, still carried its own, and the only thing left pointing at it
    # was its WEAPON PALETTE entry. So the palette is what was still feeding it.
    #
    # Repointing a palette entry is safe in a way that removing one is not: the palette
    # is indexed BY POSITION, so an in-place path swap changes what an index means and
    # renumbers nothing. Any placement using that index draws the port instead.
    hits = all_hits
    have = [off for off, path in got if path == a.port]
    print('   %s: %d weapon references, %d of them profile slots'
          % (a.level, len(got), len(prof)))
    print('   %-52s %d occurrence(s), %d in a profile' % (a.donor, len(all_hits), len(hits)))
    print('   %-52s %d occurrence(s)' % (a.port, len(have)))
    for off in all_hits:
        print('      %#08x  %s' % (off, 'PROFILE' if off in prof else 'weapon palette'))
    if have and not hits:
        print('\nalready placed')
        return
    if not hits:
        raise SystemExit('no %s reference to take' % a.donor)

    if not a.write:
        print('\n(dry run -- pass --write)')
        return
    if not os.path.exists(backup):
        shutil.copy2(p, backup)
        print('   kept the pristine scenario as %s' % os.path.basename(backup))
    before = len(d)
    for off in hits:
        d[off:off + len(a.port)] = a.port.encode('latin1')
    if len(d) != before:
        raise SystemExit('the file changed length -- that was not an in-place overwrite')
    after = refs(bytes(d))
    back = profile_slots(bytes(d))
    if not any(path == a.port and off in back for off, path in after):
        raise SystemExit('the new path does not read back as a profile slot')
    if any(path == a.donor for _o, path in after):
        raise SystemExit('the donor is still referenced somewhere')
    print('   took %d reference(s): %s'
          % (len(hits), ', '.join('%#x %s' % (o, 'profile' if o in prof else 'palette')
                                  for o in hits)))
    open(p, 'wb').write(bytes(d))
    print('   wrote %s (%d bytes, unchanged)' % (os.path.basename(p), len(d)))
    print('\nNow build: PORT_EK=odst python odst_ek_build.py --build %s' % a.level)


if __name__ == '__main__':
    main()
