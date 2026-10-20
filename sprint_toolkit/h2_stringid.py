r"""Rename STRING IDS inside a loose Halo 2 (H2EK) tag -- any length, verified by tool.

A string id field in an H2 loose tag is 4 bytes in its struct, the string's LENGTH in the
HIGH byte (`f9 0d 00 0b` for an 11-character id: the low 24 bits are a string index Bungie's
tags carry and tool-written ones may zero), and the string itself is POOLED with no
terminator after the struct, in field order, next to the tag-reference paths (measured on
saw.weapon 2026-10-20: its ten message ids are ten consecutive fields at +0x1DC, pooled as one
run `saw2_pickupsaw2_swap...saw2_swap_ai`).

That is why `h2_port_messages.py --repoint` used to insist the port's prefix have the DONOR's
length (`saw2` for `gpmg`): an in-place overwrite needs no length bookkeeping. With the length
byte located this is no longer needed -- a port's message prefix can be any length:

  1. tool.exe exports the tag; the ids to rename are found in it, in field order;
  2. the CONSECUTIVE fields holding exactly that run of lengths are located in the element
     arrays (must be unique), and the POOLED run of the old strings (must be unique);
  3. the length bytes and the pooled run are rewritten (nothing in a loose tag stores an
     absolute offset, as h2_tagref's path edits rely on);
  4. tool exports again: every renamed field must read its new value and every other field
     must be unchanged -- otherwise the file is put back and the rename refused.

    python h2_stringid.py <tag> --list
    python h2_stringid.py <tag> --prefix gpmg ar2 [--write]
"""
import argparse
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_tagref  # noqa: E402

H2EK = h2_tagref.H2EK
SIG = b'dfbt'


def export(tag_path):
    """[(field name, type, value)] for every field tool prints, in export order."""
    fd, out = tempfile.mkstemp(suffix='.xml', prefix='_h2sid_')
    os.close(fd)
    try:
        subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml',
                        os.path.abspath(tag_path), out], cwd=H2EK,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        xml = open(out, encoding='utf-8', errors='replace').read()
    finally:
        os.remove(out)
    return re.findall(r'<field name="([^"]*)" type="([^"]*)"(?: />|>([^<]*)</field>)', xml)


def string_ids(rows):
    return [(i, r[0], r[2]) for i, r in enumerate(rows) if r[1] in ('string id', 'old string id')]


def _arrays(data):
    out, i = [], data.find(SIG)
    while i >= 0:
        _v, count, elem = struct.unpack_from('<III', data, i + 4)
        out.append((i + 16, i + 16 + count * elem))
        i = data.find(SIG, i + 4)
    return out


def rename(tag_path, renames, write=False, verbose=True):
    """renames: {old id: new id}. Renames every CONSECUTIVE run of string-id fields whose
    values are all keys of `renames` (in the export, a run = adjacent string-id rows)."""
    data = bytearray(open(tag_path, 'rb').read())
    rows = export(tag_path)
    sids = string_ids(rows)
    # runs of adjacent export rows that are all to be renamed
    runs, cur = [], []
    for k, (i, name, val) in enumerate(sids):
        if val in renames and (not cur or cur[-1][0] == i - 1):
            cur.append((i, name, val))
        else:
            if cur:
                runs.append(cur)
            cur = [(i, name, val)] if val in renames else []
    if cur:
        runs.append(cur)
    if not runs:
        return 'nothing to rename'
    edits = []
    arrays = _arrays(data)
    for run in runs:
        old = [v for _i, _n, v in run]
        new = [renames[v] for v in old]
        # the HIGH byte of each field is the length; the low 24 bits are a string index
        # (Bungie's tags carry one, tool-written ones zero) and are kept as they are
        at = [p for a0, b0 in arrays for p in range(a0, b0 - 4 * len(old) + 1)
              if all(data[p + 4 * k + 3] == len(v) for k, v in enumerate(old))]
        pooled = ''.join(old).encode('latin-1')
        pat = [m.start() for m in re.finditer(re.escape(pooled), bytes(data))]
        if len(at) != 1 or len(pat) != 1:
            raise SystemExit('%s: ambiguous run %s (length fields %d, pooled %d)'
                             % (os.path.basename(tag_path), old, len(at), len(pat)))
        edits.append((at[0], pat[0], old, new))
    # back to front, so earlier offsets stay valid; lengths are fixed-size (no shift)
    for lat, pat, old, new in sorted(edits, key=lambda e: -e[1]):
        for k, v in enumerate(new):
            data[lat + 4 * k + 3] = len(v)
        a, b = pat, pat + len(''.join(old))
        data[a:b] = ''.join(new).encode('latin-1')
    if not write:
        return 'would rename %d id(s) in %d run(s)' % (sum(len(e[2]) for e in edits), len(edits))
    original = open(tag_path, 'rb').read()
    open(tag_path, 'wb').write(bytes(data))
    after = export(tag_path)
    want = [(n, t, renames.get(v, v) if t in ('string id', 'old string id') and
             any(i == j for e in runs for j, _n, _v in e) else v)
            for i, (n, t, v) in enumerate(rows)]
    if after != want:
        open(tag_path, 'wb').write(original)
        bad = [(w, a) for w, a in zip(want, after) if w != a][:4]
        raise SystemExit('%s: tool reads something else after the rename -- restored. %s'
                         % (os.path.basename(tag_path), bad or (len(want), len(after))))
    n = sum(len(e[2]) for e in edits)
    if verbose:
        print('   %s: %d id(s) renamed, verified by tool (%d -> %d bytes)'
              % (os.path.basename(tag_path), n, len(original), len(data)))
    return 'renamed %d' % n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tag')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--prefix', nargs=2, metavar=('OLD', 'NEW'))
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    rows = export(a.tag)
    if a.list or not a.prefix:
        for i, n, v in string_ids(rows):
            print('%4d  %-28s %s' % (i, n, v))
        return
    old, new = a.prefix
    ren = {v: new + v[len(old):] for _i, _n, v in string_ids(rows) if v.startswith(old + '_')}
    print(rename(a.tag, ren, a.write))


if __name__ == '__main__':
    main()
