r"""Explosion visual size vs radius cards: which EFFECTS draw each radius card's damage,
what in them sets the visual size, and who else shares them. Halo 2 .. Halo 4.
(Halo 1 is covered by sprint_toolkit/EXPLOSION_VISUAL_SCALE.md: HEK tags, plain fields.)

The chain per card and game: card `tag` (jpt!, resolved like the enhancer does) ->
every tag that references the jpt! (projectile, effect, object, ...) -> the effects
that owner names (a projectile's detonation effects; an effect that carries the jpt!
as a part is itself the effect). Read straight from the shipped cache maps, every
campaign map of the game; a tagRef index (group + ident/datum) finds the owners.

Per effect it reports: particle systems / emitters, how many Particle Size and
Emission Radius functions there are (the fields a visual scale would write), Halo 4's
Global Size Scale, and every OTHER tag that references the effect (a shared effect
resized by a card resizes those too; two cards on one effect compound).

    python explosion_fx_audit.py                      all five games, every campaign map
    python explosion_fx_audit.py --game "Halo 3" --maps 040_voi
Writes reports/explosion_fx_audit.json and .txt.
"""
import argparse
import bisect
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MCC = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
import assembly_plugins as ap  # noqa: E402
import halo_map as hm  # noqa: E402

GAMES = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']
MAP_DIRS = {'Halo 2': 'halo2/h2_maps_win64_dx11', 'Halo 3': 'halo3/maps',
            'Halo 3: ODST': 'halo3odst/maps', 'Halo Reach': 'haloreach/maps', 'Halo 4': 'halo4/maps'}
CAMPAIGN = {'Halo 2': r'^0\d\w*\.map$', 'Halo 3': r'^\d{3}_\w+\.map$',
            'Halo 3: ODST': r'^(sc\d+|l\d+|c\d+|h100)\.map$', 'Halo Reach': r'^m\d+\.map$',
            'Halo 4': r'^m\d+\w*\.map$'}
SKIP_MAP = re.compile(r'test|_count|\.og$|shipped', re.I)
PLUGIN_DIRS = {'Halo 2': ['Halo2MCC', 'Halo2'], 'Halo 3': ['Halo3MCC', 'Halo3'],
               'Halo 3: ODST': ['ODSTMCC', 'ODST'], 'Halo Reach': ['ReachMCC', 'Reach'],
               'Halo 4': ['Halo4MCC', 'Halo4']}
RADIUS_FIELDS = {'Radius', 'Radius Max'}


# --- cards -----------------------------------------------------------------
def resolve_gamed(value, game):
    if not isinstance(value, dict):
        return value
    if game in value:
        return value[game]
    if 'default' in value:
        return value['default']
    for g in reversed(GAMES[:GAMES.index(game)]):
        if g in value:
            return value[g]
    return None


def card_offered(card, game):
    g = card.get('game')
    if not g:
        return True
    g = [g] if isinstance(g, str) else g
    return game in g or (game == 'Halo 3: ODST' and 'Halo 3' in g)


def target_applies(t, game):
    if t.get('ignore') or game in (t.get('skip_games') or []):
        return False
    return not t.get('games') or game in t['games']


def radius_cards(game):
    """[(card path, [jpt paths])] for cards whose targets write a jpt! Radius."""
    db = json.load(open(os.path.join(ROOT, 'halo.json'), encoding='utf-8'))
    out = []

    def walk(o, path):
        if isinstance(o, dict):
            if isinstance(o.get('targets'), list) and card_offered(o, game):
                tag = resolve_gamed(o.get('tag'), game)
                for t in o['targets']:
                    if not isinstance(t, dict) or not target_applies(t, game):
                        continue
                    f = resolve_gamed(t.get('field'), game)
                    tt = resolve_gamed(t.get('tag'), game) or tag
                    if f in RADIUS_FIELDS and isinstance(tt, str) and tt.startswith('jpt! '):
                        out.append((' > '.join(path), [p.strip() for p in tt[5:].split(' & ')]))
                        break
            for k, v in o.items():
                walk(v, path + [k])
    walk(db, [])
    return out


# --- maps --------------------------------------------------------------------
def load(game, path):
    if game == 'Halo 2':
        import halo2_map
        return halo2_map.Halo2Map(path)
    if game in ('Halo 3', 'Halo 3: ODST'):
        import halo3_map
        return halo3_map.Halo3Map(path)
    if game == 'Halo Reach':
        import reach_map
        return reach_map.ReachMap(path)
    import halo4_map
    return halo4_map.Halo4Map(path)


