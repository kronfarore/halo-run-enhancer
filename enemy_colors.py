r"""enemy_colors.py -- per-rank enemy colour overrides (visual only, never a card).

The option page lists every enemy rank of a game with its stock colours, read from
`enemy_colors_catalog.json` (built by sprint_toolkit/enemy_color_catalog.py from every
campaign map). A run stores overrides as

    CONFIG['enemy_colors'] = {game: {row id: {slot: 'RRGGBB'}}}

and `apply(m, game, overrides, catalog_rows)` writes them into the map on patch. Patching
rebuilds from the baseline, so clearing an override restores the stock colour.

Routes (all confirmed in game, 2026-09-18 -- see the halo-enemy-colors memory):
  actv    Halo 1 actor variant Change Colors (0x22C, elem 0x20; lower +0, upper +0xC)
  h1bipd  Halo 1 biped change colour permutations (0x164/0x2C -> 0x20/0x1C, colour +4 and
          +0x10) -- ranks whose actor variant leaves the colours to the biped (Grunt minor)
  perm    Halo 2 / 3 / ODST / Reach biped Change Colors -> Initial Permutations, matched by
          the rank's variant name (weight +0, lower +4, upper +0x10, name +0x1C)
  tint    Halo 4 armour materials: Postprocess Definition Float Constant[0], which
          multiplies the rank's texture (white = stock)
  armour  ODST Brute armour shaders. Where the shader has `variant` colour overlays they
          ARE the armour colour (painting their gradient stops recolours it; the static
          constants underneath are overwritten every frame); overlay 1 is the main armour
          colour. The static Float Constants are NOT drawn (all three set magenta on the
          overlay-less chieftain and stalker shaders: no change), so only shaders with
          overlays have armour rows. Per SHADER, not per rank: minor, major and captain share one, and still read
          apart through their own textures and per-rank body colours (biped route)
  shield  Jackal shields: H1 bipd slot C + sotr stage 0; H2 shad colour ramps; H3/ODST/
          Reach rmhg colour overlays; H4 mat colour functions
"""
import json
import os
import struct

B = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(HERE, 'enemy_colors_catalog.json')

# bipd Change Colors (block offset, element size) per engine
PERM_BLOCK = {'Halo 2': (0xAC, 0x10), 'Halo 3': (0xD4, 0x18), 'Halo 3: ODST': (0xD4, 0x18),
              'Halo Reach': (0x134, 0x18), 'Halo 4': (0x148, 0x18)}
H1_NEAR_BLACK = 0.02         # Halo 1 reads a (0,0,0) change colour as "no tint"
# Where a rank has NO permutation in a colour slot (Reach Jackal minor, the Jackal sniper)
# one is appended, relocating that slot's block into partition slack (halo_patch's
# _h3_reserve). Third-gen layouts only; Halo 2's growth moves blocks to EOF, unverified.
ADD_GAMES = ('Halo 3', 'Halo 3: ODST', 'Halo Reach')


def load_catalog(path=CATALOG_PATH):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def rgb(hexstr):
    """'RRGGBB' -> (r, g, b) floats 0..1."""
    h = str(hexstr).lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def hexcol(r, g, b):
    return '%02X%02X%02X' % tuple(int(round(max(0.0, min(1.0, x)) * 255)) for x in (r, g, b))


# Readable names for the patch log, from hue / saturation / brightness: the hue picks
# the name, brightness and saturation add dark / light / greyish. (A nearest-of-a-palette
# match read most muted rank colours as "grey" -- 2E3673, a Brute major's blue, included.)
_HUES = ((12, 'red'), (40, 'orange'), (68, 'yellow'), (100, 'lime'), (160, 'green'),
         (200, 'cyan'), (255, 'blue'), (285, 'violet'), (320, 'magenta'), (345, 'pink'),
         (360, 'red'))


def colour_name(hexstr):
    import colorsys
    h = str(hexstr).lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    hue, sat, val = colorsys.rgb_to_hsv(r, g, b)
    if val < 0.10:
        return 'black'
    if sat < 0.15 or (val < 0.25 and sat < 0.35):
        return ('dark grey' if val < 0.40 else 'grey' if val < 0.70
                else 'light grey' if val < 0.93 else 'white')
    deg = hue * 360
    name = next(n for top, n in _HUES if deg < top)
    if name == 'orange' and val < 0.60:
        name = 'brown'
    elif name == 'yellow' and val < 0.60:
        name = 'olive'
    elif name == 'cyan' and val < 0.60:
        name = 'teal'
    if val < 0.45:
        name = 'dark ' + name
    elif sat < 0.45 and val > 0.70:
        name = {'red': 'pink', 'orange': 'tan'}.get(name, 'light ' + name)
    elif sat < 0.45:
        name = 'greyish ' + name
    return name


