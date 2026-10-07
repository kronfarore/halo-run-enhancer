r"""Self-test for player_armour.py (the player's own damage-table armour rows).

For one or two baseline maps per game it COPIES the map into a scratch folder (the
baselines and the live MCC maps are never written), runs player_armour.apply(), saves,
reopens, and checks:

  (a) the materials block the engine reads (matg Materials; Runtime Materials in Reach/H4)
      grew by exactly the number of clones made;
  (b) every player-hlmt material-index field points at a clone of the material it pointed
      at before, and every NON-player hlmt's index fields are unchanged;
  (c) for every damage group of every damage-table element, the multiplier the player's
      materials get is the same before and after, and so is every Elite / Brute / Grunt /
      Jackal / Hunter (Reach: + Skirmisher, H4: + Prometheans) material's -- resolved
      by an independent reader (its own offsets), under the module's rule ("specific
      wins"); the groups that would differ under "general x specific" are listed;
  (d) a second apply() on the saved map writes nothing;
  (e) every byte that differs from the baseline lies inside a range the module recorded
      as written (plus the header checksum), and the whole matg tag compares equal to the
      baseline leaf-for-leaf through the plugin (block pointers followed, not compared)
      except the grown materials / armour-row blocks.

    python sprint_toolkit/player_armour_selftest.py [--scratch DIR] [--only "Halo 3"]
"""
import argparse
import gc
import os
import shutil
import struct
import sys
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
import halo_patch as hp          # noqa: E402
import player_armour as pa       # noqa: E402

BASE = r'E:\HaloBaselines'
PLUGINS = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
SUB = {'Halo 2': 'Halo2MCC', 'Halo 3': 'Halo3MCC', 'Halo 3: ODST': 'ODSTMCC',
       'Halo Reach': 'ReachMCC', 'Halo 4': 'Halo4MCC'}
MAPS = [
    ('Halo 2', r'halo2\h2_maps_win64_dx11\03a_oldmombasa.map'),
    ('Halo 2', r'halo2\h2_maps_win64_dx11\04a_gasgiant.map'),          # Arbiter level
    ('Halo 3', r'halo3\maps\010_jungle.map'),
    ('Halo 3', r'halo3\maps\100_citadel.map'),
    ('Halo 3: ODST', r'halo3odst\maps\sc100.map'),
    ('Halo Reach', r'haloreach\maps\m10.map'),
    ('Halo 4', r'halo4\maps\m10_crash.map'),
]
# independent reader: (materials off, es, general off, specific off), (table off, es,
# group es), hlmt index fields [(block off, es, (field offs))], top-level fields, model off,
# header checksum offset
IND = {
    'Halo 2': dict(mats=(0x150, 0xB4, 0x10, 0x14), dt=(0xD0, 0x8, 0xC), model=(0x34, 4), cs=0x2F8,
                   hl=[(0x58, 0x14, (0x10,)), (0x60, 0xF8, (0xCC, 0xCE))], top=()),
    'Halo 3': dict(mats=(0x464, 0x170, 0xC, 0x10), dt=(0x3EC, 0xC, 0x10), model=(0x34, 0xC), cs=0x360,
                   hl=[(0x7C, 0x14, (0x10,)), (0x88, 0xA4, (0x80, 0x82))], top=()),
    'Halo 3: ODST': dict(mats=(0x480, 0x178, 0xC, 0x10), dt=(0x3FC, 0xC, 0x10), model=(0x34, 0xC), cs=0x360,
                         hl=[(0x88, 0x14, (0x10,)), (0x94, 0xA4, (0x80, 0x82))], top=()),
    'Halo Reach': dict(mats=(0x658, 0x1A8, 0xC, 0x10), dt=(0x3F0, 0xC, 0x10), model=(0x64, 0xC), cs=0x360,
                       hl=[(0xA8, 0x14, (0x10,)), (0xB4, 0x14, (0x10,)), (0xC0, 0x10C, (0xE4, 0xE6)),
                           (0xE0, 0xC0, (0xBE,))], top=(0x104,)),
    'Halo 4': dict(mats=(0x8A0, 0x1A8, 0xC, 0x10), dt=(0x580, 0xC, 0x10), model=(0x64, 0xC), cs=0x358,
                   hl=[(0xE8, 0x14, (0x10,)), (0xF4, 0xB8, (0x90, 0x92)), (0x114, 0xB4, (0xB2,))], top=(0x138,)),
}
ENEMIES = {
    'Halo 2': ('elite', 'brute', 'grunt', 'jackal', 'hunter'),
    'Halo 3': ('elite', 'brute', 'grunt', 'jackal', 'hunter'),
    'Halo 3: ODST': ('elite', 'brute', 'grunt', 'jackal', 'hunter'),
    'Halo Reach': ('elite', 'brute', 'grunt', 'jackal', 'hunter', 'skirmisher'),
    'Halo 4': ('elite', 'grunt', 'jackal', 'hunter', 'knight', 'pawn', 'bishop'),
}
# blocks the module grows: matg Materials / Runtime Materials and Damage Table rows
GROWN = {'Materials', 'Runtime Materials', 'Armor Modifiers'}


