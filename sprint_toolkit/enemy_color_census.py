r"""enemy_color_census.py -- every enemy rank variant and its colour slots, all six games.

The groundwork for enemy recolouring (visual only, not a card). Established 2026-09-18
and confirmed in game per engine (see the halo-enemy-colors memory):

  Halo 1          actor variant (actv) Change Colors 0x22C -- one entry per slot (A, B...)
  Halo 2/3/ODST/  biped Change Colors -> Initial Permutations, one entry per rank VARIANT
  Reach           name, several slots per biped
  ODST Brutes     the armour shader's `variant` colour overlays override the biped
  Halo 4          per-rank armour `mat` tint (multiplies the rank's texture)
  Jackal shields  H1 bipd slot C; H2 shad ramps; H3/ODST/Reach/H4 shader/material ramps

A variant is RELEVANT when an AI character actually spawns with it, so this walks every
character of every enemy family: character -> unit biped -> the variant names it uses
(parents followed when a character leaves them empty) -> the biped's colour entries for
that variant. Variants are matched by raw stringID, because Halo 3's static-range names
do not always resolve; the display name is best effort. Every campaign map is read and
the results are merged, so a rank that only appears on one level is still listed.

    python sprint_toolkit/enemy_color_census.py                  # all six games
    python sprint_toolkit/enemy_color_census.py --game "Halo 3"
    python sprint_toolkit/enemy_color_census.py --json out.json --md out.md
"""
import argparse
import collections
import contextlib
import io
import json
import os
import struct
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import halo_enhancer as he                                        # noqa: E402
import halo_patch as hp                                           # noqa: E402
import behaviour_census as bc                                     # noqa: E402

B = chr(92)
# game: (char unit off, tagref size, variants block, variants elem, bipd change colours,
#        change colour elem)
LAYOUT = {
    'Halo 2': (0xC, 8, 0x2C, 0xC, 0xAC, 0x10),
    'Halo 3': (0x14, 16, 0x54, 0x14, 0xD4, 0x18),
    'Halo 3: ODST': (0x14, 16, 0x54, 0x14, 0xD4, 0x18),
    'Halo Reach': (0x14, 16, 0x54, 0x18, 0x134, 0x18),
    'Halo 4': (0x14, 16, 0x54, 0x18, 0x148, 0x18),
}
PARENT = 0x4


def hexcol(r, g, b):
    return '%02X%02X%02X' % tuple(int(round(max(0.0, min(1.0, x)) * 255)) for x in (r, g, b))


class Maps:
    """Per-map helpers that hide the tagref/ident differences between engines."""

    def __init__(self, m, game):
        self.m, self.game = m, game
        self.gen2 = game == 'Halo 2'
        tags = [t for t in m.tags if isinstance(t, dict)]
        key = 'datum' if self.gen2 else 'ident'
        self.by_id = {t.get(key): t for t in tags if t.get(key) is not None}
        self.by_base = {t.get('base'): t for t in tags if t.get('base')}

    def ref(self, base, off):
        ident = self.m.u32(base + off + (4 if self.gen2 else 0xC))
        return self.by_id.get(ident)

    def name(self, sid):
        try:
            return self.m.resolve_stringid(sid)
        except Exception:
            return None


def census_gen2plus(game, subs, folder, fam, out):
    unit_off, _rs, var_blk, var_el, cc_blk, cc_el = LAYOUT[game]
    for mp in bc.ca.game_maps(folder, game):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                m = hp.open_map(mp, game)
        except Exception:
            continue
        H = Maps(m, game)
        chars = {}
        for tp, base in m.find_tags('char', '*'):
            chars[base] = tp

        def resolve(base, depth=0):
            """(unit tag, [variant sids]) with parents followed."""
            unit = H.ref(base, unit_off)
            sids = [m.u32(e) & 0xFFFFFFFF for e in m.follow_all(base, [var_blk], [var_el], 'all')]
            if (unit is None or not sids) and depth < 6:
                par = H.ref(base, PARENT)
                if par and par.get('base') and par['base'] != base:
                    pu, ps = resolve(par['base'], depth + 1)
                    unit = unit or pu
                    sids = sids or ps
            return unit, sids

        for base, tp in chars.items():
            enemy = bc.family_of(tp, fam)
            if not enemy or enemy == bc.GENERIC:
                continue
            unit, sids = resolve(base)
            if not unit or unit.get('class') != 'bipd' or not unit.get('base'):
                continue
            slots = m.follow_all(unit['base'], [cc_blk], [cc_el], 'all')
            for sid in (sids or [0]):
                vname = H.name(sid) if sid else None
                cols = []
                for si, s in enumerate(slots):
                    perms = m.follow_all(s, [0x0], [0x20], 'all')
                    hit = [p for p in perms if m.u32(p + 0x1C) == sid] or \
                          [p for p in perms if m.u32(p + 0x1C) in (0, 0xFFFFFFFF)]
                    if hit:
                        p = hit[0]
                        lo = struct.unpack_from('<3f', m.data, p + 4)
                        hi = struct.unpack_from('<3f', m.data, p + 0x10)
                        cols.append((si, hexcol(*lo), hexcol(*hi), 'own' if m.u32(p + 0x1C) == sid else 'any'))
                    elif perms:
                        cols.append((si, None, None, 'none'))
                key = (game, enemy, vname or ('sid:%08X' % sid if sid else '(none)'),
                       unit['name'].rsplit(B, 1)[-1])
                rec = out.setdefault(key, {'chars': set(), 'maps': set(), 'slots': cols,
                                           'bipd': unit['name']})
                rec['chars'].add(tp.rsplit(B, 1)[-1])
                rec['maps'].add(os.path.basename(mp))
                if len(cols) > len(rec['slots']):
                    rec['slots'] = cols
        del m


