r"""enemy_color_catalog.py -- build enemy_colors_catalog.json for the Enemy colours options.

Reads every campaign map of every game (via enemy_color_census) and writes one row per
enemy rank with its patch route, its targets and its stock colours:

    {game: [{id, enemy, label, route, slots: [{stock, hi, editable}], targets, maps}]}

Routes are the ones enemy_colors.py applies. Rank variants that differ only by a head
model (Halo 2/3 `_dog`/`_scl`, Grunt `_crz`/`_dop`, Brute `_bth`/`_crl`) are one row.
Halo 4 ranks come from the per-rank armour materials, not the biped (its change colours
do nothing in game). Jackal shields are their own rows.

    python sprint_toolkit/enemy_color_catalog.py            # all games -> tool folder
    python sprint_toolkit/enemy_color_catalog.py --game "Halo 4" --out x.json
"""
import argparse
import collections
import contextlib
import io
import json
import os
import pickle
import struct
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)

import halo_enhancer as he                                        # noqa: E402
import halo_patch as hp                                           # noqa: E402
import behaviour_census as bc                                     # noqa: E402
import enemy_color_census as cen                                  # noqa: E402
import enemy_colors as ec                                         # noqa: E402

B = chr(92)
HEAD_SUFFIXES = ('_dog', '_scl', '_crz', '_dop', '_bth', '_crl')
H4_FAMILIES = {'storm_elite_ai': 'Elite', 'storm_grunt': 'Grunt', 'storm_jackal': 'Jackal',
               'storm_knight': 'Knight', 'storm_hunter': 'Hunter', 'storm_pawn': 'Crawler',
               'storm_bishop': 'Watcher'}
H4_SKIP = ('anatomy', 'techsuit', 'visor', 'skin', 'glass', 'eye')
# ODST Brute armour shaders -> one row each group (shared stock, shared ranks)
ODST_ARMOUR = (('armour', ('minor_major_armor', 'brute_metal')),
               ('jump pack armour', ('jumppack_armor',)),
               ('chieftain armour', ('chieftain_armor', 'chief_stalker_metal')),
               ('stalker armour', ('stalker_armor',)))
RANK_ORDER = ('minor', 'default', 'heavy', 'major', 'officer', 'captain', 'captain_major',
              'captain_ultra', 'spec_ops', 'ultra', 'general', 'zealot', 'ranger', 'stealth',
              'stealth_major', 'honor_guard', 'bodyguard', 'jumppack', 'jumppack_major',
              'jumppack_ultra', 'chieftain', 'chieftain_armor', 'chieftain_weapon', 'sniper')


def short(name):
    return str(name).rsplit(B, 1)[-1]


def tidy(label, enemy):
    """Drop a leading species name from a rank label: Reach `jackal_major` -> `major`."""
    pre = enemy.lower().split(' ')[0] + '_'
    return label[len(pre):] if label.startswith(pre) and len(label) > len(pre) else label


def rank_base(v):
    for s in HEAD_SUFFIXES:
        if v.endswith(s):
            return v[:-len(s)]
    return v


def _rank_key(label):
    base = label.split(' ')[0]
    return (RANK_ORDER.index(base) if base in RANK_ORDER else len(RANK_ORDER), label)


# ----------------------------------------------------------------------------- biped rows
def perm_rows(game, out):
    """Halo 2 / 3 / ODST / Reach: one row per (enemy, biped, rank)."""
    groups = collections.OrderedDict()
    for (g, enemy, variant, bshort), rec in out.items():
        if g != game:
            continue
        rank = rank_base(variant)
        groups.setdefault((enemy, bshort, rank), []).append((variant, rec))
    per_enemy_bipds = collections.defaultdict(collections.Counter)
    for enemy, bshort, _r in groups:
        per_enemy_bipds[enemy][bshort] += 1
    rows = []
    for (enemy, bshort, rank), members in groups.items():
        width = max([c[0] + 1 for _v, r in members for c in r['slots']] or [0])
        slots = []
        for si in range(width):
            got = [c for _v, r in members for c in r['slots'] if c[0] == si]
            live = [c for c in got if c[3] in ('own', 'any')]
            c = live[0] if live else (got[0] if got else (si, None, None, 'none'))
            # A slot the rank has no entry in can still be painted where the patcher
            # can append one (enemy_colors.ADD_GAMES): stock is then the texture's own.
            add = not live and bool(got) and game in ec.ADD_GAMES and rank not in ('(none)', 'default')
            slots.append({'stock': c[1], 'hi': c[2], 'editable': bool(live) or add,
                          'add': add})
        targets = []
        for variant, r in members:
            src = ['none'] * width
            for c in r['slots']:
                src[c[0]] = c[3]
            targets.append({'bipd': r['bipd'], 'variant': '' if variant == '(none)' else variant,
                            'chars': sorted(r['chars']),
                            'src': src})
        label = tidy(rank, enemy) if rank not in ('(none)', 'default') else 'all'
        if label.startswith('sid:'):
            # A Halo 3 static-range name that never resolves: name it by its character.
            label = sorted(members[0][1]['chars'])[0]
        # The enemy's main biped goes unnamed; heretics, rangers and the like say theirs.
        main = per_enemy_bipds[enemy].most_common(1)[0][0]
        if bshort != main:
            label += ' (%s)' % bshort
        maps = set().union(*(r['maps'] for _v, r in members))
        rows.append({'id': '%s:%s' % (bshort, rank), 'enemy': enemy, 'label': label,
                     'route': 'perm', 'slots': slots, 'targets': targets, 'maps': len(maps)})
    return rows


