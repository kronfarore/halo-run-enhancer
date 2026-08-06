r"""Cache-side setup for Halo 2 sprint.

Neither Halo has a script verb that changes player speed, so sprint is done in tags,
the same way H1's does it:

  * matg Player Information "Run Forward" is raised by the sprint multiplier, which
    speeds up everyone holding a weapon with no movement penalty;
  * every REAL weapon gets a Forward Movement Penalty that cancels the raise back out,
    so ordinary play is unchanged;
  * the token weapon keeps a penalty of 0, so holding it -- and only it -- is fast.

H2 ships a usable token already: objects\weapons\melee\unarmed\unarmed, the invisible
weapon melee-only characters carry, so unlike H1 nothing has to be authored.

The script hands the token over with unit_add_equipment, which takes a starting
PROFILE resolved by name when scripts are compiled. Rather than add a profile (which
the compiled script could not name), this repoints one the scenario already declares --
by default `wimpy`. "starting profile" and "respawn profile" are used by the engine for
spawn and respawn and must never be borrowed.

    python h2_sprint.py "<map>" --show
    python h2_sprint.py "<map>" --mult 1.5 --profile wimpy
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as hp    # noqa: E402

PROFILES, PES = 0xF8, 0x44          # scnr Player Starting Profile
PROF_PRIMARY = 0x28                 # tagRef: class magic @0x0, datum @0x4
PROF_PRI_LOADED, PROF_PRI_TOTAL = 0x30, 0x32
PROF_SECONDARY = 0x34
PROF_SEC_LOADED, PROF_SEC_TOTAL = 0x3C, 0x3E

RUN_FORWARD = 0x2C                  # matg Player Information
RUN_BACKWARD = 0x30
RUN_SIDEWAYS = 0x34
SNEAK_FORWARD = 0x3C
SIDEWAYS_PENALTY = 0x234            # weap, right after Forward Movement Penalty
# H1 and H2 happen to ship the SAME stock movement values, so H1's tuning transfers
# directly -- unlike the vitality scale, which differs (75 vs 70). Pinned as constants
# rather than read from the map: re-running against an already-patched map would
# otherwise compound the multiplier (3.375 -> 5.06 -> ...).
STOCK_RUN_FORWARD = 2.25
STOCK_RUN_SIDEWAYS = 2.0
STOCK_RUN_BACKWARD = 2.0
STOCK_SNEAK_FORWARD = 0.9
PLAYER_INFO, PIS = 0x130, 0x11C
FWD_PENALTY = 0x230                 # weap
WEAP_FLAGS = 0x12C
# The two flags that make a token weapon behave as a sprint trigger rather than as
# cargo. Without them unit_add_equipment quietly puts the token in the player's pack:
# it needs a free slot to land at all, and even then the player keeps holding the gun
# they had -- so the movement bonus never applies. (Diagnosed by the user against H1's
# sprint weapon, which sets both.)
FLAG_MUST_BE_READIED = 1 << 3        # forces it active, so the engine swaps to it
FLAG_NO_SLOT_COST = 1 << 4           # doesn't occupy a weapon slot, so no free slot needed

TOKEN = 'objects' + chr(92) + 'weapons' + chr(92) + 'melee' + chr(92) + 'unarmed' \
        + chr(92) + 'unarmed'
# Profiles the engine itself uses; borrowing one would change how the player spawns.
RESERVED = ('starting profile', 'respawn profile')


def _player_held(name):
    """Vehicle guns and emplacements share the weap class but are never carried, so
    penalising them would slow turrets for no reason. Mirrors H1's player_held()."""
    low = name.lower()
    return not (low.startswith('objects' + chr(92) + 'vehicles')
                or low.startswith('scenarios' + chr(92))
                or 'turret' in low or 'handheld' in low)


def _player_info(m):
    """Player Information lives on the GLOBALS tag, not the scenario -- resolving it
    from scnr silently reads zeros."""
    g = next((t for t in m.tags if t['class'] == 'matg' and t['base']), None)
    return hp._block_base(m, g['base'] + PLAYER_INFO) if g else None


def _profiles(m, scnr):
    n = m.i32(scnr + PROFILES)
    b = hp._block_base(m, scnr + PROFILES)
    out = []
    for i in range(n if b else 0):
        e = b + i * PES
        out.append((i, e, m.data[e:e + 0x20].split(b'\0')[0].decode('latin-1')))
    return out


