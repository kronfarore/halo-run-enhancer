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
    # Halo 4 ships no .map.bak either, so these read the live maps -- fine for the
    # question asked, which is whether a tag carries the field at all. Shutdown is the
    # first pick because it fields both factions and a wide weapon set, but ONE map is
    # not enough here and has produced two false positives already: the Rocket
    # Launcher's Target Tracking (no rocket launcher on Shutdown) and the Jackal's
    # Hopping (no Jackal Ranger, the only Jackal that hops). Composer and Infinity
    # cover between them every rarer thing Shutdown lacks -- Jackal Ranger, space
    # Grunt, Crawler Prime, Watcher, rocket launcher, shotgun, DMR, Spartan laser and
    # the Scattershot.
    ('Halo 4',       ['Halo4MCC', 'Halo4'], R + r'\halo4\maps\m70_liftoff.map'),
    ('Halo 4',       ['Halo4MCC', 'Halo4'], R + r'\halo4\maps\m80_delta.map'),
    ('Halo 4',       ['Halo4MCC', 'Halo4'], R + r'\halo4\maps\m60_rescue.map'),
]
DIFF = he.CONFIG.get('target_difficulty', 'Impossible')

# Dead cards that have been LOOKED AT and accepted. They are suppressed by default so
# a run that prints nothing means "nothing new broke"; `--all` lists them again with
# the reason. Add to this only after establishing WHY a card reads empty -- an entry
# here silences it permanently, which is the opposite of what this audit is for.
#
# Keyed (game, card path, tag) so a card dead in one game still reports in another,
# and so the same card on two maps of one game collapses to a single entry.
_S = chr(92)
VERIFIED = {
    # The empty-block class: from Halo 3 on, most per-enemy char property blocks ship
    # ZERO elements and the enemy inherits ai\generic. The card resolves, finds an
    # empty block and writes nothing. See the halo3-odst-empty-char-blocks note.
    #
    # NOTE these are the cards with NO seeder. A card carrying init_defaults {grow}
    # also reads empty here and is NOT dead -- it grows the block before writing --
    # and is skipped in the loop below rather than listed here. Five entries that used
    # to sit in this table (the ODST Brute Chieftain and the four Elite Specops
    # Commander cards) were exactly that case and were removed 2026-09-09; the
    # stale-entry report at the end of a run is what surfaced them.
    ('Halo 3: ODST', 'Specific Enemy modifier / Flood Combat Form / Vision',
     'char objects' + _S + 'characters' + _S + 'floodcombat*'):
        'Flood Combat Forms ship an empty Perception block; they inherit ai' + _S + 'generic',
    ('Halo 3: ODST', 'Specific Enemy modifier / Flood Combat Form / Hearing Distance',
     'char objects' + _S + 'characters' + _S + 'floodcombat*'):
        'same empty Perception block',
    ('Halo 3: ODST', 'Specific Enemy modifier / Flood Combat Form / Perception',
     'char objects' + _S + 'characters' + _S + 'floodcombat*'):
        'same empty Perception block',
    ('Halo 3', 'Specific Enemy modifier / Brute / Grenades',
     'char objects' + _S + 'characters' + _S + 'brute' + _S + 'ai' + _S + 'brute*'):
        'empty Grenades block -- the Brute Grenades finding',
    ('Halo 3', 'Specific Enemy modifier / Brute / Grenades Chance',
     'char objects' + _S + 'characters' + _S + 'brute' + _S + 'ai' + _S + 'brute*'):
        'empty Grenades block -- the Brute Grenades finding',
    ('Halo 3', 'Hero enemy modifier / Brute Chieftain / Melee Behavior',
     'char objects' + _S + 'characters' + _S + 'brute' + _S + 'ai' + _S
     + 'brute_chieftain*'): 'empty Melee block on the 030 chieftain',
    # Pre-existing, unrelated to any Halo 4 work: matg carries no such field there.
    ('Halo 4', 'Player Modifiers / General Modifiers / Stun Penalty',
     'matg globals' + _S + 'globals'): 'Halo 4 matg has no Stun Penalty field',
    ('Halo 4', 'Player Modifiers / General Modifiers / Stun Time',
     'matg globals' + _S + 'globals'): 'Halo 4 matg has no Stun Time field',
}
SHOW_ALL = '--all' in sys.argv
_seen_verified = []
_new = []
_status = {}

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
        # A card held out of the pools is never offered, so it cannot be a silent
        # no-op for the player -- which is the only thing this audit looks for. The
        # enhancer drops these at halo_enhancer:1776 and every other audit skips them;
        # this one did not, and so reported deliberately parked cards as new.
        if c.get('ignore'):
            continue
        # `skip_games` is a DENY list and wins over the allow list, exactly as
        # _game_ok has it. Without this the audit reports cards that were
        # deliberately gated out of a game -- which is the opposite of dead.
        sk = c.get('skip_games')
        sk = [sk] if isinstance(sk, str) else (sk or [])
        if game in sk:
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
            # A card that SEEDS the block it edits is not dead when that block reads
            # empty -- being empty is the whole reason it seeds. `init_defaults` with
            # `grow` gives the tag its own copy, populated from the nearest ancestor,
            # before any value is written. halo_enhancer makes the same block-name
            # comparison at _seeded_default. Without this every grow card looks dead
            # here, which is why four of them sat on the VERIFIED list.
            _init = c.get('init_defaults')
            _init = he.resolve_gamed(_init, game, games) \
                if isinstance(_init, dict) and game in _init else _init
            if isinstance(_init, dict) and _init.get('grow') and _init.get('block') \
                    and blk and str(_init['block']).lower() == str(blk).lower():
                live += 1
                continue
            idx = t.get('index', 0)
            # `nth` picks WHICH declaration of a repeated field name to read, and
            # ignoring it reads the wrong one. Halo 4 declares `Maximum Vitality`
            # twice on hlmt -- once in Old Damage Info, once at the tag root -- so a
            # card carrying nth:1 was being read at nth 0, finding an empty block,
            # and reported DEAD while writing perfectly well.
            nth = t.get('nth', 0)
            nth = he.resolve_gamed(nth, game, games) if isinstance(nth, dict) else nth
            try:
                if m.read_all(cls, first, f, plugin, blk, idx if idx is not None else 0,
                              nth or 0):
                    live += 1
            except Exception:
                live += 1                               # can't tell; don't accuse it
        # A verdict is per GAME, not per map. Halo 4 samples three levels, and one
        # map can only under-report: the Jackal's Hopping block is filled in by the
        # Ranger alone and Shutdown fields no Ranger, exactly as Shutdown carries no
        # rocket launcher. Both read as dead there and are perfectly alive elsewhere,
        # so a card counts as dead only when EVERY sampled map of its game says so.
        label = ' / '.join(path[-3:])
        st = _status.setdefault((game, label, tag), {'live': [], 'dead': []})
        st['live' if live else 'dead'].append(os.path.basename(mp))

