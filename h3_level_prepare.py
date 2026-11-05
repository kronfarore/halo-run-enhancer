# h3_level_prepare.py -- stop a third-generation level PRELOADING the next one.
#
# ODST's level scripts call `(game_level_prepare <next level>)` well before the level
# ends: every level's `f_end_scene` does it straight after the level-complete
# achievements, then plays the whole outro cinematic, then `(game_level_advance ...)`;
# the hub's `f_h100_transition_out` does it before a mission's intro. From that call
# on MCC is reading the next map, so a patch written then either fails (Errno 13, the
# file is held open) or is written and ignored (the copy is already in memory).
#
# Removing the call leaves `game_level_advance` to load the level on its own -- which
# is how Halo 3 already works: none of its nine campaign levels calls
# game_level_prepare at all (measured on the pristine baselines, 2026-11-05: their
# script strings hold `game_won` but not the verb). On Halo 3 this pass therefore
# reports Skipped on every level.
#
# Technique: halo3_cutscene's in-place statement skip. Statements in a (begin ...) are
# a Next-linked sibling list, so the call's GROUP is dropped by pointing its one
# predecessor's Next at the group's own Next. No expression is added or removed, the
# string blob is untouched, and only one u32 per call changes. Everything is checked
# before anything is written; anything unexpected refuses the whole level.
#
# Record (0x18): salt u16 @0, opcode u16 @2, value type u16 @4, flags u16 @6,
# next datum u32 @8 ((salt<<16)|index, 0xFFFFFFFF = end), string offset u32 @0xC,
# value u32 @0x10 (a group's first child in the low word).

import struct

VERB = 'game_level_prepare'

# scnr offsets per game: (Scripts block, element size), Script Expressions block,
# Script Strings dataRef. Halo 3 sits 0x40 below ODST throughout; each confirmed by
# finding the verbs in the strings blob (2026-11-05: Halo 3 0x49C has 27760
# expressions on 010 and 0x4DC is empty; ODST the other way round).
LAYOUT = {
    'Halo 3':       {'scripts': (0x3EC, 0x34), 'exprs': 0x49C, 'strings': 0x3D8},
    'Halo 3: ODST': {'scripts': (0x42C, 0x34), 'exprs': 0x4DC, 'strings': 0x418},
}
EXPR_SIZE = 0x18
END = 0xFFFFFFFF
T_SPECIAL, T_FUNCNAME, T_VOID = 1, 2, 4
F_PRIMITIVE = 0x1


def _block(m, off):
    """(count, file offset) of a tagblock at absolute `off`."""
    n = struct.unpack_from('<i', m.data, off)[0]
    ptr = struct.unpack_from('<I', m.data, off + 4)[0]
    return max(0, n), (m.data2off(ptr) if ptr else None)


class _Tree:
    def __init__(self, m, game):
        lay = LAYOUT[game]
        self.m = m
        d = m.data
        s = m.scenario_tag()['base']
        self.n, self.base = _block(m, s + lay['exprs'])
        ss = struct.unpack_from('<i', d, s + lay['strings'])[0]
        sp = struct.unpack_from('<I', d, s + lay['strings'] + 0xC)[0]
        so = m.data2off(sp) if sp else None
        self.blob = bytes(d[so:so + ss]) if so and ss > 0 else b''
        sn, sb = _block(m, s + lay['scripts'][0])
        self.scripts = []                         # (name, root index)
        for i in range(sn if sb else 0):
            e = sb + i * lay['scripts'][1]
            name = bytes(d[e:e + 0x20]).split(b'\0')[0].decode('latin-1')
            root = struct.unpack_from('<I', d, e + 0x24)[0]
            self.scripts.append((name, None if root == END else root & 0xFFFF))

    def rec(self, i):
        salt, op, vt, fl, nx, so, val = struct.unpack_from(
            '<HHHHIII', self.m.data, self.base + i * EXPR_SIZE)
        return dict(salt=salt, op=op, vt=vt, fl=fl, next=nx, str=so, value=val)

    def string(self, off):
        if off >= len(self.blob):
            return None
        e = self.blob.find(b'\0', off)
        return self.blob[off:e if e >= 0 else len(self.blob)].decode('latin-1')

    def datum(self, i):
        return (self.rec(i)['salt'] << 16) | i


