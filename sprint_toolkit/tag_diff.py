r"""Compare two tags of the same class, field by field.

`plugin_diff.py` compares two PLUGINS -- what a tag class can hold in two games. This
compares two TAGS -- what two actual tags hold, in one map, through one plugin. That is
the question you ask when a level ships two things that look like the same weapon and
you need to know whether they really are: the Sentinel's beam and its eliminator beam,
a normal Brute's gun and a Chieftain's, a stock weapon and the variant a mission swaps
in.

Reading is the whole point. A plugin lists every field the class CAN have and most tags
carry only some, so "both read nothing" and "both read the same value" are different
answers and are reported differently -- a field neither tag defines is not a similarity,
it is an absence, and a card written against it would silently do nothing.

    python sprint_toolkit/tag_diff.py --game "Halo 2" --map 06a --class weap \
        objects\characters\sentinel_aggressor\weapons\beam\sentinel_aggressor_beam \
        objects\characters\sentinel_aggressor\weapons\beam_elim\sent_agg_beam_elim

    ... --same        also list the fields that agree
    ... --auto        find the map that carries both, instead of naming one
"""
import argparse
import contextlib
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOL = os.path.dirname(_HERE)
os.chdir(_TOOL)
sys.path.insert(0, _TOOL)

with contextlib.redirect_stdout(io.StringIO()):
    import halo_patch as hp                                       # noqa: E402

CFG = json.load(open('settings.json', encoding='utf-8'))
_ROOT = CFG.get('mcc_root') or (
    r'C:\Program Files (x86)\Steam\steamapps\common'
    r'\Halo The Master Chief Collection')

GAMES = {
    'Halo 1':       (['Halo1MCC', 'Halo1'], os.path.join(_ROOT, 'halo1', 'maps')),
    'Halo 2':       (['Halo2MCC', 'Halo2'],
                     os.path.join(_ROOT, 'halo2', 'h2_maps_win64_dx11')),
    'Halo 3':       (['Halo3MCC', 'Halo3'], os.path.join(_ROOT, 'halo3', 'maps')),
    'Halo 3: ODST': (['ODSTMCC', 'ODST'], os.path.join(_ROOT, 'halo3odst', 'maps')),
    'Halo Reach':   (['ReachMCC', 'Reach'], os.path.join(_ROOT, 'haloreach', 'maps')),
}
JUNK = ('shared', 'campaign', 'single_player_shared', 'bitmaps', 'sounds', 'ui',
        'mainmenu')


def plugin_fields(plugin):
    """(name, block) for every numeric or enum field the plugin declares, in order."""
    out, seen = [], set()
    for f in getattr(plugin, 'fields', []):
        t = str(f.get('type', ''))
        if not t.startswith(('float', 'int', 'real', 'rangef', 'degree', 'short',
                             'uint', 'enum', 'byte', 'bool')):
            continue
        key = (f['name'], '/'.join(f.get('block_chain') or []) or None)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def read(m, cls, path, field, plug, block):
    """The value(s) this field holds on this tag, or None when it defines nothing.

    read_all returns (tag_path, value) pairs -- one per tag matching the path -- so the
    paths have to be dropped or every field reads as 'different' simply because the two
    tags have different names."""
    try:
        rows = m.read_all(cls, path, field, plug, block, 'all')
    except Exception:
        return None
    vals = [v for _p, v in (rows or [])]
    if not vals:
        return None
    # a value may itself be a list (index='all' over a block); flatten one level so
    # a one-element block and a bare value compare the same
    flat = []
    for v in vals:
        flat.extend(v if isinstance(v, (list, tuple)) else [v])
    return flat


def norm(v):
    """Compare loosely enough that float noise is not a difference."""
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return tuple(norm(x) for x in v)
    try:
        return round(float(v), 5)
    except (TypeError, ValueError):
        return v


def fmt(v, width=30):
    if v is None:
        return '(undefined)'
    if isinstance(v, (list, tuple)):
        s = ', '.join(str(x) for x in v) if len(v) > 1 else str(v[0])
    else:
        s = str(v)
    return s if len(s) <= width else s[:width - 1] + '…'


def find_map(game, cls, a, b, want=None):
    subs, folder = GAMES[game]
    if not os.path.isdir(folder):
        return None, None
    names = sorted(set(f[:-4] for f in os.listdir(folder) if f.endswith('.map')))
    if want:
        names = [n for n in names if n.lower() == want.lower()] or names
    for nm in names:
        if nm in JUNK:
            continue
        p = os.path.join(folder, nm + '.map')
        try:
            m = hp.open_map(p, game)
        except Exception:
            continue
        if m.find_tags(cls, a) and m.find_tags(cls, b):
            return nm, m
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tags', nargs=2, help='two tag paths of the same class')
    ap.add_argument('--game', required=True, choices=sorted(GAMES))
    ap.add_argument('--map', help='mission id; omit to search for one carrying both')
    ap.add_argument('--class', dest='cls', required=True,
                    help='tag class, e.g. weap / proj / jpt!')
    ap.add_argument('--same', action='store_true', help='also list fields that agree')
    args = ap.parse_args()

    a, b = args.tags
    nm, m = find_map(args.game, args.cls, a, b, args.map)
    if m is None:
        print('no %s map carries both %r and %r as %s'
              % (args.game, a, b, args.cls))
        return 1
    subs, _ = GAMES[args.game]
    plug = hp.PluginRegistry(CFG['assembly_plugins_dir'], subs).get(args.cls)
    if plug is None:
        print('no %s plugin for %s' % (args.cls, args.game))
        return 1

    print('%s   map %s   class %s' % (args.game, nm, args.cls))
    print('  A = %s' % a)
    print('  B = %s' % b)
    print()
    diff, same, only_a, only_b, neither = [], [], [], [], 0
    for field, block in plugin_fields(plug):
        va = read(m, args.cls, a, field, plug, block)
        vb = read(m, args.cls, b, field, plug, block)
        if va is None and vb is None:
            neither += 1
            continue
        if va is None:
            only_b.append((field, block, vb)); continue
        if vb is None:
            only_a.append((field, block, va)); continue
        (same if norm(va) == norm(vb) else diff).append((field, block, va, vb))

    print('=' * 88)
    print('DIFFERENT   %d field(s)' % len(diff))
    print('  %-34s %-30s %-30s' % ('field', 'A', 'B'))
    for field, block, va, vb in diff:
        print('  %-34s %-30s %-30s%s'
              % (field[:34], fmt(va), fmt(vb), '   [%s]' % block if block else ''))
    for label, rows in (('ONLY A defines', only_a), ('ONLY B defines', only_b)):
        if rows:
            print()
            print('%s   %d field(s)' % (label, len(rows)))
            for field, block, v in rows:
                print('  %-34s %-30s%s'
                      % (field[:34], fmt(v), '   [%s]' % block if block else ''))
    if args.same:
        print()
        print('IDENTICAL   %d field(s)' % len(same))
        for field, block, va, _vb in same:
            print('  %-34s %s' % (field[:34], fmt(va)))
    print()
    print('%d different, %d identical, %d only-A, %d only-B, %d defined by neither'
          % (len(diff), len(same), len(only_a), len(only_b), neither))
    return 0


if __name__ == '__main__':
    sys.exit(main())