def show(map_path):
    m = hp.open_map(map_path, 'Halo 2')
    scnr = hp._scnr_base(m)
    for i, e, name in _profiles(m, scnr):
        print('  profile[%d] %-18s primary=%s' %
              (i, name, hp._tag_name_by_id(m, m.u32(e + PROF_PRIMARY + 4)) or '-'))
    pi = _player_info(m)
    if pi:
        print('  Run Forward = %.3f' % struct.unpack_from('<f', m.data, pi + RUN_FORWARD))
    tok = [t for t in m.tags if t['class'] == 'weap' and t['name'] == TOKEN]
    print('  token weapon in map: %s' % ('yes' if tok else 'NO -- script must reference it'))


def apply(map_path, mult=1.5, profile='wimpy', out_path=None, side='cancel',
          mode='token', allow_reserved=False, run_forward=None, run_sideways=None,
          run_backward=None, sneak_forward=None, penalty=None, token_side=None,
          side_delta=0.2, verbose=True):
    m = hp.open_map(map_path, 'Halo 2')
    scnr = hp._scnr_base(m)

    token = next((t for t in m.tags if t['class'] == 'weap' and t['name'] == TOKEN), None)
    if token is None:
        raise SystemExit('%s is not in this map -- the ability script must reference it '
                         '(objects_delete_by_definition pulls it in)' % TOKEN)

    if profile in RESERVED and not allow_reserved:
        raise SystemExit('%r is used by the engine for spawning; borrow another '
                         '(or pass --allow-reserved: some levels declare no other, and '
                         'borrowing it changes what a respawning co-op player gets)'
                         % profile)
    hit = next((p for p in _profiles(m, scnr) if p[2] == profile), None)
    if hit is None:
        have = ', '.join(repr(p[2]) for p in _profiles(m, scnr))
        raise SystemExit('no starting profile named %r. This map has: %s' % (profile, have))
    _, e, _ = hit
    flags, = struct.unpack_from('<I', m.data, token['base'] + WEAP_FLAGS)
    struct.pack_into('<I', m.data, token['base'] + WEAP_FLAGS,
                     flags | FLAG_MUST_BE_READIED | FLAG_NO_SLOT_COST)
    if verbose:
        print('token flags 0x%08X -> 0x%08X (must be readied + no slot cost)'
              % (flags, flags | FLAG_MUST_BE_READIED | FLAG_NO_SLOT_COST))

    struct.pack_into('<I', m.data, e + PROF_PRIMARY + 4, token['datum'])
    struct.pack_into('<hh', m.data, e + PROF_PRI_LOADED, 0, 0)
    # A secondary would be handed over too and shove the player's real weapon out.
    struct.pack_into('<I', m.data, e + PROF_SECONDARY + 4, 0xFFFFFFFF)
    struct.pack_into('<hh', m.data, e + PROF_SEC_LOADED, 0, 0)
    if verbose:
        print('profile %r -> %s' % (profile, TOKEN))

    pi = _player_info(m)
    if pi is None:
        raise SystemExit('no matg Player Information block on this map')
    # H1 raises Sneak Forward alongside Run Forward; without it, crouched movement is
    # untouched by sprint.
    live, = struct.unpack_from('<f', m.data, pi + RUN_FORWARD)
    if mode == 'token':
        # Leave global movement completely alone and give the boost to the TOKEN as a
        # NEGATIVE forward penalty. Halo 2 evidently blends diagonal movement from the
        # raised Run Forward in a way the per-weapon forward penalty does not fully
        # cancel -- measured in-game: normal weapons strafe/move diagonally too fast,
        # while Halo 1 with the identical arrangement feels right. Touching nothing
        # global sidesteps that entirely.
        struct.pack_into('<f', m.data, pi + RUN_FORWARD, STOCK_RUN_FORWARD)
        struct.pack_into('<f', m.data, pi + SNEAK_FORWARD, STOCK_SNEAK_FORWARD)
        if verbose:
            print('Run Forward %.3f -> %.3f (stock; boost moved onto the token)'
                  % (live, STOCK_RUN_FORWARD))
    else:
        fwd = STOCK_RUN_FORWARD * mult if run_forward is None else run_forward
        snk = STOCK_SNEAK_FORWARD * mult if sneak_forward is None else sneak_forward
        struct.pack_into('<f', m.data, pi + RUN_FORWARD, fwd)
        struct.pack_into('<f', m.data, pi + SNEAK_FORWARD, snk)
        if verbose:
            print('Run Forward %.3f -> %.3f   Sneak Forward -> %.3f' % (live, fwd, snk))
    # side='delta': penalise sideways HARDER than forward (by side_delta) and raise
    # Run Sideways/Backward to match, so each axis still recomputes to its vanilla value
    # with a real weapon in hand. The extra sideways penalty damps the diagonal blend,
    # which is the part the forward penalty alone cannot reach. Not vanilla-exact on the
    # diagonal, but close -- arrived at by in-game tuning, not theory.
    if side == 'delta' and mode != 'token':
        fwd_pen = (1.0 - 1.0 / float(mult)) if penalty is None else penalty
        side_pen = min(fwd_pen + side_delta, 0.95)
        if run_sideways is None:
            run_sideways = STOCK_RUN_SIDEWAYS / (1.0 - side_pen)
        if run_backward is None:
            run_backward = STOCK_RUN_BACKWARD / (1.0 - side_pen)
        if verbose:
            print('side delta %.2f: fwd pen %.3f, side pen %.3f' % (side_delta, fwd_pen, side_pen))

    # Explicit overrides for the two axes that feed diagonal movement. Exposed because
    # the interaction is not predictable from the tag values alone: raising Run Forward
    # inflates diagonal speed in a way the per-weapon penalty does not cancel.
    for off, val, label in ((RUN_SIDEWAYS, run_sideways, 'Run Sideways'),
                            (RUN_BACKWARD, run_backward, 'Run Backward')):
        if val is not None:
            was, = struct.unpack_from('<f', m.data, pi + off)
            struct.pack_into('<f', m.data, pi + off, val)
            if verbose:
                print('%-13s %.3f -> %.3f' % (label, was, val))

    # Cancel the raise for every real weapon. penalty p leaves speed at mult*(1-p), so
    # p = 1 - 1/mult restores exactly normal walking speed with a gun in hand.
    # 'global' mode: everyone is faster, every real weapon pays it back.
    # 'token' mode: nobody is faster, and the token carries a negative penalty, which
    # the field's "percent slowdown" semantics should read as a speed-up.
    if penalty is None:
        penalty = 0.0 if mode == 'token' else 1.0 - 1.0 / float(mult)
    n = 0
    for t in m.tags:
        if t['class'] != 'weap' or t['base'] is None or t['name'] == TOKEN:
            continue
        if not _player_held(t['name']):
            continue
        struct.pack_into('<f', m.data, t['base'] + FWD_PENALTY, penalty)
        # side='cancel' also penalises sideways, on the theory that raising Run Forward
        # speeds up strafing in H2. side='h1' leaves it alone, which is exactly what
        # Halo 1 does -- there only the SPRINT weapon gets a sideways penalty. Kept
        # switchable because the two games evidently blend diagonal movement
        # differently and only in-game comparison settles it.
        if side == 'cancel':
            struct.pack_into('<f', m.data, t['base'] + SIDEWAYS_PENALTY, penalty)
        elif side == 'delta':
            struct.pack_into('<f', m.data, t['base'] + SIDEWAYS_PENALTY,
                             min(penalty + side_delta, 0.95))
        n += 1
    # The token keeps forward at 0 (that IS the sprint) but takes H1's sideways
    # penalty, so sprinting is a forward dash rather than a fast sidestep.
    if token_side is None:
        # Match the real weapons' sideways penalty so strafing WHILE sprinting stays at
        # vanilla speed: sprint is a forward dash, as in Halo 1.
        token_side = min(penalty + side_delta, 0.95) if side == 'delta' else 0.5
    token_fwd = (1.0 - float(mult)) if mode == 'token' else 0.0
    struct.pack_into('<f', m.data, token['base'] + FWD_PENALTY, token_fwd)
    struct.pack_into('<f', m.data, token['base'] + SIDEWAYS_PENALTY, token_side)
    if verbose:
        print('penalty %.3f on %d player weapons; token forward %.3f / sideways 0.5'
              % (penalty, n, token_fwd))

    m.update_checksum()
    m.save(out_path or map_path)
    if verbose:
        print('wrote %s' % (out_path or map_path))


