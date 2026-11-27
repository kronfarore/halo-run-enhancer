r"""Can every weapon, grenade and piece of equipment a game offers be PLACED at the
enhancer markers?  Read-only: each level's patch baseline is loaded into memory, the
patcher's own placers run on that copy exactly as a patch would run them, and nothing
is written anywhere.

Per game, the items are the ones the enhancer itself would hand a placer:
  WEAPONS    every weapon any of the game's levels can offer (db.get_game_weapons:
             the halo.json lists, turrets, enabled ports, map pools where that option
             is on), as the tag _spawn_weapons_spec would pass -- a run carries its
             weapons from level to level, so every level is asked for all of them.
  EQUIPMENT  Halo 3, ODST, Reach, Halo 4: the union of the levels' equipment pools
             (db.level_equipment), as _spawn_equipment_spec passes them.
  GRENADES   every grenade type, by the Grenades block index its Maximum Count card
             writes, as _spawn_grenades_spec passes them.

Both players get the full list (two-player co-op), in the patcher's order: weapons,
then equipment, then grenades. A row the placer reports ok is PLACED; anything else is
a miss, sorted by reason. Capacity misses (a block's 128 cap, no room to grow) are
counted apart: they say the full list does not FIT, not that an item cannot be placed.

What this does not prove: that the game then shows the item. That needs the item
loaded where the marker is -- h3_map_audit.py (Halo 3), odst_dz_enhancer.py
--check-built (ODST), the dz_enhancer readers for Reach and Halo 4 -- and a boot.

    python marker_placement_audit.py                    # all six games
    python marker_placement_audit.py --game "Halo 2"    # one game
    python marker_placement_audit.py --game ODST h100   # some levels
"""
import argparse
import contextlib
import io
import json
import os
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he       # noqa: E402
import halo_patch as HP           # noqa: E402

GAMES = ('Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4')
ALIASES = {'h1': 'Halo 1', 'h2': 'Halo 2', 'h3': 'Halo 3', 'odst': 'Halo 3: ODST',
           'reach': 'Halo Reach', 'h4': 'Halo 4'}
REPORT = os.path.join(HERE, 'reports', 'marker_placement_audit.txt')
CAPACITY = ('full', 'no free', 'no room', 'free space', 'free run')


def _first_path(tag, game):
    """`weap path & path2` -> the one path a placement takes (the enhancer's rule)."""
    if not tag or ' ' not in tag:
        return None
    p = tag.split(' ', 1)[1].strip()
    alts = [x.strip() for x in p.split('&') if x.strip()]
    if not alts:
        return None
    if game == 'Halo 4':
        return next((x for x in alts if x.endswith('_pve')), alts[0])
    return alts[0]


def game_items(db, game):
    """{'weapons': [(name, path)], 'equipment': [(name, path)], 'grenades': [(name, idx)]}"""
    fielded = list(db.get_game_weapons(game) or ())
    try:
        import weapon_ports
        for p in weapon_ports.active_ports(game, he.CONFIG):
            if p.get('weapon') and p['weapon'] not in fielded:
                fielded.append(p['weapon'])
    except Exception:
        pass
    weapons, seen = [], set()
    for w in fielded:
        if db.is_equipment(w) or db.is_grenade(w):
            continue
        tag = db.weap_tag_for(w, game)
        if not tag or not tag.startswith('weap '):
            continue
        # a weapon takes the FIRST '&' variant -- not the Halo 4 _pve rule
        pth = tag.split(' ', 1)[1].split('&')[0].strip()
        if pth and pth.lower() not in seen:
            seen.add(pth.lower())
            weapons.append((w, pth))
    equipment = []
    if he.equipment_placement_supported(game):
        names = []
        for mid, _nm in db.get_missions_for_game(game):
            for e in db.level_equipment(mid) or ():
                if e not in names:
                    names.append(e)
        seen = set()
        for e in names:
            pth = _first_path(db.eqip_tag_for(e, game), game)
            if pth and pth.lower() not in seen:
                seen.add(pth.lower())
                equipment.append((e, pth))
    grenades, gseen = [], set()
    for mid, _nm in db.get_missions_for_game(game):
        for g in db.mission_grenades.get(mid) or ():
            for mod in db.get_weapon_modifiers(g):
                if mod.get('name') != 'Maximum Count' or not db._game_ok(mod, game):
                    continue
                for t in mod.get('targets') or []:
                    ix = he.resolve_gamed(t.get('index'), game)
                    if isinstance(ix, int) and ix not in gseen:
                        gseen.add(ix)
                        grenades.append((g, ix))
    return {'weapons': weapons, 'equipment': equipment, 'grenades': grenades}


