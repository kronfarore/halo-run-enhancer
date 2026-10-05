r"""Move the Halo 2 SAW from its CLONE donors' values to the SMG yardstick (user, 2026-10-05).

WHY. Every other port is cloned from the weapon its balance is measured against, so a
field no card covers still reads like that donor -- the game's own convention. Halo 2's
is not: the weapon tag is the cut GPMG, the bullet and both damage effects the Warthog AP
turret's (h2_saw_weapon.py), while the balance chain measures against the SMG. So fields
where the Halo 4 SAW and AR AGREE still carried machine-gun-turret values the source
weapon never had (port_field_audit.py --game h2, lists 4 and 5): a 1.25 s fire-rate
spin-up, error decay 10x slower, a bullet that never ricochets or overpenetrates, a
35-unit physics shove on every hit, turret rider damage, the turret's hit flash.

WHAT THIS DOES, all verified through tool's own export:
  1. the two damage effects (impact + firing) are RE-CLONED from the SMG's -- every field
     of them was the turret's -- and h2_saw_numbers.py puts the SAW's own numbers back;
  2. the bullet keeps everything that is its own (tracer attachment, velocities, refs)
     and takes the SMG's MATERIAL RESPONSES block whole: it is the last block of the tag
     with no sub-blocks, so it is the file's tail from its chunk header on; the one other
     byte that knows its size is the count in the root struct's tag block field;
  3. the weapon's fire-rate ramp, error ramp, recoil, ready/reload times, AI fear and
     barrel cosmetics take the SMG's values; the error DECELERATION takes the Halo 4
     SAW's own difference instead (h2_saw_numbers.py, 0.49).
KEPT, on purpose: what belongs to the SAW's model or is identity -- size and physics of
the dropped object, first-person offset, pickup message, no dual wield (and so the dual
weapon error fields), the medal / kill-feed reporting types (h2_saw_numbers SKIPPED).

Backups: E:\HaloBackups\H2EK_saw_before_yardstick (first run only).

    python h2_saw_yardstick.py [--write]
then  python h2_saw_numbers.py   and rebuild 03a.
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_tagfield as tf                                            # noqa: E402

B = os.sep
TAGS = os.path.join(tf.H2EK, 'tags')
SAW = B.join(['objects', 'weapons', 'rifle', 'saw'])
SMG = B.join(['objects', 'weapons', 'rifle', 'smg'])
BACKUP = os.path.join('E:' + B, 'HaloBackups', 'H2EK_saw_before_yardstick')
WEAPON, SMG_WEAPON = SAW + B + 'saw.weapon', SMG + B + 'smg.weapon'
BULLET = SAW + B + B.join(['projectiles', 'saw_bullet.projectile'])
SMG_BULLET = SMG + B + B.join(['projectiles', 'smg_bullet.projectile'])
#: (the SMG's damage effect, the port's) -- re-cloned whole
DAMAGE = [(SMG + B + B.join(['damage_effects', 'smg_bullet.damage_effect']),
           SAW + B + B.join(['damage_effects', 'saw_bullet.damage_effect'])),
          (SMG + B + B.join(['damage_effects', 'smg_trigger.damage_effect']),
           SAW + B + B.join(['damage_effects', 'saw_trigger.damage_effect']))]
#: weapon fields -> the SMG's value: (name, block, element, nth, the port's value now --
#: a guard, so a re-run or an edited tag is noticed, ROOT = in the root struct)
WEAPON_FIELDS = [
    ('ready time', '', 0, 0, 0.0),
    ('ai scariness', '', 0, 0, 8.0),
    ('throttle magnitude', '', 0, 0, 0.0),
    ('throttle minimum distance', '', 0, 0, 0.0),
    ('reload time', 'magazines', 0, 0, 0.0),
    ('acceleration time', 'barrels', 0, 0, 1.25),          # Firing: fire-rate spin-up
    ('deceleration time', 'barrels', 0, 0, 2.0),           # Firing: spin-down
    ('acceleration time', 'barrels', 0, 1, 1.5),           # Error: bloom build-up
    ('angle change per shot', 'barrels', 0, 0, (0.5, 0.5)),
    ('angle change function', 'barrels', 0, 0, None),
    ('ejection port recovery time', 'barrels', 0, 0, 0.15),
    ('illumination recovery time', 'barrels', 0, 0, 0.1),
]
#: fields that read ZERO in the port: zero matches the padding everywhere, so the field
#: is placed by an ANCHOR -- a nearby non-zero field found in both tags -- and the
#: target's distance from it measured on the SMG's tag, where the target is non-zero.
#: (NOT the absolute offset: the SAW's weapon root is the GPMG's, 1524 bytes against the
#: SMG's 1128 -- a first attempt wrote the SMG's offset, and the export check refused it.)
ZERO_FIELDS = ('ready time', 'throttle magnitude', 'throttle minimum distance')


def find_offset(path, name, block, index, nth):
    """h2_tagfield.offset_of WITHOUT its cache, which is keyed by tag GROUP and so would
    hand one weapon's offset to another (it did, once)."""
    original = open(path, 'rb').read()
    xml = tf.export(path)
    rows = tf.read_all(xml)
    row = tf.pick(rows, name, block, index, nth)
    ftype, values = row[3], tf._numbers(row[4])
    if ftype not in tf.SCALARS or not values or not any(values):
        return None
    code, _size, n = tf.SCALARS[ftype]
    probe = tf.stored(ftype, values[0]) + 0.5 if code == '<f' else int(values[0]) + 3
    cands = tf.candidates(bytearray(original), ftype, values,
                          tf.scope(bytearray(original), xml, block, index))
    if not cands or len(cands) > tf.MAX_CANDIDATES:
        return None
    tmp = path + '._anchor' + os.path.splitext(path)[1]
    try:
        for at in cands:
            edited = bytearray(original)
            struct.pack_into(code, edited, at, probe)
            open(tmp, 'wb').write(bytes(edited))
            after = tf.read_all(tf.export(tmp) or '')
            if len(after) != len(rows):
                continue
            moved = [i for i, (a, b) in enumerate(zip(rows, after)) if a[4] != b[4]]
            if len(moved) == 1 and rows[moved[0]] is row:
                return at
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return None