def census_h1(folder, fam, out):
    game = 'Halo 1'
    for mp in bc.ca.game_maps(folder, game):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                m = hp.open_map(mp, game)
        except Exception:
            continue

        def refname(base, off):
            ptr = m.u32(base + off + 4)
            if ptr <= m.magic:
                return None
            o = ptr - m.magic
            return bytes(m.data[o:m.data.index(b'\0', o)]).decode('latin1')
        for tp, base in m.find_tags('actv', '*'):
            enemy = bc.family_of(tp, fam)
            if not enemy:
                continue
            actr = refname(base, 0x4) or ''
            unit = refname(base, 0x14) or ''
            cols = []
            for si, e in enumerate(m.follow_all(base, [0x22C], [0x20], 'all')):
                lo = struct.unpack_from('<3f', m.data, e)
                hi = struct.unpack_from('<3f', m.data, e + 0xC)
                cols.append((si, hexcol(*lo), hexcol(*hi), 'actv'))
            key = (game, enemy, actr.rsplit(B, 1)[-1] or tp.rsplit(B, 1)[-1], unit.rsplit(B, 1)[-1])
            rec = out.setdefault(key, {'chars': set(), 'maps': set(), 'slots': cols,
                                       'bipd': unit})
            rec['chars'].add(tp.rsplit(B, 1)[-1])
            rec['maps'].add(os.path.basename(mp))
        del m


def merge_unnamed(out):
    """Fold `sid:` rows (a variant whose name does not resolve on that map) into the named
    row of the same game, enemy and biped with identical colours -- the same rank read on
    a map where Halo 3's static-range name was missing."""
    for key in [k for k in out if k[2].startswith('sid:')]:
        game, enemy, _v, bipd = key
        twin = next((k for k in out if k[:2] == (game, enemy) and k[3] == bipd
                     and not k[2].startswith('sid:') and out[k]['slots'] == out[key]['slots']), None)
        if twin:
            out[twin]['chars'] |= out[key]['chars']
            out[twin]['maps'] |= out[key]['maps']
            del out[key]


def _fn_stops(m, off, size):
    """The four BGRA colour stops of a colour function (H3+ layout), as hex strings."""
    if not off or size < 0x14:
        return []
    return ['%02X%02X%02X' % tuple(m.data[off + 4 + 4 * k + j] for j in (2, 1, 0)) for k in range(4)]


