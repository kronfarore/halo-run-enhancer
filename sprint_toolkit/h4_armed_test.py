"""Halo 4 Armed-cards ENGINE test (2026-11-19): the questions armed_scope/h4/H4_ARMED_SCOPING.md leaves
to the game, answered on ONE map (Composer, m80_delta) before the module is written. Nothing is taught:
weapons are written straight into the squads, so each question gets a clean answer.

  U1  which cell twin is read      squads with BOTH a designer (+0x54) and a templated (+0x60) cell:
                                   designer -> Fuel Rod, templated -> Rocket Launcher
  U2  type-less / class-less       Grunt spawn points -> DMR, Grunt cells -> SAW (no Grunt type for
                                   either); Jackal spawn points (every 2nd) -> Rocket (no missile class)
  U3  no firing row                Elite spawn points -> Sticky Detonator (no row in any map)
  U6  shield + rifle / no shield   Jackal cells (shield kept) -> BR; every other Jackal spawn point ->
                                   DMR with the 'minor_no_shield' variant
  U9  Elite hammer                 Elite cells -> Gravity Hammer
  allies                           Marines -> Scattershot
U5 (flee drop) is watched on the Grunts. Species stay as shipped; only weapons change.
Test rules: god shield, DMR cheat (secondary of every profile, dmr bullet x1000), run x2.

  python h4_armed_test.py engine [level] -> boot 1's engine test (Composer)
  python h4_armed_test.py [level]        -> boot 2: the SHIPPED pass (Forerunner)   (h4_armed_test.cmd deploy)
"""
import contextlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import halo_patch as hp            # noqa: E402

GAME = 'Halo 4'
BS = chr(92)
BASELINE = r'E:\HaloBaselines\halo4\maps'
MAPS = os.path.join(os.path.dirname(ROOT), 'halo4', 'maps')

SQUADS, SQ_ES, SQ_TEAM = 0x3F0, 0x6C, 0x24
SP, SP_ES, SP_CHAR, SP_WEAP, SP_WEAP2, SP_VAR = 0x3C, 0x7C, 0x2E, 0x30, 0x32, 0x40
CELLS = (('designer', 0x54), ('templated', 0x60))
CELL_ES, CELL_CHARS, CELL_WEAPS, CELL_WEAPS2, ARR_ES, ARR_IDX, CELL_VEH = 0x64, 0xC, 0x18, 0x24, 0x8, 0x4, 0x3E
WPAL, CPAL, PAL_ES, PAL_ID = 0x1BC, 0x444, 0x10, 0xC
PROFILES, PROFILE_ES = 0x310, 0x7C
# the Halo4MCC hlmt plugin (the plain Halo4 set is the 360 layout): Old Damage Info 0xB8 -- body
# vitality +0x14, shield vitality +0x28, shield stun +0x34, recharge time +0x38 (read: 45 / 70 / 7 / 3)
HLMT_ROOT_VITALITY, HLMT_DAMAGE, HLMT_DAMAGE_ES = 0x104, 0xF4, 0xB8
GOD = ((0x14, 1e6), (0x28, 1e6), (0x34, 0.0), (0x38, 0.1))
PLAYER_MODEL = 'objects' + BS + 'characters' + BS + 'storm_masterchief' + BS + 'storm_masterchief'
MATG_PLAYER, MATG_PLAYER_ES = 0x5EC, 0xDC          # Halo4MCC matg Player Information
SPEED_FIELDS = (0x4, 0x8, 0xC, 0x10, 0x14, 0x18, 0x1C, 0x20)
JPT_DAMAGE = (0x38, 0x3C, 0x40)          # lower bound, upper bound (rangef)
NO_SHIELD = 'minor_no_shield'

#: the weapons by palette leaf
W = {'dmr': 'storm_dmr', 'saw': 'storm_lmg', 'rocket': 'storm_rocket_launcher', 'fuelrod': 'storm_fuel_rod_cannon',
     'sticky': 'storm_sticky_detonator_pve', 'br': 'storm_br', 'hammer': 'storm_gravity_hammer',
     'scattershot': 'storm_spread_gun'}


def _i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def _species(name):
    leaf = (name or '').lower().rsplit(BS, 1)[-1]
    for w, s in (('grunt', 'Grunt'), ('jackal', 'Jackal'), ('elite', 'Elite'), ('marine', 'Marine')):
        if w in leaf:
            return s
    return None


