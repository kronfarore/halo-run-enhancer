r"""h3_armed_test.py -- the first Halo 3 Armed-card boot (2026-11-02, ARMED_ALL_GAMES.md).

Builds halo3\maps\<level>_armed_test.map from the patcher BASELINE (E:\HaloBaselines) with:

  * THE TEST LAYOUT (the Armed-test rule: every case at once at the start): the starting
    locations of the hostile on-foot squads nearest the first player start are dealt the
    ENEMY cases below round robin, PER_CASE locations each; the nearest friendly Marine squads
    get the MARINE cases. Each location gets its character, weapon, secondary -1 and variant
    (Jackals: 'shieldless' for two-handed, cleared otherwise) written; the fire-team gets its
    first location's character and weapon (its extras past the locations spawn as that case).
  * REFUSED cases are FORCED in (the Armed pass would never hand them out): they answer what a
    unit does with a weapon its graph cannot hold -- unarmed, or its default weapon?
  * the borrowed firing data (h3_enemy_weapons.borrow_firing: ODST Magnum <- Magnum, Silenced SMG
    <- SMG, Brute Plasma Rifle <- Plasma Rifle);
  * the god shield (masterchief hlmt: body + shield 1e6, no shield stun, 0.1 s recharge), the
    cheat (Covenant Carbine as every profile's secondary, carbine_slug damage x1000) and the
    player's run / sneak speeds x2.

    python sprint_toolkit/h3_armed_test.py [level]          (default 010_jungle)
    sprint_toolkit\h3_armed_test.cmd deploy | restore [level]
"""
import contextlib
import io
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import halo_patch as hp            # noqa: E402
import h3_enemy_weapons as ew      # noqa: E402

BS = chr(92)
GAME = 'Halo 3'
BASELINE = r'E:\HaloBaselines\halo3\maps'
MAPS = os.path.join(os.path.dirname(ROOT), 'halo3', 'maps')
W = 'objects' + BS + 'weapons' + BS
C = 'objects' + BS + 'characters' + BS


def _w(p):
    return W + p.replace('/', BS)


def _c(s):
    return C + s + BS + 'ai' + BS + s


#: (label, character, weapon, forced): forced = the gate refuses it, written anyway
#: v3 (2026-11-03): boots 1-2 confirmed the stock pairs, refused = unarmed, Jackal shields; v3 tests
#: the TAUGHT weapons (h3_enemy_weapons.teach: Weapon List re-class to a donor's class)
#: v4 (boot 5, 2026-11-05): the GRIP markers (h3_enemy_weapons.grip) for the weapons that pointed
#: skyward; the Grunt Machine Gun Turret is NATIVE (no teaching, no grip): the control
ENEMY_CASES = (
    ('Grunt + Flamethrower (grip)', _c('grunt'), _w('turret/flamethrower/flamethrower'), True),
    ('Grunt + Missile Pod (grip)', _c('grunt'), _w('turret/missile_pod/missile_pod'), True),
    ('Grunt + Machine Gun Turret (native, control)', _c('grunt'), _w('turret/machinegun_turret/machinegun_turret'), False),
    ('Jackal + Brute Shot (grip)', _c('jackal'), _w('support_low/brute_shot/brute_shot'), True),
    ('Jackal + Machine Gun Turret (grip)', _c('jackal'), _w('turret/machinegun_turret/machinegun_turret'), True),
    ('Jackal + Plasma Cannon (grip)', _c('jackal'), _w('turret/plasma_cannon/plasma_cannon'), True),
    ('Jackal + Flamethrower (grip)', _c('jackal'), _w('turret/flamethrower/flamethrower'), True),
)
MARINE_CASES = (
    ('Marine + Brute Shot (grip)', _c('marine'), _w('support_low/brute_shot/brute_shot'), True),
    ('Marine + Machine Gun Turret (pose, confirmed)', _c('marine'), _w('turret/machinegun_turret/machinegun_turret'), True),
)
PER_CASE = 2
#: the shield case keeps its shield on purpose (the open question: a shielded Jackal with a rifle)
KEEP_SHIELD = ()

