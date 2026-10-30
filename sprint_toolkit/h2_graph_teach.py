r"""Teach a Halo 2 character's third-person animation graph a WEAPON CLASS it lacks, by cloning one
it has under a new label -- in every mode that carries it (the AR pilot, 2026-10-20/21).

WHY. Halo 2 lets you hand an ally your weapon only if the ally's 3P graph holds its weapon class /
weapon type (the weapon tag's `weapon class` / `weapon name` -- the AR's are the BR's `rifle` /
`br`). The Grunt's graph has NO `rifle` class at all (pistol: plasma pistol / needler / plasma
rifle, missile: the rocket launcher), so an allied Grunt refused the AR (user, boot on 04a) -- and
Halo 2's own BR. User: "teach the Grunt 'rifle'". This clones the Grunt's `pistol` class as
`rifle` with its `pr` type renamed `br`: a Grunt then holds a rifle the way it holds a plasma
rifle (rifle/br -> the pr overlays, everything else -> the class's `any` set).

THE LOOSE GRAPH'S MODE TREE (decoded on grunt.model_animation_graph, 2026-10-21; `walk` must
end exactly where the modes block ends or nothing is written):

    mode        28  label sid, weapon class block, mode ik block
    class       28  label sid, weapon type block, weapon ik block
    type        76  label sid, actions, overlays, deaths and damage, transitions, high / low precache
    action      8   label sid, animation index struct           (overlays: the same)
    death       16  label sid, directions block;  direction 12 = regions block;  region 4 = index
    transition  24  full name sid, state info struct (state sid + 4), destinations block
    destination 20  full name sid, mode sid, state info struct, animation index struct
    ik          8   two sids;   precache 4

  A block's chunk ('dfbt', version, count, element size) is followed by its element array, then
  each element's data in FIELD ORDER: a sid's string (no terminator; its LENGTH is the sid's high
  byte), a nested struct's 16-byte DESCRIPTOR ('IINA' animation index, 'SSTA' state info -- emitted
  where the struct's field sits, before the struct's own strings), a child block's chunk (none at
  all when it is empty). Nothing stores an absolute offset, so bytes may be inserted anywhere.
  The count is stored twice: the chunk header and the parent element's in-struct block field.

The clone = the class's struct (label sid re-lengthed, string index 0 as tool writes it) appended
to the mode's class array, its data (label renamed, type labels renamed in place) appended after
the last class's data; both counts bumped. Proved by tool's export: every original row unchanged,
the new class's rows = the source class's with the labels renamed.

    python h2_graph_teach.py <graph tag> --clone pistol=rifle --type pr=br [--write]
"""
import argparse
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_stringid  # noqa: E402  (export)

SIG = b'dfbt'
BACKUP = os.path.join('E:' + os.sep, 'HaloBackups', 'h2_graph_teach')
SCHEMA = {
    'mode': [('sid', 0), ('blk', 4, 'class'), ('blk', 16, 'ik')],
    'class': [('sid', 0), ('blk', 4, 'type'), ('blk', 16, 'ik')],
    'type': [('sid', 0), ('blk', 4, 'action'), ('blk', 16, 'action'), ('blk', 28, 'death'),
             ('blk', 40, 'transition'), ('blk', 52, 'precache'), ('blk', 64, 'precache')],
    'action': [('sid', 0), ('desc', b'IINA')],
    'ik': [('sid', 0), ('sid', 4)],
    'precache': [],
    'death': [('sid', 0), ('blk', 4, 'direction')],
    'direction': [('blk', 0, 'region')],
    'region': [('desc', b'IINA')],
    'transition': [('sid', 0), ('desc', b'SSTA'), ('sid', 4), ('blk', 12, 'destination')],
    'destination': [('sid', 0), ('sid', 4), ('desc', b'SSTA'), ('sid', 8), ('desc', b'IINA')],
}


