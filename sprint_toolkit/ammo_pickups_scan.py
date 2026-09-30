"""The pickup items a ported weapon's magazines can be pointed at, scanned from the
pristine baselines of every campaign map of a game.

A magazine's Equipment reference can name ANY equipment tag, not just the ammo
powerups -- so the list is every eqip tag the game's maps carry, with the maps each one
appears in, because it is per map (a10 has no rocket or shotgun ammo at all).

    python ammo_pickups_scan.py "Halo 1" [--write]     # --write updates the catalog
"""
import contextlib, io, json, os, sys
TOOL = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection', 'tool')
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he
import halo_patch as hp

B = os.sep
GAMES = {'Halo 1': ('halo1', 'h1_campaign_maps')}
CATALOG = os.path.join(TOOL, 'weapon_ports_catalog.json')
SMALL = ('a', 'of', 'the')


def label_for(path):
    leaf = path.split(B)[-1]
    name = ' '.join(w if w in SMALL else w[:1].upper() + w[1:] for w in leaf.split())
    return name


def scan(game):
    folder, key = GAMES[game]
    per = {}
    for mission in he.CONFIG[key]:
        src = he.baseline_source(hp.default_map_path(he.mcc_root(), folder, mission), game)
        if not os.path.exists(src):
            print('  no baseline for', mission)
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            m = hp.open_map(src, game)
        for cls, path in m.tags:
            if cls == 'eqip':
                per.setdefault(path, set()).add(mission)
        del m
    return per


def choices(per, missions):
    ammo, other = [], []
    for path in sorted(per):
        c = {'label': label_for(path), 'tag': path}
        if set(per[path]) != set(missions):
            c['maps'] = sorted(per[path])
        (ammo if path.endswith('ammo') else other).append(c)
    return ammo + other


def main():
    he.load_settings()
    game = next((a for a in sys.argv[1:] if not a.startswith('--')), 'Halo 1')
    per = scan(game)
    missions = he.CONFIG[GAMES[game][1]]
    out = choices(per, missions)
    for c in out:
        print('%-24s %-44s %s' % (c['label'], c['tag'],
                                  'every map' if 'maps' not in c else ' '.join(c['maps'])))
    if '--write' in sys.argv:
        cat = json.load(open(CATALOG, encoding='utf-8'))
        n = 0
        for port in cat.get(game) or ():
            if port.get('ammo'):
                port['ammo']['choices'] = out
                port['ammo']['maps_total'] = len(missions)
                n += 1
        json.dump(cat, open(CATALOG, 'w', encoding='utf-8'), indent=1)
        print('updated %d port(s) in %s' % (n, CATALOG))


if __name__ == '__main__':
    main()
