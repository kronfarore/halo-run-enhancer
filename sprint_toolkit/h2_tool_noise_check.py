r"""Are two H2EK tags CONTENT-equal although their bytes differ? (tool's run-to-run noise check)

`tool bitmaps / render / collision` rewrite a tag each run, and a byte comparison then calls a
regenerated tag "changed" (h2_port_tool_proof sawp1: 8 bitmaps, 3 render models, 1 collision model).
This compares what TOOL READS: `export-tag-to-xml` of both (every field), and for a bitmap also
`export-bitmap-tga` (every image's pixels). Prints, per pair, the byte ranges that differ and
whether the exports are identical.

    python h2_tool_noise_check.py <tag A> <tag B> [...pairs]
    python h2_tool_noise_check.py --dir <folder of copies A> <kit root B> <rel tag> ...
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
TOOL = os.path.join(H2EK, 'tool.exe')


#: fields tool stamps on every import -- not content (measured on the SAW, 2026-10-20)
NOISE = ('import date', 'import time', 'modification date')


def xml_diff(xa, xb):
    """The XML lines that differ, apart from the NOISE stamps."""
    import difflib
    out = []
    for ln in difflib.unified_diff(xa.splitlines(), xb.splitlines(), n=0, lineterm=''):
        if ln.startswith(('---', '+++', '@@')):
            continue
        if any('name="%s"' % f in ln for f in NOISE):
            continue
        out.append(ln.strip()[:120])
    return out


def xml(tag):
    fd, out = tempfile.mkstemp(suffix='.xml', prefix='_h2noise_', dir=os.environ.get('TEMP'))
    os.close(fd)
    subprocess.run([TOOL, 'export-tag-to-xml', os.path.abspath(tag), out], cwd=H2EK,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    s = open(out, encoding='utf-8', errors='replace').read()
    os.remove(out)
    return s


def pixels(tag):
    """SHA-1 of every exported image of a bitmap tag (it must sit inside H2EK\\tags)."""
    rel = os.path.splitext(os.path.relpath(tag, os.path.join(H2EK, 'tags')))[0]
    d = tempfile.mkdtemp(prefix='_h2px_', dir=os.environ.get('TEMP'))
    pre = os.path.join(d, 'x_')
    subprocess.run([TOOL, 'export-bitmap-tga', rel, pre], cwd=H2EK,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = sorted((f, hashlib.sha1(open(os.path.join(d, f), 'rb').read()).hexdigest())
                 for f in os.listdir(d))
    shutil.rmtree(d)
    return out


def byte_ranges(a, b, limit=6):
    if len(a) != len(b):
        return 'sizes %d vs %d' % (len(a), len(b))
    r, i = [], 0
    while i < len(a) and len(r) < limit:
        if a[i] != b[i]:
            j = i
            while j < len(a) and a[j] != b[j]:
                j += 1
            r.append('0x%X+%d' % (i, j - i))
            i = j
        i += 1
    n = sum(1 for x, y in zip(a, b) if x != y)
    return '%d bytes differ: %s' % (n, ' '.join(r))


def compare(a, b):
    """a = a copy (anywhere), b = the tag in the kit. tool exports only from the kit's own tags
    folder, so a is swapped into b's place for its exports and b put back after."""
    da, db = open(a, 'rb').read(), open(b, 'rb').read()
    xb = xml(b)
    pb = pixels(b) if b.endswith('.bitmap') else None
    keep = b + '._noise_keep'
    shutil.copy2(b, keep)
    try:
        shutil.copy2(a, b)
        xa = xml(a if a.startswith(os.path.join(H2EK, 'tags')) else b)
        pa = pixels(b) if pb is not None else None
    finally:
        shutil.copy2(keep, b)
        os.remove(keep)
    diff = xml_diff(xa, xb)
    ok = not diff and bool(xa)
    line = '%-30s %s; tool XML %s' % (os.path.basename(b), byte_ranges(da, db),
                                      'identical apart from the import stamps' if ok
                                      else 'DIFFERS: %s' % ' | '.join(diff[:4]))
    if pb is not None:
        line += '; pixels %s (%d images)' % ('IDENTICAL' if pa == pb and pa else 'DIFFER', len(pb))
        ok = ok and pa == pb
    print(line, flush=True)
    return ok


def main():
    args = sys.argv[1:]
    ok = True
    if args[:1] == ['--dir']:
        a_root, b_root, rels = args[1], args[2], args[3:]
        for rel in rels:
            ok &= compare(os.path.join(a_root, rel), os.path.join(b_root, rel))
    else:
        for a, b in zip(args[::2], args[1::2]):
            ok &= compare(a, b)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