class Reader:
    def __init__(self, m, game):
        self.m, self.g, self.L = m, game, IND[game]
        self.matg = m.globals_tag()['base']

    def i16(self, o):
        return struct.unpack_from('<h', self.m.data, o)[0]

    def blk(self, off):
        n = self.m.i32(off)
        return (n, hp._block_base(self.m, off)) if n > 0 else (0, None)

    def mats(self):
        mo, es, go, so = self.L['mats']
        n, b = self.blk(self.matg + mo)
        out = []
        for i in range(n):
            e = b + i * es
            out.append(dict(name=self.m.u32(e), gen=self.m.u32(e + go), spec=self.m.u32(e + so)))
        return out

    def tables(self):
        to, tes, ges = self.L['dt']
        out = []
        tn, tb = self.blk(self.matg + to)
        for t in range(tn):
            gn, gb = self.blk(tb + t * tes)
            groups = []
            for g in range(gn):
                ge = gb + g * ges
                rn, rb = self.blk(ge + 4)
                rows = {}
                for r in range(rn):
                    nm, v = struct.unpack_from('<If', self.m.data, rb + r * 8)
                    rows.setdefault(nm, v)
                groups.append((self.m.u32(ge), rows))
            out.append(groups)
        return out

    def hlmt_fields(self, hbase):
        vals = []
        for off, es, fs in self.L['hl']:
            n, b = self.blk(hbase + off)
            for i in range(n):
                vals += [self.i16(b + i * es + f) for f in fs]
        vals += [self.i16(hbase + f) for f in self.L['top']]
        return vals

    def model_of(self, tag):
        mo, idoff = self.L['model']
        d = self.m.u32(tag['base'] + mo + idoff)
        t = self.m.tag(d & 0xFFFF) if d not in (0, 0xFFFFFFFF) else None
        return t if t and t.get('class') == 'hlmt' else None


def _same(xs, ys):
    """Per-group multipliers equal, to float32 precision: a product like 3 x 0.11667 is
    stored as a float32 and never compares bit-exact with the double product."""
    return len(xs) == len(ys) and all(
        (x is None and y is None) or (x is not None and y is not None
                                      and abs(x - y) <= 1e-6 * max(1.0, abs(x)))
        for x, y in zip(xs, ys))


def mult(mats, groups_rows, idx, rule='multiply'):
    """Per (table, group): the multiplier material idx gets (None = no row = 1)."""
    m = mats[idx]
    out = []
    for groups in groups_rows:
        for gname, rows in groups:
            s, g = m['spec'], m['gen']
            hs, hg = bool(s) and s in rows, bool(g) and g in rows
            if rule == 'multiply' and hs and hg:
                out.append(rows[s] * rows[g])
            elif hs:
                out.append(rows[s])
            elif hg:
                out.append(rows[g])
            else:
                out.append(None)
    return out


# --- plugin deep compare of matg ------------------------------------------------------
def deep_compare(old, new, ob, nb, node, path, diffs, ranges, depth=0):
    """Compare one struct (element) of matg leaf-for-leaf: raw bytes with block/data
    pointer words masked, recursing into every block and data ref."""
    kids = []
    mask = set()
    for ch in node:
        t = ch.tag.lower()
        off = ch.get('offset')
        if off is None:
            continue
        off = int(off, 16)
        if t == 'tagblock':
            kids.append(('block', ch, off))
            mask.add(off + 4)
        elif t == 'dataref':
            kids.append(('data', ch, off))
            mask.add(off + 0xC)
    return kids, mask