def _one(m, blk, idx):
    """A private single weapon element naming palette index `idx` (chance 1)."""
    got = hp._h3_reserve(m, [ARR_ES])
    el = bytearray(ARR_ES)
    struct.pack_into('<hh', el, ARR_IDX, idx, 1)
    struct.pack_into('<H', el, 0, 0)          # difficulty flags: every difficulty
    m.data[got[0]:got[0] + ARR_ES] = el
    struct.pack_into('<iI', m.data, blk, 1, m.off2data(got[0]))


def layout(m, report):
    base = hp._scnr_base(m)
    wnames = [(hp._tag_name_by_id(m, m.u32(e + PAL_ID)) or '').lower().rsplit(BS, 1)[-1]
              for e in m.follow_all(base, [WPAL], [PAL_ES], 'all')]
    cnames = [hp._tag_name_by_id(m, m.u32(e + PAL_ID)) for e in m.follow_all(base, [CPAL], [PAL_ES], 'all')]
    wi = {k: wnames.index(v) for k, v in W.items() if v in wnames}
    for k in W:
        if k not in wi:
            report.append('SKIP %s: not in the weapon palette' % W[k])
    jack = next((b for p, b in m.find_tags('hlmt', '*') if p.lower().endswith(BS + 'storm_jackal')), None)
    nosh = None
    for e in m.follow_all(jack, [0xC4], [0x6C], 'all') if jack is not None else ():
        if (m.resolve_stringid(m.u32(e)) or '').lower() == NO_SHIELD:
            nosh = m.u32(e)
    report.append('jackal variant %s = %s' % (NO_SHIELD, hex(nosh) if nosh else 'MISSING'))
    _bound = set()
    import enemy_count as ec
    try:
        _bound = set(ec.h3_script_refs(m, None, GAME)['bound'])
    except Exception:
        pass
    count, jn = {}, 0

    def tally(k):
        count[k] = count.get(k, 0) + 1
    for sq in m.follow_all(base, [SQUADS], [SQ_ES], 'all'):
        name = bytes(m.data[sq:sq + 32]).split(b'\0')[0].decode('latin-1').lower()
        cells = {kind: m.follow_all(sq, [off], [CELL_ES], 'all') for kind, off in CELLS}
        twin = bool(cells['designer']) and bool(cells['templated'])
        for sp in m.follow_all(sq, [SP], [SP_ES], 'all'):
            if _i16(m, sp + 0x36) >= 0:
                continue                                   # in a vehicle
            c = _i16(m, sp + SP_CHAR)
            if c < 0:
                continue                                   # inherits the cell's (dealt below)
            s = _species(cnames[c] if c < len(cnames) else None)
            pick, var = None, None
            if s == 'Grunt':
                pick = 'dmr'
            elif s == 'Jackal':
                jn += 1
                if jn % 2:
                    pick = 'rocket'
                else:
                    pick, var = 'dmr', nosh
            elif s == 'Elite':
                pick = 'sticky'
            elif s == 'Marine':
                pick = 'scattershot'
            if pick in wi:
                struct.pack_into('<hh', m.data, sp + SP_WEAP, wi[pick], -1)
                if var:
                    struct.pack_into('<I', m.data, sp + SP_VAR, var)
                tally('%s spawn point -> %s%s' % (s, W[pick], ' (no shield)' if var else ''))
        for kind, cs in cells.items():
            for cell in cs:
                if _i16(m, cell + CELL_VEH) >= 0 or m.i32(cell + CELL_WEAPS) <= 0:
                    continue
                chars = [_i16(m, e + ARR_IDX) for e in m.follow_all(cell, [CELL_CHARS], [ARR_ES], 'all')]
                ss = {_species(cnames[c]) if 0 <= c < len(cnames) else None for c in chars}
                if len(ss) != 1:
                    continue
                s = ss.pop()
                if twin and s in ('Grunt', 'Jackal', 'Elite'):
                    pick = 'fuelrod' if kind == 'designer' else 'rocket'
                    label = '%s TWIN %s cell -> %s' % (s, kind, W[pick])
                else:
                    pick = {'Grunt': 'saw', 'Jackal': 'br', 'Elite': 'hammer', 'Marine': 'scattershot'}.get(s)
                    label = '%s %s cell -> %s' % (s, kind, W.get(pick))
                if pick in wi:
                    _one(m, cell + CELL_WEAPS, wi[pick])
                    struct.pack_into('<i', m.data, cell + CELL_WEAPS2, 0)          # no secondary
                    tally(label)
    for k in sorted(count):
        report.append('  %4d  %s' % (count[k], k))