def walk(d, at, kind, elems, chunks):
    """Parse the block chunk at `at`; returns its end. elems: (kind, chunk, index, struct
    offset, data start, data end); chunks: {chunk offset: (kind, count, size, end)}."""
    if d[at:at + 4] != SIG:
        raise ValueError('no %s chunk at 0x%X' % (kind, at))
    _v, n, sz = struct.unpack_from('<III', d, at + 4)
    p = at + 16 + n * sz
    for i in range(n):
        e = at + 16 + i * sz
        start = p
        for f in SCHEMA[kind]:
            if f[0] == 'sid':
                p += d[e + f[1] + 3]
            elif f[0] == 'desc':
                if d[p:p + 4] != f[1]:
                    raise ValueError('no %s descriptor at 0x%X (%s)' % (f[1], p, kind))
                p += 16
            elif struct.unpack_from('<I', d, e + f[1])[0]:
                # the Jackal + Drone graphs: a stale precache count with no chunk behind it
                if f[2] == 'precache' and d[p:p + 4] != SIG:
                    continue
                p = walk(d, p, f[2], elems, chunks)
        elems.append((kind, at, i, e, start, p))
    chunks[at] = (kind, n, sz, p)
    return p


def modes_chunk(d):
    """The modes block: the root struct's 49-ish 28-byte chunk -- found as the chunk whose walk
    as 'mode' succeeds and ends on a root descriptor (the field after it)."""
    i = d.find(SIG, 0x40 + 16)
    while i >= 0:
        _v, n, sz = struct.unpack_from('<III', d, i + 4)
        if sz == 28 and n > 0:
            try:
                el, ch = [], {}
                end = walk(d, i, 'mode', el, ch)
                if d[end:end + 4].isalpha() or end == len(d):
                    return i, end, el, ch
            except (ValueError, struct.error, IndexError):
                pass
        i = d.find(SIG, i + 4)
    raise SystemExit('no modes block found')


def label(d, el):
    kind, _c, _i, e, start, _end = el
    return d[start:start + d[e + 3]].decode('latin-1')


def teach(path, src, dst, type_renames, write=False):
    d = bytearray(open(path, 'rb').read())
    at, end, elems, chunks = modes_chunk(bytes(d))
    by_struct = {e[3]: e for e in elems}
    modes = [e for e in elems if e[0] == 'mode' and e[1] == at]
    edits = []                          # (mode element, class chunk, source class element)
    for m in modes:
        cnt = struct.unpack_from('<I', d, m[3] + 4)[0]
        if not cnt:
            continue
        cls_chunk = next(c for c, v in chunks.items() if v[0] == 'class' and m[4] <= c < m[5])
        mine = [e for e in elems if e[0] == 'class' and e[1] == cls_chunk]
        names = [label(d, e) for e in mine]
        if dst in names:
            print('   %-20s already has %s' % (label(d, m), dst))
            continue
        if src in names:
            edits.append((m, cls_chunk, mine[names.index(src)], mine))
    print('%s: %d modes, %s in %d of them' % (os.path.basename(path), len(modes), src, len(edits)))
    for m, cc, e, _mine in edits:
        print('   %-20s %s -> +%s' % (label(d, m), src, dst))
    if not edits or not write:
        return edits
    before = h2_stringid.export(path)
    os.makedirs(BACKUP, exist_ok=True)
    keep = os.path.join(BACKUP, os.path.basename(path))
    if not os.path.exists(keep):
        shutil.copy(path, keep)
    for m, cc, e, mine in sorted(edits, key=lambda t: -t[1]):
        _k, _c, _i, so, ds, de = e
        clone_struct = bytearray(d[so:so + 28])
        struct.pack_into('<I', clone_struct, 0, len(dst) << 24)
        data = bytearray(d[ds:de])
        # the type labels inside, renamed in place (same length only)
        for t in elems:
            if t[0] == 'type' and ds <= t[4] < de:
                old = label(d, t)
                new = type_renames.get(old)
                if new:
                    if len(new) != len(old):
                        raise SystemExit('type rename %s -> %s must keep the length' % (old, new))
                    off = t[4] - ds
                    data[off:off + len(old)] = new.encode('latin-1')
        data = bytearray(dst.encode('latin-1')) + data[len(src):]
        _kind, n, sz, cend = chunks[cc]
        d[cend:cend] = data                                 # the data, after the last class's
        d[cc + 16 + n * sz:cc + 16 + n * sz] = clone_struct  # the struct, after the last struct
        struct.pack_into('<I', d, cc + 8, n + 1)             # the chunk's count
        struct.pack_into('<I', d, m[3] + 4, n + 1)           # the mode's in-struct count
    original = open(path, 'rb').read()
    open(path, 'wb').write(bytes(d))
    # proofs: our own walk ends where the modes block ends, and tool reads every original row
    # unchanged with the new rows added
    a2, e2, _el, _ch = modes_chunk(bytes(d))
    after = h2_stringid.export(path)
    grown = sum(1 for _ in after) - sum(1 for _ in before)
    lost = [r for r in before if r not in after]
    bad = []
    if lost:
        bad.append('%d original rows changed' % len(lost))
    if not any(r[2] == dst for r in after):
        bad.append('tool does not read a %s label' % dst)
    if bad:
        open(path, 'wb').write(original)
        raise SystemExit('refused, restored: %s %s' % ('; '.join(bad), lost[:3]))
    print('   written: +%d bytes, tool reads %d more rows, every original row unchanged'
          % (len(d) - len(original), grown))
    return edits