def compare_struct(old, new, ob, nb, size, node, path, diffs, ranges, grown=GROWN):
    kids, mask = deep_compare(old, new, ob, nb, node, path, diffs, ranges)
    a = old.data[ob:ob + size]
    b = new.data[nb:nb + size]
    if a != b:
        for w in range(0, size, 4):
            if a[w:w + 4] != b[w:w + 4] and w not in mask:
                # the count of a grown block is allowed to differ
                if any(k == 'block' and o == w and ch.get('name') in grown for k, ch, o in kids):
                    continue
                diffs.append('%s +%#x: %s -> %s' % (path, w, a[w:w + 4].hex(), b[w:w + 4].hex()))
                break
    for k, ch, off in kids:
        nm = ch.get('name')
        if k == 'block':
            es = int(ch.get('elementSize'), 16)
            co, cn = old.i32(ob + off), new.i32(nb + off)
            if co <= 0 and cn <= 0:
                continue
            po, pn = hp._block_base(old, ob + off), hp._block_base(new, nb + off)
            if co != cn and nm not in grown:
                diffs.append('%s/%s count %d -> %d' % (path, nm, co, cn))
                continue
            if cn < co:
                diffs.append('%s/%s shrank %d -> %d' % (path, nm, co, cn))
                continue
            ranges.append((po, po + co * es))
            for i in range(co):
                compare_struct(old, new, po + i * es, pn + i * es, es, ch, '%s/%s[%d]' % (path, nm, i), diffs, ranges,
                               grown)
        else:
            so, sn = old.u32(ob + off), new.u32(nb + off)
            if so != sn:
                diffs.append('%s/%s data size %d -> %d' % (path, nm, so, sn))
                continue
            if so:
                po, pn = old.data2off(old.u32(ob + off + 0xC)), new.data2off(new.u32(nb + off + 0xC))
                if po is None or pn is None or old.data[po:po + so] != new.data[pn:pn + so]:
                    diffs.append('%s/%s data differs' % (path, nm))


def matg_deep(old, new, game):
    """(diffs, matg-reachable ranges in the OLD map) -- None for Halo 2."""
    if game == 'Halo 2':
        return None, []                                 # nothing moves in Halo 2
    root = ET.parse(os.path.join(PLUGINS, SUB[game], 'matg.xml')).getroot()
    size = int(root.get('baseSize'), 16)
    diffs, ranges = [], []
    gb = old.globals_tag()['base']
    ranges.append((gb, gb + size))
    compare_struct(old, new, gb, new.globals_tag()['base'], size, root, 'matg', diffs, ranges)
    return diffs, ranges


def owners_deep(old, new, game, moved, matg_ranges):
    """Every pointer the in-place growth rewrote: attribute it to the tag whose main
    struct holds it and deep-compare that whole tag through its plugin; a pointer that
    sits in no main struct must lie inside matg's reachable data (compared already)."""
    import bisect
    if not moved:
        return [], [], []
    tags = sorted((t['base'], t['index']) for t in old.tags if t.get('base') is not None and t.get('class'))
    bases = [b for b, _i in tags]
    roots, owners, loose = {}, {}, []
    for r in moved['referencers']:
        k = bisect.bisect_right(bases, r) - 1
        t = old.tag(tags[k][1]) if k >= 0 else None
        root = None
        if t is not None:
            if t['class'] not in roots:
                f = os.path.join(PLUGINS, SUB[game], t['class'] + '.xml')
                roots[t['class']] = ET.parse(f).getroot() if os.path.isfile(f) else None
            root = roots[t['class']]
        if root is not None and r < t['base'] + int(root.get('baseSize'), 16):
            owners[t['index']] = t
        elif not any(a <= r < e for a, e in matg_ranges):
            loose.append(r)
    diffs = []
    for idx, t in owners.items():
        if t['class'] == 'matg':
            continue
        root = roots[t['class']]
        compare_struct(old, new, t['base'], new.tag(idx)['base'], int(root.get('baseSize'), 16), root,
                       '%s %s' % (t['class'], t['name']), diffs, [], grown=set())
    return sorted('%s %s' % (t['class'], (t['name'] or '').rsplit(chr(92), 1)[-1]) for t in owners.values()), loose, diffs