def god_and_cheat(m, report):
    for _n, t in m.find_tags('hlmt', PLAYER_MODEL):
        for e in m.follow_all(t, [HLMT_DAMAGE], [HLMT_DAMAGE_ES], 'all')[:1]:
            for off, v in GOD:
                struct.pack_into('<f', m.data, e + off, v)
        struct.pack_into('<f', m.data, t + HLMT_ROOT_VITALITY, 1e6)
        report.append('god shield: storm_masterchief body + shield 1e6')
    for _n, t in m.find_tags('jpt!', 'objects' + BS + 'weapons' + BS + '*storm_dmr*'):
        for off in JPT_DAMAGE:
            v = struct.unpack_from('<f', m.data, t + off)[0]
            struct.pack_into('<f', m.data, t + off, v * 1000.0)
        report.append('cheat: %s damage x1000' % _n.rsplit(BS, 1)[-1])
    ref = hp._h3_tag_datum(m, 'weap', next(p for p, _b in m.find_tags('weap', '*')
                                           if p.lower().endswith(BS + 'storm_dmr')))
    n = 0
    for pr in m.follow_all(hp._scnr_base(m), [PROFILES], [PROFILE_ES], 'all'):
        if ref is not None and not hp._profile_is_empty(m, pr, GAME):
            hp._write_starting_weapon(m, pr, 'secondary', ref, -1, -1, GAME)
            n += 1
    report.append('cheat: storm_dmr as the secondary of %d profiles' % n)
    for _n, t in m.find_tags('matg', 'globals' + BS + 'globals'):
        for e in m.follow_all(t, [MATG_PLAYER], [MATG_PLAYER_ES], 'all'):
            for off in SPEED_FIELDS:
                v = struct.unpack_from('<f', m.data, e + off)[0]
                struct.pack_into('<f', m.data, e + off, v * 2.0)
            report.append('player run / sneak x2 (run forward now %.3g)' % struct.unpack_from('<f', m.data, e + 4)[0])