def baseline(game, mid):
    """The patch baseline the enhancer builds a patch from, resolved its own way
    (_port_level_map): halo.json keys are only prefixes in Halo 2 and Halo 3 --
    '03a' is 03a_oldmombasa.map, '010' is 010_jungle.map."""
    folder = (he.CONFIG.get('map_game_folder', {}) or {}).get(game, '')
    live = HP.default_map_path(he.mcc_root(), folder, mid)
    try:
        src = HP.existing_baseline(live, he.CONFIG.get('baseline_root'), folder) or live
    except Exception:
        src = live
    return str(src) if src else None


def _short(p):
    return str(p).replace('/', chr(92)).rsplit(chr(92), 1)[-1].lower()


def _markers(m, game):
    try:
        slots = HP.player_marker_slots(m, game)
    except Exception:
        slots = {}
    return {p + 1: [nm for nm, _i in v] for p, v in sorted(slots.items())}


def _pattern(key):
    """The basename pattern a placer's row `field` is matched against. Halo 4's cards
    name tags as patterns over the path (`storm_active_camo*`, and Thruster Pack's whole
    folder `storm_thruster_pack\\*`), and a placer reports the concrete basename."""
    s = str(key).replace('/', chr(92)).lower()
    folder, _sep, base = s.rpartition(chr(92))
    if base == '*':
        return folder.rsplit(chr(92), 1)[-1] + '*'
    return base


def _match(field, items):
    """The item a row's field belongs to: exact basename, then a pattern, then the
    longest name the field starts with (a palette variant: Reach's family members,
    Halo 4's _pve)."""
    import fnmatch
    f = field.lower()
    if not f:
        return None
    pats = [(_pattern(k) if isinstance(k, str) else str(k), n) for n, k in items]
    for p, n in pats:
        if p == f:
            return n
    for p, n in pats:
        if '*' in p and fnmatch.fnmatch(f, p):
            return n
    best = None
    for p, n in pats:
        if '*' not in p and f.startswith(p) and (best is None or len(p) > len(best[0])):
            best = (p, n)
    return best[1] if best else None


def _sort_rows(rows, items, effect_names):
    """{item name: {'ok': placed rows, 'cap': capacity misses, 'why': [other reasons]}}"""
    got = {name: {'ok': 0, 'why': [], 'cap': 0} for name, _k in items}
    for r in rows:
        if r.get('effect') not in effect_names:
            continue
        name = _match(str(r.get('field') or ''), items)
        why = str(r.get('reason') or '')
        if name is None:
            if (r.get('ok') and not r.get('skip')) or r.get('field') == 'anchor':
                continue
            # a refusal of the whole call (no field) counts against every item
            for n in got:
                if any(c in why for c in CAPACITY):
                    got[n]['cap'] += 1
                else:
                    got[n]['why'].append(why or 'skipped')
            continue
        if r.get('ok') and not r.get('skip'):
            got[name]['ok'] += 1
        elif any(c in why for c in CAPACITY):
            got[name]['cap'] += 1
        else:
            got[name]['why'].append(why or 'skipped')
    for n, v in got.items():
        if not v['ok'] and not v['cap'] and not v['why']:
            v['why'].append('the placer reported nothing for it')
    return got


