r"""Read and write numeric fields inside a loose Halo 2 (H2EK) tag.

`h2_tagref.py` moves tag REFERENCES; this moves the numbers -- rounds per magazine, rate
of fire, damage, velocity -- which is what steps 4, 5 and 7 of a port are made of.

**The Assembly plugins cannot be used for this.** They give every field's offset, but in
the CACHE layout, and a loose tag is laid out differently: the weapon's root struct is
0x31C bytes in a cache and 0x5F4 on disk. It is not a matter of converting, either. In
the cache a tag reference is 8 bytes, a tag block 8 and a string id 4; on disk a tag
reference is 16. Solving 35*(ref-8) + 13*(block-8) + 15*(stringid-4) = 728 for the
weapon's root struct has no sensible whole-number answer at all, so the loose struct
holds editor-side data the cache does not, and no arithmetic gets from one to the other.

**So the offset is found, and the finding is proved.** `tool export-tag-to-xml` prints
every field's value, so:

    1. read what the field currently says,
    2. list every place in the tag whose bytes decode to that, given its type,
    3. write a probe into each candidate in turn and export again -- the offset is the
       one where THAT field changed to the probe and nothing else moved.

Each candidate costs one export, and a field with a distinctive value usually has only a
handful. A field reading zero has hundreds, because padding reads zero too, and that is
reported rather than guessed at. Results are cached in `h2_tagfield_offsets.json`, keyed
by the tag group and the field, so the search happens once per field per tag type.

Every write is confirmed the same way `h2_tagref.py` confirms its own: the tag is
exported again, that field must hold the new value, nothing else may have changed, and
the file is restored if either is untrue.

    python h2_tagfield.py <tag>                                  what tool reports
    python h2_tagfield.py <tag> --get "<field>"                  read one, with its offset
    python h2_tagfield.py <tag> --set "<field>" <value>          write one
    python h2_tagfield.py <tag> --set "<field>" <v> --block Magazines --index 0
"""
import json
import math
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref

H2EK = h2_tagref.H2EK
CACHE = os.path.join(HERE, 'h2_tagfield_offsets.json')
SIG = b'dfbt'
CHUNK = 16
#: A field whose value repeats all over its own element cannot be told from the padding,
#: and trying every match means writing probes into structural bytes until something
#: breaks. Past this many, say so instead.
MAX_CANDIDATES = 40

#: Angles are stored in RADIANS and printed in DEGREES. Searching the file for the 1.0
#: that tool prints for a barrel's minimum error finds nothing at all; 0.0174533 finds it
#: on the nose, with the error angle pair in the two floats that follow. Every angle is
#: converted on the way in and on the way out.
ANGLES = ('angle', 'angle bounds')

#: struct code, width and how many numbers in a row, per type tool prints
SCALARS = {
    'real': ('<f', 4, 1), 'angle': ('<f', 4, 1), 'real fraction': ('<f', 4, 1),
    'short integer': ('<h', 2, 1), 'char integer': ('<b', 1, 1),
    'long integer': ('<i', 4, 1),
    'enum': ('<h', 2, 1), 'char enum': ('<b', 1, 1),
    'word flags': ('<H', 2, 1), 'long flags': ('<I', 4, 1), 'byte flags': ('<B', 1, 1),
    # bounds are two numbers side by side; `--set` takes them as "lo,hi"
    'real bounds': ('<f', 4, 2), 'angle bounds': ('<f', 4, 2),
    'short integer bounds': ('<h', 2, 2),
}


def export(tag_path):
    # per-process: two searches running at once would otherwise fight over one file,
    # and on Windows the loser fails with "used by another process" rather than waiting
    out = os.path.join(os.environ.get('TEMP', '.'), '_h2tagfield_%d.xml' % os.getpid())
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.abspath(tag_path), out],
                   cwd=H2EK, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out) or not os.path.getsize(out):
        return None                      # the probe broke the tag; that candidate is out
    return open(out, encoding='utf-8', errors='replace').read()


def read_all(xml):
    """[(block, element index, field name, type, text)] in the order tool prints them."""
    out, stack = [], []
    token = re.compile(r'<(/?)(block|element|field)\b([^>]*)>([^<]*)', re.S)
    for m in token.finditer(xml):
        closing, kind, attrs, text = m.group(1), m.group(2), m.group(3), m.group(4)
        if kind == 'block':
            if closing:
                if stack:
                    stack.pop()
            else:
                name = re.search(r'name="([^"]*)"', attrs)
                stack.append([name.group(1) if name else '?', 0])
        elif kind == 'element' and not closing and stack:
            idx = re.search(r'index="(\d+)"', attrs)
            stack[-1][1] = int(idx.group(1)) if idx else 0
        elif kind == 'field' and not closing:
            name = re.search(r'name="([^"]*)"', attrs)
            ftype = re.search(r'type="([^"]*)"', attrs)
            if name and ftype:
                block, index = (stack[-1][0], stack[-1][1]) if stack else ('', 0)
                out.append((block, index, name.group(1), ftype.group(1), text.strip()))
    return out