def h1_rows(out):
    rows = []
    seen = {}
    for (g, enemy, actr, bshort), rec in out.items():
        if g != 'Halo 1':
            continue
        route = 'actv'
        if rec['slots'] and rec['slots'][0][3] == 'bipd':
            route = 'h1bipd'
        slots = [{'stock': lo, 'hi': hi, 'editable': True} for _si, lo, hi, _h in rec['slots']]
        if actr in seen:
            prev = seen[actr]
            tg = rec['targets'] if route == 'actv' else [rec['bipd']]
            prev['targets'] = sorted(set(prev['targets']) | set(tg))
            prev['maps'] = max(prev['maps'], len(rec['maps']))
            continue
        rows.append({'id': actr, 'enemy': enemy,
                     'label': actr.replace(enemy.lower() + ' ', '') if enemy else actr,
                     'route': route, 'slots': slots,
                     'targets': sorted(rec['targets']) if route == 'actv' else [rec['bipd']],
                     'maps': len(rec['maps'])})
        seen[actr] = rows[-1]
    return rows


# ----------------------------------------------------------------------------- map scans
def _stops_hex(m, off, stops):
    return ['%02X%02X%02X' % (m.data[off + s + 2], m.data[off + s + 1], m.data[off + s])
            for s in stops]


def _brightest(hexes):
    hexes = [h for h in hexes if h and h != '000000']
    return max(hexes, key=lambda h: max(ec.rgb(h))) if hexes else None


