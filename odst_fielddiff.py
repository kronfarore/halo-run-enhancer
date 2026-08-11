r"""Diff the ODST tag definitions against Halo 3's, per tag class.

ODST is an H3-engine build, but a later one, and it moved and ADDED fields. The
scenario alone shifted Squads 0x384 -> 0x3B8 and replaced Fire-Teams with
Single Locations / Designer Cells / Templated Cells. Anything else that changed is
a field halo.json may be able to target in ODST and nowhere else -- or, worse
silently, an H3 field that no longer sits where the H3 plugin says it does.

Source of truth is Assembly's plugin XML for each game, which is what the patcher
resolves field names against anyway.

    python odst_fielddiff.py                    # summary across every shared class
    python odst_fielddiff.py char               # one class, full field lists
    python odst_fielddiff.py char --new-only    # just what ODST added
    python odst_fielddiff.py --moved            # fields that exist in both but MOVED
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

PLUGINS = (r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
           r"\Assembly-1-2023-11-29-1702446457\Plugins")
H3 = os.path.join(PLUGINS, 'Halo3MCC')
ODST = os.path.join(PLUGINS, 'ODSTMCC')

BLOCKS = ('reflexive', 'tagblock', 'block', 'struct')
SKIP = ('undefined', 'unused', 'unknown', 'padding', 'pad')


def _int(s):
    if not s:
        return None
    try:
        return int(s, 16) if s.lower().startswith('0x') else int(s)
    except ValueError:
        return None


def fields(path, keep_dupes=False):
    """{'Block>Sub>Field': (offset, type)} for one plugin file.

    A plugin can define the SAME field name twice in one block -- weap's Barrels
    carries two `Minimum Error` / `Error Angle` pairs, the first for dual wielding
    and the second for single. Keyed naively they collapse and the first one
    disappears, so repeats get a `#n` suffix. `keep_dupes=False` still returns one
    entry per name for diffing, but the suffixed keys make the repeat visible.
    """
    out = {}
    seen = {}

    def add(key, val):
        n = seen.get(key, 0)
        seen[key] = n + 1
        out[key if n == 0 else '%s#%d' % (key, n + 1)] = val

    def walk(node, prefix):
        for ch in node:
            nm = (ch.get('name') or '').strip()
            if not nm or nm.lower() in SKIP:
                continue
            key = (prefix + '>' + nm) if prefix else nm
            if ch.tag.lower() in BLOCKS:
                add(key + '/', (_int(ch.get('offset')),
                                'block:' + str(_int(ch.get('entrySize')
                                                    or ch.get('elementSize')))))
                walk(ch, key)
            else:
                add(key, (_int(ch.get('offset')), ch.tag.lower()))

    try:
        walk(ET.parse(path).getroot(), '')
    except ET.ParseError as e:
        return {'<<parse error>>': (None, str(e))}
    return out


def classes():
    h3 = {f[:-4] for f in os.listdir(H3) if f.endswith('.xml')}
    od = {f[:-4] for f in os.listdir(ODST) if f.endswith('.xml')}
    return sorted(h3 & od), sorted(od - h3), sorted(h3 - od)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cls', nargs='*', help='tag classes to detail, e.g. char weap')
    ap.add_argument('--new-only', action='store_true')
    ap.add_argument('--moved', action='store_true')
    ap.add_argument('--min-new', type=int, default=1,
                    help='summary: only list classes with at least this many new fields')
    a = ap.parse_args(argv)

    shared, odst_only, h3_only = classes()
    if odst_only:
        print('tag classes ONLY in ODST: %s' % ', '.join(odst_only))
    if h3_only:
        print('tag classes ONLY in Halo 3: %s' % ', '.join(h3_only))

    targets = a.cls or shared
    rows = []
    for c in targets:
        f3 = fields(os.path.join(H3, c + '.xml'))
        fo = fields(os.path.join(ODST, c + '.xml'))
        new = sorted(set(fo) - set(f3))
        gone = sorted(set(f3) - set(fo))
        moved = sorted(k for k in (set(f3) & set(fo))
                       if f3[k][0] != fo[k][0] and f3[k][0] is not None)
        rows.append((c, len(f3), len(fo), new, gone, moved))

        if a.cls:
            print('\n=== %s  (H3 %d fields, ODST %d) ===' % (c, len(f3), len(fo)))
            print('  NEW IN ODST (%d):' % len(new))
            for k in new:
                print('     +%-58s @%s %s' % (k, fo[k][0], fo[k][1]))
            if not a.new_only:
                print('  GONE FROM ODST (%d):' % len(gone))
                for k in gone:
                    print('     -%-58s @%s' % (k, f3[k][0]))
                if a.moved:
                    print('  MOVED (%d):' % len(moved))
                    for k in moved:
                        print('     ~%-52s H3 @%s -> ODST @%s'
                              % (k, f3[k][0], fo[k][0]))

    if not a.cls:
        print('\n%-8s %6s %6s %6s %6s %6s' % ('class', 'H3', 'ODST', 'new', 'gone', 'moved'))
        print('-' * 46)
        for c, n3, no, new, gone, moved in sorted(rows, key=lambda r: -len(r[3])):
            if len(new) < a.min_new and not moved:
                continue
            print('%-8s %6d %6d %6d %6d %6d'
                  % (c, n3, no, len(new), len(gone), len(moved)))
        print('\n%d shared class(es); run with a class name for detail.' % len(shared))
    return 0


if __name__ == '__main__':
    sys.exit(main())