def describe(hexstr):
    """'FF00F6' -> 'FF00F6 (magenta)'."""
    return '%s (%s)' % (str(hexstr).upper(), colour_name(hexstr))


# ----------------------------------------------------------------------------- helpers
def _tags(m, cls):
    """name -> tag dict of one class (second-gen and later). Keyed by class too: a
    biped, its model and its physics share one path."""
    return {str(t.get('name')): t for t in m.tags
            if isinstance(t, dict) and t.get('class') == cls and t.get('base')}


def _scaled_stop(stock_bgr, col):
    """A shield ramp stop recoloured to `col` at the stock stop's brightness, so the
    full -> broken animation keeps its shape. A black stop stays black."""
    peak = max(stock_bgr) / 255.0
    top = max(col) or 1.0
    return tuple(int(round(min(1.0, c / top * peak) * 255)) for c in col)


def _write_stops(m, off, stops, col):
    """Colour function stops (BGRA dwords) at off + each of `stops`, alpha kept."""
    n = 0
    for s in stops:
        p = off + s
        b, g, r = m.data[p], m.data[p + 1], m.data[p + 2]
        nr, ng, nb = _scaled_stop((r, g, b), col)
        m.data[p:p + 3] = bytes([nb, ng, nr])
        n += 1
    return n


# character tag: (variants block, element size, parent tagref) per engine
CHAR_VARIANTS = {'Halo 2': (0x2C, 0xC), 'Halo 3': (0x54, 0x14), 'Halo 3: ODST': (0x54, 0x14),
                 'Halo Reach': (0x54, 0x18), 'Halo 4': (0x54, 0x18)}


def _sid_chars(m, game):
    """variant stringID -> short names of the characters on this map that spawn it.
    The fallback for variant names that do not resolve: some Halo 3 static-range
    names are missing from a map's string table, and their raw value differs from map
    to map, but the character that uses the variant still says which rank it is."""
    cache = getattr(m, '_ec_sid_chars', None)
    if cache is not None:
        return cache
    cache = {}
    blk, el = CHAR_VARIANTS.get(game, (None, None))
    if blk is not None:
        for t in m.tags:
            if isinstance(t, dict) and t.get('class') == 'char' and t.get('base'):
                for e in m.follow_all(t['base'], [blk], [el], 'all'):
                    cache.setdefault(m.u32(e), set()).add(str(t['name']).rsplit(B, 1)[-1])
    m._ec_sid_chars = cache
    return cache


def _variant_matches(m, game, sid, want, chars=()):
    if want == '':
        return sid in (0, 0xFFFFFFFF)
    if want.startswith('sid:'):
        return sid == int(want[4:], 16)
    try:
        name = m.resolve_stringid(sid)
    except Exception:
        name = None
    if name:
        return name == want
    return bool(_sid_chars(m, game).get(sid, set()) & set(chars))


# ----------------------------------------------------------------------------- routes
def _route_actv(m, row, slots):
    n = 0
    for name in row['targets']:
        for _p, base in m.find_tags('actv', name):
            els = m.follow_all(base, [0x22C], [0x20], 'all')
            for si, col in slots.items():
                if int(si) < len(els):
                    c = tuple(max(H1_NEAR_BLACK, x) for x in col) if max(col) < H1_NEAR_BLACK else col
                    struct.pack_into('<3f', m.data, els[int(si)], *c)
                    struct.pack_into('<3f', m.data, els[int(si)] + 0xC, *c)
                    n += 1
    return n


def _h1_bipd_perms(m, name, slot):
    for _p, base in m.find_tags('bipd', name):
        sl = m.follow_all(base, [0x164], [0x2C], 'all')
        if slot < len(sl):
            yield from m.follow_all(sl[slot], [0x20], [0x1C], 'all')


def _route_h1bipd(m, row, slots):
    n = 0
    for name in row['targets']:
        for si, col in slots.items():
            if max(col) < H1_NEAR_BLACK:
                col = (H1_NEAR_BLACK,) * 3
            for p in _h1_bipd_perms(m, name, int(si)):
                struct.pack_into('<3f', m.data, p + 4, *col)
                struct.pack_into('<3f', m.data, p + 0x10, *col)
                n += 1
    return n