def scan_maps(game, folder, acc):
    """Shield sources and (Halo 4) armour materials on every map of a game."""
    for mp in bc.ca.game_maps(folder, game):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                m = hp.open_map(mp, game)
        except Exception:
            continue
        mname = os.path.basename(mp)
        if game == 'Halo 1':
            for tp, base in m.find_tags('bipd', 'characters' + B + 'jackal' + B + '*'):
                sl = m.follow_all(base, [0x164], [0x2C], 'all')
                perms = m.follow_all(sl[2], [0x20], [0x1C], 'all') if len(sl) > 2 else []
                if perms:
                    acc.setdefault(('h1bipdC', tp), ec.hexcol(
                        *struct.unpack_from('<3f', m.data, perms[0] + 4)))
            for tp, base in m.find_tags('sotr', '*jackal shield*'):
                st = m.follow_all(base, [0x60], [0x70], 'all')
                if st:
                    a, r, g, b = struct.unpack_from('<4f', m.data, st[0] + 0xC)
                    rec = acc.setdefault(('sotr', tp), {'stock': ec.hexcol(r, g, b), 'maps': set()})
                    rec['maps'].add(mname)
            del m
            continue
        for t in m.tags:
            if not isinstance(t, dict) or not t.get('base'):
                continue
            n, cls = str(t.get('name')), t.get('class')
            if (game == 'Halo 3: ODST' and cls == 'rmsh'
                    and 'characters' + B + 'brute' + B + 'shaders' + B in n):
                for label, names in ODST_ARMOUR:
                    if short(n) in names:
                        fc = []
                        for pp in m.follow_all(t['base'], [0x28], [0x8C], 'all'):
                            fc = m.follow_all(pp, [0x1C], [0x10], 'all')
                        if len(fc) > max(ec.ODST_ARMOUR_CONSTS):
                            rec = acc.setdefault(('armour', label), {'targets': set(), 'maps': set(),
                                                                     'stock': None})
                            rec['targets'].add(n)
                            rec['maps'].add(mname)
                            if short(n) == names[0] or rec['stock'] is None:
                                rec['stock'] = [ec.hexcol(*struct.unpack_from('<3f', m.data, fc[i]))
                                                for i in ec.ODST_ARMOUR_CONSTS]
                continue
            if game == 'Halo 2' and cls == 'shad' and n.endswith(('jackal_shield', 'jackal_shield_major')):
                stops = []
                for pp in m.follow_all(t['base'], [0x20], [0x7C], 'all'):
                    for o in m.follow_all(pp, [0x3C], [0x14], 'all'):
                        if m.u32(o):
                            off = m.p2o(m.u32(o + 0x10))
                            if off and m.i32(o + 0xC) >= 0x14:
                                stops += _stops_hex(m, off, (0x4, 0x10))
                rank = 'major' if n.endswith('_major') else 'minor'
                rec = acc.setdefault(('shield', rank), {'targets': set(), 'stops': [], 'maps': set()})
            elif game in ('Halo 3', 'Halo 3: ODST', 'Halo Reach') and cls == 'rmhg' and (
                    'jackal' + B + 'shaders' + B + 'jackal_shield' in n
                    or (game == 'Halo Reach' and ('cov_portable_shield' + B + 'shaders' in n
                                                  or 'skirmisher_bracers' + B + 'shaders' in n))):
                pp_off, sizes = (0x38, (0xB4, 0xAC)) if game == 'Halo Reach' else (0x28, (0x8C,))
                stops = []
                for es in sizes:
                    pps = m.follow_all(t['base'], [pp_off], [es], 'all')
                    if pps:
                        break
                for pp in pps:
                    for o in m.follow_all(pp, [0x5C], [0x24], 'all'):
                        if m.u32(o) == 1:
                            off = m.data2off(m.u32(o + 0x10 + 0xC))
                            if off and m.i32(o + 0x10) >= 0x14:
                                stops += _stops_hex(m, off, (0x4, 0x8, 0xC, 0x10))
                rank = 'all' if game == 'Halo Reach' else ('major' if n.endswith('_major') else 'minor')
                rec = acc.setdefault(('shield', rank), {'targets': set(), 'stops': [], 'maps': set()})
            elif game == 'Halo 4' and cls == 'mat ' and (
                    'jackal_shield' + B + 'shaders' in n or 'cov_portable_shield' + B + 'shaders' in n):
                stops = []
                for pp in m.follow_all(t['base'], [0x1C], [0x9C], 'all'):
                    for f in m.follow_all(pp, [0x54], [0x2C], 'all'):
                        if m.u32(f) == 1:
                            off = m.data2off(m.u32(f + 0x18 + 0xC))
                            if off and m.i32(f + 0x18) >= 0x14:
                                stops += _stops_hex(m, off, (0x4, 0x8, 0xC, 0x10))
                rank = 'major' if 'jackal_major' in short(n) else 'minor'
                rec = acc.setdefault(('shield', rank), {'targets': set(), 'stops': [], 'maps': set()})
            elif game == 'Halo 4' and cls == 'mat ' and 'objects' + B + 'characters' + B + 'storm_' in n:
                fam_dir = n.split('characters' + B)[1].split(B)[0]
                enemy = H4_FAMILIES.get(fam_dir)
                if not enemy or any(x in short(n) for x in H4_SKIP):
                    continue
                by = getattr(m, '_ec_by_ident', None)
                if by is None:
                    by = m._ec_by_ident = {x.get('ident'): x for x in m.tags if isinstance(x, dict)}
                shader = by.get(m.u32(t['base'] + 0xC))
                if not shader or not short(shader.get('name')).startswith(
                        ('srf_char_cov', 'srf_char_blinn_reflection_selfillum')):
                    continue
                p = ec._mat_fc0(m, t['base'])
                if p is None:
                    continue
                folder_name = n.rsplit(B, 1)[0].rsplit(B, 1)[-1]
                rank = folder_name
                for pre in (fam_dir + '_', 'storm_'):
                    if rank.startswith(pre):
                        rank = rank[len(pre):]
                for suf in ('_materials', '_material'):
                    if rank.endswith(suf):
                        rank = rank[:-len(suf)]
                if rank in ('materials', 'material', fam_dir) or folder_name == fam_dir:
                    rank = 'all'
                rec = acc.setdefault(('tint', enemy, rank), {'targets': set(), 'stock': {},
                                                             'maps': set()})
                rec['targets'].add(n)
                rec['stock'][n] = ec.hexcol(*struct.unpack_from('<3f', m.data, p))
                rec['maps'].add(mname)
                continue
            else:
                continue
            rec['targets'].add(n)
            rec['stops'] += stops
            rec['maps'].add(mname)
        del m