def _numbers(text):
    """The numbers tool printed for a field: one, or a pair for a bounds."""
    first = text.splitlines()[0] if text.strip() else ''
    return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', first)]


def _number(text):
    ns = _numbers(text)
    return ns[0] if ns else None


def pick(rows, name, block='', index=0, nth=0):
    """The `nth` field of this name in that element.

    A name is not unique. tool flattens a block's nested structs into one list, so
    `barrels` prints TWO "minimum error" fields and two "error angle"s -- the first pair
    belonging to the firing-error struct, the live ones second. Asking for the wrong one
    is how a weapon gets its spread written into its rate of fire.
    """
    hits = [row for row in rows
            if row[2].lower() == name.lower() and row[0].lower() == block.lower()
            and (not block or row[1] == index)]
    if len(hits) > nth:
        return hits[nth]
    raise KeyError('no field %r%s%s'
                   % (name, ' in %s[%d]' % (block, index) if block else '',
                      ', occurrence %d of %d' % (nth, len(hits)) if hits else ''))


def arrays(data):
    """(start, end) of every chunk's element array -- the only bytes a field can be in."""
    out = []
    i = data.find(SIG)
    while i >= 0:
        _ver, count, elem = struct.unpack_from('<III', data, i + 4)
        out.append((i + CHUNK, i + CHUNK + count * elem))
        i = data.find(SIG, i + 4)
    return out


def chunk_for(xml, block, index):
    """Which chunk, and which slice of it, a block's element occupies.

    Chunks are written depth first and the XML prints blocks in that same order, so the
    Nth block tool opens is the Nth chunk after the root. Scoping the search this way is
    what makes it quick: the candidates for a field are only the bytes of its own
    element, not of the whole file, so even a field reading zero has a handful rather
    than hundreds.
    """
    if not block:
        return 0, 0
    n = 0
    for m in re.finditer(r'<block name="([^"]*)"', xml):
        n += 1
        if m.group(1).lower() == block.lower():
            return n, index
    raise KeyError('no block %r in this tag' % block)


def scope(data, xml, block, index):
    """(start, end) of the bytes that element occupies, or the whole file if unknown."""
    which, idx = chunk_for(xml, block, index)
    chunks = arrays(data)
    if which >= len(chunks):
        return None
    start, end = chunks[which]
    if which == 0:
        return start, end
    elem = (end - start)
    counts = struct.unpack_from('<III', data, start - CHUNK + 4)
    if counts[1]:
        elem = (end - start) // counts[1]
    base = start + idx * elem
    return base, min(base + elem, end)


def stored(ftype, value):
    """What a value tool PRINTS looks like in the file."""
    return math.radians(value) if ftype in ANGLES else value


def printed(ftype, value):
    """The other way round."""
    return math.degrees(value) if ftype in ANGLES else value


def candidates(data, ftype, values, within=None):
    """Every offset whose bytes already decode to `values`, given the field's type."""
    code, size, n = SCALARS[ftype]
    values = [stored(ftype, v) for v in values]
    out = []
    for start, end in ([within] if within else arrays(data)):
        for at in range(start, max(start, end - size * n + 1)):
            ok = True
            for k, want in enumerate(values[:n]):
                got = struct.unpack_from(code, data, at + k * size)[0]
                if code == '<f':
                    ok = abs(got - want) <= max(5e-7, abs(want) * 1e-6)
                else:
                    ok = got == int(want)
                if not ok:
                    break
            if ok:
                out.append(at)
    return out


def _cache():
    try:
        return json.load(open(CACHE, encoding='utf-8'))
    except Exception:
        return {}


def _remember(group, key, offset):
    d = _cache()
    d.setdefault(group, {})[key] = offset
    json.dump(d, open(CACHE, 'w', encoding='utf-8'), indent=1, sort_keys=True)


def group_of(tag_path):
    return os.path.splitext(tag_path)[1].lstrip('.')