def _route_perm(m, game, row, slots):
    blk, el = PERM_BLOCK[game]
    tags = _tags(m, 'bipd')
    n = 0
    for tgt in row['targets']:
        t = tags.get(tgt['bipd'])
        if not t:
            continue
        sl = m.follow_all(t['base'], [blk], [el], 'all')
        for si, col in slots.items():
            si = int(si)
            if si >= len(sl) or si >= len(tgt['src']):
                continue
            if tgt['src'][si] == 'none':
                if game in ADD_GAMES and tgt['variant']:
                    sid = _variant_sid(m, game, tgt)
                    if sid is not None:
                        _pending(m).setdefault(sl[si], []).append((sid, col))
                        n += 1
                continue
            if tgt['src'][si] not in ('own', 'any'):
                continue
            want = tgt['variant'] if tgt['src'][si] == 'own' else ''
            for p in m.follow_all(sl[si], [0x0], [0x20], 'all'):
                if _variant_matches(m, game, m.u32(p + 0x1C), want, tgt.get('chars', ())):
                    struct.pack_into('<3f', m.data, p + 4, *col)
                    struct.pack_into('<3f', m.data, p + 0x10, *col)
                    n += 1
    return n


def _variant_sid(m, game, tgt):
    """This map's stringID for a target's variant, read off the characters that spawn
    it (the variant has no permutation to read it from, which is the point)."""
    chars = set(tgt.get('chars', ()))
    cands = [sid for sid, cs in _sid_chars(m, game).items() if cs & chars and sid]
    for sid in cands:
        try:
            if m.resolve_stringid(sid) == tgt['variant']:
                return sid
        except Exception:
            pass
    return cands[0] if len(cands) == 1 else None


def _pending(m):
    p = getattr(m, '_ec_pending', None)
    if p is None:
        p = m._ec_pending = {}
    return p


def _append_perms(m):
    """Grow each colour slot's Initial Permutations by the queued (variant, colour)
    entries: copy the block into reserved slack, append, repoint. Structural, so it runs
    once after every value write."""
    import halo_patch
    out = 0
    for slot, adds in sorted(_pending(m).items()):
        count, ptr = m.i32(slot), m.u32(slot + 4)
        src = m.data2off(ptr) if count else None
        size = (count + len(adds)) * 0x20
        got = halo_patch._h3_reserve(m, [size])
        if not got:
            raise RuntimeError('no free run of %d bytes for a colour permutation' % size)
        dest = got[0]
        if count:
            m.data[dest:dest + count * 0x20] = m.data[src:src + count * 0x20]
        for k, (sid, col) in enumerate(adds):
            e = dest + (count + k) * 0x20
            m.data[e:e + 0x20] = bytes(0x20)
            struct.pack_into('<f3f3fI', m.data, e, 1.0, *col, *col, sid)
        struct.pack_into('<i', m.data, slot, count + len(adds))
        struct.pack_into('<I', m.data, slot + 4, m.off2data(dest))
        out += len(adds)
    m._ec_pending = {}
    return out


def _mat_fc0(m, base):
    for pp in m.follow_all(base, [0x1C], [0x9C], 'all'):
        fc = m.follow_all(pp, [0x18], [0x10], 'all')
        if fc:
            return fc[0]
    return None


def _route_tint(m, row, slots):
    col = slots.get('0')
    if col is None:
        return 0
    tags = _tags(m, 'mat ')
    n = 0
    for name in row['targets']:
        t = tags.get(name)
        if not t:
            continue
        p = _mat_fc0(m, t['base'])
        if p is None:
            continue
        # Multiply onto the material's own tint: sub-variants keep their shade
        # differences, and white leaves the rank exactly stock.
        stock = struct.unpack_from('<3f', m.data, p)
        struct.pack_into('<3f', m.data, p, *(s * c for s, c in zip(stock, col)))
        n += 1
    return n


