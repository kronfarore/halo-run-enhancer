r"""Repoint a tag reference inside a loose Halo 2 (H2EK) tag file.

`tool export-tag-to-xml` reads a tag out; nothing writes one back, and H2EK ships no
importer, so every tag edit a port needs -- "this model uses THAT render model", "this
weapon uses THIS first person model" -- has to be done in the bytes. `h2_loosetag.py`
does that for scenarios, where the job is inserting elements; this is the other half.

A tag reference is sixteen bytes (see `halo2-loose-tag-format`):

    class 4CC, REVERSED ('mode' is written 'edom')
    pointer -- zero in a tag tool.exe wrote, but the tags BUNGIE shipped still carry
               the 2004 runtime address here, so it cannot be used to recognise one
    path length, little endian, EXCLUDING the null
    datum id, 0xFFFFFFFF

The path is not in the record. Paths are pooled null terminated in the file, and the
file is laid out in strict FIELD order -- so a struct's own paths are interleaved with
its child blocks rather than sitting in one run after it. Reconstructing which record
owns which string therefore needs the struct layout, which a loose tag does not carry.

So this does not try. It edits **by path**: the caller names the class and the current
path, both of which tool.exe reports, and the edit only goes ahead when exactly one
pooled string and exactly one record can possibly be meant. Changing a path to a
different length moves every byte after it, which is safe only because nothing in a
loose tag stores an absolute offset.

**Then tool.exe checks the work.** After writing, the tag is exported again and the
reference list must be the old one with exactly that single entry replaced -- otherwise
the file is restored. An edit that cannot be proved correct is not kept.

    python h2_tagref.py <tag>                              list the references
    python h2_tagref.py <tag> --set <class> <old> <new>    repoint one, in place
    python h2_tagref.py <tag> --copy-to <new tag>          copy first, then --set on it
"""
import os
import re
import struct
import subprocess
import sys

H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
NULL = 0xFFFFFFFF
SIG = b'dfbt'
CHUNK = 16
PATH_OK = re.compile(rb'^[A-Za-z0-9_\\\-. ]+$')
#: the characters a Halo 2 group tag is spelled with -- 'jpt!' and 'snd!' are why this
#: cannot just be `isalnum()`
CLASS_CHARS = set(b'abcdefghijklmnopqrstuvwxyz0123456789!#_ ')


def references(tag_path):
    """(class, path) for every reference that points somewhere, as TOOL.EXE reads it.

    This is the authority, not a guess: an empty reference is written
    `<tag_reference name="x" />` with no type at all, so only the ones with a path
    appear -- which is also the only kind that can be repointed.
    """
    # per-process (two sessions at once must not read each other's export), and removed
    # first so a failed export can never hand back the PREVIOUS tag's references
    out_xml = os.path.join(os.environ.get('TEMP', '.'), '_h2tagref_%d.xml' % os.getpid())
    if os.path.exists(out_xml):
        os.remove(out_xml)
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.abspath(tag_path), out_xml],
                   cwd=H2EK, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    xml = open(out_xml, encoding='utf-8', errors='replace').read()
    return [(m.group(1), m.group(2)) for m in
            re.finditer(r'<tag_reference name="[^"]*" type="([^"]*)">([^<]+)<', xml)]


def _arrays(data):
    """(start, end) of every chunk's element array -- the only bytes a record lives in."""
    out = []
    i = data.find(SIG)
    while i >= 0:
        _ver, count, elem = struct.unpack_from('<III', data, i + 4)
        out.append((i + CHUNK, i + CHUNK + count * elem))
        i = data.find(SIG, i + 4)
    return out


def records(data, length, cls=None):
    """Offsets of every reference record of this path length, optionally of one class."""
    want = cls.encode('latin-1')[::-1] if cls else None
    out = []
    for start, end in _arrays(data):
        for i in range(start, max(start, end - 15), 4):   # fields are 4-byte aligned
            head = data[i:i + 4]
            if want is not None and head != want:
                continue
            if want is None and not all(b in CLASS_CHARS for b in head):
                continue
            _ptr, n, datum = struct.unpack_from('<III', data, i + 4)
            if datum == NULL and n == length:
                out.append(i)
    return sorted(out)


def pooled(data, path):
    """Offsets where this exact path sits in the file as a null terminated string.

    Only the null AFTER it can be tested. A pooled path is not necessarily preceded by
    one: in a shader the parameter's string id is pooled flush against it, so the byte
    before the path is an ordinary letter (`...base_mapobjects\\weapons\\...`). Requiring
    a null on both sides finds nothing at all, which is how the first attempt at this
    silently failed.
    """
    raw = path.encode('latin-1') + b'\0'
    out, at = [], 0
    while True:
        at = data.find(raw, at)
        if at < 0:
            return out
        out.append(at)
        at += 1


