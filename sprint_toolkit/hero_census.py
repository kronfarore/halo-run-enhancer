r"""hero_census.py -- every campaign character the ENGINE labels Hero or Leader.

The campaign-metagame bucket on a character tag carries a `Class` (Halo 3 onward) /
`Metagame Classification` (Halo 1-2) enum, and its options are identical in all five
games:

    0 Infantry   1 Leader   2 Hero   3 Specialist   4-7 vehicles

That is Bungie's own answer to "is this a boss", so it is a far better source for the
boss lists than reading names and guessing. This walks every campaign map of every
game and reports the Hero and Leader characters, cross-referenced against the bosses
halo.json already declares -- i.e. what we missed.

Where the field lives differs per game, so it is read THROUGH THE PLUGIN by field name
rather than by hardcoded offset:

    Halo 1        `actv` tag, root level, "Metagame Classification"  (enum16)
    Halo 2        `char` tag, "Campaign Metagame Bucket" block, "Metagame
                  Classification". Note Halo 2 ALSO has that field name under General
                  Properties, so the block name is required to disambiguate.
    Halo 3/ODST   `char` tag, "Campaign Metagame Bucket" block, "Class"
    Reach         same as Halo 3

Two caveats the output makes explicit:

  * INHERITANCE. A variant that does not populate the bucket inherits it from its
    parent character, and reads back as an empty list. Those are reported as
    `inherits` rather than silently dropped -- a boss card must name fields the
    variant itself holds (see ModifierDatabase.get_boss_modifiers_filtered), so an
    inheriting variant cannot carry one.
  * USED vs PRESENT. Every character tag in the map is read, which OVER-reports: a
    tag can arrive as a dependency of another tag and never spawn. That is the right
    error direction for a "what did we miss" sweep, but it means a hit is a candidate,
    not a confirmation. Confirm with the scenario's character palette before acting on
    one -- `reach_census.py --union` does that for Reach.

Reads only. MCC may be running.

    python sprint_toolkit/hero_census.py
    python sprint_toolkit/hero_census.py --game "Halo 2"
    python sprint_toolkit/hero_census.py --class Leader
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import assembly_plugins
import halo_patch                                    # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_vault as V                                # noqa: E402

ROOT = os.environ.get(
    'MCC_ROOT',
    r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection")
# Resolved rather than hardcoded: Assembly moved off the Steam drive and every
# CLI tool that had the old path baked in stopped finding it.
PLUGINS = assembly_plugins.plugins_dir()
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_JSON = os.path.join(TOOL, 'halo.json')

CLASSES = {0: 'Infantry', 1: 'Leader', 2: 'Hero', 3: 'Specialist',
           4: 'Light Vehicle', 5: 'Heavy Vehicle', 6: 'Giant Vehicle',
           7: 'Standard Vehicle'}

# game -> (map folder, plugin subdirs, tag group, field, block, palette block
#          -- the palette name is kept for the confirmation step, unused here)
GAMES = {
    'Halo 1': ('halo1/maps', ['Halo1MCC', 'Halo1'], 'actv',
               'Metagame Classification', None, 'Actor Palette'),
    'Halo 2': ('halo2/h2_maps_win64_dx11', ['Halo2MCC', 'Halo2'], 'char',
               'Metagame Classification', 'Campaign Metagame Bucket',
               'Character Palette'),
    'Halo 3': ('halo3/maps', ['Halo3MCC', 'Halo3'], 'char',
               'Class', 'Campaign Metagame Bucket', 'Character Palette'),
    'Halo 3: ODST': ('halo3odst/maps', ['ODSTMCC', 'ODST'], 'char',
                     'Class', 'Campaign Metagame Bucket', 'Character Palette'),
    'Halo Reach': ('haloreach/maps', ['ReachMCC', 'Reach'], 'char',
                   'Class', 'Campaign Metagame Bucket', 'Character Palette'),
}


def tag_names(m, group):
    """(class, name) pairs for one tag group, across the parsers' two tag shapes:
    Halo 1 keys a dict by (class, name); everything else is a list of dicts."""
    out = []
    if isinstance(m.tags, dict):
        for (cls, name) in m.tags:
            if cls == group and name:
                out.append(name)
    else:
        for t in m.tags:
            if t.get('class') == group and t.get('name'):
                out.append(t['name'])
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', action='append', choices=sorted(GAMES))
    ap.add_argument('--class', dest='klass', action='append',
                    choices=sorted(set(CLASSES.values())),
                    help='which classes to report (default Hero and Leader)')
    ap.add_argument('--all-classes', action='store_true',
                    help='report the class of every character, not just the interesting ones')
    a = ap.parse_args()
    want = set(a.klass or ['Hero', 'Leader'])
    if a.all_classes:
        want = set(CLASSES.values())

    missions = json.load(open(HALO_JSON, encoding='utf-8'))['Missions']
    for game in (a.game or list(GAMES)):
        folder, subdirs, group, field, block, _pal = GAMES[game]
        reg = halo_patch.PluginRegistry(PLUGINS, subdirs)
        plugin = reg.get(group)
        print("=== %s   (%s tag, field %r%s)"
              % (game, group, field, '' if not block else ' in %r' % block))
        if plugin is None:
            print("    no %s plugin under %s" % (group, subdirs))
            continue
        found = {}          # tag name -> {'cls': set, 'maps': [], 'inherits': [] }
        for mid in sorted(missions.get(game, {})):
            # Halo 2 and Halo 3 name their files `03a_oldmombasa.map` / `010_jungle.map`
            # where the halo.json key is just `03a` / `010`, so resolve rather than
            # assuming key == basename (which silently found nothing at all).
            p = V.resolve(game, mid)
            if not p or not os.path.exists(p):
                print("    %-12s map missing" % mid)
                continue
            try:
                m = halo_patch.open_map(p, game)
            except Exception as e:
                print("    %-12s open failed: %s" % (mid, e))
                continue
            for name in tag_names(m, group):
                try:
                    vals = m.read_all(group, name, field, plugin,
                                      block=block, index='all')
                except Exception:
                    vals = []
                rec = found.setdefault(name, {'cls': set(), 'maps': [], 'inherits': []})
                if not vals:
                    rec['inherits'].append(mid)
                    continue
                for _, v in vals:
                    if isinstance(v, str):
                        rec['cls'].add(v)
                    else:
                        rec['cls'].add(CLASSES.get(int(v), 'class %s' % v))
                if mid not in rec['maps']:
                    rec['maps'].append(mid)
        rows = [(n, r) for n, r in found.items() if r['cls'] & want]
        if not rows:
            print("    nothing in %s" % ', '.join(sorted(want)))
        for n, r in sorted(rows, key=lambda kv: (sorted(kv[1]['cls']), kv[0])):
            print("    %-9s %-58s %s"
                  % ('/'.join(sorted(r['cls'])), n,
                     ' '.join(r['maps']) if r['maps'] else '(none)'))
        inh = [n for n, r in found.items() if not r['cls'] and r['inherits']]
        if inh:
            print("    (%d character tags populate no bucket at all and inherit it)"
                  % len(inh))


if __name__ == '__main__':
    main()