# --- one map ----------------------------------------------------------------------------
def run(game, rel, scratch):
    src = os.path.join(BASE, rel)
    dst = os.path.join(scratch, 'pa_' + os.path.basename(rel))
    shutil.copyfile(src, dst)
    reg = hp.PluginRegistry(PLUGINS, [SUB[game]])
    S = {'map': os.path.basename(rel), 'game': game, 'fail': []}
    try:
        t0 = time.time()
        m = hp.open_map(dst, game)
        res = pa.apply(m, game, reg)
        writes = list(getattr(m, '_player_armour_writes', []))
        moved = getattr(m, '_player_armour_moved', None)
        S['apply'] = res
        S['t_apply'] = time.time() - t0
        bad = [r for r in res if not r['ok']]
        if bad:
            S['fail'] += ['apply: %s %s' % (r['field'], r.get('reason')) for r in bad]
        m.save()
        del m
        gc.collect()
        old = hp.open_map(src, game)
        new = hp.open_map(dst, game)
        ro, rn = Reader(old, game), Reader(new, game)
        mo, mn = ro.mats(), rn.mats()
        made = [r for r in res if r['field'].split(' [')[0] in ('clone', 'wet clone') and '(existing)' not in r['new']]
        # (a)
        S['a'] = (len(mo), len(mn), len(made))
        if len(mn) != len(mo) + len(made):
            S['fail'].append('(a) materials %d -> %d, %d clones' % (len(mo), len(mn), len(made)))
        for i in range(len(mo)):
            if mo[i] != mn[i]:
                S['fail'].append('(a) material [%d] changed' % i)
        # (b)
        bip, _sk = pa.player_bipeds(pa._Ctx(old, game))
        player_hlmts = set()
        for _n, t, _s in bip:
            h = ro.model_of(t)
            if h is not None:
                player_hlmts.add(h['index'])
        nrep = nsame = 0
        player_pairs = set()
        for t in old.tags:
            if t.get('class') != 'hlmt' or t.get('base') is None:
                continue
            fo = ro.hlmt_fields(t['base'])
            fn = rn.hlmt_fields(new.tag(t['index'])['base'])
            if t['index'] in player_hlmts:
                for a, b in zip(fo, fn):
                    if 0 <= a < len(mo):
                        if b < len(mo) or mn[b]['name'] != mo[a]['name']:
                            S['fail'].append('(b) %s field %d -> %d is not its clone' % (t['name'], a, b))
                        else:
                            nrep += 1
                            player_pairs.add((a, b))
            else:
                if fo != fn:
                    S['fail'].append('(b) non-player hlmt %s changed' % t['name'])
                else:
                    nsame += 1
        S['b'] = (nrep, nsame, sorted(player_pairs))
        # (c)
        go, gn = ro.tables(), rn.tables()
        ngroups = sum(len(g) for g in go)
        cdiff = []
        mult_diff = set()
        for a, b in sorted(player_pairs):
            if not _same(mult(mo, go, a), mult(mn, gn, b)):
                cdiff.append('player [%d]->[%d]' % (a, b))
            mm_o, mm_n = mult(mo, go, a, 'multiply'), mult(mn, gn, b, 'multiply')
            k = 0
            for ti, groups in enumerate(go):
                for gname, rows in groups:
                    if not _same([mm_o[k]], [mm_n[k]]):
                        mult_diff.add('[%d] %s' % (ti, pa.sid_name(old, game, gname)))
                    k += 1
        enemy_idx = set()
        names_enemy = set()
        for t in old.tags:
            if t.get('class') != 'bipd' or t.get('base') is None:
                continue
            leaf = (t.get('name') or '').rsplit(chr(92), 1)[-1].lower()
            if not any(k in leaf for k in ENEMIES[game]):
                continue
            h = ro.model_of(t)
            if h is None or h['index'] in player_hlmts:
                continue
            names_enemy.add(leaf)
            enemy_idx.update(v for v in ro.hlmt_fields(h['base']) if 0 <= v < len(mo))
        for i in sorted(enemy_idx):
            if not _same(mult(mo, go, i), mult(mn, gn, i)) or not _same(mult(mo, go, i, 'specific'), mult(mn, gn, i, 'specific')):
                cdiff.append('enemy material [%d]' % i)
        # every other material too
        for i in range(len(mo)):
            if i not in enemy_idx and not _same(mult(mo, go, i), mult(mn, gn, i)):
                cdiff.append('material [%d]' % i)
        S['c'] = (ngroups, len(player_pairs), len(enemy_idx), len(names_enemy), cdiff, sorted(mult_diff))
        if cdiff:
            S['fail'].append('(c) multipliers changed: %s' % ', '.join(cdiff[:8]))
        # (f) the engine BINARY-SEARCHES groups and armour rows (halo3.dll 0x18013eeb4,
        # signed *key - *elem): every array sorted, and the search finds every row
        unsorted, missed = [], []
        cn = pa._Ctx(new, game)
        for t, groups in cn.tables():
            gids = [g[1] for g in groups]
            if gids != sorted(gids, key=lambda v: struct.unpack('<i', struct.pack('<I', v))[0]):
                unsorted.append('[%d] groups' % t)
            for _ge, gsid, _rn, _rb, rows in groups:
                ids = [struct.unpack('<i', struct.pack('<I', r[0]))[0] for r in rows]
                if ids != sorted(ids):
                    unsorted.append('[%d] %s' % (t, pa.sid_name(new, game, gsid)))
                for want in ids:
                    lo, hi, hit = 0, len(ids) - 1, False
                    while lo <= hi:
                        mid = (lo + hi) // 2
                        if ids[mid] == want:
                            hit = True
                            break
                        if ids[mid] < want:
                            lo = mid + 1
                        else:
                            hi = mid - 1
                    if not hit:
                        missed.append('[%d] %s %s' % (t, pa.sid_name(new, game, gsid),
                                                     pa.sid_name(new, game, want & 0xFFFFFFFF)))
        S['f'] = (unsorted, missed)
        if unsorted or missed:
            S['fail'].append('(f) unsorted %s; binary search misses %s' % (unsorted[:4], missed[:4]))
        # (e)
        S['e'] = diff_outside(old, new, writes, IND[game]['cs'], game)
        if S['e'][0]:
            S['fail'].append('(e) %d byte range(s) changed outside the recorded writes: %s' % (
                S['e'][0], S['e'][1][:4]))
        md, mranges = matg_deep(old, new, game)
        S['deep'] = md
        if md:
            S['fail'].append('(e) matg deep compare: %s' % md[:6])
        own, loose, odiff = owners_deep(old, new, game, moved, mranges)
        S['owners'] = (own, loose, odiff)
        if loose:
            S['fail'].append('(e) %d rewritten pointer(s) outside any main struct or matg data: %s'
                             % (len(loose), [hex(x) for x in loose[:4]]))
        if odiff:
            S['fail'].append('(e) owner-tag deep compare: %s' % odiff[:6])
        del old
        gc.collect()
        # (d)
        res2 = pa.apply(new, game, reg)
        w2 = getattr(new, '_player_armour_writes', [])
        S['d'] = [r for r in res2 if r['field'] == 'player armour']
        if w2 or not S['d'] or S['d'][0].get('old') != 'already applied':
            S['fail'].append('(d) second apply wrote %d range(s): %s' % (len(w2), res2[:3]))
        del new
        gc.collect()
    finally:
        try:
            os.remove(dst)
        except OSError:
            pass
    return S