def build(level='m80_delta'):
    src = os.path.join(BASELINE, level + '.map')
    out = os.path.join(MAPS, level + '_armed_test.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    report = ['%s from %s' % (os.path.basename(out), src)]
    layout(m, report)
    god_and_cheat(m, report)
    m.save(out)
    print('\n'.join(report))
    return out


#: (boot 2, 2026-11-20) the SHIPPED pass: h3_enemy_weapons.apply exactly as a patch runs it, one
#: weapon per species at 100% so every group is told apart at a glance -- each exercises a new piece:
#: Grunt DMR (taught: a type copied in the AR pose), Jackal Rocket Launcher (taught as the BR +
#: the shieldless clone / major with threshold -1), Elite Sticky Detonator (borrowed Concussion Rifle
#: firing rows), Knight Fuel Rod (taught in the Rocket Launcher pose; the class-'any' actions rule)
SHIPPED_V2 = {'Grunt': 'storm_dmr', 'Jackal': 'storm_rocket_launcher', 'Elite': 'storm_sticky_detonator_pve',
              'Knight': 'storm_fuel_rod_cannon'}
#: boot 2 RESULT (2026-11-21): all four hold and fire (Knight Fuel Rod, Grunt DMR, Elite Sticky Detonator,
#: shieldless Jackal Rocket) -> the shipped Halo 4 pass works. Boot 3: the pairs not yet seen -- the
#: turrets (taught + grip marker), the SAW, the Railgun. (U9 answered offline: the gate itself refuses
#: the hammer for Elites -- their 'any' hammer set has no idle -- matching boot 1's unarmed Elites; it
#: stays EXCLUDED.)
SHIPPED_V3 = {'Grunt': 'storm_lmg', 'Jackal': 'storm_machinegun_turret', 'Elite': 'storm_rail_gun_pve',
              'Knight': 'storm_plasma_turret'}
#: boot 3 RESULT (2026-11-21): Grunt SAW fires but aims UP when firing (the DMR too: the Focus Rifle
#: port lent its pose -> POSE_PREFER_GAMES); Jackal MG Turret holds well + fires; Elite Railgun fires;
#: Knights kept VANILLA weapons with the Plasma Turret (a Weapon List row onto the class's 'any' type --
#: ACTION_ANY now needs a type named for the weapon). Boot 4: Grunt SAW again (the AR pose now),
#: Knight Plasma Turret again (its own type now), Jackal Plasma Turret, Elite Spartan Laser (unseen)
SHIPPED_V4 = {'Grunt': 'storm_lmg', 'Jackal': 'storm_plasma_turret', 'Elite': 'storm_spartan_laser',
              'Knight': 'storm_plasma_turret'}
#: boot 4 RESULT (2026-11-21): Jackal Plasma Turret good; Elite Spartan Laser fires, aims a little off
#: (accepted, user); Grunt SAW unchanged -- level at idle, aims up only when firing (accepted, user);
#: Knights STILL no turret. Both turrets carry weap +0x2A0 bit 8 'Support Weapon', the launchers
#: Knights do carry not. Boot 5 (user: one experiment boot): the Plasma Turret's Support Weapon flag
#: CLEARED on this test map only (knowledge -- shipping it would change the player's turret); the rest
#: unseen pairs
SHIPPED_V5 = {'Grunt': 'storm_forerunner_incineration_launcher', 'Jackal': 'storm_spartan_laser',
              'Elite': 'storm_machinegun_turret', 'Knight': 'storm_plasma_turret'}
#: boot 5 RESULT (2026-11-22): Grunt Incineration Cannon + Jackal Spartan Laser good; Elites point the
#: MG Turret up even at idle (-> REPOSE Elite turrets); SOME Knights carry + fire the Plasma Turret
#: elsewhere in the map -- the flag was never the block: most Knights spawn from spawn points naming
#: their character and weapon -1 (default) in empty cells, which the pass skipped (-> SP_DEFAULT_GAMES).
#: Boot 6: Knight Plasma Turret again (flag as shipped), Elite MG Turret re-posed, unseen pairs
SHIPPED = {'Grunt': 'storm_forerunner_smg', 'Jackal': 'storm_forerunner_sniper_rifle',
           'Elite': 'storm_machinegun_turret', 'Knight': 'storm_plasma_turret'}
CLEAR_SUPPORT = ()                             # boot 5's experiment: weap +0x2A0 bit 8
WEAP_FLAGS2, SUPPORT_BIT = 0x2A0, 1 << 8
HAMMER_TEST = False


def build_shipped(level='m30_cryptum'):
    import h3_enemy_weapons as ew
    src = os.path.join(BASELINE, level + '.map')
    out = os.path.join(MAPS, level + '_armed_test.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    report = ['%s from %s (the shipped Armed pass)' % (os.path.basename(out), src)]
    tags = {p.lower().rsplit(BS, 1)[-1]: p for p, _b in m.find_tags('weap', '*')}
    cards = {e: {tags[w]: 1.0} for e, w in SHIPPED.items() if w in tags}
    for e, w in SHIPPED.items():
        report.append('  %-7s -> %s%s' % (e, w, '' if w in tags else '  (NOT IN THIS MAP)'))
    if HAMMER_TEST:
        ew.EXCLUDED_BY_GAME = dict(ew.EXCLUDED_BY_GAME, **{GAME: ()})       # test only: the hammer goes out
    for r in ew.apply(m, hp, {'cards': cards}, game=GAME):
        report.append('%s%s | %s | %s' % ('' if r.get('ok') else 'FAILED ', r.get('tag'), r.get('field'),
                                         r.get('new') or r.get('reason')))
    for leaf in CLEAR_SUPPORT:
        for p, t in m.find_tags('weap', '*'):
            if p.lower().rsplit(BS, 1)[-1] == leaf:
                v = m.u32(t + WEAP_FLAGS2)
                struct.pack_into('<I', m.data, t + WEAP_FLAGS2, v & ~SUPPORT_BIT)
                report.append('EXPERIMENT: %s Support Weapon flag %s -> cleared' % (leaf, bool(v & SUPPORT_BIT)))
    god_and_cheat(m, report)
    m.save(out)
    print('\n'.join(report))
    return out


if __name__ == '__main__':
    # h4_armed_test.py              -> the shipped pass on Forerunner (boot 2)
    # h4_armed_test.py engine [lvl] -> boot 1's engine test (Composer)
    if len(sys.argv) > 1 and sys.argv[1] == 'engine':
        build(sys.argv[2] if len(sys.argv) > 2 else 'm80_delta')
    else:
        build_shipped(sys.argv[1] if len(sys.argv) > 1 else 'm30_cryptum')
