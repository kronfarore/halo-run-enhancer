"""Per game: for every char block an enemy card edits, how many of that card's own
tags DEFINE the block vs inherit it. The input to the ancestor-path design question."""
import json, os, sys, io, contextlib, collections
os.chdir(r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool')
sys.path.insert(0, os.getcwd())
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    import halo_enhancer as he
    import halo_patch as hp
    sys.path.insert(0, os.path.join(os.getcwd(), 'sprint_toolkit'))
    import map_vault as V
    db = he.ModifierDatabase()

CFG = json.load(open('settings.json', encoding='utf-8'))
R = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
# Several maps per game, unioned. One map can only UNDER-report: an enemy it does not
# field is invisible, and Reach in particular spreads its cast thinly -- the Engineer
# is on m30 onward, the Bugger on m35/m52/m70, the Brute on m50/m70. A tag counts as
# defining a block if it defines it on ANY of these.
CASES = [
    ('Halo 2',       ['Halo2MCC', 'Halo2'],  [
        R + r'\halo2\h2_maps_win64_dx11' + os.sep + '07a_highcharity.map',
        R + r'\halo2\h2_maps_win64_dx11' + os.sep + '03a_oldmombasa.map',
        R + r'\halo2\h2_maps_win64_dx11' + os.sep + '05a_deltaapproach.map']),
    ('Halo 3',       ['Halo3MCC', 'Halo3'],  [
        R + r'\halo3\maps' + os.sep + '030_outskirts.map',
        R + r'\halo3\maps' + os.sep + '050_floodvoice.map',
        R + r'\halo3\maps' + os.sep + '120_halo.map']),
    ('Halo 3: ODST', ['ODSTMCC', 'ODST'],    [
        R + r'\halo3odst\maps\l300.map',
        R + r'\halo3odst\maps\sc110.map',
        R + r'\halo3odst\maps\sc140.map']),
    ('Halo Reach',   ['ReachMCC', 'Reach'],  [
        R + r'\haloreach\maps\m10.map',
        R + r'\haloreach\maps\m30.map',
        R + r'\haloreach\maps\m35.map',
        R + r'\haloreach\maps\m50.map',
        R + r'\haloreach\maps\m70.map']),
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

for game, subs, mps in CASES:
    mps = [V.pristine_source(game, m) for m in mps]
    reg = hp.PluginRegistry(CFG['assembly_plugins_dir'], subs)
    maps = []
    for one in mps:
        try:
            maps.append(hp.open_map(one, game))
        except Exception:
            pass
    if not maps:
        print('%s: none of its maps opened' % game)
        continue
    m = maps[0]
    plug = reg.get('char')
    allchar = sorted({p for mm in maps for p, _ in mm.find_tags('char', '*')})         if plug is not None else []
    print('=' * 92)
    print('%s   %d map(s): %s'
          % (game, len(maps), ', '.join(os.path.basename(x) for x in mps)))
    if plug is None:
        print('  no char plugin'); continue
    rows = []
    for path, c in cards:
        # halo.json says "game"; a BUILT mod says "games". _game_ok reads the built
        # key, so calling it on a raw card returns True for every game and the audit
        # silently evaluated every card against every game. Normalise first.
        if not db._game_ok({'games': db._parse_games(c.get('game')),
                            'skip_games': c.get('skip_games')}, game):
            continue
        if game in (c.get('skip_games') or []):
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
        tags = sorted({p for mm in maps
                       for p, _ in mm.find_tags(cls, tpath.split(' & ')[0])})
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
                       if any(mm.read_all(cls, p, f, plug, blk, 'all')
                              for mm in maps))
            # When the card's own tags carry nothing, is the field defined ANYWHERE?
            # ai\generic having it means an ancestor walk (or a grow seeded from it)
            # could rescue the card; nothing having it means no mechanism can.
            rescue = ''
            if have == 0:
                gen = any(mm.read_all(cls, 'ai' + chr(92) + 'generic', f,
                                      plug, blk, 'all') for mm in maps)
                if gen:
                    rescue = 'A: ai/generic has it'
                else:
                    anyone = sum(1 for p2 in allchar
                                 if any(mm.read_all(cls, p2, f, plug, blk, 'all')
                                        for mm in maps))
                    rescue = ('A: %d other tag(s) have it' % anyone if anyone
                              else 'B: defined on NO tag in this map')
            rows.append((' / '.join(path[-2:]), f, blk or '-', have, len(tags),
                         rescue))
            # EVERY field, not one representative. A card can be alive through one
            # target and dead through another -- Cover Chance lands its chance fields
            # and misses Cover Chance Time -- and a per-card verdict hides exactly
            # that. Rows are per FIELD; the summary below folds them back per card.
    tot = len(rows)
    dead = [r for r in rows if r[3] == 0]
    part = [r for r in rows if 0 < r[3] < r[4]]
    full = [r for r in rows if r[3] == r[4]]
    # per card: alive if ANY of its fields lands, wholly dead if none do
    bycard = collections.defaultdict(list)
    for r in rows:
        bycard[r[0]].append(r)
    wholly = [c for c, rs in bycard.items() if all(r[3] == 0 for r in rs)]
    partly = [c for c, rs in bycard.items()
              if any(r[3] == 0 for r in rs) and any(r[3] for r in rs)]
    print('  %d field-target(s) across %d card(s): %d land on EVERY tag, '
          '%d on SOME, %d on NONE'
          % (tot, len(bycard), len(full), len(part), len(dead)))
    print('  cards: %d wholly dead, %d partly dead (some fields land, some do not)'
          % (len(wholly), len(partly)))
    if wholly:
        print('  --- WHOLLY DEAD: %s' % ', '.join(sorted(wholly)))
    if partly:
        print('  --- PARTLY DEAD: %s' % ', '.join(sorted(partly)))
    gen = any(mm.find_tags('char', 'ai' + chr(92) + 'generic') for mm in maps)
    print('  (ai\\generic present: %s)' % bool(gen))
    for label, rs in (('NONE (inherits — card is a no-op today)', dead),
                      ('SOME (base defines it, variants inherit)', part)):
        if not rs:
            continue
        print('  --- %s' % label)
        for row in sorted(rs):
            name, f, blk, have, n = row[:5]
            rescue = row[5] if len(row) > 5 else ''
            print('      %-44s %-26s %d/%-3d %s' % (name, f[:26], have, n, rescue))