def diff_outside(old, new, writes, cs_off, game):
    import numpy as np
    a = np.frombuffer(old.data, dtype=np.uint8)
    b = np.frombuffer(new.data, dtype=np.uint8)
    n = min(len(a), len(b))
    CH = 1 << 26
    idx = np.concatenate([np.nonzero(a[o:min(n, o + CH)] != b[o:min(n, o + CH)])[0] + o
                          for o in range(0, n, CH)] or [np.zeros(0, dtype=np.int64)])
    allowed = []
    for s, e in sorted(writes + [(cs_off, cs_off + 4)]):          # merge overlapping ranges
        if allowed and s <= allowed[-1][1]:
            allowed[-1] = (allowed[-1][0], max(allowed[-1][1], e))
        else:
            allowed.append((s, e))
    starts = np.array([s for s, e in allowed], dtype=np.int64)
    ends = np.array([e for s, e in allowed], dtype=np.int64)
    if len(idx):
        k = np.searchsorted(starts, idx, side='right') - 1
        ok = (k >= 0) & (idx < ends[np.clip(k, 0, None)])
        bad = idx[~ok]
    else:
        bad = idx
    tail = len(b) - len(a)
    runs = []
    if len(bad):
        cur = [int(bad[0]), int(bad[0])]
        for x in bad[1:]:
            x = int(x)
            if x <= cur[1] + 16:
                cur[1] = x
            else:
                runs.append(tuple(cur))
                cur = [x, x]
        runs.append(tuple(cur))
    if tail and not any(s <= n and e >= len(b) for s, e in writes):
        runs.append(('appended', tail))
    return len(runs), ['%#x-%#x' % r if isinstance(r[0], int) else str(r) for r in runs], int(len(idx)), tail