def write_by_anchor(name, block, index, nth, want):
    """Place a zero-reading field by BRACKETING it in the port's own tag: the nearest
    non-zero fields before and after it (export order = file order within a struct) are
    located, and every zero-valued position between them is tried in a copy. Kept only
    when tool's export shows that ONE field changed, to `want`. (Measuring the distance on
    the SMG's tag failed: the SAW's root is the GPMG's, 396 bytes longer, laid out apart.)"""
    port = _abs(WEAPON)
    rows = tf.read_all(tf.export(port))
    ti = rows.index(tf.pick(rows, name, block, index, nth))
    code, size, n = tf.SCALARS[rows[ti][3]]
    vals = want if isinstance(want, (list, tuple)) else [want]

    def anchor(step):
        i = ti + step
        while 0 <= i < len(rows):
            r = rows[i]
            if (r[0], r[1]) == (block, index) and r[3] in tf.SCALARS:
                nn = sum(1 for x in rows[:i] if x[2] == r[2] and (x[0], x[1]) == (block, index))
                at = find_offset(port, r[2], block, index, nn)
                if at is not None:
                    return at, r[2]
            i += step
        return None, None
    lo, lo_name = anchor(-1)
    hi, hi_name = anchor(+1)
    original = open(port, 'rb').read()
    if hi is None:                           # nothing non-zero after it: the element's end
        span = tf.scope(bytearray(original), tf.export(port), block, index)
        if span:
            hi, hi_name = span[1], 'the end of %s[%d]' % (block or 'root', index)
    if lo is None or hi is None or hi <= lo:
        raise SystemExit('%s: could not bracket it (%s / %s)' % (name, lo_name, hi_name))
    tried = 0
    for at in range(lo + 1, hi - size * n + 1):
        if any(original[at:at + size * n]):
            continue                         # the field reads zero, so its bytes are zero
        tried += 1
        edited = bytearray(original)
        for k, v in enumerate(vals):
            struct.pack_into(code, edited, at + k * size,
                             tf.stored(rows[ti][3], float(v)) if code == '<f' else int(v))
        open(port, 'wb').write(bytes(edited))
        after = tf.read_all(tf.export(port) or '')
        moved = [j for j, (a, b) in enumerate(zip(rows, after)) if a[4] != b[4]]
        if len(after) == len(rows) and moved == [ti]:
            print('      between %s and %s: 0x%X -> %s (%d tried)'
                  % (lo_name, hi_name, at, after[ti][4].strip(), tried))
            return
        open(port, 'wb').write(original)
    raise SystemExit('%s: %d positions between %s and %s, none moved it alone; the tag '
                     'is unchanged' % (name, tried, lo_name, hi_name))