# --- powerup sprint -----------------------------------------------------------
# Far better than the token weapon: eqip "Powerup Type" (0x12C) has an engine option
# 1 = "Double Speed" that Bungie shipped no tag for. Retyping an equipment tag to it
# makes speed a per-player POWERUP delivered by the same create/attach/detach the camo
# ability uses -- so no global Run Forward change (and therefore no diagonal
# inflation), no per-weapon penalties, no borrowed starting profile, and no weapon
# swap (so dual wielding survives).
# over_shield is the tag to repurpose: campaign maps never reference it, so nothing
# else in the level changes behaviour.
POWERUP_TYPE = 0x12C
POWERUP_TIME = 0x130
SPEED_TAG = ('objects' + chr(92) + 'powerups' + chr(92) + 'over_shield'
             + chr(92) + 'over_shield')
PT_DOUBLE_SPEED = 1


def make_speed_powerup(map_path, seconds=4.0, tag=SPEED_TAG, out_path=None, verbose=True):
    m = hp.open_map(map_path, 'Halo 2')
    t = next((x for x in m.tags if x['class'] == 'eqip' and x['name'] == tag), None)
    if t is None:
        raise SystemExit('%s is not in this map -- the ability script must reference it '
                         '(object_type_predict pulls it in)' % tag)
    was_type, = struct.unpack_from('<h', m.data, t['base'] + POWERUP_TYPE)
    was_time, = struct.unpack_from('<f', m.data, t['base'] + POWERUP_TIME)
    struct.pack_into('<h', m.data, t['base'] + POWERUP_TYPE, PT_DOUBLE_SPEED)
    struct.pack_into('<f', m.data, t['base'] + POWERUP_TIME, float(seconds))
    if verbose:
        print('%s: powerup type %d -> %d (Double Speed), time %.1f -> %.1f s'
              % (tag.rsplit(chr(92), 1)[-1], was_type, PT_DOUBLE_SPEED, was_time, seconds))
    m.update_checksum()
    m.save(out_path or map_path)
    return t


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--mult', type=float, default=1.5,
                    help='sprint speed as a multiple of normal run (default 1.5)')
    ap.add_argument('--profile', default='wimpy',
                    help='starting profile to borrow (default wimpy)')
    ap.add_argument('--mode', choices=('token', 'global'), default='token',
                    help="'token' leaves world movement stock and boosts only the "
                         "sprint token (no side effects); 'global' is H1's arrangement")
    ap.add_argument('--side-delta', type=float, default=0.2,
                    help="side='delta' only: how much harder sideways is "
                         "penalised than forward (default 0.2)")
    ap.add_argument('--side', choices=('cancel', 'h1', 'delta'), default='delta',
                    help="'cancel' penalises sideways on normal weapons too; "
                         "'h1' leaves it vanilla, matching Halo 1")
    ap.add_argument('--allow-reserved', action='store_true',
                    help='permit borrowing "starting profile" / "respawn profile" on '
                         'levels that declare no other (test use)')
    ap.add_argument('--run-forward', type=float, help='absolute Run Forward (stock 2.25)')
    ap.add_argument('--run-sideways', type=float, help='absolute Run Sideways (stock 2.0)')
    ap.add_argument('--run-backward', type=float, help='absolute Run Backward (stock 2.0)')
    ap.add_argument('--sneak-forward', type=float, help='absolute Sneak Forward (stock 0.9)')
    ap.add_argument('--penalty', type=float,
                    help='forward penalty on real weapons (default 1 - 1/mult)')
    ap.add_argument('--token-side', type=float, default=0.5,
                    help="token's sideways penalty (default 0.5, as Halo 1)")
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    if a.show:
        show(a.map)
    else:
        apply(a.map, a.mult, a.profile, a.out, a.side, a.mode,
              a.allow_reserved, a.run_forward, a.run_sideways, a.run_backward,
              a.sneak_forward, a.penalty, a.token_side, a.side_delta)


if __name__ == '__main__':
    main()
