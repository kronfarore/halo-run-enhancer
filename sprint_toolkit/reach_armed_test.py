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
#: v8 (Reach boot 7, 2026-11-15): the Engage block (DMR 2/2) is the lead -> split it, and test whether
#: the style / retreat fix still matter. Each entry: (weapon, style, retreat fix, engage) with engage
#: None = the Jackal's, 'full' = the Skirmisher's, or a list of (start, end) byte ranges of the
#: Skirmisher's element laid over the Jackal's; 'flags0' = the Jackal's with Fight Stable cleared
BISECT = (
    ('DMR', 'skirm', True, 'full'),
    ('Concussion Rifle', 'skirm', True, 'flags0'),
    ('Shotgun', 'skirm', True, [(0xC, 0x1C)]),
    ('Plasma Launcher', 'skirm', True, [(0x50, 0x60)]),
    ('Rocket Launcher', 'jackal', True, 'full'),
    ('Spike Rifle', 'jackal', False, 'full'),
    ('Focus Rifle', 'skirm', True, None),
)
_ENGAGE = {'full': 'the Skirmisher Engage', 'flags0': 'Jackal Engage, Fight Stable off', None: 'the Jackal Engage'}
_WP = {'DMR': 'rifle/dmr/dmr', 'Concussion Rifle': 'rifle/concussion_rifle/concussion_rifle',
       'Shotgun': 'rifle/shotgun/shotgun', 'Plasma Launcher': 'support_high/plasma_launcher/plasma_launcher',
       'Rocket Launcher': 'support_high/rocket_launcher/rocket_launcher', 'Spike Rifle': 'rifle/spike_rifle/spike_rifle',
       'Focus Rifle': 'rifle/focus_rifle/focus_rifle'}
