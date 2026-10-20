r"""Halo 2 'Armed: <weapon>' -- what weapons the AI carries, at patch time (H2_PORT_PLAN.md 0.5b).
The Halo 2 counterpart of h1_enemy_weapons.py, and much smaller: Halo 2 looks a character's
firing behaviour up BY WEAPON in ai\generic (parent of every species), so arming an enemy is
only a matter of the scenario's squad weapon indices. A port's ai\generic entry is in the kit
tag already (sprint_toolkit/ai_firing_profile.py --h2-port <key> -> h2_ai_firing.py) and rides
every rebuilt level; a stock infantry weapon has had one since 2004.

    apply(m, hp, spec) -> [result rows]        (halo_patch calls it; Halo 2 only)
    spec = {'cards': {'Grunt': {<weapon tag>: share, ...}, 'Marine': {...}, ...},
            'balanced': [<weapon tag>, ...]}     ports whose Balanced box is on

ARMING. Squad Initial Weapon / Initial Secondary (+0x3C / +0x3E) and each starting location's
pair (+0x22 / +0x24) index the scnr Weapon Palette (+0x98, 0x28). Every squad unit whose
character is of a carded species draws a deterministic number in [0, 1) (map name + the field's
address: both co-op machines and a re-patch agree): below the sum of its shares it takes the
weapon whose interval holds it (above 100% in total the shares count by weight, as in Halo 1),
secondary -1. Units the Thunderstorm code protects (vehicle-bound / script-loaded squads,
halo_patch._ts_units) keep theirs. A location whose own weapon is -1 inherits its squad's, so
it follows the squad's draw. A weapon not in the level's palette cannot be handed out (a port
is resident in all 13 levels -- H2_PORT_PLAN 0.1; a stock weapon may be missing): reported.

BALANCED. ai_firing_profiles.json['Halo 2'][weapon] may carry 'balanced_props' {field: value}
and 'balanced_patterns' [{field: value}, {field: value}] (Assembly Halo 2 char names); for a
weapon in spec['balanced'] they are written over the map's ai\generic entry (fixed-size field
writes: Weapons Properties +0xCC/0xCC, weapon datum +0x8; Firing Pattern Properties +0xD4/0x10,
weapon datum +0x4, patterns +0x8/0x40).
"""
import hashlib
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_FILE = os.path.join(HERE, 'ai_firing_profiles.json')
GAME = 'Halo 2'

#: enemy type (the enhancer's names) -> character folders it covers. Bosses, Hunters (built-in
#: gun), Sentinels / Drones (built-in weapons) and the story characters are left out.
ENEMY_CHARS = {
    'Grunt': ('grunt', 'heretic_grunt'),
    'Jackal': ('jackal',),
    'Elite': ('elite', 'heretic'),
    'Brute': ('brute',),
    'Flood Combat Form': ('floodcombat_elite', 'floodcombat_human'),
    'Marine': ('marine',),                       # the Ally (Friend) twin
}
NEVER = ('brute_tartarus', 'heretic_leader', 'heretic_leader_hologram', 'marine_johnson_boss',
         'elite_councilor')
WPAL, WPAL_ES = 0x98, 0x28
PROPS, PROPS_ES, PROPS_W = 0xCC, 0xCC, 0x8          # datum of the weapon tagref (+0x4)
FPP, FPP_ES, FPP_W, FPP_PAT, PAT_ES = 0xD4, 0x10, 0x4, 0x8, 0x40


def enemy_of(char_path):
    """The enemy type a character tag belongs to, or None."""
    if not char_path:
        return None
    parts = char_path.lower().split('\\')
    if parts[-1] in NEVER or len(parts) < 3:
        return None
    folder = parts[2]                               # objects\characters\<folder>\ai\<name>
    return next((e for e, fs in ENEMY_CHARS.items() if folder in fs), None)


def _draw(salt, addr):
    return int(hashlib.sha256(('%s|%d' % (salt, addr)).encode()).hexdigest()[:8], 16) / 2.0 ** 32


def _pick(shares, x):
    """The weapon `x` lands on, or None (keep the unit's own)."""
    total = sum(shares.values())
    if total <= 0:
        return None
    scale = 1.0 / total if total > 1.0 else 1.0
    acc = 0.0
    for w, s in sorted(shares.items()):
        acc += s * scale
        if x < acc:
            return w
    return None


def palette(m, hp, base):
    pal = m.follow_all(base, [WPAL], [WPAL_ES], 'all')
    return [hp._tag_name_by_id(m, struct.unpack_from('<I', m.data, e + 0x4)[0]) for e in pal]