def _abs(rel):
    return os.path.join(TAGS, rel)


def backup():
    if os.path.exists(BACKUP):
        print('backup exists: %s' % BACKUP)
        return
    for rel in (WEAPON, BULLET) + tuple(d for _s, d in DAMAGE):
        dst = os.path.join(BACKUP, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(_abs(rel), dst)
    print('backup: %s' % BACKUP)


def flat(rel):
    import port_field_audit as fa
    fa._CACHE.pop(('H2EK', rel), None)
    return fa.flatten('H2EK', rel)


def reclone_damage(write):
    for src, dst in DAMAGE:
        # ONLY while the tag is still the turret's (= its pre-yardstick backup): after the
        # re-clone h2_saw_numbers.py writes the SAW's numbers into it, and a re-run that
        # compared against the SMG's bytes copied over them (2026-10-05)
        keep = os.path.join(BACKUP, dst)
        cur = open(_abs(dst), 'rb').read()
        still_turret = os.path.exists(keep) and cur == open(keep, 'rb').read()
        if not os.path.exists(keep) and cur != open(_abs(src), 'rb').read():
            still_turret = True                    # dry run before any backup
        print('   %-34s <- %s %s' % (os.path.basename(dst), os.path.basename(src),
                                      '' if still_turret else '(done earlier: left alone)'))
        if write and still_turret:
            shutil.copyfile(_abs(src), _abs(dst))


def _last_chunk(data):
    at = data.rfind(tf.SIG)
    ver, count, size = struct.unpack_from('<III', data, at + 4)
    return at, ver, count, size


def splice_material_responses(write):
    port, smg = bytearray(open(_abs(BULLET), 'rb').read()), open(_abs(SMG_BULLET), 'rb').read()
    before, want = flat(BULLET), flat(SMG_BULLET)
    n_port = int(before['material responses/#count'][1])
    n_smg = int(want['material responses/#count'][1])
    p_at, p_ver, p_cnt, p_size = _last_chunk(port)
    s_at, s_ver, s_cnt, s_size = _last_chunk(smg)
    if (p_cnt, s_cnt) != (n_port, n_smg) or (p_ver, p_size) != (s_ver, s_size):
        raise SystemExit('the last chunks are not the material responses blocks '
                         '(%s/%s elements, sizes %s/%s)' % (p_cnt, s_cnt, p_size, s_size))
    mr = lambda d: {k: v for k, v in d.items() if k.startswith('material responses')}
    if mr(before) == mr(want):
        print('   material responses: already the SMG\'s (%d)' % n_smg)
        return
    print('   material responses: %d (turret: always detonate) -> %d (SMG)' % (n_port, n_smg))
    new = port[:p_at] + smg[s_at:]
    # the count stored a second time, in the root struct's tag block field (count, then
    # two pointer words -- NOT zero on disk, measured: 0x398 in a projectile). Same group,
    # same root layout: it is where the port reads its count and the SMG reads its own.
    root_end = 0x50 + struct.unpack_from('<I', port, 0x4C)[0]
    cands = [o for o in range(0x50, root_end - 4)
             if struct.unpack_from('<I', port, o)[0] == n_port
             and struct.unpack_from('<I', smg, o)[0] == n_smg]
    for o in cands:
        trial = bytearray(new)
        struct.pack_into('<I', trial, o, n_smg)
        probe = _abs(BULLET) + '._splice.projectile'
        open(probe, 'wb').write(bytes(trial))
        try:
            import port_field_audit as fa
            got = fa.flatten_h2(os.path.relpath(probe, TAGS))
        except SystemExit:
            got = None
        finally:
            if os.path.exists(probe):
                os.remove(probe)
        if not got:
            continue
        rest_ok = {k: v for k, v in got.items() if not k.startswith('material responses')} == \
            {k: v for k, v in before.items() if not k.startswith('material responses')}
        if rest_ok and mr(got) == mr(want):
            print('      count field at 0x%X; everything else reads as before' % o)
            if write:
                open(_abs(BULLET), 'wb').write(bytes(trial))
            return
    raise SystemExit('no count field made the splice read back cleanly (%d tried)' % len(cands))


#: flags words h2_tagfield cannot read: tool prints a set flags word as the number AND its
#: bit names on further lines, which its reader takes as an empty value
FLAGS = [('barrels/[0]/flags', 'barrels', 0, 2080)]       # GPMG: 2080; the SMG: 0


def flags_fields(write):
    path = _abs(WEAPON)
    for key, block, index, guard in FLAGS:
        now = int(flat(WEAPON)[key][1].split()[0])
        want = int(flat(SMG_WEAPON)[key][1].split()[0])
        if now == want:
            print('   %-42s already the SMG\'s %d' % (key, want))
            continue
        if now != guard:
            raise SystemExit('%s reads %d, expected %d -- check before writing' % (key, now, guard))
        print('   %-42s %d -> %d' % (key, now, want))
        if not write:
            continue
        data = bytearray(open(path, 'rb').read())
        xml = tf.export(path)
        lo, hi = tf.scope(data, xml, block, index)
        before = flat(WEAPON)
        for at in range(lo, hi - 3):
            if struct.unpack_from('<I', data, at)[0] != now:
                continue
            trial = bytearray(data)
            struct.pack_into('<I', trial, at, want)
            open(path, 'wb').write(bytes(trial))
            after = flat(WEAPON)
            moved = [k for k in before if before[k] != after.get(k)]
            if moved == [key] and int(after[key][1].split()[0]) == want:
                print('      written at 0x%X, nothing else moved' % at)
                break
            open(path, 'wb').write(bytes(data))
        else:
            raise SystemExit('%s: no candidate changed it alone; left as it was' % key)


def weapon_fields(write):
    smg_rows = tf.read_all(tf.export(_abs(SMG_WEAPON)))
    rows = tf.read_all(tf.export(_abs(WEAPON)))
    for name, block, index, nth, guard in WEAPON_FIELDS:
        want = tf._numbers(tf.pick(smg_rows, name, block, index, nth)[4])
        row = tf.pick(rows, name, block, index, nth)
        now = tf._numbers(row[4])
        code, _size, n = tf.SCALARS[row[3]]
        want = want[:n]
        label = ('%s[%d].' % (block, index) if block else '') + name + ("'" * nth)
        if all(abs(a - b) <= 1e-5 for a, b in zip(now[:n], want)):
            print('   %-42s already the SMG\'s %s' % (label, want))
            continue
        if guard is not None:
            g = guard if isinstance(guard, tuple) else (guard,)
            if any(abs(a - b) > 1e-4 for a, b in zip(now[:n], g)):
                raise SystemExit('%s reads %s, expected %s -- the tag changed since the '
                                 'audit; check before writing' % (label, now[:n], g))
        print('   %-42s %s -> %s' % (label, now[:n], want))
        if not write:
            continue
        if not any(now[:n]):                 # reads zero: bracket it (ZERO_FIELDS)
            write_by_anchor(name, block, index, nth, want if n > 1 else want[0])
        else:
            tf.set_field(_abs(WEAPON), name, want if n > 1 else want[0], block, index, nth)


def main():
    write = '--write' in sys.argv
    if write:
        backup()
    print('1. damage effects re-cloned from the SMG')
    reclone_damage(write)
    print('2. bullet material responses')
    splice_material_responses(write)
    print('3. weapon fields -> the SMG\'s')
    weapon_fields(write)
    flags_fields(write)
    print('\nnow: python h2_saw_numbers.py (the SAW\'s own numbers on the new damage '
          'effect), then rebuild 03a' if write else '\n(dry run -- pass --write)')


if __name__ == '__main__':
    main()
