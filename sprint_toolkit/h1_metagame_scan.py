r"""Static scan of the MCC binaries for the Halo 1 metagame (score) point table.

Background: metagame point VALUES are not in the tags. The tags carry only the
metagame TYPE and CLASS enums; the MCC wrapper reads those and decides what a kill
is worth. So somewhere in a binary there is an enum -> points lookup. This finds
the anchors for it without disassembling anything.

Read-only. It never opens the game process and never writes to a binary.

    python h1_metagame_scan.py strings            # where 'metagame' text lives
    python h1_metagame_scan.py enums              # the type/class enum name blocks
    python h1_metagame_scan.py table --near <VA>  # int/float runs near an offset
    python h1_metagame_scan.py values 10 15 25    # find a known point sequence
"""
import argparse
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MCC_ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"

BINARIES = {
    'halo1': os.path.join(MCC_ROOT, 'halo1', 'halo1.dll'),
    'halo2': os.path.join(MCC_ROOT, 'halo2', 'halo2.dll'),
    'halo3': os.path.join(MCC_ROOT, 'halo3', 'halo3.dll'),
    'odst': os.path.join(MCC_ROOT, 'halo3odst', 'halo3odst.dll'),
    'groundhog': os.path.join(MCC_ROOT, 'groundhog', 'groundhog.dll'),
    'mcc': os.path.join(MCC_ROOT, 'MCC', 'Binaries', 'Win64',
                        'MCC-Win64-Shipping.exe'),
}

# The metagame TYPE enum, in the order the tag definitions use it. This order is
# what makes a lookup table findable: a points table indexed by type has these
# many entries, in this sequence.
META_TYPES = ['brute', 'grunt', 'jackal', 'marine', 'bugger', 'hunter',
              'flood_infection', 'flood_carrier', 'flood_combat', 'flood_pure',
              'sentinel', 'elite', 'engineer', 'mule', 'turret', 'mongoose',
              'warthog', 'scorpion', 'hornet', 'pelican', 'revenant', 'seraph',
              'shade', 'watchtower', 'ghost', 'chopper', 'mauler', 'wraith',
              'banshee', 'phantom', 'scarab', 'guntower', 'engineer_dropship']

META_CLASSES = ['infantry', 'leader', 'hero', 'specialist', 'light_vehicle',
                'heavy_vehicle', 'giant_vehicle', 'standard_vehicle']


def load(name):
    path = BINARIES[name]
    if not os.path.exists(path):
        raise SystemExit('not found: ' + path)
    with open(path, 'rb') as f:
        return path, f.read()


def ascii_strings(buf, minlen=4):
    """Yield (offset, text) for printable ASCII runs."""
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, buf):
        yield m.start(), m.group().decode('ascii')


def cmd_strings(args):
    pat = re.compile(args.pattern.encode('ascii'), re.IGNORECASE)
    for name in args.bins:
        path, buf = load(name)
        print('\n=== %s  (%s, %.1f MB) ===' % (name, os.path.basename(path),
                                               len(buf) / 1048576))
        hits = 0
        for off, text in ascii_strings(buf, args.minlen):
            if pat.search(text.encode('ascii')):
                print('  %08X  %s' % (off, text[:120]))
                hits += 1
                if hits >= args.limit:
                    print('  ... (limit %d reached)' % args.limit)
                    break
        if not hits:
            print('  no match')


def _find_all(buf, needle):
    out, i = [], buf.find(needle)
    while i != -1:
        out.append(i)
        i = buf.find(needle, i + 1)
    return out


def cmd_enums(args):
    """Locate the metagame enum name blocks. A tag-definition enum stores its
    names as consecutive NUL-terminated strings, so several of these landing
    within a few hundred bytes of each other is the block we want."""
    for name in args.bins:
        path, buf = load(name)
        print('\n=== %s ===' % name)
        for label, names in (('TYPE', META_TYPES), ('CLASS', META_CLASSES)):
            found = {}
            for n in names:
                offs = _find_all(buf, n.encode('ascii') + b'\x00')
                if offs:
                    found[n] = offs
            print('  %s enum: %d/%d names present' % (label, len(found), len(names)))
            if not found:
                continue
            # cluster: names whose offsets sit close together
            flat = sorted((o, n) for n, offs in found.items() for o in offs)
            best, run = [], []
            for o, n in flat:
                if run and o - run[-1][0] > args.gap:
                    if len(run) > len(best):
                        best = run
                    run = []
                run.append((o, n))
            if len(run) > len(best):
                best = run
            if len(best) >= 3:
                print('    tightest cluster: %d names, %08X..%08X'
                      % (len(best), best[0][0], best[-1][0]))
                for o, n in best[:40]:
                    print('      %08X  %s' % (o, n))
            else:
                print('    no cluster (names appear only in isolation)')


