"""Per game: for every char block an enemy card edits, how many of that card's own
tags DEFINE the block vs inherit it. The input to the ancestor-path design question."""
import json, os, sys, io, contextlib, collections
os.chdir(r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool')
sys.path.insert(0, os.getcwd())
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    import halo_enhancer as he
    import halo_patch as hp
    db = he.ModifierDatabase()

CFG = json.load(open('settings.json', encoding='utf-8'))
R = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
CASES = [
    ('Halo 2',       ['Halo2MCC', 'Halo2'],  R + r'\halo2\h2_maps_win64_dx11\07a_highcharity.map'),
    ('Halo 3',       ['Halo3MCC', 'Halo3'],  R + r'\halo3\maps\030_outskirts.map.bak'),
    ('Halo 3: ODST', ['ODSTMCC', 'ODST'],    R + r'\halo3odst\maps\l300.map.bak'),
]
DIFF = 'Impossible'
games = db.get_games()

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


for k in ('Enemy modifiers',):
    walk(d[k], [k])

for game, subs, mp in CASES:
    reg = hp.PluginRegistry(CFG['assembly_plugins_dir'], subs)
    m = hp.open_map(mp, game)
    plug = reg.get('char')
    print('=' * 92)
    print('%s   %s' % (game, os.path.basename(mp)))
    if plug is None:
        print('  no char plugin'); continue
    rows = []
    for path, c in cards:
        g = c.get('game'); g = [g] if isinstance(g, str) else g
        if not db._game_ok(c, game):
            continue
        tag = c.get('tag')
        tag = he.resolve_gamed(tag, game, games) if isinstance(tag, dict) else tag
        if not isinstance(tag, str) or not tag.startswith('char '):
            continue
        ts = c['targets']
        ts = he.resolve_gamed(ts, game, games) if isinstance(ts, dict) else ts
        ts = [t for t in (ts or []) if isinstance(t, dict) and he.target_applies(t, game)]
        if not ts:
            continue
        cls, tpath = hp.hm.split_tag(tag)
        tags = [p for p, _ in m.find_tags(cls, tpath.split(' & ')[0])]
        if not tags:
            continue
        for t in ts:
            if any(t.get(k) for k in ('reload_anim', 'swap_anim', 'map_swap',
                                      'map_equip', 'equip_drop', 'choice', 'derived')):
                continue
            f = t.get('field')
            f = he.resolve_gamed(f, game, games) if isinstance(f, dict) else f
            if not isinstance(f, str):
                continue
            f = hp.apply_difficulty(f, t, DIFF)
            blk = t.get('block')
            blk = he.resolve_gamed(blk, game, games) if isinstance(blk, dict) else blk
            have = sum(1 for p in tags
                       if m.read_all(cls, p, f, plug, blk, 'all'))
            rows.append((' / '.join(path[-2:]), f, blk or '-', have, len(tags)))
            break                       # one representative field per card is enough
    tot = len(rows)
    dead = [r for r in rows if r[3] == 0]
    part = [r for r in rows if 0 < r[3] < r[4]]
    full = [r for r in rows if r[3] == r[4]]
    print('  %d enemy cards on this map: %d define the block on EVERY tag, '
          '%d on SOME, %d on NONE' % (tot, len(full), len(part), len(dead)))
    gen = sum(1 for p in [x for x, _ in m.find_tags('char', 'ai' + chr(92) + 'generic')] for _ in [1])
    print('  (ai\\generic present: %s)' % bool(gen))
    for label, rs in (('NONE (inherits — card is a no-op today)', dead),
                      ('SOME (base defines it, variants inherit)', part)):
        if not rs:
            continue
        print('  --- %s' % label)
        for name, f, blk, have, n in sorted(rs):
            print('      %-46s %-26s %-24s %d/%d' % (name, f[:26], blk[:24], have, n))
