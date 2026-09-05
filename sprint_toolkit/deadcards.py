"""Every halo.json card, tested against a real map: does ANY matching tag carry
the field it edits? A card whose every target reads empty is a silent no-op."""
import json, os, sys
os.chdir(r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool')
sys.path.insert(0, os.getcwd())
import halo_patch as hp
import halo_enhancer as he
sys.path.insert(0, os.path.join(os.getcwd(), 'sprint_toolkit'))
import map_vault as V

CFG = json.load(open('settings.json', encoding='utf-8'))
R = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
CASES = [
    # Plain .map paths -- V.pristine_source picks the baseline where there is one.
    # These used to name `.map.bak` directly, which stops resolving the moment the
    # baseline store moves and leaves the audit silently reading PATCHED maps.
    ('Halo 3: ODST', ['ODSTMCC', 'ODST'], R + r'\halo3odst\maps\l300.map'),
    ('Halo 3: ODST', ['ODSTMCC', 'ODST'], R + r'\halo3odst\maps\l200.map'),
    ('Halo 3',       ['Halo3MCC', 'Halo3'], R + r'\halo3\maps\030_outskirts.map'),
    ('Halo 2',       ['Halo2MCC', 'Halo2'], R + r'\halo2\h2_maps_win64_dx11\08b_deltacontrol.map'),
]
DIFF = he.CONFIG.get('target_difficulty', 'Impossible')

d = json.load(open('halo.json', encoding='utf-8'))
cards = []


def walk(node, path):
    if isinstance(node, dict):
        if 'targets' in node:
            cards.append((path, node)); return
        for k, v in node.items():
            walk(v, path + [k])
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + [str(i)])


for k in d:
    if k in ('Comment', 'Missions'):
        continue
    walk(d[k], [k])

games = list(d['Missions'].keys())
for game, subs, mp in CASES:
    mp = V.pristine_source(game, mp)
    reg = hp.PluginRegistry(CFG['assembly_plugins_dir'], subs)
    m = hp.open_map(mp, game)
    print('=' * 78)
    print(game, os.path.basename(mp))
    for path, c in cards:
        if not he._game_ok_static(c, game) if hasattr(he, '_game_ok_static') else False:
            continue
        g = c.get('game')
        g = [g] if isinstance(g, str) else g
        if g and game not in g:
            continue
        tag = c.get('tag')
        tag = he.resolve_gamed(tag, game, games) if isinstance(tag, dict) else tag
        if not isinstance(tag, str) or not tag:
            continue
        ts = c['targets']
        ts = he.resolve_gamed(ts, game, games) if isinstance(ts, dict) else ts
        ts = [t for t in (ts or []) if isinstance(t, dict) and he.target_applies(t, game)]
        if not ts:
            continue
        cls, tpath = hp.hm.split_tag(tag)
        plugin = reg.get(cls)
        if plugin is None:
            continue
        first = tpath.split(' & ')[0].strip()
        if not m.find_tags(cls, first):
            continue                                    # not on this map: legitimate
        live = 0
        for t in ts:
            # Targets that do NOT read a plugin field: the jmad animation scalers
            # (Reload Time / Weapon Swap Speed go through halo3_reload), the placement
            # swappers, and the equipment-drop op. Reading them always yields nothing
            # and reports a working card as dead.
            if any(t.get(k) for k in ('reload_anim', 'swap_anim', 'map_swap',
                                      'map_equip', 'equip_drop', 'choice', 'derived')):
                live += 1
                continue
            f = t.get('field')
            f = he.resolve_gamed(f, game, games) if isinstance(f, dict) else f
            if not isinstance(f, str):
                continue
            f = hp.apply_difficulty(f, t, DIFF)
            blk = t.get('block')
            blk = he.resolve_gamed(blk, game, games) if isinstance(blk, dict) else blk
            idx = t.get('index', 0)
            try:
                if m.read_all(cls, first, f, plugin, blk, idx if idx is not None else 0):
                    live += 1
            except Exception:
                live += 1                               # can't tell; don't accuse it
        if live == 0:
            print('  DEAD  %-38s %s' % (' / '.join(path[-3:]), tag))
