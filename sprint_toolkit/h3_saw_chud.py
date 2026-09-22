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
they SHARE it -- the same trap that moved the Assault Rifle's magazine to 72 when the
port's was written. So the chud is cloned and the weapon repointed, exactly like the
projectile and the damage effect, and the threshold itself is a balance row applied to
the port's own tag at patch time.

    python h3_saw_chud.py            # show what it would do
    python h3_saw_chud.py --write
"""
import argparse, os, shutil, sys

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

    wp = os.path.join(TAGS, SAW_WEAPON + '.weapon')
    w = h3tag.Tag(wp)
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