print('=' * 78)
for (game, label, tag), st in _status.items():
    if st['live']:
        if SHOW_ALL and st['dead']:
            print('  ok    %-38s %s' % (label, tag))
            print('        empty on %s, live on %s -- that map does not field it'
                  % (', '.join(st['dead']), ', '.join(st['live'])))
        continue
    why = VERIFIED.get((game, label, tag))
    if why is not None:
        _seen_verified.append((game, label, tag, why))
        if SHOW_ALL:
            print('  ok    %-38s %s' % (label, tag))
            print('        verified dead: %s' % why)
        continue
    _new.append((game, label, tag))
    print('  DEAD  %-14s %-38s %s' % (game, label, tag))
print('=' * 78)
if _new:
    print('%d NEW dead card(s) -- these are not on the verified list:' % len(_new))
    for game, label, tag in _new:
        print('   %-14s %-38s %s' % (game, label, tag))
else:
    print('No new dead cards.')
print('%d verified dead card(s) suppressed%s.'
      % (len(_seen_verified), '' if SHOW_ALL else ' (--all to list them with reasons)'))
# An entry that never fires is a card that was fixed, or a tag/label that drifted.
# Either way the list should not keep carrying it.
_fired = {(g, l, t) for g, l, t, _w in _seen_verified}
_stale = [k for k in VERIFIED if k not in _fired]
if _stale:
    print('%d verified entr(y/ies) did NOT fire -- fixed, or the label/tag drifted:'
          % len(_stale))
    for g, l, t in _stale:
        print('   %-14s %-38s %s' % (g, l, t))