def cmd_values(args):
    """Find a known point sequence as consecutive ints or floats."""
    vals = [int(v) for v in args.values]
    print('looking for the sequence %s' % vals)
    for name in args.bins:
        path, buf = load(name)
        print('\n=== %s ===' % name)
        for width, fmt, label in ((4, '<i', 'int32'), (2, '<h', 'int16'),
                                  (1, 'b', 'int8'), (4, '<f', 'float32')):
            try:
                needle = b''.join(struct.pack(fmt, v) for v in vals)
            except struct.error:
                continue
            offs = _find_all(buf, needle)
            if offs:
                print('  %-8s %d hit(s): %s' % (label, len(offs),
                                                ', '.join('%08X' % o for o in offs[:10])))
            else:
                print('  %-8s -' % label)


def cmd_cluster(args):
    """Find WINDOWS containing all the given values, rather than a contiguous run.

    This is the right shape for a metagame table. Points are indexed by the
    metagame TYPE enum, in which grunt, jackal, hunter and elite are NOT adjacent
    (H3 order: brute, grunt, jackal, marine, bugger, hunter, ...flood..., sentinel,
    elite). So the observed values sit scattered through one table with other
    entries between them, and an exact-sequence search would miss it even when the
    table is right there.
    """
    vals = [int(v) for v in args.values]
    print('values %s, window %d bytes' % (vals, args.window))
    for name in args.bins:
        path, buf = load(name)
        print('\n=== %s (%.1f MB) ===' % (name, len(buf) / 1048576))
        # uint8 is deliberately absent: single bytes 10/15/20 occur hundreds of
        # thousands of times in a 29 MB image, so every window "matches" and the
        # result carries no information.
        for width, fmt, label in ((4, '<i', 'int32'), (2, '<h', 'int16'),
                                  (4, '<f', 'float32')):
            try:
                wanted = {struct.pack(fmt, v): v for v in vals}
            except (struct.error, OverflowError):
                continue
            # one aligned pass per width, rather than a find() loop per value
            pos = {v: [] for v in vals}
            for align in range(width if args.unaligned else 1):
                for off in range(align, len(buf) - width + 1, width):
                    v = wanted.get(buf[off:off + width])
                    if v is not None:
                        pos[v].append(off)
            for v in vals:
                pos[v].sort()
            missing = [v for v in vals if not pos[v]]
            if missing:
                print('  %-8s value(s) %s never appear -> no table this width'
                      % (label, missing))
                continue
            # sweep: every offset of the rarest value, check the others are near
            rarest = min(vals, key=lambda v: len(pos[v]))
            others = [v for v in vals if v != rarest]
            sets = {v: pos[v] for v in others}
            hits = []
            for anchor in pos[rarest]:
                lo, hi = anchor - args.window, anchor + args.window
                near = {}
                ok = True
                for v in others:
                    cand = [o for o in sets[v] if lo <= o <= hi]
                    if not cand:
                        ok = False
                        break
                    near[v] = min(cand, key=lambda o: abs(o - anchor))
                if ok:
                    hits.append((anchor, near))
            print('  %-8s %d occurrence(s) of the rarest value %d; %d window(s) hold all'
                  % (label, len(pos[rarest]), rarest, len(hits)))
            for anchor, near in hits[:args.limit]:
                spread = [anchor] + list(near.values())
                print('     %08X..%08X   %s' % (min(spread), max(spread),
                                                ', '.join('%d@%08X' % (v, o)
                                                          for v, o in
                                                          sorted(near.items()))))


