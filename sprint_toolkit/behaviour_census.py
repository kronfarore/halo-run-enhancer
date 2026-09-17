# -*- coding: utf-8 -*-
r"""behaviour_census.py -- which enemies really carry the behaviour fields no card drives.

Written for the 2026-09-16 card request: Brace Grenade Chance beside Dive Grenade Chance,
Evasion Properties, the aggressive/defensive Cover fields, Search / Pre-Search times and
every berserk field. A card is only worth offering for an enemy that ships a MEANINGFUL
value, and that differs per game and per variant, so this reads every character tag of
every campaign map, Halo 1 (actr/actv) through Halo 4.

Why coverage_audit did not raise these: its default view lists only fields some OTHER
game already has a card for. None of these was carded in any game, so they only showed
under --all, which is too noisy to read.

For each game and field: per enemy family, how many variant tags define a non-zero value
and the range. From Halo 3 on it also lists which BERSERK behaviours each family's style
allows (the style is followed through the parent character when a char leaves it unset).

    python sprint_toolkit/behaviour_census.py
    python sprint_toolkit/behaviour_census.py --game "Halo 4" --enemy Elite
    python sprint_toolkit/behaviour_census.py --json out.json
    python sprint_toolkit/behaviour_census.py --fields "board|flee"
"""
import argparse
import contextlib
import fnmatch
import io
import json
import os
import re
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import halo_enhancer as he                                        # noqa: E402
import halo_patch as hp                                           # noqa: E402
import coverage_audit as ca                                       # noqa: E402

S = chr(92)
GENERIC = 'ai' + S + 'generic'
ROOT = os.path.dirname(TOOL)
FIELD_RX = re.compile(r'dive grenade|brace grenade|dive from grenade|dive retreat|evasion'
                      r'|berserk|beserk|kamikaze|search time|search distance|presearch'
                      r'|defensive|target search|stalking discovery|uncover delay',
                      re.I)
NUMERIC = ('float', 'int', 'real', 'rangef', 'degree', 'short', 'uint')


def cases():
    out = [('Halo 1', ['Halo1MCC', 'Halo1'], os.path.join(ROOT, 'halo1', 'maps'),
            ('actr', 'actv'))]
    names = set()
    for c in ca.CASES:
        out.append((c[0], c[1], c[2], ('char',)))
        names.add(c[0])
    if 'Halo 4' not in names:
        out.append(('Halo 4', ['Halo4MCC', 'Halo4'], os.path.join(ROOT, 'halo4', 'maps'),
                    ('char',)))
    return out


def families(db):
    """[(enemy, [lowercased fnmatch patterns])] from every game's cards."""
    fam = []
    for enemy in sorted(db.enemy_mods):
        pats = [p.lower() for p in ca.enemy_tag_patterns(db, enemy)]
        for mod in db.enemy_mods.get(enemy) or []:     # Halo 1 actr/actv patterns too
            tag = mod.get('tag')
            for t in (tag.values() if isinstance(tag, dict) else [tag]):
                if isinstance(t, str) and t.split(' ', 1)[0] in ('actr', 'actv'):
                    for part in t.split(' ', 1)[1].split(' & '):
                        part = part.strip().lower()
                        if part and part not in pats:
                            pats.append(part)
        if pats:
            fam.append((enemy, pats))
    return fam


def family_of(path, fam):
    p = path.lower()
    if p == GENERIC:
        return GENERIC
    for enemy, pats in fam:
        if any(fnmatch.fnmatch(p, x) for x in pats):
            return enemy
    return None


def census_fields(plug):
    seen, out = set(), []
    for f in getattr(plug, 'fields', []):
        if not str(f.get('type', '')).startswith(NUMERIC):
            continue
        if not FIELD_RX.search(f['name']):
            continue
        blk = '/'.join(f.get('block_chain') or []) or None
        if (f['name'], blk) not in seen:
            seen.add((f['name'], blk))
            out.append((f['name'], blk))
    return out


def _flag_fields(subs, cls='styl'):
    """Top-level flags fields of a plugin with their bit names, read from the plugin XML
    itself (the loader keeps no bit names)."""
    import xml.etree.ElementTree as ET
    import assembly_plugins
    for sub in subs:
        path = os.path.join(assembly_plugins.plugins_dir(), sub, cls + '.xml')
        if os.path.exists(path):
            break
    else:
        return []
    out = []
    for c in ET.parse(path).getroot():
        if not c.tag.lower().startswith('flags') or not c.get('offset'):
            continue
        pairs = [(int(b.get('index'), 0), b.get('name') or '') for b in c
                 if b.tag.lower() == 'bit']
        if pairs:
            out.append((int(c.get('offset'), 16), pairs))
    return out