PSTART, PSTART_ES = 0x24C, 0x18
PROFILES, PROFILE_ES = 0x240, 0x58
LOC_POS, LOC_VEHICLE, FT_VEHICLE = 0x8, 0x30, 0x12
HLMT_DAMAGE, HLMT_DAMAGE_ES = 0x88, 0xA4
GOD = ((0xC, 1e6), (0x20, 1e6), (0x2C, 0.0), (0x30, 0.1))
CHEAT_WEAPON = _w('rifle/covenant_carbine/covenant_carbine')
CHEAT_DAMAGE = CHEAT_WEAPON.rsplit(BS, 1)[0] + BS + 'damage_effects' + BS + 'carbine_slug'
CHEAT_DAMAGE_FIELDS = ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')
MATG_PLAYER, MATG_PLAYER_ES = 0x434, 0xC0
SPEED_FIELDS = (0x4, 0x8, 0xC, 0x10, 0x14, 0x18, 0x1C, 0x20)     # run / sneak + accelerations


def _i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def layout(m, report):
    base = hp._scnr_base(m)
    ps = m.follow_all(base, [PSTART], [PSTART_ES], 'all')
    p0 = struct.unpack_from('<fff', m.data, ps[0])
    wnames = [(hp._tag_name_by_id(m, m.u32(e + ew.WPAL_ID)) or '').lower()
              for e in m.follow_all(base, [ew.WPAL], [ew.WPAL_ES], 'all')]
    cpal = m.follow_all(base, [ew.CPAL], [ew.CPAL_ES], 'all')
    ids = [m.u32(e + ew.CPAL_ID) for e in cpal]
    cnames = [hp._tag_name_by_id(m, i) if i != 0xFFFFFFFF else None for i in ids]
    friends, char_team = hp._player_friends(m, GAME, cnames, ids)
    sid = ew.find_variant(m, hp, 'shieldless')

    def idx(lst, name):
        name = name.lower()
        return next((i for i, n in enumerate(lst) if (n or '').lower() == name), None)

    hostile, friendly = [], []
    for sq in m.follow_all(base, [ew.SQUADS], [ew.SQ_ES], 'all'):
        steam = _i16(m, sq + ew.SQ_TEAM)
        for ft in m.follow_all(sq, [ew.FT], [ew.FT_ES], 'all'):
            if _i16(m, ft + FT_VEHICLE) >= 0:
                continue
            fc = _i16(m, ft + ew.FT_CHAR)
            locs = [l for l in m.follow_all(ft, [ew.LOCS], [ew.LOC_ES], 'all')
                    if _i16(m, l + LOC_VEHICLE) < 0]
            if not locs:
                continue
            chars = [c for c in [fc] + [_i16(m, l + ew.LOC_CHAR) for l in locs] if c >= 0]
            types = set(ew.enemy_of(cnames[c]) if c < len(cnames) else None for c in chars)
            if None in types or not types:
                continue                     # story characters, Hunters, vehicles ...
            team = steam if steam > 0 else (char_team[chars[0]] if chars[0] < len(char_team) else None)
            d = min(math.dist(p0, struct.unpack_from('<fff', m.data, l + LOC_POS)) for l in locs)
            name = bytes(m.data[sq:sq + 32]).split(b'\0')[0].decode('latin-1')
            entry = (d, name, sq, ft, locs, team)
            if team in friends:
                if types == {'Marine'}:
                    friendly.append(entry)
            elif 'Marine' not in types:
                hostile.append(entry)

    def deal(cands, cases):
        usable = []
        for label, ch, wp, forced in cases:
            ci, wi = idx(cnames, ch), idx(wnames, wp)
            if ci is None or wi is None:
                report.append('  SKIP %s: %s not in this level\'s palette'
                              % (label, 'character' if ci is None else 'weapon'))
                continue
            usable.append((label, ch, ci, wp, wi, forced))
        k, need, placed = 0, PER_CASE * len(usable), {}
        for d, name, sq, ft, locs, team in sorted(cands, key=lambda x: x[0]):
            if k >= need:
                break
            got = []
            for n, l in enumerate(locs):
                if k >= need:
                    break
                label, ch, ci, wp, wi, forced = usable[k % len(usable)]
                struct.pack_into('<hhh', m.data, l + ew.LOC_CHAR, ci, wi, -1)
                v = 0
                if 'jackal' in ch and sid is not None and label not in KEEP_SHIELD:
                    v = sid if ew.two_handed(m, hp, ew.weapon_info(m, wnames[wi])) else 0
                struct.pack_into('<I', m.data, l + ew.LOC_VARIANT, v)
                if n == 0:
                    struct.pack_into('<hhh', m.data, ft + ew.FT_CHAR, ci, wi, -1)
                placed[label] = placed.get(label, 0) + 1
                got.append(label.split(' (')[0])
                k += 1
            if team is not None and team > 0:
                struct.pack_into('<h', m.data, sq + ew.SQ_TEAM, team)   # keep its side
            report.append('  %-28s %5.0f wu  %s' % (name, d, ', '.join(got)))
        for label, *_r in usable:
            if placed.get(label, 0) < PER_CASE:
                report.append('  SHORT %s: %d of %d locations' % (label, placed.get(label, 0), PER_CASE))

    report.append('enemy squads (nearest the start first):')
    deal(hostile, ENEMY_CASES)
    report.append('friendly Marine squads:')
    deal(friendly, MARINE_CASES)
    if sid is None:
        report.append('  NOTE: no shieldless variant id in this map -- Jackals keep the shield')


