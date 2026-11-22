# h3_scripts.py -- Halo 3 story-flow edits in the COMPILED script tree (record layout:
# hud_titles.py; call lookup: reach_scripts.py).
#
# KEEP THE LOADOUT THROUGH THE GUILTY SPARK FIGHT. Halo (120) re-arms every player
# after the fight, in cin_halo_activation:
#     (if (= (game_insertion_point_get) 0)
#         (begin (unit_add_equipment (player0..3) post_spark_fight TRUE TRUE))
#         (begin (unit_add_equipment (player0..3) teleport_profile TRUE TRUE)))
# with the reset flag (third argument) set, which throws away what the players carried
# (post_spark_fight = an Assault Rifle and no grenades; play session 2026-11-21).
# Only the insertion-0 branch is edited: teleport_profile is also what the trench-run
# insertion itself starts the players with (ins_trench_run), so it stays vanilla.
# Each branch is four calls and nothing else, and a block's last statement cannot be
# orphaned (hud_titles._skip), so the calls stay and lose their reset instead: the
# flag constant goes TRUE -> FALSE here, and halo_patch empties the profile, so
# the call adds nothing to the weapons the players already hold.

import hud_titles as ht
import reach_scripts as RS

PLAYERS = RS.PLAYERS
LOADOUT_RESETS = {'120_halo': ('post_spark_fight',)}


def keep_loadout(m, mission, block_base, scnr_base):
    """Clear the reset flag on the mid-mission re-arm calls in LOADOUT_RESETS. The
    profiles it names must be emptied as well (halo_patch does that)."""
    profiles = LOADOUT_RESETS.get(mission)
    if not profiles:
        return {'skip': True, 'quiet': True,
                'reason': 'no mid-mission loadout reset on this mission'}
    t = ht.Tree(m, 'Halo 3', block_base, scnr_base)
    if not t.ok():
        return {'skip': True, 'reason': 'no compiled scripts'}
    parent, _pred = RS._index(t)

    def player(r):
        # Halo 3 writes the unit as a call, `(player0)`: a group whose child is the
        # function name (Reach's tree stores the bare name)
        if r['string'] in PLAYERS:
            return True
        c = t.at(r['child']) if not t.primitive(r['i']) else None
        return bool(c) and c['vtype'] == ht.T_FUNCNAME and c['string'] in PLAYERS

    calls = [(g, a) for g, a in RS._calls(t, 'unit_add_equipment', parent)
             if len(a) >= 3 and a[1]['string'] in profiles and player(a[0])]
    if not calls:
        return {'ok': False, 'reason': 'no reset call found for %s' % ', '.join(profiles)}
    flags = [a[2] for _g, a in calls]
    if any(f['vtype'] != ht.T_BOOL or not t.primitive(f['i']) for f in flags):
        return {'ok': False, 'reason': 'a reset argument is not a boolean constant'}
    live = [f for f in flags if f['value'] & 0xFF]
    for f in live:
        t.set_value(f['i'], f['value'] & 0xFFFFFF00)
    return {'ok': True, 'found': len(calls), 'cleared': len(live), 'profiles': profiles,
            'reason': ('reset cleared on %d of %d re-arm call(s) (%s)'
                       % (len(live), len(calls), ', '.join(profiles))) if live else
                      'already applied: %d re-arm call(s) keep the loadout' % len(calls)}