def scan_rows(game, acc, out):
    rows = []
    for key, rec in acc.items():
        if key[0] == 'tint':
            _k, enemy, rank = key
            base = [v for n, v in rec['stock'].items() if not n[-3:-2] == '_']
            stock = base[0] if base else sorted(rec['stock'].values())[-1]
            label = {'default': 'minor', 'leader': 'prime', 'battle_wagon': 'battlewagon'}.get(rank, rank)
            if sum(1 for k in acc if k[0] == 'tint' and k[1] == enemy) == 1:
                label = 'all'
            rows.append({'id': '%s:%s' % (enemy.lower(), rank), 'enemy': enemy, 'label': label,
                         'route': 'tint', 'slots': [{'stock': stock, 'hi': None, 'editable': True,
                                                     'name': 'tint'}],
                         'targets': sorted(rec['targets']), 'maps': len(rec['maps'])})
        elif key[0] == 'armour':
            label = key[1]
            rows.append({'id': 'armour:%s' % label.replace(' ', '_'), 'enemy': 'Brute',
                         'label': label, 'route': 'armour',
                         'slots': [{'stock': c, 'hi': None, 'editable': True,
                                    'name': 'armour colour %d' % (i + 1)}
                                   for i, c in enumerate(rec['stock'])],
                         'targets': sorted(rec['targets']), 'maps': len(rec['maps'])})
        elif key[0] == 'shield':
            rank = key[1]
            label = {'minor': 'minor shield', 'major': 'major shield',
                     'all': 'shields (shared with the portable shield and Skirmisher bracers)'}[rank]
            rows.append({'id': 'shield:%s' % rank, 'enemy': 'Jackal', 'label': label,
                         'route': 'shield', 'slots': [{'stock': _brightest(rec['stops']), 'hi': None,
                                                       'editable': True, 'name': 'shield'}],
                         'targets': sorted(rec['targets']), 'maps': len(rec['maps'])})
    if game == 'Halo 1':
        # Shield = the Jackal biped's change colour C + the shared shield shader's stage 0.
        sotr = sorted(k[1] for k in acc if k[0] == 'sotr')
        for (g, enemy, actr, _b), rec in out.items():
            if g != 'Halo 1' or enemy != 'Jackal':
                continue
            rank = 'major' if 'major' in actr else 'minor'
            rows.append({'id': 'shield:%s' % rank, 'enemy': 'Jackal', 'label': rank + ' shield',
                         'route': 'shield',
                         'slots': [{'stock': acc.get(('h1bipdC', rec['bipd'])),
                                    'hi': None, 'editable': True, 'name': 'shield'}],
                         'targets': [rec['bipd']], 'sotr': sotr, 'maps': len(rec['maps'])})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game')
    ap.add_argument('--out', default=ec.CATALOG_PATH)
    ap.add_argument('--cache', help='folder for per-game scan pickles: reused when present, '
                                    'so label/row tweaks rebuild in seconds')
    a = ap.parse_args()
    he.load_settings()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    fam = bc.families(db)
    catalog = ec.load_catalog(a.out) if a.game else {}
    for game, subs, folder, _classes in bc.cases():
        if a.game and a.game != game:
            continue
        print('reading', game, flush=True)
        pk = os.path.join(a.cache, game.replace(':', '') + '.pickle') if a.cache else None
        if pk and os.path.exists(pk):
            with open(pk, 'rb') as f:
                out, acc = pickle.load(f)
        else:
            out = {}
            if game == 'Halo 1':
                cen.census_h1(folder, fam, out)
            elif game in cen.LAYOUT and game != 'Halo 4':
                cen.census_gen2plus(game, subs, folder, fam, out)
                cen.merge_unnamed(out)
            acc = {}
            scan_maps(game, folder, acc)
            if pk:
                os.makedirs(a.cache, exist_ok=True)
                with open(pk, 'wb') as f:
                    pickle.dump((out, acc), f)
        rows = h1_rows(out) if game == 'Halo 1' else perm_rows(game, out)
        rows += scan_rows(game, acc, out)
        rows.sort(key=lambda r: (r['enemy'], r['route'] in ('shield', 'armour'),
                                 _rank_key(r['label'])))
        catalog[game] = rows
        print('  %d rows' % len(rows), flush=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=1, sort_keys=True)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
