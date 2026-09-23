"""Side-by-side vanilla values of a weapon's card fields in two games, from the pristine
baselines, and the ratio target/source per field -- the raw material for a port's
suggested balance.

    python balance_compare.py "Assault Rifle" "Halo 4" "Halo 1"
"""
import contextlib, io, json, os, sys
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he
import halo_patch as hp

# a representative campaign map per game that carries the weapon (pristine baseline)
MAPS = {'Halo 1': ('halo1', 'a10'), 'Halo 2': ('halo2', '01b_spacestation'),
        'Halo 3': ('halo3', '010_jungle'), 'Halo 3: ODST': ('halo3odst', 'sc100'),
        'Halo Reach': ('haloreach', 'm10'), 'Halo 4': ('halo4', 'm10_crash')}


GAME_ORDER = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']


def resolve(v, g, games=None):
    """Exactly halo_enhancer.resolve_gamed: exact match, then 'default', then the
    nearest EARLIER game, then None. Kept as a thin wrapper so the two can never drift
    -- the enhancer's own function is the authority."""
    return he.resolve_gamed(v, g, list(games or GAME_ORDER))


def values(weapon, game, db):
    folder, mission = MAPS[game]
    sub = he.CONFIG.get('map_game_folder', {}).get(game, folder)
    path = hp.default_map_path(he.mcc_root(), sub, mission)
    src = he.baseline_source(path, game)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, game)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(game, []))
    cards = db.data['Player Modifiers']['Specific Weapon Modifier'][weapon]
    out = {}
    for name, c in cards.items():
        if not isinstance(c, dict) or str(c.get('ignore', '')).lower() in ('yes', 'true'):
            continue
        games = c.get('game')
        if games and game not in (games if isinstance(games, list) else [games]):
            continue
        if game in (c.get('skip_games') or []):
            continue
        tag = resolve(c.get('tag'), game)
        if not isinstance(tag, str) or ' ' not in tag:
            continue
        cls, path_ = hp.hm.split_tag(tag.split(' & ')[0])
        plugin = reg.get(cls)
        if plugin is None:
            continue
        for t in resolve(c.get('targets'), game) or []:
            if not isinstance(t, dict) or not he.target_applies(t, game):
                continue
            field, block = resolve(t.get('field'), game), resolve(t.get('block'), game)
            if not field:
                continue
            try:
                v = m.read_first(cls, path_, field, plugin, block, t.get('index', 0) or 0,
                                 nth=resolve(t.get('nth', 0), game) or 0)
            except Exception as e:
                v = 'ERR %s' % type(e).__name__
            out.setdefault(name, []).append((field, block, v))
    return out, src


def main(weapon, src_game, dst_game):
    he.load_settings()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    a, pa = values(weapon, src_game, db)
    b, pb = values(weapon, dst_game, db)
    print('%s: %s (%s)  vs  %s (%s)' % (weapon, src_game, pa, dst_game, pb))
    rows = []
    for card in list(dict.fromkeys(list(a) + list(b))):
        fa = {(f, bl): v for f, bl, v in a.get(card, [])}
        fb = {(f, bl): v for f, bl, v in b.get(card, [])}
        for key in list(dict.fromkeys(list(fa) + list(fb))):
            va, vb = fa.get(key), fb.get(key)
            ratio = (vb / va) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and va else None
            rows.append((card, key[0], key[1], va, vb, ratio))
            print('%-22s %-34s %14s %14s   %s' % (card, key[0][:34],
                                                 va if not isinstance(va, float) else round(va, 4),
                                                 vb if not isinstance(vb, float) else round(vb, 4),
                                                 '' if ratio is None else 'x%.3f' % ratio))
    json.dump([dict(card=r[0], field=r[1], block=r[2], src=r[3], dst=r[4], ratio=r[5]) for r in rows],
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'balance_%s_%s_to_%s.json' % (weapon.replace(' ', '_'),
                                                             src_game.replace(' ', '').replace(':', ''),
                                                             dst_game.replace(' ', '').replace(':', ''))), 'w'),
              indent=1, default=str)


if __name__ == '__main__':
    main(*sys.argv[1:4])
