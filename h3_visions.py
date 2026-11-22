# h3_visions.py -- what is left of Halo 3's Cortana / Gravemind "vision" moments after
# halo3_cutscene.remove_cortana_flicker, removed BY NAME in the compiled script tree
# (record layout: hud_titles.py). Runs under the same option (remove_h3_cutscenes).
#
# The recipe in halo3_cutscene is a list of expression ranges copied from the "Cortana
# Begone" mod and realigned per build. Play session 2026-11-21: on Floodgate, Cortana
# and Halo the effect was not completely gone and the SLOWDOWN stayed. Measured on the
# rebuilt baselines after the recipe ran: the moment scripts still set
# g_gravemind_header / g_cortana_header, still play the cortana_channel screen effect
# (damage_players) and camera_set_briefing, the !..._sc_sh1 sub-scripts still call
# cinematic_scripting_play_cortana_effect, and Cortana keeps its looping effect sound.
#
# The slowdown itself is in the GLOBAL header scripts every map compiles:
#     gs_gravemind_header: player_control_scale_all_input 0.15 2  (+ no damage, ai off)
#     gs_cortana_header:   player_control_scale_all_input 0.15 0.5, damage_players
#                          cortana_effect, gs_hud_flicker_out
# The footers put input back to 1.0, so removing the header's scale, screen effect and
# HUD flicker is safe whether or not a footer runs. Dialogue (the voice lines) is not
# touched by this pass (user, 2026-11-22: keep the voices).

import hud_titles as ht

T = ht.TERMINATOR
HEADERS = ('gs_gravemind_header', 'gs_cortana_header')
HEADER_VERBS = ('player_control_scale_all_input', 'damage_players', 'gs_hud_flicker_out')
EFFECT_VERBS = ('cinematic_scripting_play_cortana_effect', 'camera_set_briefing',
                'damage_players', 'sound_looping_start')


def _owners(t):
    """{expression index: script name} for every expression reachable from a script."""
    m, scnr = t.m, t.scnr
    off, es, ro, _kind = ht.SCRIPTS['Halo 3']
    n = max(0, m.i32(scnr + off))
    base = t.block_base(m, scnr + off) if n else None
    own = {}
    for k in range(n if base else 0):
        e = base + k * es
        name = bytes(m.data[e:e + 0x20]).split(b'\x00')[0].decode('latin-1')
        root = m.u32(e + ro)
        stack, seen = ([root & 0xFFFF] if root != T else []), set()
        while stack:
            i = stack.pop()
            if i in seen or not (0 <= i < t.n):
                continue
            seen.add(i)
            own.setdefault(i, name)
            r = t.at(i)
            if r['next'] != T:
                stack.append(r['next'] & 0xFFFF)
            if r['vtype'] != ht.T_FUNCNAME and not t.primitive(i) and r['value'] != T:
                stack.append(r['value'] & 0xFFFF)
    return own


def _first_string(t, name_rec):
    a = t.at(name_rec['next'] & 0xFFFF) if name_rec['next'] != T else None
    return (a or {}).get('string') or ''


def _wanted(t, i, r, script):
    """Is the call named by record i (verb r['string']) one this pass removes?"""
    verb = r['string']
    if script in HEADERS:
        return verb in HEADER_VERBS
    if verb == 'cinematic_scripting_play_cortana_effect':
        return True
    if verb == 'camera_set_briefing':
        return t.number(t.at(r['next'] & 0xFFFF)) == 1.0      # only the TRUE (on) call
    if verb == 'damage_players':
        return 'cortana_channel' in _first_string(t, r).lower()
    if verb == 'sound_looping_start':
        return 'cortana_effect' in _first_string(t, r).lower()
    return False


def strip_visions(m, block_base, scnr_base):
    """Skip the vision leftovers (see above). {'ok', 'removed', 'stuck', 'by_script'}."""
    t = ht.Tree(m, 'Halo 3', block_base, scnr_base)
    if not t.ok():
        return {'ok': False, 'reason': 'script block unreadable'}
    child_of = {}
    for i in range(t.n):
        child_of.setdefault(t.at(i)['child'], []).append(i)
    own = _owners(t)
    targets = {}
    for i, script in own.items():
        r = t.at(i)
        if r['vtype'] != ht.T_FUNCNAME:
            continue
        if r['string'] not in HEADER_VERBS + EFFECT_VERBS:
            continue
        if not _wanted(t, i, r, script):
            continue
        groups = [p for p in child_of.get(i, []) if ht.is_group(t, p, i)]
        if groups:
            targets[groups[0]] = script
    if not targets:
        return {'ok': True, 'removed': 0, 'stuck': 0, 'by_script': {},
                'reason': 'nothing left of the vision moments'}
    # Live = reachable from a script, re-read each pass: entered() also counts dead
    # predecessors -- nodes the recipe already orphaned still point at these calls.
    done = set()
    for _pass in range(8):
        reach = _owners(t)
        live = [g for g in targets if g in reach]
        if not live:
            break
        moved = 0
        for g in live:
            if ht._skip(t, g):
                done.add(g)
                moved += 1
        if not moved:
            break
    reach = _owners(t)
    stuck = [g for g in targets if g in reach]
    by = {}
    for g in done - set(stuck):
        by[targets[g]] = by.get(targets[g], 0) + 1
    return {'ok': True, 'removed': len(done - set(stuck)), 'stuck': len(stuck),
            'by_script': by}
