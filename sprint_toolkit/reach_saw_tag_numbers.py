r"""Write the ported SAW's own (Halo 4) numbers into its Reach tags -- step 4.

Same job as `h3_saw_tag_numbers.py` and `saw_port_values.py`: the map ships the Halo 4
SAW, and the patcher applies the suggested balance on top when the option is on. The
clone starts as Reach's Assault Rifle, so without this it fires the Assault Rifle's
bullet at the Assault Rifle's rate out of a 32-round magazine.

There is no XML importer -- HREK exports tags and cannot read them back -- so these are
byte edits, located by a SIGNATURE of adjacent values that must match exactly once in the
file. A signature that matches twice is refused rather than guessed at.

AND THEN IT IS PROVEN. `tool export-tag-to-xml` names every field, so after writing, each
tag is exported again and the named fields are read back. A byte edit that lands in the
wrong place, or an offset that was right for the Assault Rifle and wrong for a clone,
fails here instead of in game. Nothing about the offsets is taken on trust.

WHAT IS NOT WRITTEN, deliberately:

  * `rounds total maximum`. The kit tag holds 320 while the plugin's "Rounds Inventory
    Maximum" reads 288 off the shipped map, so those are not the same field and the
    balance table's 216 cannot be assigned to one of them without guessing. Left at the
    Assault Rifle's value; revisit if the port turns out to carry the wrong reserve.
  * the MELEE damage effect. Its 70 lives in `globals\damage_effects\strike_melee`,
    which every weapon in the game shares. The port does not own it and must not edit it.

    python reach_saw_tag_numbers.py [--write]
"""
import argparse
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_kit                                                   # noqa: E402

B = os.sep
SAW = B.join(['objects', 'weapons', 'rifle', 'saw'])
BULLET = SAW + B + 'projectiles' + B + 'saw_bullet_h4_original_numbers'

#: (tag, signature of the Assault Rifle's values, [(offset, format, new, field name)])
#:
#: The field names are the ones `export-tag-to-xml` prints, because that is what the
#: verification reads back.
EDITS = [
    (SAW + B + 'saw.weapon',
     struct.pack('<hhh', 160, 320, 32),        # initial, total maximum, loaded maximum
     # `rounds total maximum` is the RESERVE PLUS THE MAGAZINE, which is why the tag and
     # the plugin appear to disagree and do not: Reach's Assault Rifle reads 320 in the
     # tag while the plugin's "Rounds Inventory Maximum" reads 288, and 288 + 32 = 320.
     # So the port's is its own 216 + 72 = 288 -- the same number h3_saw_tag_numbers.py
     # writes for Halo 3, arrived at from the other end.
     [(0, '<h', 216, 'rounds total initial'),
      (2, '<h', 288, 'rounds total maximum'),
      (4, '<h', 72, 'rounds loaded maximum'),
      (14, '<h', 72, 'rounds reloaded')]),
    (BULLET + '.projectile',
     struct.pack('<ff', 3000.0, 3000.0),       # initial and final velocity
     [(0, '<f', 300.0, 'initial velocity'),
      (4, '<f', 300.0, 'final velocity')]),
    (BULLET + '.damage_effect',
     # float32 exactly as stored -- a rounded literal packs to different bytes and the
     # signature then matches nothing at all, which is how this first came back as 0 hits
     struct.pack('<fff', 5.834000110626221, 5.834000110626221, 6.788000106811523),
     # `damage upper bound` is a "real bounds" field and exports as ONE value with both
     # members in it, `7.5,7.5`, so the two halves are read back by index.
     [(0, '<f', 7.5, 'damage lower bound'),
      (4, '<f', 7.5, 'damage upper bound[0]'),
      (8, '<f', 7.5, 'damage upper bound[1]')]),
    # FIELDS NO CARD COVERS (port_field_audit.py --game reach, 2026-10-05): where the
    # Halo 4 SAW differs from the Halo 4 AR, the clone still carried the AR's value.
    (SAW + B + 'saw.weapon',
     # event sync projectiles/s, max barrel error for event sync, firing error struct:
     # deceleration time, damage error x2, min error look pitch rate
     struct.pack('<6f', 8.0, 0.7, 0.5, 0.0, 0.0, 0.0),
     [(4, '<f', 0.5, 'maximum_barrel_error_for_event_synchronization'),
      # `#2`: the weapon names TWO "deceleration time" fields; the first is the barrel's
      # rate-of-fire one (0), the firing error's comes second
      (8, '<f', 0.49, 'deceleration time#2')]),
    (BULLET + '.damage_effect',
     struct.pack('<fiffff', 0.0, 1, 0.125, 1.0, 1.0, 0.0),  # stun time, damage stun (int),
     [(8, '<f', 0.15, 'instantaneous acceleration')]),     # inst. accel., rider scales
]