def summary(S):
    print('=' * 100)
    print('%s  %s   %s' % (S['game'], S['map'], 'PASS' if not S['fail'] else 'FAIL'))
    for r in S.get('apply', []):
        f = r['field']
        if f == 'row':
            continue
        txt = r.get('new') or r.get('reason') or ''
        if f == 'both-rows groups':
            txt = txt[:300] + ('...' if len(txt) > 300 else '')
        print('  %-48s %s%s' % (f[:48], ('%s -> ' % r['old']) if r.get('old') else '', txt))
    if 'a' in S:
        print('  (a) materials %d -> %d (%d clone(s))' % S['a'])
        print('  (b) %d player field(s) repointed %s; %d non-player hlmts unchanged' % (
            S['b'][0], ' '.join('%d->%d' % p for p in S['b'][2]), S['b'][1]))
        ng, npl, nen, nsp, cd, md = S['c']
        print('  (c) %d groups x %d player material(s) + %d enemy material(s) (%d bipeds) + all others: %s'
              % (ng, npl, nen, nsp, 'identical' if not cd else 'CHANGED %s' % cd[:6]))
        if md:
            print('      under "general x specific" the player would differ in: %s' % ', '.join(md))
        print('  (d) second apply: %s' % (S['d'][0].get('new') if S.get('d') else '?'))
        if 'f' in S:
            print('  (f) armour arrays sorted, binary search finds every row: %s' % (
                'yes' if not any(S['f']) else 'NO %s %s' % (S['f'][0][:3], S['f'][1][:3])))
        print('  (e) %d differing byte(s), all inside recorded writes: %s; appended %d B; matg deep compare: %s'
              % (S['e'][2], 'yes' if not S['e'][0] else 'NO %s' % S['e'][1][:4], S['e'][3],
                 'n/a (H2)' if S['deep'] is None else ('equal' if not S['deep'] else S['deep'][:3])))
    if S.get('owners') and any(S['owners']):
        own, loose, odiff = S['owners']
        kinds = {}
        for o in own:
            kinds[o.split(' ')[0]] = kinds.get(o.split(' ')[0], 0) + 1
        print('      rewritten pointers sit in: matg data%s; those tags deep-compare %s'
              % (''.join(', %d %s tag(s)' % (v, k) for k, v in sorted(kinds.items()) if k != 'matg'),
                 'equal' if not odiff else 'DIFFERENT'))
    for f in S['fail']:
        print('  FAIL', f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scratch', default=os.path.join(os.environ.get('TEMP', '.'), 'player_armour_selftest'))
    ap.add_argument('--only', help='run one game only, e.g. "Halo 3"')
    a = ap.parse_args()
    os.makedirs(a.scratch, exist_ok=True)
    allok = True
    for game, rel in MAPS:
        if a.only and game != a.only:
            continue
        S = run(game, rel, a.scratch)
        summary(S)
        allok &= not S['fail']
        sys.stdout.flush()
    print('ALL PASS' if allok else 'SOME FAILED')


if __name__ == '__main__':
    main()