def _top_tagrefs(subs, cls='char'):
    """{name: offset} of a plugin's top-level tagRefs (the loader keeps none)."""
    import xml.etree.ElementTree as ET
    import assembly_plugins
    for sub in subs:
        path = os.path.join(assembly_plugins.plugins_dir(), sub, cls + '.xml')
        if os.path.exists(path):
            break
    else:
        return {}
    return {c.get('name'): int(c.get('offset'), 16)
            for c in ET.parse(path).getroot()
            if c.tag.lower() == 'tagref' and c.get('offset') and c.get('name')}


def berserk_style_bits(m, refs, flag_fields, base, by_index, depth=0):
    """Berserk behaviour names the char's style allows (H3+; parent followed)."""
    if not flag_fields or depth > 4:
        return set()
    so, po = refs.get('Style'), refs.get('Parent Character')
    if so is None:
        return set()
    ident = m.u32(base + so + 0xC)
    if ident == 0xFFFFFFFF:
        if po is None:
            return set()
        parent = by_index.get(m.u32(base + po + 0xC) & 0xFFFF)
        if parent and parent.get('base'):
            return berserk_style_bits(m, refs, flag_fields, parent['base'],
                                      by_index, depth + 1)
        return set()
    st = by_index.get(ident & 0xFFFF)
    if not st or not st.get('base'):
        return set()
    out = set()
    for off, pairs in flag_fields:
        val = m.u32(st['base'] + off)
        for idx, name in pairs:
            if 'berserk' in name.lower() and (val >> idx) & 1:
                out.add(name)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game')
    ap.add_argument('--enemy')
    ap.add_argument('--json')
    ap.add_argument('--fields', metavar='REGEX',
                    help='census these field names instead of the behaviour set '
                         '(case-insensitive regex)')
    a = ap.parse_args()
    if a.fields:
        global FIELD_RX
        FIELD_RX = re.compile(a.fields, re.I)
    he.load_settings()
    P = he.CONFIG['assembly_plugins_dir']
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    fam = families(db)
    report = {}
    for game, subs, folder, classes in cases():
        if a.game and a.game != game:
            continue
        reg = hp.PluginRegistry(P, subs)
        styl_plug = reg.get('styl') if game not in ('Halo 1', 'Halo 2') else None
        flag_fields = _flag_fields(subs) if styl_plug is not None else []
        refs = _top_tagrefs(subs) if styl_plug is not None else {}
        paths = ca.game_maps(folder, game)
        print('\n=== %s  (%d maps) ===' % (game, len(paths)), flush=True)
        g = report.setdefault(game, {'fields': {}, 'berserk_style': {}, 'tags': {}})
        for cls in classes:
            plug = reg.get(cls)
            if plug is None:
                continue
            fields = census_fields(plug)
            seen = set()
            for mp in paths:
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        m = hp.open_map(mp, game)
                except Exception:
                    continue
                tags = getattr(m, 'tags', None)
                by_index = ({t.get('index'): t for t in tags if isinstance(t, dict)}
                            if isinstance(tags, list) else {})
                for tp, base in m.find_tags(cls, '*'):
                    if tp in seen:
                        continue
                    seen.add(tp)
                    fm = family_of(tp, fam)
                    if not fm or (a.enemy and fm != a.enemy):
                        continue
                    g['tags'].setdefault(fm, set()).add(tp)
                    for name, blk in fields:
                        try:
                            v = m.read_tag_field(base, name, plug, blk, 'all', 0)
                        except Exception:
                            v = None
                        if isinstance(v, (int, float)) and v and v != -1:
                            key = '%s: %s' % (cls, name if not blk else blk + '/' + name)
                            g['fields'].setdefault(key, {}).setdefault(fm, []).append(
                                (tp.rsplit(S, 1)[-1], round(float(v), 3)))
                    if cls == 'char' and flag_fields and by_index:
                        try:
                            bits = berserk_style_bits(m, refs, flag_fields, base, by_index)
                        except Exception:
                            bits = set()
                        if bits:
                            g['berserk_style'].setdefault(fm, set()).update(bits)
                del m
        for key in sorted(g['fields']):
            print('  %s' % key)
            for fm, rows in sorted(g['fields'][key].items()):
                vals = [v for _t, v in rows]
                total = len(g['tags'].get(fm, ()))
                print('      %-26s %2d/%-2d tags  %s..%s  e.g. %s'
                      % (fm, len({t for t, _v in rows}), total, min(vals), max(vals),
                         rows[0][0]))
        if g['berserk_style']:
            print('  -- berserk behaviours the style allows:')
            for fm, bits in sorted(g['berserk_style'].items()):
                print('      %-26s %s' % (fm, sorted(bits)))
        print('  (flags fields found on styl: %d)' % len(flag_fields), flush=True)
    if a.json:
        def conv(o):
            return sorted(o) if isinstance(o, set) else str(o)
        with io.open(a.json, 'w', encoding='utf-8') as f:
            json.dump(report, f, default=conv, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