def extras(game, folder, out_extra):
    """Colour sources that are not biped change colours: ODST Brute armour overlays,
    Halo 4 rank armour materials, and the Jackal shields (Halo 2 onward)."""
    for mp in bc.ca.game_maps(folder, game):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                m = hp.open_map(mp, game)
        except Exception:
            continue
        tags = [t for t in m.tags if isinstance(t, dict)]

        def put(kind, name, detail):
            rec = out_extra.setdefault((game, kind, name), {'detail': detail, 'maps': set()})
            rec['maps'].add(os.path.basename(mp))
        if game == 'Halo 2':
            for t in tags:
                n = str(t.get('name'))
                if t.get('class') == 'shad' and n.endswith(('jackal_shield', 'jackal_shield_major')):
                    for pp in m.follow_all(t['base'], [0x20], [0x7C], 'all'):
                        for o in m.follow_all(pp, [0x3C], [0x14], 'all'):
                            if m.u32(o) == 0:
                                continue
                            off = m.p2o(m.u32(o + 0x10))
                            st = ['%02X%02X%02X' % tuple(m.data[off + x + j] for j in (2, 1, 0))
                                  for x in (4, 0x10)]
                            put('Jackal shield', n.rsplit(B, 1)[-1],
                                'shield ramp full %s -> broken %s' % tuple(st))
        if game in ('Halo 3', 'Halo 3: ODST', 'Halo Reach'):
            pp_off, pp_sizes = (0x28, (0x8C,)) if game != 'Halo Reach' else (0x38, (0xB4, 0xAC))
            for t in tags:
                n = str(t.get('name'))
                cls = t.get('class')
                want = None
                if cls == 'rmhg' and ('jackal' + B + 'shaders' + B + 'jackal_shield' in n
                                      or 'cov_portable_shield' + B + 'shaders' in n
                                      or 'skirmisher_bracers' + B + 'shaders' in n):
                    want = 'Jackal shield'
                elif cls == 'rmsh' and game == 'Halo 3: ODST' and 'brute' + B + 'shaders' in n:
                    want = 'Brute armour (rank overlay)'
                if not want:
                    continue
                pps = []
                for es in pp_sizes:
                    pps = m.follow_all(t['base'], [pp_off], [es], 'all')
                    if pps:
                        break
                for pp in pps:
                    for o in m.follow_all(pp, [0x5C], [0x24], 'all'):
                        if m.u32(o) != 1:
                            continue
                        st = _fn_stops(m, m.data2off(m.u32(o + 0x10 + 0xC)), m.i32(o + 0x10))
                        put(want, n.rsplit(B, 1)[-1], 'input %s stops %s' % (
                            m.resolve_stringid(m.u32(o + 4)), ' '.join(st)))
        if game == 'Halo 4':
            for t in tags:
                n = str(t.get('name'))
                if t.get('class') != 'mat ':
                    continue
                if 'jackal_shield' + B + 'shaders' in n or 'cov_portable_shield' + B + 'shaders' in n:
                    for pp in m.follow_all(t['base'], [0x1C], [0x9C], 'all'):
                        for f in m.follow_all(pp, [0x54], [0x2C], 'all'):
                            if m.u32(f) == 1:
                                st = _fn_stops(m, m.data2off(m.u32(f + 0x18 + 0xC)), m.i32(f + 0x18))
                                put('Jackal shield', n.rsplit(B, 1)[-1], 'stops ' + ' '.join(st))
                elif 'objects' + B + 'characters' + B + 'storm_' in n and (
                        n.endswith('_armor') or n.endswith('_pack')):
                    for pp in m.follow_all(t['base'], [0x1C], [0x9C], 'all'):
                        fc = m.follow_all(pp, [0x18], [0x10], 'all')
                        if fc:
                            tint = struct.unpack_from('<3f', m.data, fc[0])
                            famname = n.split('characters' + B)[1].split(B)[0]
                            put('Armour material (tint)', famname + ' / ' + n.rsplit(B, 1)[-1],
                                'tint %s' % hexcol(*tint))
        del m


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game')
    ap.add_argument('--json')
    ap.add_argument('--md')
    a = ap.parse_args()
    he.load_settings()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    fam = bc.families(db)
    out = {}
    for game, subs, folder, _classes in bc.cases():
        if a.game and a.game != game:
            continue
        print('reading', game, flush=True)
        if game == 'Halo 1':
            census_h1(folder, fam, out)
        elif game in LAYOUT:
            census_gen2plus(game, subs, folder, fam, out)
    merge_unnamed(out)
    out_extra = {}
    for game, subs, folder, _classes in bc.cases():
        if (a.game and a.game != game) or game == 'Halo 1':
            continue
        print('reading extras', game, flush=True)
        extras(game, folder, out_extra)
    lines = []
    last = None
    for key in sorted(out, key=lambda k: (k[0], k[1], k[2])):
        game, enemy, variant, bipd = key
        rec = out[key]
        if (game, enemy) != last:
            lines.append('')
            lines.append('## %s -- %s' % (game, enemy))
            last = (game, enemy)
        slots = '  '.join('s%d %s%s%s' % (si, lo or '-', ('..' + hi) if hi and hi != lo else '',
                                           '' if how in ('own', 'actv') else '(%s)' % how)
                          for si, lo, hi, how in rec['slots'])
        lines.append('- **%s** (%s) %s | %d map(s) | chars: %s' % (
            variant, bipd, slots or 'NO COLOUR SLOTS', len(rec['maps']),
            ', '.join(sorted(rec['chars']))[:160]))
    last = None
    for key in sorted(out_extra):
        game, kind, name = key
        if (game, kind) != last:
            lines.append('')
            lines.append('## %s -- %s' % (game, kind))
            last = (game, kind)
        lines.append('- **%s** %s | %d map(s)' % (name, out_extra[key]['detail'],
                                                 len(out_extra[key]['maps'])))
    text = '\n'.join(lines)
    print(text)
    if a.md:
        io.open(a.md, 'w', encoding='utf-8').write('# Enemy colour census\n' + text + '\n')
    if a.json:
        conv = [{'game': k[0], 'enemy': k[1], 'variant': k[2], 'bipd': v['bipd'],
                 'slots': v['slots'], 'maps': sorted(v['maps']), 'chars': sorted(v['chars'])}
                for k, v in out.items()]
        conv += [{'game': k[0], 'kind': k[1], 'name': k[2], 'detail': v['detail'],
                  'maps': sorted(v['maps'])} for k, v in out_extra.items()]
        json.dump(conv, io.open(a.json, 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