def all_jackals(m, report):
    """v2 (user's first boot 2026-11-03: the first Jackals met had their vanilla weapons and
    shields): EVERY Jackal location / fire-team in the level is dealt the three Jackal cases
    round robin, so whichever Jackal shows up first is a test case."""
    base = hp._scnr_base(m)
    wnames = [(hp._tag_name_by_id(m, m.u32(e + ew.WPAL_ID)) or '').lower()
              for e in m.follow_all(base, [ew.WPAL], [ew.WPAL_ES], 'all')]
    cnames = [(hp._tag_name_by_id(m, m.u32(e + ew.CPAL_ID)) or '').lower()
              for e in m.follow_all(base, [ew.CPAL], [ew.CPAL_ES], 'all')]
    sid = ew.find_variant(m, hp, 'shieldless')
    cases = [(lb, wnames.index(wp.lower())) for lb, ch, wp, _f in ENEMY_CASES
             if 'jackal' in ch and wp.lower() in wnames]
    if not cases:
        return
    jack = [i for i, n in enumerate(cnames) if ew.enemy_of(n) == 'Jackal']
    k, by = 0, {}
    for sq in m.follow_all(base, [ew.SQUADS], [ew.SQ_ES], 'all'):
        for ft in m.follow_all(sq, [ew.FT], [ew.FT_ES], 'all'):
            fc = _i16(m, ft + ew.FT_CHAR)
            if fc in jack:
                struct.pack_into('<hh', m.data, ft + ew.FT_WEAP, cases[0][1], -1)
            for l in m.follow_all(ft, [ew.LOCS], [ew.LOC_ES], 'all'):
                lc = _i16(m, l + ew.LOC_CHAR)
                if (lc if lc >= 0 else fc) not in jack:
                    continue
                label, wi = cases[k % len(cases)]
                k += 1
                struct.pack_into('<hh', m.data, l + ew.LOC_WEAP, wi, -1)
                two = ew.two_handed(m, hp, ew.weapon_info(m, wnames[wi]))
                struct.pack_into('<I', m.data, l + ew.LOC_VARIANT,
                                 sid if sid is not None and two and label not in KEEP_SHIELD else 0)
                by[label] = by.get(label, 0) + 1
    report.append('every Jackal in the level: ' + ', '.join('%s x%d' % kv for kv in sorted(by.items()))
                  + ' (Jackal fire-teams: %s, their extras keep the shield)' % cases[0][0])