def retarget(data, cls, old_path, new_path, record=None):
    """`data` with a `cls` reference to `old_path` pointing at `new_path`.

    A record does not carry its path, and which record owns which pooled string cannot be
    recovered from a loose tag -- the file is laid out in field order, so a struct's paths
    interleave with its child blocks. Where that leaves more than one candidate, `record`
    names which to try and `set_reference` works through them, letting tool.exe say which
    was right. Guessing is fine when the guess is checked; it is only unchecked guessing
    that ruins a tag.
    """
    at = pooled(data, old_path)
    if len(at) != 1:
        raise ValueError('%d pooled copies of %r; expected one' % (len(at), old_path))
    mine = records(data, len(old_path), cls)
    if not mine:
        raise ValueError('no %s record with a %d-character path' % (cls, len(old_path)))
    rec = record if record is not None else mine[0]
    new = new_path.encode('latin-1')
    out = bytearray(data)
    # THE LENGTH FIELD FIRST, then the string. A record is not necessarily before the
    # string it names: the file is laid out in FIELD order, so paths interleave with the
    # elements that follow them, and in a HUD the last scope widget's record sits two
    # kilobytes past the first pooled path. Replacing a path with a shorter one deletes
    # bytes and moves everything after it, so a length written afterwards at its original
    # offset lands in the middle of some other field. Writing lengths first cannot move
    # anything, so every offset is still the one that was measured.
    struct.pack_into('<I', out, rec + 8, len(new))
    out[at[0]:at[0] + len(old_path)] = new
    return bytes(out)


def candidates(data, cls, length):
    """Every record that could be the one, in file order."""
    return records(data, length, cls)


def retarget_all(data, cls, old_path, new_path):
    """`data` with EVERY `cls` reference to `old_path` pointing at `new_path`.

    A shader commonly names the same bitmap twice -- the shotgun's sight light is its own
    base map and its own self-illumination map -- and then neither copy of the string can
    be told from the other. Moving them together is well defined where moving one is not.
    """
    at = pooled(data, old_path)
    mine = records(data, len(old_path), cls)
    same_length = records(data, len(old_path))
    if not at or len(at) != len(same_length) or len(mine) != len(at):
        raise ValueError('%d pooled copies of %r, %d records of that length, %d of them '
                         '%s -- not every copy is this reference'
                         % (len(at), old_path, len(same_length), len(mine), cls))
    new = new_path.encode('latin-1')
    out = bytearray(data)
    # lengths first, for the reason in `retarget`: with eight copies to move, most of the
    # records sit AFTER some of the strings and would have shifted out from under these
    # offsets. Then the strings from the end backwards, so the earlier ones still hold.
    for rec in mine:
        struct.pack_into('<I', out, rec + 8, len(new))
    for start in reversed(at):
        out[start:start + len(old_path)] = new
    return bytes(out)


def retarget_one(data, cls, old_path, new_path, which, rec):
    """`data` with the `which`th pooled copy of `old_path` repointed, using record `rec`.

    For a tag that names the same path twice -- a weapon's `first person` block holds one
    model per species, and a port starts with both pointing at the same one -- neither copy
    can be told from the other by content. They CAN be told apart by order, since the file
    is laid out in field order, and anyway the caller need not be right: every combination
    is offered to tool.exe and the one that produces the intended list is kept.
    """
    at = pooled(data, old_path)
    new = new_path.encode('latin-1')
    out = bytearray(data)
    struct.pack_into('<I', out, rec + 8, len(new))      # the length first, as ever
    out[at[which]:at[which] + len(old_path)] = new
    return bytes(out)


