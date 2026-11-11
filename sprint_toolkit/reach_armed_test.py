r"""reach_armed_test.py -- the first Reach Armed-card boot (2026-11-09, ARMED_ALL_GAMES.md);
the ODST rig (odst_armed_test.py) with Reach's offsets.

Reach's opening zone sets hold only the species of their own fights: Tip of the Spear (m35)
has Grunts, Jackals, Skirmishers, Elites and Marines resident from its first set (Brutes and
Drones need another level).

Builds haloreach\maps\<level>_armed_test.map from the patcher BASELINE (E:\HaloBaselines) with
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
GAME = 'Halo Reach'
BASELINE = r'E:\HaloBaselines\haloreach\maps'
MAPS = os.path.join(os.path.dirname(ROOT), 'haloreach', 'maps')
W = 'objects' + BS + 'weapons' + BS
C = 'objects' + BS + 'characters' + BS


def _w(p):
    return W + p.replace('/', BS)


def _c(s):
    return C + s + BS + 'ai' + BS + s


#: (label, character, weapon): the Halo 3 findings carried over, every species at once
#: v4 (Reach boot 3, 2026-11-11): only open / unseen pairs. Reach ignores the graph's class 'any'
#: (turrets came out unarmed); Jackals' shieldless clone now takes the SKIRMISHER's character data
#: (Jackals with DMR / Concussion Rifle never fired). Turrets first: the nearest cells.
ENEMY_CASES = (
    ('Grunt + Plasma Turret (own pgt anims)', _c('grunt'), _w('turret/plasma_turret/plasma_turret')),
    ('Jackal + Machine Gun Turret (taught + grip)', _c('jackal'), _w('turret/machinegun_turret/machinegun_turret')),
    ('Grunt + Machine Gun Turret (own mgt anims)', _c('grunt'), _w('turret/machinegun_turret/machinegun_turret')),
    ('Jackal + Plasma Turret (taught + grip)', _c('jackal'), _w('turret/plasma_turret/plasma_turret')),
    ('Skirmisher + Plasma Turret (taught + grip)', C + 'jackal' + BS + 'ai' + BS + 'skirmisher', _w('turret/plasma_turret/plasma_turret')),
    ('Elite + Plasma Turret', _c('elite'), _w('turret/plasma_turret/plasma_turret')),
    ('Jackal + DMR (Skirmisher-based clone)', _c('jackal'), _w('rifle/dmr/dmr')),
    ('Jackal + Concussion Rifle (Skirmisher-based clone)', _c('jackal'), _w('rifle/concussion_rifle/concussion_rifle')),
    ('Jackal + Shotgun (Skirmisher-based clone)', _c('jackal'), _w('rifle/shotgun/shotgun')),
    ('Grunt + Grenade Launcher (taught)', _c('grunt'), _w('rifle/grenade_launcher/grenade_launcher')),
    ('Grunt + Concussion Rifle (taught)', _c('grunt'), _w('rifle/concussion_rifle/concussion_rifle')),
    ('Grunt + Plasma Repeater (taught)', _c('grunt'), _w('rifle/plasma_repeater/plasma_repeater')),
    ('Skirmisher + Spartan Laser (taught)', C + 'jackal' + BS + 'ai' + BS + 'skirmisher', _w('support_high/spartan_laser/spartan_laser')),
    ('Elite + Focus Rifle', _c('elite'), _w('rifle/focus_rifle/focus_rifle')),
)
MARINE_CASES = (
    ('Marine + Plasma Turret (taught + grip)', C + 'marine' + BS + 'ai' + BS + 'trooper', _w('turret/plasma_turret/plasma_turret')),
    ('Marine + Machine Gun Turret (taught + grip)', C + 'marine' + BS + 'ai' + BS + 'trooper', _w('turret/machinegun_turret/machinegun_turret')),
    ('Marine + Plasma Repeater', C + 'marine' + BS + 'ai' + BS + 'trooper', _w('rifle/plasma_repeater/plasma_repeater')),
)
#: cells per case; None = EVERY cell of the level (v2, ODST boot 1: the nearest Grunt / Jackal
#: cells were not the first ones met)
PER_CASE = None

PSTART, PSTART_ES = 0x274, 0x1C
PROFILES, PROFILE_ES = 0x268, 0x68
CELL_VEH = 0x46
PLAYER_MODELS = ('spartans' + BS + 'spartans',)      # the player (spartans_ai is Noble Team)
# Reach: the root Maximum Vitality (+0xD0) is the shared pool; the Old Damage Info block (+0xC0,
# 0x10C) keeps body / shield vitality +0x28 / +0x7C, shield stun / recharge +0x88 / +0x8C
HLMT_ROOT_VITALITY = 0xD0
HLMT_DAMAGE, HLMT_DAMAGE_ES = 0xC0, 0x10C
GOD = ((0x28, 1e6), (0x7C, 1e6), (0x88, 0.0), (0x8C, 0.1))
CHEAT_WEAPON = _w('rifle/dmr/dmr')
CHEAT_DAMAGE = CHEAT_WEAPON.rsplit(BS, 1)[0] + BS + 'projectiles' + BS + 'dmr_bullet'
CHEAT_DAMAGE_FIELDS = ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')
MATG_PLAYER, MATG_PLAYER_ES = 0x468, 0xF4
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


def _used_chars(m, base):
    used = set()
    for sq in m.follow_all(base, [ew.SQUADS], [ew.SQ_ES], 'all'):
        for sp in m.follow_all(sq, [ew.SP], [ew.SP_ES], 'all'):
            used.add(_i16(m, sp + ew.SP_CHAR))
        for off in ew.CELL_BLOCKS:
            for cell in m.follow_all(sq, [off], [ew.CELL_ES], 'all'):
                for e in m.follow_all(cell, [ew.CELL_CHARS], [ew.CELL_ARR_ES], 'all'):
                    used.add(_i16(m, e + ew.CELL_IDX))
    return used


def layout(m, report):
    base = hp._scnr_base(m)
    shipped_used = _used_chars(m, base)       # v2: spares from the map as shipped
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
        if not cells:
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
            team = steam if steam > 0 else (char_team[chars[0]] if chars[0] < len(char_team) else None)
            # Reach squads often spawn through FORMATIONS: no spawn point -- dealt last
            d = min(math.dist(p0, struct.unpack_from('<fff', m.data, sp + 0x14)) for sp in mine)                 if mine else 99999.0
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
            ci = idx(cnames, ch)
            wi = next((i for i, n in enumerate(wnames)            # by NAME: Reach's folders differ
                       if (n or '').lower().rsplit(BS, 1)[-1] == wp.lower().rsplit(BS, 1)[-1]), None)
            wp = wnames[wi] if wi is not None else wp
            if ci is None or wi is None:
                report.append("  SKIP %s: %s not in this level's palette"
                              % (label, 'character' if ci is None else 'weapon'))
                continue
            usable.append((label, ch, ci, wp, wi))
        k, dealt = 0, {}
        need = len(cands) if PER_CASE is None else PER_CASE * len(usable)
        for d, name, cell, sps in sorted(cands, key=lambda x: x[0]):
            if k >= need:
                break
            if cell in done_cells:
                continue                   # a cell block shared by two squads: dealt once
            done_cells.add(cell)
            label, ch, ci, wp, wi = usable[k % len(usable)]
            k += 1
            _one(m, cell + ew.CELL_CHARS, ci)
            _one(m, cell + ew.CELL_WEAPS, wi)
            struct.pack_into('<i', m.data, cell + ew.CELL_WEAPS + 0xC, 0)    # no secondary
            two = ew.two_handed(m, hp, ew.weapon_info(m, wnames[wi]))
            if 'jackal' in ch and two:
                jackal_cells.append(cell)
            for sp in sps:
                struct.pack_into('<hhh', m.data, sp + ew.SP_CHAR, -1, -1, -1)
                v = sid if ('jackal' in ch and two and sid is not None) else 0
                struct.pack_into('<I', m.data, sp + ew.SP_VARIANT, v)
            dealt[label] = dealt.get(label, 0) + _i16(m, cell + ew.CELL_COUNT)
            if k <= 12:
                report.append('  %-28s %5.0f wu  %s (%d spawn points, %d units)'
                              % (name, d, label, len(sps), _i16(m, cell + ew.CELL_COUNT)))
        report.append('  units per case: ' + ', '.join('%s %d' % kv for kv in sorted(dealt.items())))
        if k < need:
            report.append('  SHORT: %d of %d cells' % (k, need))

    jackal_cells, done_cells = [], set()
    report.append('enemy cells (nearest the start first):')
    deal(hostile, ENEMY_CASES)
    report.append('friendly Marine cells:')
    deal(friendly, MARINE_CASES)
    # v3 (ODST boot 2): two-handed Jackal cells onto the pass's shieldless clone (formation /
    # extra Jackals never touch a spawn point's variant)
    used = _used_chars(m, base) | shipped_used
    sl = ew._Shieldless(m, hp, base, cnames, used)
    for cell in dict.fromkeys(jackal_cells):
        e = hp._block_base(m, cell + ew.CELL_CHARS)       # the private one-element array
        ci = sl.of(_i16(m, e + ew.CELL_IDX))
        if ci is not None:
            struct.pack_into('<h', m.data, e + ew.CELL_IDX, ci)
    for r in sl.rows:
        report.append('  %s: %s' % (r['tag'], r['new']))
    report.append('  %d two-handed Jackal cells on the shieldless clone' % len(set(jackal_cells)))
    if sid is None:
        report.append('  (no shieldless model variant by name: the clones carry their own)')


def god_and_cheat(m, report):
    for leaf in PLAYER_MODELS:
        for _n, t in m.find_tags('hlmt', C + leaf):
            for e in m.follow_all(t, [HLMT_DAMAGE], [HLMT_DAMAGE_ES], 'all')[:1]:
                for off, v in GOD:
                    struct.pack_into('<f', m.data, e + off, v)
                struct.pack_into('<f', m.data, t + HLMT_ROOT_VITALITY, 1e6)
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
                report.append('cheat: %s %s %.3g -> %.4g' % (CHEAT_DAMAGE.rsplit(BS, 1)[-1], f, v, v * 1000.0))
    ref = hp._h3_tag_datum(m, 'weap', CHEAT_WEAPON)
    n = 0
    for pr in m.follow_all(hp._scnr_base(m), [PROFILES], [PROFILE_ES], 'all'):
        if ref is not None and not hp._profile_is_empty(m, pr, GAME):
            hp._write_starting_weapon(m, pr, 'secondary', ref, -1, -1, GAME)
            n += 1
    report.append('cheat: dmr as the secondary of %d profiles' % n)
    for _n, t in m.find_tags('matg', 'globals' + BS + 'globals'):
        for e in m.follow_all(t, [MATG_PLAYER], [MATG_PLAYER_ES], 'all'):
            for off in SPEED_FIELDS:
                v = struct.unpack_from('<f', m.data, e + off)[0]
                struct.pack_into('<f', m.data, e + off, v * 2.0)
            report.append('player run / sneak x2 (run forward now %.3g)'
                          % struct.unpack_from('<f', m.data, e + 4)[0])


def build(level='m20'):
    src = os.path.join(BASELINE, level + '.map')
    out = os.path.join(MAPS, level + '_armed_test.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    ew.bind(GAME, m, hp)
    report = ['%s from %s' % (os.path.basename(out), src)]
    # the Jackal graph species' own firing rows BEFORE the clones copy their roots
    for r in ew.species_firing(m, hp, [(ew.enemy_of(ch), next((p for p, _b in m.find_tags('weap', '*')
                                        if p.lower().rsplit(BS, 1)[-1] == wp.lower().rsplit(BS, 1)[-1]), wp))
                                       for _l, ch, wp in ENEMY_CASES]):
        report.append('firing: %s %s %s' % (r['tag'], r['field'], r['new']))
    layout(m, report)
    # teach the cases' weapons exactly as the Armed pass does (refused + REPOSE pairs)
    want, graphs = {}, ew.Graphs(m, hp)
    for cases in (ENEMY_CASES, MARINE_CASES):
        for _l, ch, wp in cases:
            # by NAME: Reach keeps its turrets under objects\vehicles
            wp = next((p for p, _b in m.find_tags('weap', '*')
                       if p.lower().rsplit(BS, 1)[-1] == wp.lower().rsplit(BS, 1)[-1]), wp)
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
    for _l, ch, wp in ENEMY_CASES:
        e = ew.enemy_of(ch)
        if e in ew.MARKER_SPECIES.get(GAME, ()):
            full = next((p for p, _b in m.find_tags('weap', '*')
                         if p.lower().rsplit(BS, 1)[-1] == wp.lower().rsplit(BS, 1)[-1]), None)
            for r in ew.species_markers(m, hp, e, full) if full else ():
                report.append('markers: %s %s' % (r['field'], r['new']))
    # (v2's EXPERIMENT -- the turrets' Support Weapon flag cleared -- left Grunts unarmed all the same:
    # dropped in v3, the turrets go out as the patch hands them)
    god_and_cheat(m, report)
    m.save(out)
    print('\n'.join(report))
    return out


if __name__ == '__main__':
    # --marines <word>: every Marine cell takes only the Marine cases whose label holds the word
    # (v5, ODST boot 4: the one Plasma Cannon Marine came late and died unseen)
    args = sys.argv[1:]
    if '--marines' in args:
        i = args.index('--marines')
        word = args[i + 1].lower()
        MARINE_CASES = tuple(c for c in MARINE_CASES if word in c[0].lower())
        del args[i:i + 2]
    build(args[0] if args else 'm20')