def god_and_cheat(m, report):
    for _n, t in m.find_tags('hlmt', C + 'masterchief' + BS + 'masterchief'):
        for e in m.follow_all(t, [HLMT_DAMAGE], [HLMT_DAMAGE_ES], 'all')[:1]:
            for off, v in GOD:
                struct.pack_into('<f', m.data, e + off, v)
            report.append('god shield: masterchief body + shield 1e6, no shield stun')
    import ai_firing_profile as A
    jpt = A._plugins()(GAME).get('jpt!')
    for _n, t in m.find_tags('jpt!', CHEAT_DAMAGE):
        for f in CHEAT_DAMAGE_FIELDS:
            fld = jpt.find(f, None, 0) if jpt else None
            if fld and not fld['block_offsets']:
                o = t + fld['offset']
                v = struct.unpack_from('<f', m.data, o)[0]
                struct.pack_into('<f', m.data, o, v * 1000.0)
                report.append('cheat: carbine_slug %s %.3g -> %.4g' % (f, v, v * 1000.0))
    ref = hp._h3_tag_datum(m, 'weap', CHEAT_WEAPON)
    base = hp._scnr_base(m)
    if ref is not None:
        for pr in m.follow_all(base, [PROFILES], [PROFILE_ES], 'all'):
            if hp._profile_is_empty(m, pr, GAME):
                continue
            hp._write_starting_weapon(m, pr, 'secondary', ref, -1, -1, GAME)
            report.append('cheat: profile %s secondary = covenant_carbine'
                          % bytes(m.data[pr:pr + 32]).split(b'\0')[0].decode('latin-1'))
    for _n, t in m.find_tags('matg', 'globals' + BS + 'globals'):
        for e in m.follow_all(t, [MATG_PLAYER], [MATG_PLAYER_ES], 'all'):
            for off in SPEED_FIELDS:
                v = struct.unpack_from('<f', m.data, e + off)[0]
                struct.pack_into('<f', m.data, e + off, v * 2.0)
            report.append('player run / sneak x2 (run forward now %.3g)'
                          % struct.unpack_from('<f', m.data, e + 4)[0])


def build(level='010_jungle'):
    src = os.path.join(BASELINE, level + '.map')
    out = os.path.join(MAPS, level + '_armed_test.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    report = ['%s from %s' % (os.path.basename(out), src)]
    layout(m, report)
    all_jackals(m, report)
    # teach the cases' weapons exactly as the Armed pass does
    # (only the pairs the gate refuses, as the pass does: a native pair stays the control)
    want, graphs = {}, ew.Graphs(m, hp)
    for cases in (ENEMY_CASES, MARINE_CASES):
        for _l, ch, wp, _f in cases:
            wi = ew.weapon_info(m, wp)
            if wi and not graphs.allows(ew.enemy_of(ch), wi['class'], wi['name']):
                want.setdefault(ew.enemy_of(ch), set()).add(wp)
    taught, trows = ew.teach(m, hp, graphs, {e: sorted(w) for e, w in want.items()})
    for r in trows:
        report.append('teach: %s %s %s' % (r['tag'], r['field'], r.get('new') or r.get('reason')))
    handed = sorted(set(wp for cases in (ENEMY_CASES, MARINE_CASES) for _l, _c2, wp, _f in cases))
    for r in ew.borrow_firing(m, hp, handed):
        report.append('firing data: %s %s %s' % (r['tag'], r['field'], r.get('new') or r.get('reason')))
    god_and_cheat(m, report)
    m.save(out)
    print('\n'.join(report))
    return out


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else '010_jungle')
