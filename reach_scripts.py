# reach_scripts.py -- two Reach story-flow edits, made in the COMPILED script tree the
# way hud_titles.py keeps the HUD up. See that module for the record layout; the short
# version is that statements in a block are a Next-linked sibling list, so a statement
# is removed by repointing its predecessor past it and nothing is ever deleted.
#
# 1. KEEP THE LOADOUT THROUGH TRAVEL SECTIONS. Two missions re-apply a starting profile
#    halfway through with its reset flag set -- `(unit_add_equipment playerN <profile>
#    TRUE FALSE)` -- which throws away whatever the players were carrying:
#        m10 Winter Contingency   profile_outpost      after the ride to the outpost
#        m35 Tip of the Spear     profile_spire        after the Falcon ride to the spire
#                                 profile_full_health  the cinematic set-up before it
#    Skipping those statements keeps the weapons (and armour ability) the players had.
#    The mission-START grants (profile_coop_starting and the like) are left alone.
#    Seen but deliberately NOT touched: m50's profile_jetpack (it is what hands out the
#    jetpacks), m50's profile_starting inside allegiance_broken_ride (a betrayal
#    penalty), and m60's v_profile (the co-op teleport into the vehicle section).
#
# 2. SKIP LONG NIGHT OF SOLACE'S SPACE SECTION (m45). The mission's startup script wakes
#    each encounter in turn and lets any encounter be skipped by raising
#    s_insertion_index past it -- that is how the "Corvette" insertion point starts
#    the level on foot inside the corvette. Its insertion script, ins_comms, sets the
#    index to the comms encounter, switches to the corvette's zone set and teleports
#    the players there. So when the players board the Sabre (lnc_boarding_control), the
#    blast-off cinematic is replaced by a call to ins_comms: the wafer, warp, corvette
#    and landing encounters are then passed over and the comms encounter wakes. The
#    call reuses the compiled (ins_comms) node the `start` script already has; its Next
#    is the terminator, so the boarding script ends right after it.

import hud_titles as ht

T = ht.TERMINATOR
PLAYERS = ('player0', 'player1', 'player2', 'player3')
LOADOUT_RESETS = {
    'm10': ('profile_outpost',),
    'm35': ('profile_spire', 'profile_full_health'),
}


def _tree(m, block_base, scnr_base):
    t = ht.Tree(m, 'Halo Reach', block_base, scnr_base)
    return t if t.ok() else None


def _index(t):
    """(name index -> [group indices], target index -> [predecessor indices])"""
    parent, pred = {}, {}
    for i in range(t.n):
        r = t.at(i)
        if r['vtype'] != ht.T_FUNCNAME:
            parent.setdefault(r['child'], []).append(i)
        if r['next'] != T:
            pred.setdefault(r['next'] & 0xFFFF, []).append(i)
    return parent, pred


def _calls(t, verb, parent):
    """[(group index, [argument records])] for every call of `verb`."""
    out = []
    for i in range(t.n):
        r = t.at(i)
        if r['vtype'] != ht.T_FUNCNAME or r['string'] != verb:
            continue
        groups = [p for p in parent.get(i, []) if p != i and t.at(p)['child'] == i]
        if not groups:
            continue
        args, nx = [], r['next']
        while nx != T and len(args) < 8:
            a = t.at(nx & 0xFFFF)
            if a is None:
                break
            args.append(a)
            nx = a['next']
        out.append((groups[0], args))
    return out


def keep_loadout(m, mission, block_base, scnr_base):
    """Skip the mid-mission profile resets listed in LOADOUT_RESETS."""
    profiles = LOADOUT_RESETS.get(mission)
    if not profiles:
        return {'skip': True, 'quiet': True,
                'reason': 'no mid-mission loadout reset on this mission'}
    t = _tree(m, block_base, scnr_base)
    if t is None:
        return {'skip': True, 'reason': 'no compiled scripts'}

    def resets():
        parent, _pred = _index(t)
        return [g for g, a in _calls(t, 'unit_add_equipment', parent)
                if len(a) >= 2 and a[0]['string'] in PLAYERS and a[1]['string'] in profiles]

    found = resets()
    # To a fixed point: the calls are adjacent siblings, and skipping one can leave its
    # orphan still pointing at the next, which _skip may rewire instead (hud_titles).
    for _pass in range(8):
        live = [g for g in found if t.entered(g)]
        if not live:
            break
        for g in live:
            ht._skip(t, g)
    left = [g for g in found if t.entered(g)]
    return {'ok': not left, 'found': len(found), 'removed': len(found) - len(left),
            'profiles': profiles}


def skip_space(m, mission, block_base, scnr_base):
    """m45: boarding the Sabre goes straight to the corvette interior (see above)."""
    if mission != 'm45':
        return {'skip': True, 'quiet': True,
                'reason': 'only Long Night of Solace has a space section'}
    t = _tree(m, block_base, scnr_base)
    if t is None:
        return {'skip': True, 'reason': 'no compiled scripts'}
    parent, pred = _index(t)
    ins = [g for g, _a in _calls(t, 'ins_comms', parent)]
    blast = [g for g, a in _calls(t, 'f_play_cinematic_advanced', parent)
             if a and a[0]['string'] == '045la_blastoff']
    enter = [g for g, a in _calls(t, 'cinematic_enter', parent)
             if a and a[0]['string'] == '045la_blastoff']
    if len(ins) != 1 or len(blast) != 1:
        return {'ok': False, 'reason': 'expected one ins_comms call and one blast-off '
                                       'cinematic, found %d and %d' % (len(ins), len(blast))}
    g_ins, g_blast = ins[0], blast[0]
    if t.at(g_ins)['next'] != T:
        return {'ok': False, 'reason': 'the ins_comms call is not the end of its block'}
    datum = (t.at(g_ins)['salt'] << 16) | g_ins
    if not t.entered(g_blast) and any(
            t.at(p)['next'] == datum and t.at(p)['vtype'] != ht.T_FUNCNAME
            for p in pred.get(g_ins, [])):
        return {'ok': True, 'reason': 'already applied'}
    live = [p for p in pred.get(g_blast, []) if t.entered(p)]
    if len(live) != 1:
        return {'ok': False, 'reason': 'blast-off cinematic has %d predecessors' % len(live)}
    t.set_next(live[0], datum)
    # No cinematic follows any more, so do not enter one (it would fade the screen out
    # and leave the players in cinematic mode with nothing to bring them back).
    for g in enter:
        ht._skip(t, g)
    return {'ok': True, 'reason': 'boarding the Sabre now runs ins_comms'}