def offset_of(tag_path, name, block='', index=0, nth=0, verbose=True):
    """Where this field lives in the file, searched for once and then remembered."""
    key = ('%s[%d].%s' % (block, index, name) if block else name)
    if nth:
        key += '#%d' % nth
    group = group_of(tag_path)
    known = _cache().get(group, {}).get(key)
    if known is not None:
        return known

    original = open(tag_path, 'rb').read()
    xml = export(tag_path)
    if xml is None:
        raise RuntimeError('tool.exe cannot even read %s' % tag_path)
    rows = read_all(xml)
    row = pick(rows, name, block, index, nth)
    ftype, values = row[3], _numbers(row[4])
    if ftype not in SCALARS or not values:
        raise ValueError('%s is a %s; this only handles numbers' % (name, ftype))
    code, _size, n = SCALARS[ftype]
    if len(values) < n:
        raise ValueError('%s printed %d numbers, expected %d' % (name, len(values), n))
    probe = stored(ftype, values[0]) + 0.5 if code == '<f' else int(values[0]) + 3

    cands = candidates(bytearray(original), ftype, values,
                       scope(bytearray(original), xml, block, index))
    if verbose:
        print('   %-44s %-14s = %-16s %d candidate%s'
              % (key, ftype, ','.join('%g' % v for v in values[:n]), len(cands),
                 '' if len(cands) == 1 else 's'))
    if len(cands) > MAX_CANDIDATES:
        raise LookupError('%s reads %s, which matches %d places in its own element -- '
                          'too many to tell apart. A field reading zero is '
                          'indistinguishable from the padding around it.'
                          % (key, ','.join('%g' % v for v in values[:n]), len(cands)))

    # Probes go into a COPY, never the tag itself. A probe lands wherever the search
    # says, which sooner or later is a string id length or a block count, and a tag with
    # one of those overwritten no longer loads -- so the original is never the thing
    # being damaged. (It was, once, when an interrupted search could not write its
    # restore back.)
    probe_path = '%s._probe_%d%s' % (os.path.splitext(tag_path)[0], os.getpid(),
                                     os.path.splitext(tag_path)[1])
    try:
        for at in cands:
            edited = bytearray(original)
            struct.pack_into(code, edited, at, probe)
            open(probe_path, 'wb').write(bytes(edited))
            xml = export(probe_path)
            if xml is None:
                continue
            after = read_all(xml)
            if len(after) != len(rows):
                continue
            moved = [i for i, (a, b) in enumerate(zip(rows, after)) if a[4] != b[4]]
            if len(moved) == 1 and rows[moved[0]] is row:
                if verbose:
                    print('      found at 0x%04X' % at)
                _remember(group, key, at)
                return at
    finally:
        if os.path.exists(probe_path):
            os.remove(probe_path)
    raise LookupError('could not pin down %s: %d candidates, none of which moved it '
                      'alone' % (key, len(cands)))


def get(tag_path, name, block='', index=0):
    rows = read_all(export(tag_path))
    return _numbers(pick(rows, name, block, index)[4])


def set_field(tag_path, name, value, block='', index=0, nth=0):
    """Write one field, then make tool.exe confirm only it changed."""
    at = offset_of(tag_path, name, block, index, nth)
    original = open(tag_path, 'rb').read()
    rows = read_all(export(tag_path))
    row = pick(rows, name, block, index, nth)
    code, size, n = SCALARS[row[3]]
    vals = value if isinstance(value, (list, tuple)) else [value]
    if len(vals) != n:
        raise ValueError('%s takes %d number%s' % (name, n, '' if n == 1 else 's'))
    # Writing what is already there changes nothing, and "nothing changed" is how a
    # failed write is recognised -- so say so instead of reporting a false failure.
    now = _numbers(row[4])[:n]
    if all(abs(a - b) <= max(5e-7, abs(b) * 1e-6) for a, b in zip(now, vals)):
        print('   %-46s already %s'
              % ('%s[%d].%s' % (block, index, name) if block else name,
                 ','.join('%g' % v for v in now)))
        return

    edited = bytearray(original)
    for k, v in enumerate(vals):
        struct.pack_into(code, edited, at + k * size,
                         stored(row[3], float(v)) if code == '<f' else int(v))
    open(tag_path, 'wb').write(bytes(edited))

    xml = export(tag_path)
    after = read_all(xml) if xml else []
    moved = [i for i, (a, b) in enumerate(zip(rows, after)) if a[4] != b[4]] if after else []
    if len(moved) != 1 or rows[moved[0]] is not row:
        open(tag_path, 'wb').write(original)
        raise ValueError('%s: writing %s changed %d fields, not one; restored'
                         % (os.path.basename(tag_path), name, len(moved)))
    print('   %-46s %s -> %s'
          % ('%s[%d].%s' % (block, index, name) if block else name,
             row[4].strip(), after[moved[0]][4].strip()))


def main():
    tag = sys.argv[1]
    args = sys.argv[2:]
    block = args[args.index('--block') + 1] if '--block' in args else ''
    index = int(args[args.index('--index') + 1]) if '--index' in args else 0
    if '--set' in args:
        i = args.index('--set')
        vals = [float(x) for x in args[i + 2].split(',')]
        set_field(tag, args[i + 1], vals if len(vals) > 1 else vals[0], block, index)
    elif '--get' in args:
        name = args[args.index('--get') + 1]
        print('%s = %s  @0x%04X'
              % (name, get(tag, name, block, index),
                 offset_of(tag, name, block, index)))
    else:
        for b, i, n, t, v in read_all(export(tag)):
            if t in SCALARS:
                print('  %-22s %-42s %-14s %s'
                      % ('%s[%d]' % (b, i) if b else '', n, t, v.split('\n')[0]))


if __name__ == '__main__':
    main()