def _route_shield(m, game, row, slots):
    col = slots.get('0')
    if col is None:
        return 0
    n = 0
    if game == 'Halo 1':
        c = tuple(max(H1_NEAR_BLACK, x) for x in col)
        for name in row['targets']:
            for p in _h1_bipd_perms(m, name, 2):
                struct.pack_into('<3f', m.data, p + 4, *c)
                struct.pack_into('<3f', m.data, p + 0x10, *c)
                n += 1
        for name in row.get('sotr', []):
            for _p, base in m.find_tags('sotr', name):
                st = m.follow_all(base, [0x60], [0x70], 'all')
                if not st:
                    continue
                for off in (0xC, 0x1C):          # stage 0 Color0 bounds, ARGB floats
                    a, r, g, b = struct.unpack_from('<4f', m.data, st[0] + off)
                    peak = max(r, g, b)
                    top = max(col) or 1.0
                    struct.pack_into('<4f', m.data, st[0] + off, a,
                                     *(x / top * peak for x in col))
                    n += 1
        return n
    tags = _tags(m, {'Halo 2': 'shad', 'Halo 4': 'mat '}.get(game, 'rmhg'))
    for name in row['targets']:
        t = tags.get(name)
        if not t:
            continue
        if game == 'Halo 2':
            for pp in m.follow_all(t['base'], [0x20], [0x7C], 'all'):
                for o in m.follow_all(pp, [0x3C], [0x14], 'all'):
                    if m.u32(o) == 0:                # the ramps are the overlays with an input
                        continue
                    size, off = m.i32(o + 0xC), m.p2o(m.u32(o + 0x10))
                    if off and size >= 0x14:
                        n += _write_stops(m, off, (0x4, 0x10), col)
        elif game == 'Halo 4':
            for pp in m.follow_all(t['base'], [0x1C], [0x9C], 'all'):
                for f in m.follow_all(pp, [0x54], [0x2C], 'all'):
                    if m.u32(f) == 1:
                        size, off = m.i32(f + 0x18), m.data2off(m.u32(f + 0x18 + 0xC))
                        if off and size >= 0x14:
                            n += _write_stops(m, off, (0x4, 0x8, 0xC, 0x10), col)
        else:
            pp_off, sizes = (0x38, (0xB4, 0xAC)) if game == 'Halo Reach' else (0x28, (0x8C,))
            pps = []
            for es in sizes:
                pps = m.follow_all(t['base'], [pp_off], [es], 'all')
                if pps:
                    break
            for pp in pps:
                for o in m.follow_all(pp, [0x5C], [0x24], 'all'):
                    if m.u32(o) == 1:
                        size, off = m.i32(o + 0x10), m.data2off(m.u32(o + 0x10 + 0xC))
                        if off and size >= 0x14:
                            n += _write_stops(m, off, (0x4, 0x8, 0xC, 0x10), col)
    return n


# rmsh Postprocess (0x28/0x8C) Float Constants (0x1C/0x10) holding the stock armour colours
# -- equal to each overlay's first stop. Read for the catalogue's stock swatches only.
ODST_ARMOUR_CONSTS = (7, 8, 16)


def _variant_overlays(m, pp):
    """The `variant` colour overlays of an ODST brute shader's Postprocess, in order:
    1-register colour overlays (+0 == 1) whose function is a colour gradient (type 8,
    >= 0x40 bytes). The shield and suit_bump overlays are not among them."""
    out = []
    for o in m.follow_all(pp, [0x5C], [0x24], 'all'):
        off = m.data2off(m.u32(o + 0x1C)) if m.i32(o + 0x10) >= 0x40 else None
        if m.u32(o) == 1 and off and m.data[off] == 8:
            out.append(off)
    return out


def _route_armour(m, row, slots):
    tags = _tags(m, 'rmsh')
    n = 0
    for name in row['targets']:
        t = tags.get(name)
        if not t:
            continue
        for pp in m.follow_all(t['base'], [0x28], [0x8C], 'all'):
            ovs = _variant_overlays(m, pp)
            for si, col in slots.items():
                si = int(si)
                if ovs:
                    if si < len(ovs):
                        # Every stop: the input reads 0 for every rank (stops painted
                        # red/green/blue came out all red), but paint the whole ramp so
                        # nothing else can land on a stock colour.
                        bgr = bytes(int(round(c * 255)) for c in reversed(col))
                        for st in (0x4, 0x8, 0xC, 0x10):
                            m.data[ovs[si] + st:ovs[si] + st + 3] = bgr
                        n += 1
    return n


