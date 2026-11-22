# odst_scripts.py -- ODST story-flow edits in the COMPILED script tree of h100 (Mombasa
# Streets), the same Next-link surgery as hud_titles / reach_scripts / h3_scripts.
#
# SKIP THE TUTORIAL AND HAVE THE MAP FROM THE START (user, play session 2026-11-21).
# The Rookie's opening (the "l100" part of h100) is gated by five campaign-progression
# booleans -- gp_tr_look_complete, gp_tr_health_complete, gp_tr_vision_complete,
# gp_tr_pda_complete, gp_tr_beacon_complete. Bungie left a debug script that sets all
# five: test_training_complete. Three edits:
#   1. l100_mission runs (test_training_complete) right after its first statement --
#      the debug script's root `begin` is spliced into the chain (its own Next is
#      otherwise unused: nothing calls it).
#   2. The "repeat training?" prompt is dropped: with every flag set, solo play would
#      offer it, and accepting it resets the flags (f_l100_retrain_players).
#   3. f_l100_pod_eject's `(if gp_h100_from_mainmenu (player_set_pda_enabled ...))`
#      loses its condition, so the PDA (the map) is on as soon as the pod opens.
# The Superintendent / phone / access story beats stay: enc_roundabout waits on the
# globals they set. The flags persist in the campaign progression (as finishing the
# tutorial would).

import hud_titles as ht
import reach_scripts as RS

T = ht.TERMINATOR
G = 'Halo 3: ODST'


def _scripts(t):
    """{script name: Scripts element base}."""
    m, scnr = t.m, t.scnr
    off, es, ro, _k = ht.SCRIPTS[G]
    n = max(0, m.i32(scnr + off))
    base = t.block_base(m, scnr + off) if n else None
    out = {}
    for k in range(n if base else 0):
        e = base + k * es
        out[bytes(m.data[e:e + 0x20]).split(b'\x00')[0].decode('latin-1')] = e
    return out


def _body(t, script_elem):
    """The top-level statement chain of a script: [group index]."""
    ro = ht.SCRIPTS[G][2]
    root = t.m.u32(script_elem + ro)
    if root == T:
        return [], None
    g = t.at(root & 0xFFFF)
    head = t.at(g['child']) if g else None          # the 'begin' name record
    if not head or head['next'] == T:
        return [], root & 0xFFFF
    chain, x = [], head['next'] & 0xFFFF
    while x is not None and len(chain) < 4096:
        chain.append(x)
        r = t.at(x)
        x = None if r['next'] == T else r['next'] & 0xFFFF
    return chain, root & 0xFFFF


def _subtree_names(t, i, limit=4000):
    """Every function / script name used anywhere under record i."""
    out, stack, seen = set(), [i], set()
    while stack and len(seen) < limit:
        x = stack.pop()
        if x in seen or not (0 <= x < t.n):
            continue
        seen.add(x)
        r = t.at(x)
        if r['vtype'] == ht.T_FUNCNAME and r['string']:
            out.add(r['string'])
        if r['next'] != T and x != i:
            stack.append(r['next'] & 0xFFFF)
        if r['vtype'] != ht.T_FUNCNAME and not t.primitive(x) and r['value'] != T:
            stack.append(r['value'] & 0xFFFF)
    return out


def _dat(t, i):
    return (t.at(i)['salt'] << 16) | i


def skip_tutorial(m, mission, block_base, scnr_base):
    """The three edits above, on h100 only. Idempotent."""
    if mission != 'h100':
        return {'skip': True, 'quiet': True, 'reason': 'the tutorial is in Mombasa Streets'}
    t = ht.Tree(m, G, block_base, scnr_base)
    if not t.ok():
        return {'ok': False, 'reason': 'no compiled scripts'}
    sc = _scripts(t)
    need = ('l100_mission', 'test_training_complete', 'f_l100_pod_eject')
    missing = [n for n in need if n not in sc]
    if missing:
        return {'ok': False, 'reason': 'script(s) not found: %s' % ', '.join(missing)}
    done = []
    # 1. splice test_training_complete in after l100_mission's first statement
    body, _r = _body(t, sc['l100_mission'])
    _tb, troot = _body(t, sc['test_training_complete'])
    if not body or troot is None:
        return {'ok': False, 'reason': 'l100_mission / test_training_complete has no body'}
    if (t.at(body[0])['next'] & 0xFFFF) == troot and t.at(body[0])['next'] != T:
        done.append('training flags already set at start')
    else:
        t.set_next(troot, t.at(body[0])['next'])
        t.set_next(body[0], _dat(t, troot))
        done.append('training flags set at start')
    # 2. the retrain prompt (re-read: the chain now has the spliced begin in it)
    body, _r = _body(t, sc['l100_mission'])
    prompt = [g for g in body if 'f_l100_retrain_players' in _subtree_names(t, g)]
    if prompt:
        if ht._skip(t, prompt[0]):
            done.append('retrain prompt removed')
        else:
            return {'ok': False, 'reason': 'could not remove the retrain prompt'}
    else:
        done.append('retrain prompt already gone')
    # 3. unwrap the PDA enable at pod eject
    pbody, _r = _body(t, sc['f_l100_pod_eject'])
    unwrapped = False
    for k, g in enumerate(pbody):
        r = t.at(g)
        name = t.at(r['child']) if r and not t.primitive(g) else None
        if not name or name['vtype'] != ht.T_FUNCNAME or name['string'] != 'if':
            continue
        cond = t.at(name['next'] & 0xFFFF) if name['next'] != T else None
        then = t.at(cond['next'] & 0xFFFF) if cond and cond['next'] != T else None
        if not then or 'player_set_pda_enabled' not in _subtree_names(t, then['i']):
            continue
        if 'gp_boolean_get' not in _subtree_names(t, cond['i']):
            continue
        if then['next'] != T:
            continue                      # an else branch: not the statement we want
        if k == 0:
            return {'ok': False, 'reason': 'the PDA statement opens its script'}
        t.set_next(then['i'], r['next'])
        t.set_next(pbody[k - 1], _dat(t, then['i']))
        unwrapped = True
        break
    if unwrapped:
        done.append('map (PDA) on at pod exit')
    else:
        done.append('map (PDA) at pod exit already on, or not found')
    return {'ok': True, 'reason': '; '.join(done)}
