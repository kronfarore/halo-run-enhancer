r"""Write the ported SAW's own (Halo 4) numbers into its Halo 3 Editing Kit tags.

Two reasons, and the second is the one that bites:

  1. A port is supposed to carry its source game's numbers in its tags, with the
     suggested balance applied on top at patch time. That is how the Halo 1 SAW works.
  2. The cache builder DEDUPLICATES identical block data. saw.weapon was a byte copy of
     the Assault Rifle, so in the built map both weapons SHARED one magazine block --
     writing the SAW's magazine changed the Assault Rifle's too (32 -> 72, measured).
     The projectile escaped only because repointing its damage reference made its
     content differ. Giving the SAW its own numbers makes every block differ, so the
     builder keeps them apart.

Fields are located by searching for their VALUE RUN, cross-checked against
`tool.exe export-tag-to-xml`, and each run must appear EXACTLY ONCE in the file. An edit
whose run already carries the NEW values is reported as done, so the script can be run
again after more edits are added (it used to refuse once its first run was written).

    python h3_saw_tag_numbers.py [--write]
"""
import argparse, os, struct, sys

B = os.sep
import h3_kit                                              # noqa: E402
EK = h3_kit.EK
TAGS = os.path.join(EK, 'tags')
SAW = os.path.join(TAGS, 'objects', 'weapons', 'rifle', 'saw')

# (file, signature, [(offset in the run, format, new value, label)])
EDITS = [
    (os.path.join(TAGS, h3_kit.SAW_WEAPON + '.weapon'),
     struct.pack('<hhh', 96, 384, 32),                       # initial, maximum, loaded
     [(0, '<h', 216, 'rounds total initial'),
      (2, '<h', 288, 'rounds total maximum'),
      (4, '<h', 72, 'rounds loaded maximum'),
      (14, '<h', 72, 'rounds reloaded')]),
    (os.path.join(SAW, 'damage_effects', 'saw_bullet_h4_original_numbers.damage_effect'),
     # AOE core radius, lower, upper, upper max. With the radius IN the run: the 3-value
     # run (0, 7.5, 7.5) also matches radius+lower+upper once lower is 7.5, and a re-run
     # wrote the AOE core radius (2026-10-05, caught by the XML diff, reverted)
     struct.pack('<ffff', 0.0, 0.0, 7.5, 7.5),
     [(4, '<f', 7.5, 'damage lower bound')]),
    # FIELDS NO CARD COVERS (port_field_audit.py, 2026-10-05): where the Halo 4 SAW differs
    # from the Halo 4 AR, the clone still carried the AR's value. Same units in both games.
    (os.path.join(SAW, 'damage_effects', 'saw_bullet_h4_original_numbers.damage_effect'),
     struct.pack('<8f', 0.1, 0, 0, 0, 0.125, 1, 1, 0),      # camo damage .. rider minimum
     [(16, '<f', 0.15, 'instantaneous acceleration')]),     # hit knockback, H4 AR 0.125
    (os.path.join(TAGS, h3_kit.SAW_WEAPON + '.weapon'),
     struct.pack('<7f', 0.5, 0.5, 0, 0, 0, 0, 0),           # barrel firing error struct
     [(4, '<f', 0.49, 'firing error deceleration time')]),  # H4 AR 0.5
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    for path, sig, edits in EDITS:
        d = bytearray(open(path, 'rb').read())
        print('%s' % os.path.basename(path))
        # the run as it reads AFTER a write (edits past the signature are checked in place)
        done = bytearray(sig)
        for off, fmt, new, _label in edits:
            if off + struct.calcsize(fmt) <= len(done):
                struct.pack_into(fmt, done, off, new)
        # DONE FIRST: a written run can itself contain the signature shifted (above)
        if d.count(bytes(done)) == 1:
            at = d.find(bytes(done))
            if all(abs(struct.unpack_from(fmt, d, at + off)[0] - new) < 1e-6
                   for off, fmt, new, _label in edits):
                print('   already written')
                continue
        hits, at = [], d.find(sig)
        while at >= 0:
            hits.append(at)
            at = d.find(sig, at + 1)
        if len(hits) != 1:
            raise SystemExit('   signature matched %d times -- refusing to guess' % len(hits))
        base = hits[0]
        print('   value run at %#x' % base)
        for off, fmt, new, label in edits:
            old = struct.unpack_from(fmt, d, base + off)[0]
            print('      %-24s %-8s -> %s' % (label, old, new))
            struct.pack_into(fmt, d, base + off, new)
        if a.write:
            open(path, 'wb').write(bytes(d))
            print('   written')
    if not a.write:
        print('\n(dry run -- pass --write)')
    else:
        print('\nNow rebuild the map so the new values reach the cache.')


if __name__ == '__main__':
    main()
