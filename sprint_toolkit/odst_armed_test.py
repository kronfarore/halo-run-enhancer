r"""odst_armed_test.py -- the first ODST Armed-card boot (2026-11-06, ARMED_ALL_GAMES.md).

Builds halo3odst\maps\<level>_armed_test.map from the patcher BASELINE (E:\HaloBaselines) with
the Halo 3 test rig's rules (h3_armed_test.py), on ODST's CELLS:

  * THE TEST LAYOUT: the cells of the hostile squads nearest the first player start (on foot)
    are dealt the ENEMY cases round robin, PER_CASE cells each; the nearest friendly Marine squads'
    cells the MARINE cases. A dealt cell gets a private one-element Character Type array (the case's
    character) and a private one-element Initial Weapon array (the case's weapon); its spawn points
    lose their own character / weapon overrides; a Jackal case's spawn points take 'shieldless'
    with a two-handed weapon.
  * the Armed pass's TEACHING and GRIPS (h3_enemy_weapons.teach, bound to ODST) for the refused /
    REPOSE pairs, and its borrowed firing data;
  * the god shield (odst / odst_recon / ONI op hlmt: body + shield 1e6), the cheat (Covenant
    Carbine as every profile's secondary, carbine_slug damage x1000), run / sneak x2.

    python sprint_toolkit/odst_armed_test.py [level]          (default sc120, Kizingo Boulevard)
    sprint_toolkit\odst_armed_test.cmd deploy | restore [level]
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
GAME = 'Halo 3: ODST'
BASELINE = r'E:\HaloBaselines\halo3odst\maps'
MAPS = os.path.join(os.path.dirname(ROOT), 'halo3odst', 'maps')
W = 'objects' + BS + 'weapons' + BS
C = 'objects' + BS + 'characters' + BS


def _w(p):
    return W + p.replace('/', BS)


def _c(s):
    return C + s + BS + 'ai' + BS + s


#: (label, character, weapon): the Halo 3 findings carried over, every species at once
ENEMY_CASES = (
    ('Grunt + Assault Rifle', _c('grunt'), _w('rifle/assault_rifle/assault_rifle')),
    ('Grunt + Flamethrower (grip)', _c('grunt'), _w('turret/flamethrower/flamethrower')),
    ('Grunt + Plasma Cannon (repose + grip)', _c('grunt'), _w('turret/plasma_cannon/plasma_cannon')),
    ('Jackal + Rocket Launcher (taught, shieldless)', _c('jackal'), _w('support_high/rocket_launcher/rocket_launcher')),
    ('Jackal + Brute Shot (grip)', _c('jackal'), _w('support_low/brute_shot/brute_shot')),
    ('Jackal + Plasma Cannon (grip)', _c('jackal'), _w('turret/plasma_cannon/plasma_cannon')),
    ('Brute + Silenced SMG', _c('brute'), _w('rifle/smg_silenced/smg_silenced')),
    ('Drone + Rocket Launcher (taught)', _c('bugger'), _w('support_high/rocket_launcher/rocket_launcher')),
    ('Drone + Brute Shot (grip)', _c('bugger'), _w('support_low/brute_shot/brute_shot')),
)
MARINE_CASES = (
    ('Marine + Brute Shot (grip)', _c('marine'), _w('support_low/brute_shot/brute_shot')),
    ('Marine + Plasma Cannon (pose)', _c('marine'), _w('turret/plasma_cannon/plasma_cannon')),
    ('Marine + Silenced SMG', _c('marine'), _w('rifle/smg_silenced/smg_silenced')),
)
PER_CASE = 2

PSTART, PSTART_ES = 0x280, 0x1C
PROFILES, PROFILE_ES = 0x274, 0x58
CELL_VEH = 0x46
PLAYER_MODELS = ('odst' + BS + 'odst', 'odst_recon' + BS + 'odst_recon',
                 'odst_oni_op' + BS + 'odst_oni_op_player')
HLMT_DAMAGE, HLMT_DAMAGE_ES = 0x94, 0xA4
GOD = ((0xC, 1e6), (0x20, 1e6), (0x2C, 0.0), (0x30, 0.1))
CHEAT_WEAPON = _w('rifle/covenant_carbine/covenant_carbine')
CHEAT_DAMAGE = CHEAT_WEAPON.rsplit(BS, 1)[0] + BS + 'damage_effects' + BS + 'carbine_slug'
CHEAT_DAMAGE_FIELDS = ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')
MATG_PLAYER, MATG_PLAYER_ES = 0x444, 0xC4
SPEED_FIELDS = (0x4, 0x8, 0xC, 0x10, 0x14, 0x18, 0x1C, 0x20)


def _i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def _one(m, blk, idx):
    """Give the array block at `blk` a private single element naming palette index `idx`."""
    got = hp._h3_reserve(m, [ew.CELL_ARR_ES])
    el = bytearray(ew.CELL_ARR_ES)
    struct.pack_into('<hh', el, ew.CELL_IDX, idx, 1)
    m.data[got[0]:got[0] + ew.CELL_ARR_ES] = el
    struct.pack_into('<iI', m.data, blk, 1, m.off2data(got[0]))


def layout(m, report):
    base = hp._scnr_base(m)
    p0 = struct.unpack_from('<fff', m.data, m.follow_all(base, [PSTART], [PSTART_ES], 'all')[0])
    wnames = [(hp._tag_name_by_id(m, m.u32(e + ew.WPAL_ID)) or '').lower()
              for e in m.follow_all(base, [ew.WPAL], [ew.WPAL_ES], 'all')]
    ids = [m.u32(e + ew.CPAL_ID) for e in m.follow_all(base, [ew.CPAL], [ew.CPAL_ES], 'all')]
    cnames = [hp._tag_name_by_id(m, i) if i != 0xFFFFFFFF else None for i in ids]
    friends, char_team = hp._player_friends(m, GAME, cnames, ids)
    sid = ew.find_variant(m, hp, 'shieldless')

    def idx(lst, name):
        return next((i for i, n in enumerate(lst) if (n or '').lower() == name.lower()), None)

    hostile, friendly = [], []
    for sq in m.follow_all(base, [ew.SQUADS], [ew.SQ_ES], 'all'):
        sps = m.follow_all(sq, [ew.SP], [ew.SP_ES], 'all')
        cells = m.follow_all(sq, [ew.CELL_BLOCKS[0]], [ew.CELL_ES], 'all')
        if not sps or not cells:
            continue
        steam = _i16(m, sq + ew.SQ_TEAM)
        for ci, cell in enumerate(cells):
            if _i16(m, cell + CELL_VEH) >= 0:
                continue
            chars = [_i16(m, e + ew.CELL_IDX)
                     for e in m.follow_all(cell, [ew.CELL_CHARS], [ew.CELL_ARR_ES], 'all')]
            types = set(ew.enemy_of(cnames[c]) if 0 <= c < len(cnames) else None for c in chars)
            if not chars or None in types:
                continue
            mine = [sp for sp in sps if _i16(m, sp + ew.SP_CELL) == ci]
            if not mine:
                continue
            team = steam if steam > 0 else (char_team[chars[0]] if chars[0] < len(char_team) else None)
            d = min(math.dist(p0, struct.unpack_from('<fff', m.data, sp + 0x14)) for sp in mine)
            name = bytes(m.data[sq:sq + 32]).split(b'\0')[0].decode('latin-1')
            entry = (d, name, cell, mine)
            if team in friends:
                if types == {'Marine'}:
                    friendly.append(entry)
            elif 'Marine' not in types:
                hostile.append(entry)

    def deal(cands, cases):
        usable = []
        for label, ch, wp in cases:
            ci, wi = idx(cnames, ch), idx(wnames, wp)
            if ci is None or wi is None:
                report.append("  SKIP %s: %s not in this level's palette"
                              % (label, 'character' if ci is None else 'weapon'))
                continue
            usable.append((label, ch, ci, wp, wi))
        k, need = 0, PER_CASE * len(usable)
        for d, name, cell, sps in sorted(cands, key=lambda x: x[0]):
            if k >= need:
                break
            label, ch, ci, wp, wi = usable[k % len(usable)]
            k += 1
            _one(m, cell + ew.CELL_CHARS, ci)
            _one(m, cell + ew.CELL_WEAPS, wi)
            struct.pack_into('<i', m.data, cell + ew.CELL_WEAPS + 0xC, 0)    # no secondary
            two = ew.two_handed(m, hp, ew.weapon_info(m, wnames[wi]))
            for sp in sps:
                struct.pack_into('<hhh', m.data, sp + ew.SP_CHAR, -1, -1, -1)
                v = sid if ('jackal' in ch and two and sid is not None) else 0
                struct.pack_into('<I', m.data, sp + ew.SP_VARIANT, v)
            report.append('  %-28s %5.0f wu  %s (%d spawn points, %d units)'
                          % (name, d, label, len(sps), _i16(m, cell + ew.CELL_COUNT)))
        if k < need:
            report.append('  SHORT: %d of %d cells' % (k, need))

    report.append('enemy cells (nearest the start first):')
    deal(hostile, ENEMY_CASES)
    report.append('friendly Marine cells:')
    deal(friendly, MARINE_CASES)
    if sid is None:
        report.append('  NOTE: no shieldless variant id in this map -- Jackals keep the shield')


def god_and_cheat(m, report):
    for leaf in PLAYER_MODELS:
        for _n, t in m.find_tags('hlmt', C + leaf):
            for e in m.follow_all(t, [HLMT_DAMAGE], [HLMT_DAMAGE_ES], 'all')[:1]:
                for off, v in GOD:
                    struct.pack_into('<f', m.data, e + off, v)
                report.append('god shield: %s body + shield 1e6' % leaf)
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
    n = 0
    for pr in m.follow_all(hp._scnr_base(m), [PROFILES], [PROFILE_ES], 'all'):
        if ref is not None and not hp._profile_is_empty(m, pr, GAME):
            hp._write_starting_weapon(m, pr, 'secondary', ref, -1, -1, GAME)
            n += 1
    report.append('cheat: covenant_carbine as the secondary of %d profiles' % n)
    for _n, t in m.find_tags('matg', 'globals' + BS + 'globals'):
        for e in m.follow_all(t, [MATG_PLAYER], [MATG_PLAYER_ES], 'all'):
            for off in SPEED_FIELDS:
                v = struct.unpack_from('<f', m.data, e + off)[0]
                struct.pack_into('<f', m.data, e + off, v * 2.0)
            report.append('player run / sneak x2 (run forward now %.3g)'
                          % struct.unpack_from('<f', m.data, e + 4)[0])


def build(level='sc120'):
    src = os.path.join(BASELINE, level + '.map')
    out = os.path.join(MAPS, level + '_armed_test.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    ew.bind(GAME, m, hp)
    report = ['%s from %s' % (os.path.basename(out), src)]
    layout(m, report)
    # teach the cases' weapons exactly as the Armed pass does (refused + REPOSE pairs)
    want, graphs = {}, ew.Graphs(m, hp)
    for cases in (ENEMY_CASES, MARINE_CASES):
        for _l, ch, wp in cases:
            e, wi = ew.enemy_of(ch), ew.weapon_info(m, wp)
            if wi and (not graphs.allows(e, wi['class'], wi['name'])
                       or wp.lower().rsplit(BS, 1)[-1] in ew.REPOSE.get(e, ())):
                want.setdefault(e, set()).add(wp)
    _taught, trows = ew.teach(m, hp, graphs, {e: sorted(w) for e, w in want.items()})
    for r in trows:
        report.append('teach: %s %s %s' % (r['tag'], r['field'], r.get('new') or r.get('reason')))
    handed = sorted(set(wp for cases in (ENEMY_CASES, MARINE_CASES) for _l, _c2, wp in cases))
    for r in ew.borrow_firing(m, hp, handed):
        report.append('firing data: %s %s %s' % (r['tag'], r['field'], r.get('new') or r.get('reason')))
    god_and_cheat(m, report)
    m.save(out)
    print('\n'.join(report))
    return out


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'sc120')
