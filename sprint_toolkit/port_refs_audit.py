r"""Recipe step 3 check: does each ported weapon fire ITS OWN projectile, and are the
damage effects it and that projectile name its own -- or deliberately shared globals?

Why (PORTING.md "Step 3 is TWO things"): the Halo 1 SAW shipped with its own bullet and
damage tags cloned and tuned while its trigger still named the Assault Rifle's bullet --
the game fired the donor's, the port's tags were orphans the cache never compiled, and
tuning the AR moved the SAW. Its MELEE damage effect was the AR's the same way. Cloning is
not enough: the weapon has to NAME the clones, and that is only visible in the BUILT map.

Reads the DEPLOYED map (what the game runs): every tagRef of the port's weapon and of each
projectile it fires, walked through the Assembly plugin, with field names. Each projectile
must be the port's own. Each damage effect is classified by how many of the map's
weapons/projectiles name it:
    OWN            under the port's folder
    GLOBAL         named by >= GLOBAL_MIN weapons -- a sandbox-wide effect (Halo 2+ melee,
                   shared firing feedback); sharing it is right, and no card may retune it
    DONOR'S        named by the port and only a few others -- a donor's per-weapon tag:
                   the Halo 1 melee bug. A problem when its field carries damage numbers.

    python port_refs_audit.py [--game "Halo 1"] [--map <path>]

Exit 1 when a port fires a projectile that is not its own, or names a donor's damage tag
in a damage-bearing field.
"""
import argparse
import collections
import json
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
import assembly_plugins                                            # noqa: E402
import halo_patch as hp                                            # noqa: E402

MCC = os.path.dirname(TOOL)
#: one deployed map per game that carries the port (port_backup.py profiles, checked)
MAPS = {'Halo 1': ['halo1/maps/a10.map', 'halo1/maps/b30.map'],
        'Halo 2': ['halo2/h2_maps_win64_dx11/01b_spacestation.map',
                   'halo2/h2_maps_win64_dx11/03a_oldmombasa.map'],
        'Halo 3': ['halo3/maps/010_jungle.map', 'halo3/maps/020_base.map'],
        'Halo 3: ODST': ['halo3odst/maps/sc150.map'],
        'Halo Reach': ['haloreach/maps/m20.map', 'haloreach/maps/m10.map'],
        'Halo 4': ['halo4/maps/m30_cryptum.map']}
SUBDIRS = {'Halo 1': ['Halo1MCC', 'Halo1'], 'Halo 2': ['Halo2MCC', 'Halo2'],
           'Halo 3': ['Halo3MCC', 'Halo3'], 'Halo 3: ODST': ['ODSTMCC', 'ODST'],
           'Halo Reach': ['ReachMCC', 'Reach'], 'Halo 4': ['Halo4MCC', 'Halo4']}
GLOBAL_MIN = 4
#: fields whose damage effect carries NO per-weapon damage numbers (played on whoever is
#: hit, or the shooter's own shake/rumble): sharing a donor's tag there is acceptable
FEEDBACK = ('response', 'firing damage', 'empty damage', 'misfire damage', 'overheated damage',
            'detonation damage', 'firing noise')


def plugin_xml(game, group):
    root = assembly_plugins.plugins_dir()
    for sub in SUBDIRS[game]:
        p = os.path.join(root, sub, group + '.xml')
        if os.path.isfile(p):
            return ET.parse(p).getroot()
    return None


def tag_index(m):
    """{tag ident: (class, name)}. Halo 1's map keeps a dict (class, name) -> meta with
    the ids in a side table; the later games a list of dicts."""
    if isinstance(m.tags, dict):
        return {m.tag_id(k): k for k in m.tags if m.tag_id(k) is not None}
    key = 'ident' if m.tags and 'ident' in m.tags[0] else 'datum'      # Halo 2: 'datum'
    return {t[key]: (t['class'], t['name']) for t in m.tags if t.get(key) is not None}