def arm(m, hp, cards, salt=None):
    """Rewrite squad weapons by share. Returns (rows, {enemy: {weapon: units}})."""
    base = hp._scnr_base(m)
    wnames = palette(m, hp, base)
    widx = {(n or '').lower(): i for i, n in enumerate(wnames)}
    lay, ts = hp._BETRAYAL[GAME], hp._TS_LAYOUT[GAME]
    cpal = m.follow_all(base, [lay['palette'][0]], [lay['palette'][1]], 'all')
    cnames = [hp._tag_name_by_id(m, struct.unpack_from('<I', m.data, e + lay['pal_id_at'])[0])
              for e in cpal]
    salt = salt or os.path.basename(str(getattr(m, 'path', '') or ''))
    rows, missing, done = [], set(), {}
    usable = {}
    for enemy, ws in (cards or {}).items():
        ok = {}
        for w, s in ws.items():
            if w and w.lower() in widx and s > 0:
                ok[w.lower()] = s
            elif w:
                missing.add(w)
        if ok:
            usable[enemy] = ok
    seen = set()
    for u in hp._ts_units(m, GAME, base, lay, ts):
        c = u['char']
        enemy = enemy_of(cnames[c]) if c is not None and 0 <= c < len(cnames) else None
        if enemy not in usable or u['protected']:
            continue
        a0, a1 = u['weap_at']
        if a0 in seen:
            continue
        seen.add(a0)
        if u['kind'] == 'loc' and struct.unpack_from('<h', m.data, a0)[0] < 0:
            continue                                # inherits its squad's draw
        w = _pick(usable[enemy], _draw(salt, a0))
        if w is None:
            continue
        struct.pack_into('<h', m.data, a0, widx[w])
        struct.pack_into('<h', m.data, a1, -1)
        by = done.setdefault(enemy, {})
        by[w] = by.get(w, 0) + 1
    for enemy, ws in sorted(done.items()):
        for w, n in sorted(ws.items()):
            rows.append({'tag': 'scnr enemy weapons\\' + enemy, 'field': 'Armed: ' + w.split('\\')[-1],
                         'ok': True, 'reason': '%d squad units / locations' % n})
    for w in sorted(missing):
        rows.append({'tag': 'scnr enemy weapons', 'field': 'Armed: ' + w.split('\\')[-1], 'ok': True,
                     'skip': True, 'reason': 'not in this level\'s weapon palette'})
    return rows, done


def profiles():
    try:
        with open(PROFILE_FILE, encoding='utf-8') as fh:
            return json.load(fh).get(GAME) or {}
    except (OSError, ValueError):
        return {}


#: stock infantry weapons with BOTH ai\generic entries in Halo 2 (H2EK generic.character,
#: 2026-10-20; the disintegrator has Weapons Properties only, vehicle / Sentinel guns are no cards)
STOCK = tuple('objects\\weapons\\' + w for w in (
    'rifle\\battle_rifle\\battle_rifle', 'rifle\\shotgun\\shotgun', 'rifle\\smg\\smg',
    'rifle\\beam_rifle\\beam_rifle', 'support_high\\flak_cannon\\flak_cannon',
    'pistol\\plasma_pistol\\plasma_pistol', 'pistol\\needler\\needler', 'pistol\\magnum\\magnum',
    'support_high\\rocket_launcher\\rocket_launcher', 'support_low\\brute_shot\\brute_shot',
    'melee\\energy_blade\\energy_blade', 'rifle\\brute_plasma_rifle\\brute_plasma_rifle',
    'rifle\\covenant_carbine\\covenant_carbine', 'rifle\\sniper_rifle\\sniper_rifle',
    'rifle\\plasma_rifle\\plasma_rifle'))


def eligible_weapons():
    """Weapon tags an Armed card may hand out in Halo 2: firing data exists for them (stock, or
    a port whose entry h2_ai_firing wrote -- recorded in ai_firing_profiles.json['Halo 2'])."""
    return list(STOCK) + sorted(w for w in profiles() if w not in STOCK)


def entry(m, hp, weapon, char='ai\\generic'):
    """(props element, [pattern elements]) of `weapon` in the map's ai\\generic, or (None, [])."""
    hit = dict(m.find_tags('char', char)).get(char)
    if hit is None:
        return None, []
    want = weapon.lower()
    pe = None
    for e in m.follow_all(hit, [PROPS], [PROPS_ES], 'all'):
        if (hp._tag_name_by_id(m, m.u32(e + PROPS_W)) or '').lower() == want:
            pe = e
            break
    pats = []
    for e in m.follow_all(hit, [FPP], [FPP_ES], 'all'):
        if (hp._tag_name_by_id(m, m.u32(e + FPP_W)) or '').lower() == want:
            pats = m.follow_all(e, [FPP_PAT], [PAT_ES], 'all')
            break
    return pe, pats


def balance(m, hp, registry, weapons):
    """Write the Balanced AI rows of each weapon in `weapons` into the map's ai\\generic."""
    rows = []
    plugin = registry.get('char') if registry else None
    profs = profiles()
    for w in weapons or ():
        prof = profs.get(w)
        if not prof or not (prof.get('balanced_props') or prof.get('balanced_patterns')):
            continue
        pe, pats = entry(m, hp, w)
        if pe is None or not pats or plugin is None:
            rows.append({'tag': 'char ai\\generic', 'field': 'Balanced AI: ' + w.split('\\')[-1],
                         'ok': False, 'reason': 'no ai\\generic entry in this map'})
            continue
        fields = {(tuple(f['block_chain']), f['name']): f for f in plugin.fields}
        n = 0
        for name, v in (prof.get('balanced_props') or {}).items():
            f = fields[(('Weapons Properties',), name)]
            _put(m, pe + f['offset'], f['type'], v)
            n += 1
        for k, row in enumerate(prof.get('balanced_patterns') or ()):
            for name, v in (row or {}).items():
                f = fields[(('Firing Pattern Properties', 'Firing Patterns'), name)]
                for p in (pats[k:k + 1] if k < len(pats) else ()):
                    _put(m, p + f['offset'], f['type'], v)
                    n += 1
        rows.append({'tag': 'char ai\\generic', 'field': 'Balanced AI: ' + w.split('\\')[-1],
                     'ok': True, 'reason': '%d fields' % n})
    return rows


def _put(m, at, ftype, v):
    fmt = {'float32': '<f', 'degree': '<f', 'int16': '<h', 'enum16': '<H'}[ftype]
    struct.pack_into(fmt, m.data, at, int(round(v)) if fmt in ('<h', '<H') else v)


def apply(m, hp, spec, registry=None):
    """The patch pass: Armed cards, then the Balanced AI rows of switched-on ports."""
    rows, _done = arm(m, hp, (spec or {}).get('cards') or {})
    rows += balance(m, hp, registry, (spec or {}).get('balanced'))
    return rows