def fill_reference(tag_path, cls, new_path, tries=400):
    """Fill an EMPTY `cls` reference (length 0: nothing pooled) with `new_path` -- the Spike
    Rifle's projectile, cloned from the SMG bullet whose object `model` is empty (boot 1: 'the
    spike is not visible'). The record gets the length; the path + null is INSERTED where tool
    expects it in FIELD order, which a loose tag does not say -- so every candidate place (the
    end of the record's own element array, then just after each pooled string that follows it)
    is tried and tool.exe decides: kept only when the reference list is the old one plus exactly
    this reference and every numeric field reads as before (h2_tagfield). Else restored."""
    import h2_tagfield as tf
    original = open(tag_path, 'rb').read()
    before = references(tag_path)
    rows_before = [r for r in tf.read_all(tf.export(tag_path))]
    want = cls.encode('latin-1')[::-1]
    recs = []
    for start, end in _arrays(original):
        for i in range(start, max(start, end - 15), 4):
            if original[i:i + 4] == want:
                _ptr, n, datum = struct.unpack_from('<III', original, i + 4)
                if n == 0 and datum == NULL:
                    recs.append((i, end))
    if not recs:
        raise ValueError('no empty %s reference in %s' % (cls, tag_path))
    raw = new_path.encode('latin-1') + b'\0'
    for rec, arr_end in recs:
        spots = [arr_end]
        at = arr_end
        while len(spots) < tries:
            nxt = original.find(b'\0', at)
            if nxt < 0:
                break
            at = nxt + 1
            if at not in spots:
                spots.append(at)
        for spot in spots:
            out = bytearray(original)
            struct.pack_into('<I', out, rec + 8, len(new_path))
            out[spot:spot] = raw
            open(tag_path, 'wb').write(bytes(out))
            after = references(tag_path)
            if sorted(after) != sorted(before + [(cls, new_path)]):
                continue
            x = tf.export(tag_path)
            rows = tf.read_all(x) if x else []
            if [r[4] for r in rows] != [r[4] for r in rows_before]:
                continue
            print('%s: %s (empty) -> %s  (record 0x%X, path at 0x%X; %d references, every field '
                  'as before)' % (os.path.basename(tag_path), cls, new_path, rec, spot, len(after)))
            return spot, len(raw)
    open(tag_path, 'wb').write(original)
    raise ValueError('no place for %s gave the intended result; %s restored'
                     % (new_path, os.path.basename(tag_path)))


def add_attachment(tag_path, donor_path, cls, element=0, tries=400, count_at=None, after=None):
    """Give an object tag with NO attachments the `element`th ATTACHMENT of a donor object of the
    same group whose type is a `cls` reference (the Spike Rifle, boot 1: the needle's light volume
    -- Halo 2 hangs a projectile's MGS2 / contrail on the object's attachments block; the SMG
    bullet clone has none). An empty block emits no chunk, so one is CREATED: 'dfbt', version 0,
    count 1, the donor's element bytes, then its pooled path; inserted in FIELD order -- which a
    loose tag does not say -- and the root struct's in-struct block count set to 1. Every
    (count field, insertion place) pair is tried; tool.exe decides: kept only when the reference
    list is the old one plus that reference and every old field reads as before (the new
    attachment's own rows aside). Else restored."""
    import h2_tagfield as tf
    donor = open(donor_path, 'rb').read()
    original = open(tag_path, 'rb').read()
    want = cls.encode('latin-1')[::-1]
    chunk = None
    i = donor.find(SIG)
    while i >= 0:
        _v, n, sz = struct.unpack_from('<III', donor, i + 4)
        if n > element and donor[i + CHUNK + element * sz:i + CHUNK + element * sz + 4] == want:
            chunk = (i, n, sz)
            break
        i = donor.find(SIG, i + 4)
    if chunk is None:
        raise ValueError('%s has no block whose element %d is a %s reference' % (donor_path, element, cls))
    at, n, sz = chunk
    elem = donor[at + CHUNK + element * sz:at + CHUNK + (element + 1) * sz]
    plen = struct.unpack_from('<I', elem, 8)[0]
    # this element's pooled data: the earlier elements' strings come first, in element order
    pool = at + CHUNK + n * sz
    for k in range(element):
        e = donor[at + CHUNK + k * sz:at + CHUNK + (k + 1) * sz]
        pool += struct.unpack_from('<I', e, 8)[0] + 1 if struct.unpack_from('<I', e, 8)[0] else 0
        pool += sum(e[o + 3] for o in range(16, sz, 4) if e[o + 3] and e[o + 3] < 64)  # sid strings
    path = donor[pool:pool + plen]
    sids = b''.join(donor[pool + plen + 1:pool + plen + 1 + sum(elem[o + 3] for o in range(16, sz, 4)
                                                                    if elem[o + 3] and elem[o + 3] < 64)])
    if sids:
        raise ValueError('the donor attachment names a marker / colour string; not handled')
    new_chunk = SIG + struct.pack('<III', 0, 1, sz) + elem + path + b'\0'
    before = references(tag_path)
    rows_before = tf.read_all(tf.export(tag_path))
    rs, re_ = _arrays(original)[0]
    # count-field candidates: every u32 reading 0 in the target's root, nearest first to where the
    # donor's root reads n (the root structs need not be the same size: the SMG bullet's is 852
    # bytes, the needle's 604 -- each saved with its own struct version; Bungie's in-struct block
    # fields still carry 2004 pointers, so no pattern beyond the count is reliable)
    d_rs, d_re = _arrays(donor)[0]
    anchors = [o for o in range(0, d_re - d_rs - 3, 4) if struct.unpack_from('<I', donor, d_rs + o)[0] == n]
    counts = [o for o in range(0, re_ - rs - 3, 4) if struct.unpack_from('<I', original, rs + o)[0] == 0]
    counts.sort(key=lambda o: min([abs(o - a) for a in anchors] or [0]))
    # hints first: `count_at` the block field's ABSOLUTE offset (from the field order: the
    # Spiker's projectile flags at 460 minus the object struct's five trailing 12-byte blocks),
    # `after` the pooled path the chunk follows (the needle's: its material effects path)
    if count_at is not None:
        counts = [count_at - rs] + [o for o in counts if o != count_at - rs]
    spots = [re_]
    if after:
        k = original.find(after.encode('latin-1') + b'\0', re_)
        if k >= 0:
            spots = [k + len(after) + 1, re_]
    p = re_
    while len(spots) < tries:
        nxt = original.find(b'\0', p)
        if nxt < 0:
            break
        p = nxt + 1
        spots.append(p)
    for co in counts:
        for spot in spots:
            out = bytearray(original)
            struct.pack_into('<I', out, rs + co, 1)
            out[spot:spot] = new_chunk
            open(tag_path, 'wb').write(bytes(out))
            after = references(tag_path)
            if sorted(after) != sorted(before + [(cls, path.decode('latin-1'))]):
                continue
            x = tf.export(tag_path)
            rows = tf.read_all(x) if x else []
            old = [r[4] for r in rows if not r[0].startswith('attachments')]
            if old != [r[4] for r in rows_before]:
                continue
            print('%s: + attachment %s %s (from %s #%d; count field root+0x%X, chunk at 0x%X; '
                  'every old field as before)' % (os.path.basename(tag_path), cls, path.decode(),
                                                  os.path.basename(donor_path), element, co, spot))
            return path.decode('latin-1')
    open(tag_path, 'wb').write(original)
    raise ValueError('no (count field, place) pair gave the intended result; %s restored'
                     % os.path.basename(tag_path))