# ----------------------------------------------------------------------------- drift
# Every active enemy card shifts colours toward the card's group -- `color` in halo.json:
# aggressive = red, defensive = blue, utility = green. Per card: + its group's step on the
# own channel, - on the other two (clamped to 0..255 once, at the end), over the stock colour or the
# player's pick.
#   Step 2  a Specific Enemy card shifts that enemy; a hero / boss card only its rank.
#   Step 3  a General enemy card shifts EVERY enemy, with its own (smaller) steps.
# Steps are per group because the pools are lopsided (specific 211 / 142 / 85, general
# 30 / 6 / 9): scaled inversely to pool share, each group moves an enemy about equally
# often.
#   WRAP: cards apply one at a time; when a card leaves one channel at 255 and the other
# two within that card's + step of 255 -- the colour has gone white -- it restarts from
# black (Halo 1 draws near-black: pure black is "no tint" there) and later cards carry
# on from black. A one-sided enemy stays pinned at pure red / blue / green; only a
# mixed build that has washed out to white wraps. (Plain modulo was considered and
# rejected: the - steps would wrap 0 -> 253, and a very aggressive enemy would cycle
# out of red, so the colour would stop saying how buffed it is.)
DRIFT_CHANNEL = {'aggressive': 0, 'defensive': 2, 'utility': 1}          # R, B, G
DRIFT_DEFAULTS = {'enabled': False,
                  'aggressive': [8, 3], 'defensive': [12, 4], 'utility': [20, 7],
                  'general_enabled': False,
                  'general': {'aggressive': [3, 1], 'defensive': [12, 4], 'utility': [8, 3]}}
GENERAL = '*'                     # `who` of a General enemy card: every enemy

# A hero or boss card shifts only its own rank rows: (enemy, label prefixes).
HERO_ROWS = {
    'Brute Chieftain': ('Brute', ('chieftain',)),
    'Elite Zealot': ('Elite', ('zealot',)),
    'Elite General': ('Elite', ('general',)),
    'Elite Honor Guard': ('Elite', ('honor',)),
    'Elite Specops Commander': ('Elite', ('soc',)),
    'Knight Commander': ('Knight', ('commander',)),
    'Jackal Ranger': ('Jackal', ('ranger',)),
    'Jackal Sniper': ('Jackal', ('sniper',)),
    'Grunt Ultra': ('Grunt', ('ultra',)),
    'Tartarus': ('Brute', ('all (brute_tartarus)',)),
    'Heretic Leader': ('Elite', ('leader_her',)),
}


def drift_rows(rows, who):
    """The catalogue rows a card for `who` (enemy family, hero, boss, or GENERAL)
    recolours."""
    if who == GENERAL:
        return list(rows)
    if who in HERO_ROWS:
        enemy, prefixes = HERO_ROWS[who]
        return [r for r in rows if r['enemy'] == enemy and r['label'].startswith(prefixes)]
    return [r for r in rows if r['enemy'] == who]


def _steps(knobs, who, group):
    if who == GENERAL:
        gk = dict(DRIFT_DEFAULTS['general'], **(knobs.get('general') or {}))
        pair = gk.get(group)
    else:
        pair = knobs.get(group) or DRIFT_DEFAULTS[group]
    return (list(pair) + [0, 0])[:2]


def shift(rgb8, group, up, down, times=1):
    """`times` cards of one group on an [r, g, b] colour, one at a time, with the
    white -> black wrap. The TOP is capped per card (a channel pinned at 255 is what the
    wrap reads), but the bottom is NOT: a channel pushed below 0 keeps that debt, so a
    later card of its own group pays it back before the colour moves -- the end result
    does not depend on which group came first. Clamp to 0..255 once, at the end
    (drift does)."""
    ch = DRIFT_CHANNEL[group]
    v = list(rgb8)
    for _ in range(times):
        v = [min(255, x + (up if c == ch else -down)) for c, x in enumerate(v)]
        if v[ch] == 255 and up > 0 and all(x >= 255 - up for c, x in enumerate(v) if c != ch):
            v = [0, 0, 0]
    return v


