# h4_scripts.py -- Halo 4 story-flow edits in the COMPILED script tree (hsdt tags), the
# Halo 4 twin of reach_scripts.py. Same technique as hud_titles: statements are a
# Next-linked sibling list, so repointing a predecessor changes what runs; nothing is
# deleted and no expression is added. Halo 4's record is 0x1C with Next at +0x4
# (hud_titles.LAYOUTS['h4']); a datum is (salt << 16) | index.
#
# SKIP MIDNIGHT'S OPENING FLIGHT (m90_sacrifice). The level's start script calls
# f_insertion_index_load (game_insertion_point_get), which dispatches on the index:
#     (if (= s_insertion insertion_index_start)
#         (begin (set_silently b_started true) (ins_trench)))       <- the flight
#     ...
#     (if (= s_insertion insertion_index_crash)
#         (begin (set_silently b_started true) (ins_crash_on_foot)))  <- after it
# ins_crash_on_foot is the level's own insertion for the crash site: it loads the zone
# set, sets the profiles and teleports the players to ps_crash_start_ins (player 1 at
# -826.50, -11.77, -74.43). The edit points the START branch's set_silently at that
# existing (ins_crash_on_foot) call node -- its Next is the terminator, so the branch
# ends there -- and ins_trench never runs. A normal start then begins on foot at the
# crash, which is what choosing that insertion would do.
#
# Both verbs are called from more than one place (ins_trench three times, the crash
# insertion twice), so a call is identified by the dispatcher BRANCH it sits in:
#     call -> the statement before it (set_silently) -> that statement's predecessor is
#     the `begin` NAME record -> the begin CALL group -> its predecessor is the `if`
#     condition group -> the `=` call's arguments name the insertion index.

import hud_titles as ht

T = ht.TERMINATOR


def _scenario_tree(m, block_base, mission):
    for t in m.tags:
        if (isinstance(t, dict) and t.get('class') == 'hsdt' and t.get('base')
                and str(t.get('name', '')).endswith('%s_scenario' % mission)):
            tr = ht.Tree(m, 'Halo 4', block_base, None, container=t['base'])
            return tr if tr.ok() else None
    return None


def _index(tr):
    parent, pred = {}, {}
    for i in range(tr.n):
        r = tr.at(i)
        if r['vtype'] != ht.T_FUNCNAME:
            parent.setdefault(r['child'], []).append(i)
        if r['next'] != T:
            pred.setdefault(r['next'] & 0xFFFF, []).append(i)
    return parent, pred


def _call_groups(tr, verb, parent):
    out = []
    for i in range(tr.n):
        r = tr.at(i)
        if r['vtype'] == ht.T_FUNCNAME and r['string'] == verb:
            out += [p for p in parent.get(i, []) if p != i and tr.at(p)['child'] == i]
    return out


def _stmt_pred(tr, i, pred):
    """The statement before `i` in its block (a call group, not a name record)."""
    p = [x for x in pred.get(i, []) if tr.at(x)['vtype'] != ht.T_FUNCNAME]
    return p[0] if len(p) == 1 else None


def _first_stmts(tr, i, pred):
    """Every first statement reachable walking back from `i`. Usually one; after the
    splice the crash call has TWO predecessors (its own branch and the start branch),
    and it belongs to both."""
    out, todo, seen = set(), [i], set()
    while todo and len(seen) < 256:
        j = todo.pop()
        if j in seen:
            continue
        seen.add(j)
        p = [x for x in pred.get(j, []) if tr.at(x)['vtype'] != ht.T_FUNCNAME]
        if p:
            todo.extend(p)
        else:
            out.add(j)
    return out


def _first_stmt(tr, i, pred):
    firsts = _first_stmts(tr, i, pred)
    return next(iter(firsts)) if len(firsts) == 1 else i


def _cond_strings(tr, first, parent, pred):
    """Argument strings of the `if` condition whose THEN block begins with `first`."""
    for n in pred.get(first, []):
        rn = tr.at(n)
        if rn['vtype'] != ht.T_FUNCNAME or rn['string'] != 'begin':
            continue
        for b in parent.get(n, []):
            if b == n or tr.at(b)['child'] != n:
                continue
            for c in pred.get(b, []):
                rc = tr.at(c)
                if rc is None or rc['vtype'] == ht.T_FUNCNAME:
                    continue
                name = tr.at(rc['child'])
                out, nx = [], name['next'] if name else T
                while nx != T and len(out) < 6:
                    a = tr.at(nx & 0xFFFF)
                    if a is None:
                        break
                    out.append(a['string'])
                    nx = a['next']
                return out
    return []


def _in_branch(tr, g, parent, pred, index_name):
    return any(index_name in _cond_strings(tr, f, parent, pred)
               for f in _first_stmts(tr, g, pred))


def skip_flight(m, mission, block_base):
    """m90_sacrifice: a normal start runs the crash insertion instead of the flight."""
    if mission != 'm90_sacrifice':
        return {'skip': True, 'quiet': True,
                'reason': 'only Midnight has this opening flight'}
    tr = _scenario_tree(m, block_base, mission)
    if tr is None:
        return {'ok': False, 'reason': 'no compiled scenario script'}
    parent, pred = _index(tr)
    crash = [g for g in _call_groups(tr, 'ins_crash_on_foot', parent)
             if _in_branch(tr, g, parent, pred, 'insertion_index_crash')]
    if len(crash) != 1 or tr.at(crash[0])['next'] != T:
        return {'ok': False, 'reason': 'expected one crash-branch ins_crash_on_foot call '
                                       'ending its block, found %d' % len(crash)}
    datum = (tr.at(crash[0])['salt'] << 16) | crash[0]
    # Already applied: some start-branch statement now leads straight to the crash call.
    for p in pred.get(crash[0], []):
        if (tr.at(p)['vtype'] != ht.T_FUNCNAME and tr.at(p)['next'] == datum
                and _in_branch(tr, p, parent, pred, 'insertion_index_start')):
            return {'ok': True, 'reason': 'already applied'}
    starts = [g for g in _call_groups(tr, 'ins_trench', parent)
              if _in_branch(tr, g, parent, pred, 'insertion_index_start')]
    if len(starts) != 1:
        return {'ok': False, 'reason': 'found %d start-branch ins_trench calls' % len(starts)}
    prev = _stmt_pred(tr, starts[0], pred)
    if prev is None:
        return {'ok': False, 'reason': 'no single statement before the start ins_trench'}
    tr.set_next(prev, datum)
    return {'ok': True, 'reason': 'a normal start now runs ins_crash_on_foot'}