class Index:
    """tagRef index of one map: refs[owner key] -> [(offset in owner, target tag)] and
    users[target key] -> [(owner tag, offset)]. Key = ident (gen 3+) / datum (Halo 2)."""

    def __init__(self, game, m):
        self.game, self.m = game, m
        h2 = game == 'Halo 2'
        self.key = (lambda t: t['datum']) if h2 else (lambda t: t['ident'])
        live = [t for t in m.tags if t.get('base') is not None and t.get('class')]
        self.by_key = {self.key(t): t for t in live}
        mags = {struct.unpack('<I', t['class'].encode('latin1')[::-1])[0]: t['class'] for t in live}
        ids = np.array(sorted(self.by_key), dtype='<u4')
        self.refs, self.users = {}, {}
        d = m.data
        if h2:      # [group][datum]; every tag has an exact size
            spans = [(t, t['base'] & ~3, max(0, t['size'] or 0) // 4) for t in live]
            gap = 1
        else:       # [group][..][..][ident]; owner = the tag whose base is the nearest below
            live.sort(key=lambda t: t['base'])
            lo = live[0]['base'] & ~3
            spans = [(None, lo, (len(d) - lo) // 4)]
            bases = [t['base'] for t in live]
            gap = 3
        for owner, b, n in spans:
            arr = np.frombuffer(bytes(d[b:b + n * 4]), dtype='<u4')
            for h in np.nonzero(np.isin(arr, ids))[0]:
                if h < gap:
                    continue
                tt = self.by_key[int(arr[h])]
                if mags.get(int(arr[h - gap])) != tt['class']:
                    continue
                at = b + (int(h) - gap) * 4
                o = owner
                if o is None:
                    k = bisect.bisect_right(bases, at) - 1
                    if k < 0:
                        continue
                    o = live[k]
                self.refs.setdefault(self.key(o), []).append((at - o['base'], tt))
                self.users.setdefault(self.key(tt), []).append((o, at - o['base']))

    def find(self, cls, path):
        pl = path.lower()
        if '*' in path:
            match = hm._wildcard_matcher(path)
            return [t for t in self.m.tags if t.get('class') == cls and t.get('name') and match(t['name'])]
        return [t for t in self.m.tags if t.get('class') == cls and str(t.get('name') or '').lower() == pl]


# --- effect layout -----------------------------------------------------------
def plugin_file(game, group):
    for s in PLUGIN_DIRS[game]:
        p = os.path.join(ap.PLUGINS, s, group + '.xml')
        if os.path.isfile(p):
            return p


def effe_layout(game):
    root = ET.parse(plugin_file(game, 'effe')).getroot()

    def child(node, name):
        return next(ch for ch in node if ch.tag.lower() == 'tagblock' and ch.get('name') == name)

    def blk(n):
        return int(n.get('offset'), 16), int(n.get('elementSize'), 16)
    ev = child(root, 'Events')
    ps = child(ev, 'Particle Systems')
    em = child(ps, 'Emitters')
    L = {'EV': blk(ev), 'PSYS': blk(ps), 'EMIT': blk(em), 'props': {}}
    title = None
    for ch in em:
        if ch.tag.lower() == 'comment':
            title = ch.get('title') or ''
        elif ch.get('name') == 'Input Variable' and title:
            L['props'][title.split(' (')[0]] = int(ch.get('offset'), 16)
    L['gss'] = next((int(ch.get('offset'), 16) for ch in root if ch.get('name') == 'Global Size Scale'), None)
    return L


def tagref_names(game, group):
    """{offset: field name} of a group's ROOT-level tagRefs (to name a projectile's
    detonation-effect fields)."""
    p = plugin_file(game, group)
    if not p:
        return {}
    root = ET.parse(p).getroot()
    return {int(ch.get('offset'), 16): ch.get('name') for ch in root
            if ch.tag.lower() == 'tagref' and ch.get('offset')}


def effect_stats(game, m, t, L):
    h2 = game == 'Halo 2'
    p2o = m.p2o if h2 else m.data2off
    fn_rel, ptr_rel = (8, 0xC) if h2 else (4, 0x10)

    def blk(o):
        n = m.i32(o)
        return n, (p2o(m.u32(o + 4)) if n > 0 else None)
    st = {'psys': 0, 'emitters': 0, 'size_fns': 0, 'radius_fns': 0}
    ne, eb = blk(t['base'] + L['EV'][0])
    for e in range(ne if eb else 0):
        nps, sb = blk(eb + e * L['EV'][1] + L['PSYS'][0])
        for s in range(nps if sb else 0):
            st['psys'] += 1
            nem, emb = blk(sb + s * L['PSYS'][1] + L['EMIT'][0])
            for j in range(nem if emb else 0):
                em = emb + j * L['EMIT'][1]
                st['emitters'] += 1
                for key, prop in (('size_fns', 'Particle Size'), ('radius_fns', 'Emission Radius')):
                    q = em + L['props'][prop]
                    if m.i32(q + fn_rel) > 0 and p2o(m.u32(q + ptr_rel)):
                        st[key] += 1
    if L['gss'] is not None:
        st['global_size_scale'] = round(struct.unpack_from('<f', m.data, t['base'] + L['gss'])[0], 4)
    return st


# --- audit -------------------------------------------------------------------
def audit_map(game, path, cards, L, proj_refs, report):
    m = load(game, path)
    ix = Index(game, m)
    mp = os.path.basename(path)
    for card, jpts in cards:
        rc = report.setdefault(card, {'jpt': {}, 'maps': []})
        hit = False
        for jp in jpts:
            for j in ix.find('jpt!', jp):
                hit = True
                rj = rc['jpt'].setdefault(j['name'], {'owners': {}})
                for owner, off in ix.users.get(ix.key(j), []):
                    ro = rj['owners'].setdefault('%s %s' % (owner['class'], owner['name']), {'effects': {}})
                    if owner['class'] == 'effe':
                        effs = [(owner, '(carries the jpt! as a part)')]
                    elif owner['class'] == 'proj':
                        effs = [(t2, proj_refs.get(o2, '+0x%X' % o2)) for o2, t2 in ix.refs.get(ix.key(owner), [])
                                if t2['class'] == 'effe']
                    else:
                        effs = []
                    for e, via in effs:
                        re_ = ro['effects'].setdefault(e['name'], {'via': set(), 'users': set()})
                        re_['via'].add(via)
                        for u, _ in ix.users.get(ix.key(e), []):
                            re_['users'].add('%s %s' % (u['class'], u['name']))
                        if 'stats' not in re_:
                            re_['stats'] = effect_stats(game, m, e, L)
        if hit:
            rc['maps'].append(mp)


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument('--game', action='append')
    ap_.add_argument('--maps', nargs='*')
    a = ap_.parse_args()
    games = a.game or GAMES[1:]
    out = {}
    for game in games:
        cards = radius_cards(game)
        L = effe_layout(game)
        proj_refs = tagref_names(game, 'proj')
        d = os.path.join(MCC, MAP_DIRS[game])
        maps = sorted(f for f in os.listdir(d) if re.match(CAMPAIGN[game], f) and not SKIP_MAP.search(f))
        if a.maps:
            maps = [f for f in maps if os.path.splitext(f)[0] in a.maps]
        rep = out.setdefault(game, {})
        for f in maps:
            print('%s %s' % (game, f), flush=True)
            try:
                audit_map(game, os.path.join(d, f), cards, L, proj_refs, rep)
            except Exception as e:      # a map the reader cannot parse is reported, not fatal
                print('   FAILED: %r' % e, flush=True)
    # shared-effect census across cards (two cards on one effect compound)
    for game, rep in out.items():
        claim = {}
        for card, rc in rep.items():
            for jn, rj in rc['jpt'].items():
                for on, ro in rj['owners'].items():
                    for en in ro['effects']:
                        claim.setdefault(en, set()).add(card)
        rep['_shared_between_cards'] = {e: sorted(c) for e, c in claim.items() if len(c) > 1}
    os.makedirs(os.path.join(HERE, 'reports'), exist_ok=True)
    js = os.path.join(HERE, 'reports', 'explosion_fx_audit.json')

    def conv(o):
        return sorted(o) if isinstance(o, set) else o
    with open(js, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, default=conv)
    lines = []
    for game, rep in out.items():
        lines.append('#### %s' % game)
        for card, rc in rep.items():
            if card.startswith('_'):
                continue
            lines.append('%s  [%d maps]' % (card, len(rc['maps'])))
            if not rc['jpt']:
                lines.append('    (no jpt! found in any campaign map)')
            for jn, rj in rc['jpt'].items():
                lines.append('    jpt! %s' % jn)
                for on, ro in rj['owners'].items():
                    lines.append('      by %s' % on)
                    for en, re_ in ro['effects'].items():
                        others = sorted(set(re_['users']) - {on})
                        lines.append('        effe %s via %s %s | other users %d%s' % (
                            en, '/'.join(sorted(re_['via'])), re_['stats'], len(others),
                            (': ' + '; '.join(others))[:400] if others else ''))
        sh = rep.get('_shared_between_cards', {})
        lines.append('  effects shared between cards: %d' % len(sh))
        for e, c in sh.items():
            lines.append('    %s <- %s' % (e, ' | '.join(c)))
    with open(js[:-5] + '.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', js)


if __name__ == '__main__':
    main()