def _find(tree):
    """Every live call of VERB as a list of plans, or raises ValueError on anything
    that does not look exactly like the measured shape."""
    if not tree.base or not tree.n:
        return []
    recs = [tree.rec(i) for i in range(tree.n)]
    names = [i for i, r in enumerate(recs)
             # a function-name node carries flags 9: the primitive bit IS set on it
             if r['salt'] and r['vt'] == T_FUNCNAME and tree.string(r['str']) == VERB]
    if not names:
        return []
    by_child = {}                                   # group whose first child is i
    by_next = {}                                    # expressions whose Next is datum
    for i, r in enumerate(recs):
        if not r['salt']:
            continue
        if not (r['fl'] & F_PRIMITIVE) and r['vt'] not in (T_SPECIAL, T_FUNCNAME):
            by_child.setdefault(r['value'] & 0xFFFF, []).append(i)
        if r['next'] != END:
            by_next.setdefault(r['next'], []).append(i)
    roots = {root for _n, root in tree.scripts if root is not None}
    script_of = {}
    plans = []
    for nm in names:
        groups = by_child.get(nm, [])
        if len(groups) != 1:
            raise ValueError('%s name node %d has %d call groups' % (VERB, nm, len(groups)))
        g = groups[0]
        gr = recs[g]
        if gr['vt'] != T_VOID:
            raise ValueError('%s call %d has value type %d, not void' % (VERB, g, gr['vt']))
        if gr['op'] != recs[nm]['op']:
            raise ValueError('%s call %d: group opcode %d != name opcode %d'
                             % (VERB, g, gr['op'], recs[nm]['op']))
        if g in roots:
            raise ValueError('%s call %d is a script root' % (VERB, g))
        preds = by_next.get(tree.datum(g), [])
        if not preds:
            plans.append(dict(group=g, pred=None, done=True))   # already unlinked
            continue
        if len(preds) != 1:
            raise ValueError('%s call %d has %d predecessors' % (VERB, g, len(preds)))
        p = preds[0]
        if gr['next'] == END and recs[p]['vt'] == T_FUNCNAME:
            raise ValueError('%s call %d is the only statement of its block' % (VERB, g))
        if gr['next'] != END and (gr['next'] & 0xFFFF) >= tree.n:
            raise ValueError('%s call %d: Next points outside the block' % (VERB, g))
        plans.append(dict(group=g, pred=p, new_next=gr['next'], done=False))
    # name the scripts for the report: walk back from each group to a root
    for pl in plans:
        i, guard = pl['group'], 0
        while i not in roots and guard < 4096:
            back = by_next.get(tree.datum(i)) or by_child.get(i)
            if not back:
                break
            i, guard = back[0], guard + 1
        pl['script'] = next((n for n, r in tree.scripts if r == i), '?')
    return plans


def remove_level_prepare(m, game):
    """Drop every live `game_level_prepare` statement from an open Halo 3 / ODST map
    (in memory; the caller saves). Returns a report dict:

      ok      False on a refusal (nothing written, `reason` says why)
      calls   how many calls the level has
      edits   how many links were rewritten (0 = nothing to do)
      scripts the scripts the calls sit in
    """
    game = str(game).strip()
    rep = {'ok': False, 'calls': 0, 'edits': 0, 'scripts': []}
    if game not in LAYOUT:
        rep['reason'] = 'not a Halo 3 / ODST map'
        return rep
    try:
        tree = _Tree(m, game)
        plans = _find(tree)
    except ValueError as e:
        rep['reason'] = str(e)
        return rep
    rep['calls'] = len(plans)
    rep['scripts'] = sorted({p['script'] for p in plans})
    for p in plans:
        if p['done']:
            continue
        off = tree.base + p['pred'] * EXPR_SIZE + 0x8
        struct.pack_into('<I', m.data, off, p['new_next'])
        rep['edits'] += 1
    rep['ok'] = True
    return rep


def live_calls(m, game):
    """How many game_level_prepare calls are still on a live chain (for checks)."""
    plans = _find(_Tree(m, str(game).strip()))
    return sum(1 for p in plans if not p['done'])


def result_row(rep):
    """The patch-log row for a report from remove_level_prepare."""
    row = {'tag': 'scnr', 'field': 'level script', 'effect': 'No next-level preload'}
    if not rep.get('ok'):
        row.update(ok=False, reason=rep.get('reason', 'script edit failed'))
    elif rep['calls'] == 0:
        row.update(ok=True, skip=True,
                   reason='this level never preloads the next one')
    elif rep['edits'] == 0:
        row.update(ok=True, skip=True, reason='the preload is already removed')
    else:
        row.update(ok=True, old='preloads the next level',
                   new='removed %d call(s) (%s)' % (rep['edits'], ', '.join(rep['scripts'])))
    return row


if __name__ == '__main__':
    import argparse
    import halo_patch as HP
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('map')
    ap.add_argument('--game', default='Halo 3: ODST', choices=sorted(LAYOUT))
    ap.add_argument('--out', help='write the patched map here')
    a = ap.parse_args()
    mm = HP.open_map(a.map, a.game)
    r = remove_level_prepare(mm, a.game)
    print(r, result_row(r))
    if a.out and r['ok']:
        mm.save(a.out)
        print('saved', a.out)