def drop_ik(path, write=False, classes=('any',)):
    """Remove the IK block of the named weapon CLASSES (the Spike Rifle, boot 5, 2026-10-22): a FP
    graph seeded from Bungie's SMG carries its single-wield class `any`'s IK entry `left_hand` ->
    weapon marker `left_hand` (the Chief grips the SMG two-handed). On a ONE-handed port it drags the
    Chief's left hand onto that marker, into the gun, whatever the animations say. The class's ik
    chunk (header, elements, their strings) is deleted and the in-struct count zeroed (an empty
    block has no chunk). Proved: our walk still ends where the modes block ends, and tool reads
    every original row unchanged but the IK strings. Returns the number of IK entries removed."""
    d = bytearray(open(path, 'rb').read())
    at, end, elems, chunks = modes_chunk(bytes(d))
    cuts = []
    for e in elems:
        if e[0] != 'class' or label(d, e) not in classes:
            continue
        _k, _c, _i, so, ds, de = e
        if not struct.unpack_from('<I', d, so + 16)[0]:
            continue
        ik = [c for c, v in chunks.items() if v[0] == 'ik' and ds <= c < de]
        if len(ik) != 1:
            raise SystemExit('class %s: %d ik chunks' % (label(d, e), len(ik)))
        c = ik[0]
        _kind, n, sz, cend = chunks[c]
        cuts.append((so, c, cend, n))
    print('%s: %d IK block(s) in %s' % (os.path.basename(path), len(cuts), '/'.join(classes)))
    if not cuts or not write:
        return sum(c[3] for c in cuts)
    before = h2_stringid.export(path)
    original = bytes(d)
    for so, c, cend, n in sorted(cuts, key=lambda t: -t[1]):
        struct.pack_into('<I', d, so + 16, 0)
        del d[c:cend]
    open(path, 'wb').write(bytes(d))
    bad = []
    try:
        modes_chunk(bytes(d))
    except SystemExit as e:
        bad.append('walk: %s' % e)
    after = h2_stringid.export(path)
    gone = [r for r in before if r not in after]
    if [r for r in after if r not in before]:
        bad.append('new rows')
    if any('ik' not in (r[0] + r[2]).lower() and 'left_hand' not in r[2] for r in gone):
        bad.append('lost non-IK rows %s' % gone[:4])
    if bad:
        open(path, 'wb').write(original)
        raise SystemExit('refused, restored: %s' % '; '.join(bad))
    print('   removed: -%d bytes, tool reads every other row unchanged (%d IK rows gone)'
          % (len(original) - len(d), len(gone)))
    return sum(c[3] for c in cuts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('graph')
    ap.add_argument('--clone', required=True, help='SOURCE=NEW weapon class label')
    ap.add_argument('--type', action='append', default=[], help='OLD=NEW weapon type label (same length)')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    src, dst = a.clone.split('=')
    teach(a.graph, src, dst, dict(t.split('=') for t in a.type), a.write)


if __name__ == '__main__':
    main()