def drift(game, events, knobs=None, base=None, catalog=None):
    """Overrides {row id: {slot: 'RRGGBB'}} for one game: `base` (the player's picks)
    with every active card's shift applied in order. `events` = [(who, group, n), ...]
    as drift_counts returns them (a dict {(who, group): n} is accepted too). Slots with
    no stock colour (the '+' ones) drift only from a player pick."""
    knobs = dict(DRIFT_DEFAULTS, **(knobs or {}))
    out = {rid: dict(sl) for rid, sl in (base or {}).items()}
    if isinstance(events, dict):
        events = [(w, g, n) for (w, g), n in events.items()]
    events = [(w, g, n) for w, g, n in (events or ())
              if n and g in DRIFT_CHANNEL
              and (knobs.get('general_enabled') if w == GENERAL else knobs.get('enabled'))]
    if not events:
        return out
    cat = catalog if catalog is not None else load_catalog()
    rows = cat.get(str(game).strip(), [])
    by_id = {r['id']: r for r in rows}
    plan = {}                                   # row id -> [(group, up, down, n), ...]
    for who, group, n in events:
        up, down = _steps(knobs, who, group)
        for r in drift_rows(rows, who):
            plan.setdefault(r['id'], []).append((group, up, down, n))
    for rid, steps in plan.items():
        r = by_id[rid]
        for si, slot in enumerate(r['slots']):
            if not slot.get('editable'):
                continue
            key = str(si)
            src = out.get(rid, {}).get(key) or slot.get('stock')
            if not src:
                continue
            v = [int(src[i:i + 2], 16) for i in (0, 2, 4)]
            for group, up, down, n in steps:
                v = shift(v, group, up, down, n)
            new = '%02X%02X%02X' % tuple(max(0, min(255, x)) for x in v)
            if new != src.upper():
                out.setdefault(rid, {})[key] = new
    return out


def drift_counts(effects):
    """[(who, group, n), ...] in the patcher's effect order (so both co-op machines wrap
    at the same card). `who` is the card's enemy family / hero / boss, or GENERAL for a
    General enemy card (no `enemy`, but a `color`: only enemy cards carry one)."""
    order, counts = [], {}
    for e in effects or ():
        group = e.get('color')
        if group not in DRIFT_CHANNEL:
            continue
        key = (e.get('enemy') or GENERAL, group)
        if key not in counts:
            order.append(key)
            counts[key] = 0
        counts[key] += int(e.get('count') or 1)
    return [(w, g, counts[(w, g)]) for w, g in order]


# ----------------------------------------------------------------------------- entry
def apply(m, game, overrides, catalog=None):
    """Write the overrides {row id: {slot: 'RRGGBB'}} of one game into an open map.
    Returns result rows for the patch log. Rows whose tags are not on this map are
    skipped silently -- a rank that does not appear on the level has nothing to paint."""
    game = str(game).strip()
    if not overrides:
        return []
    cat = catalog if catalog is not None else load_catalog()
    rows = {r['id']: r for r in cat.get(game, [])}
    out = []
    for rid, slots in sorted(overrides.items()):
        row = rows.get(rid)
        if not row or not slots:
            continue
        cols = {str(k): rgb(v) for k, v in slots.items() if v}
        if not cols:
            continue
        route = row['route']
        try:
            if route == 'actv':
                n = _route_actv(m, row, cols)
            elif route == 'h1bipd':
                n = _route_h1bipd(m, row, cols)
            elif route == 'perm':
                n = _route_perm(m, game, row, cols)
            elif route == 'tint':
                n = _route_tint(m, row, cols)
            elif route == 'shield':
                n = _route_shield(m, game, row, cols)
            elif route == 'armour':
                n = _route_armour(m, row, cols)
            else:
                continue
        except Exception as e:                        # never let a colour sink a patch
            out.append({'tag': 'enemy colours', 'field': rid, 'effect': 'Enemy colours',
                        'ok': False, 'reason': '%s: %s' % (type(e).__name__, e)})
            continue
        if n:
            out.append({'tag': 'enemy colours', 'field': '%s %s' % (row['enemy'], row['label']),
                        'effect': 'Enemy colours', 'ok': True, 'old': 'stock',
                        'new': ', '.join('%s=%s' % (k, describe(v)) for k, v in sorted(slots.items()) if v)
                               + ' (%d write%s)' % (n, '' if n == 1 else 's')})
    if getattr(m, '_ec_pending', None):
        try:
            k = _append_perms(m)
            out.append({'tag': 'enemy colours', 'field': 'added colour permutations',
                        'effect': 'Enemy colours', 'ok': True, 'old': 'none',
                        'new': '%d rank colour(s) the biped had no entry for' % k})
        except Exception as e:
            out.append({'tag': 'enemy colours', 'field': 'added colour permutations',
                        'effect': 'Enemy colours', 'ok': False,
                        'reason': '%s: %s' % (type(e).__name__, e)})
    return out