ENEMY_CASES = tuple(('Jackal + %s (bisect)' % w, _c('jackal'), _w(_WP[w])) for w, *_r in BISECT) + (
    ('Jackal + Plasma Pistol (shield, control)', _c('jackal'), _w('pistol/plasma_pistol/plasma_pistol')),
)
MARINE_CASES = (
    ('Marine + DMR', C + 'marine' + BS + 'ai' + BS + 'trooper', _w('rifle/dmr/dmr')),
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
                cell_label[cell] = label
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

    jackal_cells, done_cells, cell_label = [], set(), {}
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
    # v8 BISECT: base = Jackal data (+ the shieldless variant); per entry the style, the retreat fix
    # (threshold 0) and the Engage element are set as BISECT says
    ew.RETREAT_FIX = {}
    jack_i = next(i for i, n in enumerate(sl.cnames) if (n or '').lower().endswith(BS + 'jackal'))
    base_idx = sl.of(jack_i)                       # Jackal data, no retreat fix (RETREAT_FIX off)
    jack = dict(m.find_tags('char', sl.cnames[jack_i]))[sl.cnames[jack_i]]
    skirm = next((b for p, b in m.find_tags('char', '*') if p.lower().endswith(BS + 'skirmisher')), None)
    now_used = _used_chars(m, base)
    refd = set()
    for _p, cb in m.find_tags('char', '*'):
        for off in (0x4, 0x44):
            refd.add((hp._tag_name_by_id(m, m.u32(cb + off + 0xC)) or '').lower())
    for ci, n in enumerate(sl.cnames):
        leaf = (n or '').lower().rsplit(BS, 1)[-1]
        if n and ci not in now_used and n.lower() not in refd and ci not in sl.spares \
                and ci not in sl.made.values() and 'jackal' not in leaf and 'skirm' not in leaf \
                and not any(w in leaf for w in ew.NEVER_WORDS.get(GAME, ())):
            sl.spares.append(ci)

    def private(tag, off, es):
        n = max(0, m.i32(tag + off))
        got = hp._h3_reserve(m, [n * es])
        old = hp._block_base(m, tag + off)
        m.data[got[0]:got[0] + n * es] = m.data[old:old + n * es]
        struct.pack_into('<I', m.data, tag + off + 4, m.off2data(got[0]))
        return got[0], n
    made = {}
    if base_idx is not None and skirm is not None:
        base_tag = dict(m.find_tags('char', sl.cnames[base_idx]))[sl.cnames[base_idx]]
        se = hp._block_base(m, skirm + 0x120)                 # the Skirmisher's Engage element
        for word, style, retreat, engage in BISECT:
            if sl.spares:
                ci = sl.spares.pop(0)
            elif sl.loose:
                n0 = len(sl.cnames)
                sl._palette_add(sl.loose.pop(0))
                ci = n0
            else:
                report.append('  BISECT: out of spare characters at %s' % word)
                continue
            tag = dict(m.find_tags('char', sl.cnames[ci]))[sl.cnames[ci]]
            m.data[tag:tag + ew.CHAR_ROOT] = m.data[base_tag:base_tag + ew.CHAR_ROOT]
            if style == 'skirm':
                m.data[tag + 0x34:tag + 0x44] = m.data[skirm + 0x34:skirm + 0x44]
            if retreat:
                e0, n = private(tag, 0x150, 0x58)
                for k in range(n):
                    struct.pack_into('<f', m.data, e0 + k * 0x58 + 0x4, 0.0)
            if engage == 'full':
                m.data[tag + 0x120:tag + 0x12C] = m.data[skirm + 0x120:skirm + 0x12C]
            elif engage is not None:
                e0, n = private(tag, 0x120, 0x60)
                for k in range(n):
                    el = e0 + k * 0x60
                    if engage == 'flags0':
                        struct.pack_into('<I', m.data, el, m.u32(el) & ~(1 << 5))     # Fight Stable
                    else:
                        for a, b in engage:
                            m.data[el + a:el + b] = m.data[se + a:se + b]
            made[word] = ci
        moved = {}
        for cell, label in cell_label.items():
            word = next((w for w, *_r in BISECT if (' + %s ' % w) in label + ' '), None)
            if word in made:
                e = hp._block_base(m, cell + ew.CELL_CHARS)
                struct.pack_into('<h', m.data, e + ew.CELL_IDX, made[word])
                moved[word] = moved.get(word, 0) + 1
        for word, style, retreat, engage in BISECT:
            eg = _ENGAGE.get(engage) if not isinstance(engage, list) else \
                'Jackal Engage + Skirmisher ' + ('danger thresholds' if engage[0][0] == 0xC else 'default ranges')
            report.append('  BISECT %-17s %s style, retreat fix %-3s, %-40s %d cells'
                          % (word, style, 'on' if retreat else 'off', eg, moved.get(word, 0)))
    for r in sl.rows:
        report.append('  %s: %s' % (r['tag'], r['new']))
    report.append('  %d two-handed Jackal cells on the shieldless clone' % len(set(jackal_cells)))
    if sid is None:
        report.append('  (no shieldless model variant by name: the clones carry their own)')


def disarm_allies(m, report, words=('spartan_kat',)):
    """(v8, user 2026-11-15) Kat killed the test Jackals before they could be watched: her cells and
    spawn points get the Target Locator (no damage) instead of their weapons."""
    base = hp._scnr_base(m)
    wnames = [(hp._tag_name_by_id(m, m.u32(e + ew.WPAL_ID)) or '').lower()
              for e in m.follow_all(base, [ew.WPAL], [ew.WPAL_ES], 'all')]
    cnames = [(hp._tag_name_by_id(m, m.u32(e + ew.CPAL_ID)) or '').lower()
              for e in m.follow_all(base, [ew.CPAL], [ew.CPAL_ES], 'all')]
    tl = next((i for i, n in enumerate(wnames) if n.endswith(BS + 'target_laser')), None)
    who = {i for i, n in enumerate(cnames) if any(w in n.rsplit(BS, 1)[-1] for w in words)}
    if tl is None or not who:
        return
    n = 0
    for sq in m.follow_all(base, [ew.SQUADS], [ew.SQ_ES], 'all'):
        for off in ew.CELL_BLOCKS:
            for cell in m.follow_all(sq, [off], [ew.CELL_ES], 'all'):
                chars = {_i16(m, e + ew.CELL_IDX) for e in m.follow_all(cell, [ew.CELL_CHARS], [ew.CELL_ARR_ES], 'all')}
                if chars & who:
                    _one(m, cell + ew.CELL_WEAPS, tl)
                    struct.pack_into('<i', m.data, cell + ew.CELL_WEAPS + 0xC, 0)
                    n += 1
        for sp in m.follow_all(sq, [ew.SP], [ew.SP_ES], 'all'):
            if _i16(m, sp + ew.SP_CHAR) in who:
                struct.pack_into('<hh', m.data, sp + ew.SP_WEAP, tl, -1)
                n += 1
    report.append('Kat: %d cells / spawn points on the Target Locator' % n)


def god_and_cheat(m, report):
    for leaf in PLAYER_MODELS:
        for _n, t in m.find_tags('hlmt', C + leaf):
            for e in m.follow_all(t, [HLMT_DAMAGE], [HLMT_DAMAGE_ES], 'all')[:1]:
                for off, v in GOD:
                    struct.pack_into('<f', m.data, e + off, v)
                struct.pack_into('<f', m.data, t + HLMT_ROOT_VITALITY, 1e6)
                report.append('god shield: %s body + shield 1e6' % leaf)
    import ai_firing_profile as A
    try:
        jpt = A._plugins()(GAME).get('jpt!')
    except Exception:
        jpt = None
    # the Reach jpt! plugin's offsets (E:\Assembly backup), used when the plugins are offline
    fixed = {'Damage Lower Bound': 0x20, 'Damage Upper Bound': 0x24, 'Damage Upper Bound Max': 0x28}
    for _n, t in m.find_tags('jpt!', CHEAT_DAMAGE):
        for f in CHEAT_DAMAGE_FIELDS:
            fld = jpt.find(f, None, 0) if jpt else None
            off = fld['offset'] if fld and not fld['block_offsets'] else fixed.get(f)
            if off is not None:
                o = t + off
                v = struct.unpack_from('<f', m.data, o)[0]
                struct.pack_into('<f', m.data, o, v * 1000.0)
                report.append('cheat: %s %s %.3g -> %.4g' % (CHEAT_DAMAGE.rsplit(BS, 1)[-1], f, v, v * 1000.0))
    ref = hp._h3_tag_datum(m, 'weap', CHEAT_WEAPON)
    n = 0
    sb = hp._scnr_base(m)
    profs = m.follow_all(sb, [PROFILES], [PROFILE_ES], 'all')
    # (v8) the PLAYER's profiles only: Kat's profile had the DMR too
    roles = hp._reach_profiles(m, GAME, sb, PROFILES, PROFILE_ES, len(profs))
    for i, pr in enumerate(profs):
        if not roles.get(i, (False, False))[0]:
            continue
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
    # v8: the clones start from the JACKAL's data; the bisect sets style / retreat / engage per entry
    ew.RETREAT_FIX = {}
    ew.ROOT_SOURCE = {}
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
    disarm_allies(m, report)
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
