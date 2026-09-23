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
    out_xml = os.path.join(os.environ.get('TEMP', '.'), '_h2tagref.xml')
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


def retarget(data, cls, old_path, new_path):
    """`data` with the one `cls` reference to `old_path` pointing at `new_path`."""
    at = pooled(data, old_path)
    mine = records(data, len(old_path), cls)
    if len(mine) != 1:
        raise ValueError('%d %s records of length %d -- cannot tell which is meant'
                         % (len(mine), cls, len(old_path)))
    # A path can be pooled more than once: gpmg.model names the same path as both its
    # render model and its collision model. Both are laid out in field order, so the
    # k-th record of that length owns the k-th copy of the string.
    same_length = records(data, len(old_path))
    if len(at) != len(same_length):
        raise ValueError('%d pooled copies of %r but %d records of that length -- the '
                         'pairing is not determined' % (len(at), old_path,
                                                        len(same_length)))
    k = same_length.index(mine[0])
    new = new_path.encode('latin-1')
    out = bytearray(data)
    out[at[k]:at[k] + len(old_path)] = new
    struct.pack_into('<I', out, mine[0] + 8, len(new))
    return bytes(out)


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
    for start in reversed(at):                # from the end, so earlier offsets hold
        out[start:start + len(old_path)] = new
    for rec in mine:
        struct.pack_into('<I', out, rec + 8, len(new))
    return bytes(out)


def set_reference(tag_path, cls, old_path, new_path, every=False):
    """Repoint a reference and prove it with tool.exe, or put the tag back."""
    before = references(tag_path)
    if (cls, old_path) not in before:
        raise ValueError('tool.exe does not report a %s reference to %s in %s'
                         % (cls, old_path, tag_path))
    if not every and before.count((cls, old_path)) > 1:
        raise ValueError('%s names %s %d times; pass every=True to move them together'
                         % (os.path.basename(tag_path), old_path,
                            before.count((cls, old_path))))
    want = [(cls, new_path) if r == (cls, old_path) else r for r in before]

    original = open(tag_path, 'rb').read()
    # Build the new bytes BEFORE opening the file. `open(p, 'wb').write(f(...))`
    # truncates the moment it is evaluated, so anything f raises leaves an empty tag
    # behind -- which is exactly how the SAW's shader got destroyed once.
    edited = (retarget_all if every else retarget)(original, cls, old_path, new_path)
    open(tag_path, 'wb').write(edited)
    after = references(tag_path)
    if after != want:
        open(tag_path, 'wb').write(original)
        raise ValueError('the edit did not read back as intended; %s restored.\n'
                         '  wanted %s\n  got    %s' % (tag_path, want, after))
    print('%s: %s %s -> %s  (%d references, all others unchanged)'
          % (os.path.basename(tag_path), cls, old_path, new_path, len(after)))


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