def cmd_tablescan(args):
    """Find RUNS of plausible point values that contain all the known ones.

    Proximity alone is worthless here: a bare 'these three numbers sit within 64
    bytes' fires 20+ times even in halo3.dll, where the metagame is native. A real
    points table is stronger than proximity — it is a contiguous, aligned run in
    which EVERY entry is a small positive number, not just the three we know. That
    combination is rare enough to mean something.
    """
    want = {int(v) for v in args.values}
    for name in args.bins:
        path, buf = load(name)
        print('\n=== %s (%.1f MB) ===' % (name, len(buf) / 1048576))
        # float32 matters: the live score turned out to be a float (h1_scorescan
        # found it as f32 at 992.0), so the point values are plausibly floats too --
        # which every integer-only scan would have missed.
        for width, code, label in ((4, 'i', 'int32'), (2, 'h', 'int16'),
                                   (4, 'f', 'float32')):
            n = len(buf) // width
            raw = struct.unpack_from('<%d%s' % (n, code), buf, 0)
            if code == 'f':
                # only whole-numbered floats can be point values; this also throws
                # out the denormal soup that makes a raw float scan useless
                vals = [int(v) if (v == v and abs(v) < 1e9 and float(v).is_integer())
                        else 0 for v in raw]
            else:
                vals = raw
            runs = 0
            start = None
            for i in range(n):
                v = vals[i]
                ok = args.lo <= v <= args.hi
                if ok and start is None:
                    start = i
                elif not ok and start is not None:
                    seg = vals[start:i]
                    if len(seg) >= args.minlen and want.issubset(set(seg)):
                        runs += 1
                        if runs <= args.limit:
                            print('  %-6s %08X  len=%d  %s' %
                                  (label, start * width, len(seg),
                                   list(seg[:args.show])))
                    start = None
            if start is not None:
                seg = vals[start:n]
                if len(seg) >= args.minlen and want.issubset(set(seg)):
                    runs += 1
            print('  %-6s %d qualifying run(s)' % (label, runs))


def cmd_dump(args):
    """Every NUL-terminated string in a byte range — reads an enum name block in
    the order the binary stores it, which is the order a table is indexed by."""
    path, buf = load(args.bins[0])
    lo = int(args.start, 16)
    hi = lo + args.span
    print('%s  %08X .. %08X' % (os.path.basename(path), lo, hi))
    for m in re.finditer(rb'[\x20-\x7e]{%d,}\x00' % args.minlen, buf[lo:hi]):
        print('  %08X  %s' % (lo + m.start(),
                              m.group()[:-1].decode('ascii')[:110]))


def cmd_table(args):
    """Dump candidate numeric runs near an offset, to eyeball a points table."""
    path, buf = load(args.bins[0])
    center = int(args.near, 16)
    lo = max(0, center - args.span)
    hi = min(len(buf), center + args.span)
    print('%s  %08X .. %08X' % (path, lo, hi))
    for off in range(lo, hi - 32, 4):
        ints = struct.unpack_from('<8i', buf, off)
        if all(0 < v <= 500 for v in ints):
            print('  %08X  int32 %s' % (off, list(ints)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bins', nargs='+', default=['halo1'],
                    choices=sorted(BINARIES), help='which binaries to scan')
    sub = ap.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('strings')
    s.add_argument('pattern', nargs='?', default='metagame')
    s.add_argument('--minlen', type=int, default=4)
    s.add_argument('--limit', type=int, default=60)
    s.set_defaults(func=cmd_strings)

    e = sub.add_parser('enums')
    e.add_argument('--gap', type=int, default=400,
                   help='max byte gap between names in one cluster')
    e.set_defaults(func=cmd_enums)

    v = sub.add_parser('values')
    v.add_argument('values', nargs='+')
    v.set_defaults(func=cmd_values)

    c = sub.add_parser('cluster')
    c.add_argument('values', nargs='+')
    c.add_argument('--window', type=int, default=128)
    c.add_argument('--limit', type=int, default=25)
    c.add_argument('--unaligned', action='store_true',
                   help='also scan offsets not aligned to the value width')
    c.set_defaults(func=cmd_cluster)

    ts = sub.add_parser('tablescan')
    ts.add_argument('values', nargs='+')
    ts.add_argument('--lo', type=int, default=1)
    ts.add_argument('--hi', type=int, default=1000)
    ts.add_argument('--minlen', type=int, default=6)
    ts.add_argument('--show', type=int, default=24)
    ts.add_argument('--limit', type=int, default=20)
    ts.set_defaults(func=cmd_tablescan)

    d = sub.add_parser('dump')
    d.add_argument('start', help='file offset, hex')
    d.add_argument('--span', type=int, default=512)
    d.add_argument('--minlen', type=int, default=3)
    d.set_defaults(func=cmd_dump)

    t = sub.add_parser('table')
    t.add_argument('--near', required=True, help='file offset, hex')
    t.add_argument('--span', type=int, default=4096)
    t.set_defaults(func=cmd_table)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == '__main__':
    sys.exit(main() or 0)