def set_reference(tag_path, cls, old_path, new_path, every=False, nth=None):
    """Repoint a reference and prove it with tool.exe, or put the tag back.

    `nth` picks WHICH of several identical references to move, counted over the list
    tool.exe reports. Without it, an ambiguous edit is still refused.
    """
    before = references(tag_path)
    if (cls, old_path) not in before:
        raise ValueError('tool.exe does not report a %s reference to %s in %s'
                         % (cls, old_path, tag_path))
    if not every and nth is None and before.count((cls, old_path)) > 1:
        raise ValueError('%s names %s %d times; pass nth= to move one or every=True to '
                         'move them together'
                         % (os.path.basename(tag_path), old_path,
                            before.count((cls, old_path))))
    if nth is None:
        want = [(cls, new_path) if r == (cls, old_path) else r for r in before]
    else:
        hits = [i for i, r in enumerate(before) if r == (cls, old_path)]
        want = list(before)
        want[hits[nth]] = (cls, new_path)

    original = open(tag_path, 'rb').read()
    if nth is not None:
        copies = len(pooled(original, old_path))
        tries = [(j, rec) for j in range(copies)
                 for rec in candidates(original, cls, len(old_path))]
    else:
        tries = [None] if every else candidates(original, cls, len(old_path))
    for rec in tries:
        if nth is not None:
            edited = retarget_one(original, cls, old_path, new_path, rec[0], rec[1])
        else:
            edited = (retarget_all(original, cls, old_path, new_path) if every
                      else retarget(original, cls, old_path, new_path, rec))
        open(tag_path, 'wb').write(edited)
        if references(tag_path) == want:
            print('%s: %s %s -> %s  (%d references, all others unchanged)'
                  % (os.path.basename(tag_path), cls, old_path, new_path, len(want)))
            return
    open(tag_path, 'wb').write(original)
    raise ValueError('none of the %d candidate records gave the intended result; '
                     '%s restored' % (len(tries), os.path.basename(tag_path)))


def main():
    tag = sys.argv[1]
    args = sys.argv[2:]
    if args and args[0] == '--copy-to':
        dest = args[1]
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        open(dest, 'wb').write(open(tag, 'rb').read())
        print('copied %s -> %s' % (tag, dest))
    elif args and args[0] == '--set':
        set_reference(tag, args[1], args[2], args[3])
    else:
        for k, (cls, path) in enumerate(references(tag)):
            print('%2d  %-6s %s' % (k, cls, path))


if __name__ == '__main__':
    main()