def refs(m, base, node, datum, path=''):
    """[(field path, (class, name))] for every non-null tagRef under `node`."""
    out = []
    idx = getattr(m, '_audit_idx', None)
    if idx is None:
        idx = m._audit_idx = tag_index(m)
    for el in node:
        kind = el.tag.lower()
        name = el.get('name', '?')
        try:
            off = int(el.get('offset', '0'), 16)
        except ValueError:
            continue
        if kind == 'tagref':
            ident = m.u32(base + off + datum)
            if ident not in (0xFFFFFFFF, 0) and ident in idx:
                out.append((path + name, idx[ident]))
        elif kind in ('tagblock', 'reflexive'):
            esz = int(el.get('elementSize') or el.get('entrySize') or '0', 16)
            try:
                elems = m.follow_all(base, [off], [esz], 'all')
            except Exception:
                elems = []
            for i, e in enumerate(elems):
                out += refs(m, e, el, datum, '%s%s[%d]/' % (path, name, i))
        elif kind == 'struct':
            out += refs(m, base + off, el, datum, path + name + '/')
    return out


def damage_users(m, game, datum):
    """{damage effect name: set of weapon/projectile names that reference it}."""
    users = collections.defaultdict(set)
    for group in ('weap', 'proj'):
        px = plugin_xml(game, group)
        if px is None:
            continue
        for name, b in m.find_tags(group, '*'):
            for _f, (cls, tname) in refs(m, b, px, datum):
                if cls == 'jpt!':
                    users[tname].add(str(name))
    return users


def audit(game, entry, map_path):
    rows = entry.get('balance', [])
    weap = next((r['tag'] for r in rows if r['class'] == 'weap'), None)
    own_dir = weap.rsplit('\\', 1)[0].lower()
    m = hp.open_map(map_path, game)
    if not m.find_tags('weap', weap):
        return None
    datum = hp._tagref_datum(m)
    wx, px = plugin_xml(game, 'weap'), plugin_xml(game, 'proj')
    users = damage_users(m, game, datum)
    problems, lines = [], []

    def own(n):
        return str(n).lower().startswith(own_dir + '\\')

    def judge(field, tname, who):
        n = len(users.get(tname, ()))
        feedback = any(k in field.lower() for k in FEEDBACK)
        if own(tname):
            kind = 'OWN'
        elif n >= GLOBAL_MIN or str(tname).lower().startswith('globals' + chr(92)):
            kind = 'GLOBAL (%d users)' % n
        else:
            kind = "DONOR'S (%d users)%s" % (n, ' - feedback field, ok' if feedback else '')
            if not feedback:
                problems.append('%s %s names %s' % (who, field, tname))
        lines.append('   %-9s %-58s %s  %s' % (who, field[-58:], tname, kind))

    wb = m.find_tags('weap', weap)[0][1]
    projs = []
    for field, (cls, tname) in refs(m, wb, wx, datum):
        if cls == 'proj':
            projs.append(tname)
            ok = own(tname)
            lines.append('   %-9s %-58s %s  %s' % ('weapon', field[-58:], tname, 'OWN' if ok else 'NOT OWN'))
            if not ok:
                problems.append('fires %s -- not the port\'s own projectile' % tname)
        elif cls == 'jpt!':
            judge(field, tname, 'weapon')
    if not projs:
        problems.append('the weapon names no projectile')
    for p in dict.fromkeys(projs):
        pb = m.find_tags('proj', p)
        if not pb:
            continue
        for field, (cls, tname) in refs(m, pb[0][1], px, datum):
            if cls == 'jpt!':
                judge(field, tname, 'projectile')
    return {'weapon': weap, 'map': map_path, 'lines': lines, 'problems': problems}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game')
    ap.add_argument('--map')
    a = ap.parse_args()
    cat = json.load(open(os.path.join(TOOL, 'weapon_ports_catalog.json'), encoding='utf-8'))
    bad = 0
    for game, v in cat.items():
        if a.game and game != a.game:
            continue
        for e in (v if isinstance(v, list) else [v]):
            r = None
            for mp in ([a.map] if a.map else [os.path.join(MCC, x) for x in MAPS.get(game, [])]):
                if mp and os.path.exists(mp):
                    r = audit(game, e, mp)
                    if r:
                        break
            print('== %s %s' % (game, e.get('weapon')))
            if not r:
                print('   (no deployed map with the port found)')
                continue
            # --map may name a kit copy on another drive (relpath cannot cross drives)
            same = os.path.splitdrive(r['map'])[0].lower() == os.path.splitdrive(MCC)[0].lower()
            print('   map %s' % (os.path.relpath(r['map'], MCC) if same else r['map']))
            for line in r['lines']:
                print(line)
            for p in r['problems']:
                print('   PROBLEM: ' + p)
            bad += len(r['problems'])
    print('%d problem(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