def _find_all(data, needle):
    out, at = [], data.find(needle)
    while at >= 0:
        out.append(at)
        at = data.find(needle, at + 1)
    return out


def field_values(tag_rel, names):
    """What `export-tag-to-xml` says the named fields hold, right now."""
    import re
    out = os.path.join(h3_kit.EK, 'temp', 'verify.xml')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run([h3_kit.TOOL, 'export-tag-to-xml',
                    os.path.join(h3_kit.TAGS, tag_rel), out],
                   cwd=h3_kit.EK, capture_output=True, text=True, errors='replace')
    if not os.path.exists(out):
        return {}
    xml = open(out, encoding='utf-8', errors='replace').read()
    os.remove(out)
    got = {}
    for name in names:
        member = None
        bare = name
        nth = 1                                    # `name#2`: the second field so named
        if '#' in bare:
            bare, _, n = bare.partition('#')
            nth = int(n)
        if bare.endswith(']') and '[' in bare:
            bare, _, idx = bare[:-1].partition('[')
            member = int(idx)
        found = re.findall(r'<field name="%s" value="([^"]*)"' % re.escape(bare), xml)
        if len(found) < nth:
            continue
        value = found[nth - 1]
        got[name] = value.split(',')[member].strip() if member is not None else value
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if not h3_kit.IS_REACH:
        raise SystemExit('this writes REACH tags -- refusing to run against %s.'
                         % h3_kit.banner())

    print('%s' % h3_kit.banner())
    plans = []
    for rel, sig, edits in EDITS:
        path = os.path.join(h3_kit.TAGS, rel)
        if not os.path.exists(path):
            raise SystemExit('missing %s -- run h3_make_saw.py first' % rel)
        d = bytearray(open(path, 'rb').read())
        print('\n%s' % os.path.basename(rel))
        # The run this is looking for is the DONOR's, so after a successful write it is
        # not there any more. Rather than read as "refusing to guess" on every re-run,
        # build what the run looks like once the edits have landed and accept that too.
        done = bytearray(sig)
        for off, fmt, new, _label in edits:
            if off + struct.calcsize(fmt) <= len(sig):
                struct.pack_into(fmt, done, off, new)
        hits = _find_all(d, sig)
        # DONE FIRST (2026-10-05): a written run can contain the signature again, shifted
        # (Halo 3's damage run did, and a re-run wrote the wrong field)
        if _find_all(d, bytes(done)):
            where = _find_all(d, bytes(done))
            if len(where) != 1:
                raise SystemExit('   already written, but in %d places -- refusing to '
                                 'touch it' % len(where))
            print('   already carries the port\'s numbers, at %#x' % where[0])
            plans.append((rel, path, None, edits))
            continue
        if len(hits) != 1:
            raise SystemExit('   the value run matched %d times -- refusing to guess'
                             % len(hits))
        base = hits[0]
        print('   value run at %#x' % base)
        for off, fmt, new, label in edits:
            old = struct.unpack_from(fmt, d, base + off)[0]
            print('      %-26s %-10s -> %s' % (label, round(old, 4), new))
            struct.pack_into(fmt, d, base + off, new)
        plans.append((rel, path, d, edits))

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    for rel, path, d, _edits in plans:
        if d is not None:
            open(path, 'wb').write(bytes(d))
    print('\nwritten. reading the tags back through export-tag-to-xml:')

    bad = 0
    for rel, _path, _d, edits in plans:
        names = [label for _o, _f, _n, label in edits]
        got = field_values(rel, names)
        for _off, fmt, new, label in edits:
            have = got.get(label)
            if have is None:
                print('   %-26s NOT FOUND in the export' % label)
                bad += 1
                continue
            ok = abs(float(have) - float(new)) < (1e-3 if 'f' in fmt else 0.5)
            print('   %-26s reads %-10s %s' % (label, have, 'ok' if ok else 'WRONG'))
            bad += 0 if ok else 1
    if bad:
        raise SystemExit('%d field(s) did not come back as intended -- the offsets are '
                         'wrong for this tag.' % bad)
    print('\nall fields verified. Rebuild the map so the new values reach the cache.')


if __name__ == '__main__':
    main()