def audit_level(game, mid, items, regs):
    path = baseline(game, mid)
    if not path or not os.path.exists(path):
        return {'level': mid, 'error': 'no baseline map (%s)' % path}
    t0 = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        m = HP.open_map(path, game)          # loaded into memory; the file is not touched
    reg = regs.get(game)
    if reg is None:
        reg = regs[game] = HP.PluginRegistry(
            he.CONFIG.get('assembly_plugins_dir'),
            he.CONFIG.get('plugin_subdirs_by_game', {}).get(game, []))
    out = {'level': mid, 'path': path, 'markers': _markers(m, game)}
    W = [p for _n, p in items['weapons']]
    E = [p for _n, p in items['equipment']]
    G = [ix for _n, ix in items['grenades']]
    rows = {}
    with contextlib.redirect_stdout(io.StringIO()):
        rows['weapons'] = HP._apply_spawn_weapons(
            m, game, {'groups': [W, W], 'radius': 0.25, 'all_insertions': False}, reg) if W else []
        rows['equipment'] = HP._apply_spawn_equipment(
            m, game, {'groups': [E, E], 'all_insertions': False}) if E else []
        rows['grenades'] = HP._apply_spawn_grenades(m, game, reg, {'groups': [G, G]}) if G else []
    out['weapons'] = _sort_rows(rows['weapons'], items['weapons'], ('spawned weapons',))
    out['equipment'] = _sort_rows(rows['equipment'], items['equipment'],
                                  ('starting equipment', 'spawned equipment'))
    # grenades: the summary row per index names the TAG; placement misses follow it
    gtag = {}
    for r in rows['grenades']:
        if r.get('effect') == 'starting grenades' and str(r.get('field', '')).startswith('grenade '):
            continue
    gitems = []
    for name, ix in items['grenades']:
        sup = HP.grenade_supply(m, game, reg, ix)
        gitems.append((name, sup[1] if sup else 'grenade %d' % ix))
        gtag[name] = sup
    out['grenades'] = _sort_rows(rows['grenades'], gitems,
                                 ('starting grenades', 'starting equipment',
                                  'spawned equipment'))
    for name, ix in items['grenades']:
        if not gtag.get(name) or gtag[name][0] <= 0:
            out['grenades'][name] = {'ok': 0, 'cap': 0,
                                     'why': ['no grenade of that type on this map (slot %d)' % ix]}
    out['raw_effects'] = sorted({r.get('effect') for k in rows for r in rows[k]})
    out['seconds'] = round(time.time() - t0, 1)
    del m
    return out


def report_game(game, items, results, w):
    w('=' * 100)
    w('%s -- %d weapons, %d equipment, %d grenade types per player'
      % (game, len(items['weapons']), len(items['equipment']), len(items['grenades'])))
    misses = {}
    for r in results:
        if r.get('error'):
            w('  %-14s ERROR %s' % (r['level'], r['error']))
            continue
        mk = r['markers']
        mks = ' '.join('P%d:%s' % (p, ','.join(n.replace(HP.REACH_MARKER_PREFIX, '') for n in v))
                       for p, v in mk.items()) or 'NO MARKERS'
        parts = []
        for kind in ('weapons', 'equipment', 'grenades'):
            got = r[kind]
            if not got:
                continue
            placed = sum(1 for v in got.values() if v['ok'])
            capped = sum(1 for v in got.values() if not v['ok'] and v['cap'] and not v['why'])
            s = '%s %d/%d' % (kind, placed, len(got))
            if capped:
                s += ' (+%d only capacity)' % capped
            parts.append(s)
            for n, v in got.items():
                if not v['ok'] and v['why']:
                    misses.setdefault((kind, n), {}).setdefault(
                        '; '.join(sorted(set(v['why']))), []).append(r['level'])
        w('  %-14s markers %-22s %s   [%.0fs]' % (r['level'], mks, '   '.join(parts),
                                                 r.get('seconds', 0)))
    if misses:
        w('  MISSES:')
        for (kind, n), reasons in sorted(misses.items()):
            for why, lvls in reasons.items():
                w('    %-9s %-26s %-60s on %s' % (kind, n, why[:60],
                                                  ', '.join(lvls) if len(lvls) < len(results)
                                                  else 'EVERY level'))
    else:
        w('  MISSES: none')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--game', action='append',
                    help='game name or h1/h2/h3/odst/reach/h4 (repeatable)')
    ap.add_argument('levels', nargs='*')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    games = [ALIASES.get(g.lower(), g) for g in (a.game or GAMES)]
    he.load_settings()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    lines = []

    def w(s=''):
        print(s, flush=True)
        lines.append(s)
    w('marker_placement_audit %s (in memory, nothing written)' % time.strftime('%Y-%m-%d %H:%M'))
    regs, dump = {}, {}
    for game in games:
        items = game_items(db, game)
        res = []
        for mid, _nm in db.get_missions_for_game(game):
            if a.levels and mid not in a.levels:
                continue
            try:
                res.append(audit_level(game, mid, items, regs))
            except Exception as e:                  # one bad level must not stop the rest
                import traceback
                res.append({'level': mid, 'error': '%s: %s' % (type(e).__name__, e)})
                traceback.print_exc()
        report_game(game, items, res, w)
        dump[game] = {'items': items, 'levels': res}
    if not a.levels:
        # A run of some games writes its own file, so it never replaces the full report.
        report = REPORT if not a.game else REPORT.replace(
            '.txt', '_%s.txt' % '_'.join(g.lower().replace(' ', '').replace(':', '')
                                         for g in games))
        with open(report, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        w('report: %s' % report)
    if a.json:
        print(json.dumps(dump, default=str)[:200000])


if __name__ == '__main__':
    main()
