r"""Give the Halo 3 SAW its own HUD, so its ammo readout can be sized to its magazine.

Halo 3 draws loaded ammo as a NUMBER, not Halo 1's row of bullet ticks, so there is no
meter art to rescale -- but there is still a readout that has to match the magazine: the
chud definition's Low Ammo Loaded Threshold, the count at which the number turns red.
Halo 3 sets it at about a quarter of a magazine across the board:

    assault rifle  8 of 32     magnum        3 of 12     shotgun   2 of 12
    battle rifle   8 of 36     sniper rifle  1 of  4     smg      18 of 60

A port cloned from the Assault Rifle keeps that 8 while holding 72, so it would cry low
at a ninth of its magazine, long after the warning is any use. A quarter of 72 is 18 --
which is, for what it is worth, exactly what the SMG uses, the closest thing Halo 3 has
to a high-capacity automatic.

The port cannot simply have the number written into the Assault Rifle's chud, because
they SHARE it -- the same trap that moved the Assault Rifle's magazine to 72. So the chud
is cloned and the weapon repointed, exactly like the projectile and the damage effect.

AND THE CLONE MUST DIFFER BEFORE THE BUILD. A byte-identical copy is deduplicated by the
cache builder onto its donor's blocks, so the clone alone is not enough: the first build
came out with the port's chud SHARING the Assault Rifle's, and writing one moved the
other. Measured, not guessed -- h3_saw_deploy.py --check reported SHARED. Writing the
threshold here is what keeps them apart, and the retimed animations are not deduplicated
for exactly the same reason: they differ.

WHERE THE FIELD IS: the chud's root struct lives in the FIRST `bdat` (a chud tag has two,
the second under `want`), and the threshold triple -- loaded, reserve, battery -- sits at
its `tgbl` payload + 0x14. Verified against six weapons whose values are known from the
map: assault rifle 8, battle rifle 8, smg 18, magnum 3, sniper rifle 1, shotgun 2.
A plain byte search does NOT work: (8, 0, 0) occurs fourteen times in the Assault Rifle's
chud.

    python h3_saw_chud.py            # show what it would do
    python h3_saw_chud.py --write
"""
import argparse, os, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
TAGS = os.path.join(EK, 'tags')
EXT = '.chud_definition'

AR_CHUD = B.join(['ui', 'chud', 'assault_rifle'])
SAW_CHUD = B.join(['ui', 'chud', 'saw'])
SAW_WEAPON = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])

AR_LOADED, AR_MAGAZINE = 8, 32
SAW_MAGAZINE = 72


def threshold(donor_threshold=AR_LOADED, donor_magazine=AR_MAGAZINE,
              port_magazine=SAW_MAGAZINE):
    """The port's warning at the same FRACTION of a magazine as the donor's."""
    return int(round(donor_threshold * (float(port_magazine) / donor_magazine)))


def threshold_offset(tag):
    """Where Low Ammo Loaded Threshold sits: first `bdat` -> `tgbl` payload + 0x14."""
    root = [n for n in tag.nodes() if n.parent is None and n.marker == 'tag!'][0]
    bdat = [c for c in root.children if c.marker == 'bdat'][0]
    tgbl = [c for c in bdat.children if c.marker == 'tgbl'][0]
    return tgbl.payload_at + 0x14


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    src, dst = os.path.join(TAGS, AR_CHUD + EXT), os.path.join(TAGS, SAW_CHUD + EXT)
    if not os.path.exists(src):
        raise SystemExit('no %s' % src)

    want = threshold()
    print('low ammo warning: %d of %d (%.0f%%) -> %d of %d'
          % (AR_LOADED, AR_MAGAZINE, 100.0 * AR_LOADED / AR_MAGAZINE, want, SAW_MAGAZINE))
    print('%s -> %s' % (AR_CHUD, SAW_CHUD))

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    shutil.copyfile(src, dst)
    clone = h3tag.Tag(dst)
    ok, covered, total = clone.check()
    print('clone parses: %s (%d/%d bytes)' % (ok, covered, total))
    at = threshold_offset(clone)
    was = struct.unpack_from('<i', clone.data, at)[0]
    struct.pack_into('<i', clone.data, at, want)
    print('threshold at %#x: %d -> %d' % (at, was, want))
    ok, covered, total = clone.check()
    if not ok:
        raise SystemExit('clone no longer spans the file -- not saved')
    clone.save(dst)

    wp = os.path.join(TAGS, SAW_WEAPON + '.weapon')
    w = h3tag.Tag(wp)
    already = [p for _o, g, p in w.references() if g == 'chdt' and p == SAW_CHUD]
    if already:
        # Re-running should refresh the threshold without treating "nothing left to
        # repoint" as a failure.
        print('weapon already points at %s' % SAW_CHUD)
        return
    n = w.repoint(AR_CHUD, SAW_CHUD, 'chdt')
    ok, covered, total = w.check()
    print('weapon repointed %d reference(s); parses: %s (%d/%d bytes)'
          % (n, ok, covered, total))
    if not ok or not n:
        raise SystemExit('weapon tag not saved')
    w.save(wp)
    print('wrote %s\nwrote %s' % (dst, wp))
    print('\nNext: rebuild the map, then run h3_chud_share_check.py -- a byte-identical\n'
          'clone can still share its donor\'s BLOCKS in the cache, and if it does the\n'
          'threshold has to go into the tag before the build instead.')


if __name__ == '__main__':
    main()
