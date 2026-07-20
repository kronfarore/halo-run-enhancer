# halo_patch.py — glue between the roller's selected effects and halo_map.py.
# Collects the effects chosen during a run, resolves each to its Assembly plugin,
# and applies typed operators to the map with a per-insert success/failure report.
# No GUI dependency; safe to unit-test headless.

import json
import shutil
import struct
from pathlib import Path

import halo_map as hm


# Games that use the second-generation (Halo 2 MCC) cache format.
SECOND_GEN_GAMES = {'Halo 2'}
# Games that use the third-generation (Halo 3 MCC) cache format.
THIRD_GEN_GAMES = {'Halo 3'}


def open_map(map_path, game=None):
    """Open a map with the right parser for its game: Halo 2 -> `Halo2Map`
    (second-gen), Halo 3 -> `Halo3Map` (third-gen), everything else -> the
    Halo 1 `HaloMap`."""
    g = str(game).strip()
    if g in SECOND_GEN_GAMES:
        import halo2_map
        return halo2_map.Halo2Map(map_path)
    if g in THIRD_GEN_GAMES:
        import halo3_map
        return halo3_map.Halo3Map(map_path)
    return hm.HaloMap(map_path)


class PluginRegistry:
    """Loads Assembly plugins per tag group, honoring an MCC override order
    (e.g. Halo1MCC before Halo1). Missing plugins resolve to None, not errors."""

    def __init__(self, plugins_root, subdirs):
        self.root = Path(plugins_root) if plugins_root else None
        self.subdirs = list(subdirs or [])
        self.cache = {}

    def get(self, group):
        if group in self.cache:
            return self.cache[group]
        plugin = None
        if self.root:
            for sub in self.subdirs:
                f = self.root / sub / f"{group}.xml"
                if f.is_file():
                    try:
                        plugin = hm.Plugin(f)
                    except Exception:
                        plugin = None
                    break
        self.cache[group] = plugin
        return plugin


def collect_effects(rounds, mission_id=None):
    """Unique patchable effects from a run's rounds, in first-seen order, each
    with a selection `count`, and a source `group`/`cat` (specific weapon,
    player-general, specific enemy, enemy-general, friend, boss, exhaust) for
    display. Exhausts are one-map negatives: an exhaust is only included when
    patching the mission it was rolled in (mission_id), so leaving that mission
    drops it automatically (paired with apply_run's idempotent re-patch)."""
    seen, order = {}, []

    def add(mod, group, cat):
        if not isinstance(mod, dict) or mod.get('_game_excluded'):
            return
        tag = mod.get('tag')
        if not tag:
            return
        key = (tag, mod.get('name'))
        if key not in seen:
            seen[key] = {'name': mod.get('name'), 'desc': mod.get('desc', ''),
                         'desc_overrides': mod.get('desc_overrides'),  # #7
                         'tag': tag, 'targets': list(mod.get('targets') or []),
                         'skull': mod.get('skull'),
                         'harder_when': mod.get('harder_when'),
                         'easier_when': mod.get('easier_when'),
                         'init_defaults': mod.get('init_defaults'),
                         '_missing_in_db': mod.get('_missing_in_db'),
                         # source identity, so the patcher can remove it from the run
                         'weapon': mod.get('weapon'), 'enemy': mod.get('enemy'),
                         'group': group, 'cat': cat, 'count': 0}
            order.append(key)
        seen[key]['count'] += 1

    for rd in rounds or []:
        for pk in ('player1', 'player2'):
            mod = (rd.get(pk) or {}).get('mod')
            if isinstance(mod, dict):
                add(mod, mod['weapon'] if mod.get('weapon') else 'Player (general)',
                    0 if mod.get('weapon') else 1)
        for k in ('enemy1', 'enemy2'):
            mod = rd.get(k)
            if isinstance(mod, dict):
                add(mod, mod['enemy'] if mod.get('enemy') else 'Enemy (general)',
                    2 if mod.get('enemy') else 3)
        add(rd.get('wildcard'), 'Friend / Wildcard', 4)
        add(rd.get('wildcard2'), 'Friend / Wildcard', 4)   # player 2's wildcard slot
        for k in ('boss1', 'boss2'):
            add(rd.get(k), 'Boss', 5)
        for k in ('exhaust1', 'exhaust2'):
            ex = rd.get(k)
            if isinstance(ex, dict) and (mission_id is None
                                         or ex.get('_exhaust_mission') == mission_id):
                add(ex, 'Exhaust', 6)
    return [seen[k] for k in order]


def group_effects(effects):
    """Group effects by their source group, ordered (weapons, player, specific
    enemies, enemy-general, friend, boss), then by group name. Returns an
    ordered list of (group_name, [effects])."""
    groups = {}
    for e in effects:
        groups.setdefault(e.get('group', '?'), []).append(e)
    def key(g):
        return (min(x.get('cat', 9) for x in groups[g]), g)
    return [(g, groups[g]) for g in sorted(groups, key=key)]


def preset_key(tag, name, field, game=None):
    """Cache key for a remembered magnitude/preset. `game` is included so the
    same effect can have different remembered values per game — most tags
    already differ by game (naturally separating the cache), but a few (e.g.
    matg-based effects) share the same tag/field in both games, and the right
    magnitude for the same field can still differ in scale between engines."""
    base = f"{tag}||{name}||{field}"
    return f"{base}||{game}" if game else base


def load_presets(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_presets(path, presets):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)


def default_map_path(mcc_root, map_subdir, mission_id):
    """<mcc_root>/<map_subdir>/<mission>.map. Falls back to a prefix match
    (<mission>*.map) so a mission id like '01b' resolves to Halo 2's
    '01b_spacestation.map'."""
    if not map_subdir or not mcc_root:
        return ''
    d = Path(mcc_root).resolve() / map_subdir
    exact = d / f'{mission_id}.map'
    if exact.is_file():
        return str(exact)
    matches = sorted(d.glob(f'{mission_id}*.map'))
    return str(matches[0]) if matches else str(exact)


# Some H2 char fields (e.g. Placement Properties' Upgrade Chance family) are
# difficulty-variant by SUFFIX ("<field> (Legendary)") using different tier
# names than the matg/weap-style difficulty PREFIX ("Impossible <field>"),
# which uses the tool's own Easy/Normal/Hard/Impossible combo-box names.
DIFFICULTY_SUFFIX_MAP = {'Easy': 'Easy', 'Normal': 'Normal', 'Hard': 'Heroic', 'Impossible': 'Legendary'}


def apply_difficulty(field, op, target_difficulty):
    """Expand a field name for the run's configured difficulty, per the
    target's flavor: 'difficulty' prefixes the matg/weap-style name; 'diff_suffix'
    appends the char-plugin style "(Name)" using DIFFICULTY_SUFFIX_MAP; 'diff_prefix'
    PREPENDS that same Heroic/Legendary tier name (e.g. H2 char Accuracy fields are
    named "Legendary Accuracy Bounds"). Note there is no 'Easy' accuracy tier, so an
    Easy run simply won't resolve those and skips them."""
    if op.get('difficulty'):
        return f"{target_difficulty} {field}"
    if op.get('diff_suffix'):
        return f"{field} ({DIFFICULTY_SUFFIX_MAP.get(target_difficulty, target_difficulty)})"
    if op.get('diff_prefix'):
        # H2 char accuracy tiers are Normal/Heroic/Legendary — there is NO 'Easy'
        # tier, so an Easy run produces a field name that won't resolve and the
        # target is simply skipped (surfaced in the editor as "not defined for …").
        return f"{DIFFICULTY_SUFFIX_MAP.get(target_difficulty, target_difficulty)} {field}"
    if op.get('diff_prefix_nl'):
        # Two-tier fields that only define Normal + Legendary (e.g. H2 Body/Shield
        # Vitality): Impossible -> Legendary, every other difficulty -> Normal.
        tier = 'Legendary' if target_difficulty == 'Impossible' else 'Normal'
        return f"{tier} {field}"
    return field


def _apply_derived(m, cls, path, effect_name, op, plugin):
    """Write a derived field (sum of its source fields' current values) into
    every tag matching (cls, path). Needs the per-tag read/write interface of
    the H2 parser; H1 has no derived fields."""
    field, block = op['field'], op.get('block')
    index = op.get('index', 0) or 0
    ref = f"{cls} {path}"
    if not hasattr(m, 'p2o'):  # H2-only marker; H1 HaloMap also has read_tag_field
        return [{'effect': effect_name, 'tag': ref, 'field': field,
                 'ok': False, 'skip': True, 'reason': 'derived fields are Halo 2 only'}]
    tags = m.find_tags(cls, path)
    if not tags:
        return [{'effect': effect_name, 'tag': ref, 'field': field,
                 'ok': False, 'reason': 'not present in this map'}]
    results = []
    for tpath, tbase in tags:
        vals = [m.read_tag_field(tbase, sf, plugin, block, index)
                for sf in op['derived']]
        r = {'effect': effect_name, 'tag': f"{cls} {tpath}", 'field': field,
             'derived': True}
        if any(v is None for v in vals):
            results.append({**r, 'ok': False, 'reason': 'source field unresolved'})
            continue
        total = sum(vals)
        old = m.write_tag_field(tbase, field, total, plugin, block, index)
        if old is None:
            results.append({**r, 'ok': False, 'reason': 'derived field unresolved'})
        else:
            results.append({**r, 'ok': True, 'old': old, 'new': total})
    return results


def _apply_init_defaults(m, spec, registry):
    """One-time seeding of an enemy that lacks a field/block by default (e.g. Elite
    grenades): copy defaults from a `source` tag onto every target variant that
    isn't set yet. Runs BEFORE the effect's normal ops. `spec` (already resolved to
    the active game):
      tag           target variant wildcard (e.g. 'actv characters\\elite\\*')
      source        tag to read defaults from (e.g. Grunt Minor / base Grunt)
      block         (H2) tagblock holding the fields; grown if empty
      grow          (H2) True -> copy source's whole block element into an empty block
      copy          (H1) list of root field names to copy from source
      set           {field: value} forced values (enum names allowed, e.g.
                    'Grenade Stimulus': 'Visible Target')
      only_if_zero  a field that must read 0/None on the target for it to be seeded
    """
    out = []
    cls, path = hm.split_tag(spec['tag'])
    plugin = registry.get(cls)
    if plugin is None:
        return [{'effect': 'init defaults', 'ok': False, 'reason': f'no plugin for {cls}'}]
    scls, spath = hm.split_tag(spec['source'])
    src = m.find_tags(scls, spath)
    if not src:
        return [{'effect': 'init defaults', 'ok': False, 'reason': f'init source {spath} not in map'}]
    src_base = src[0][1]
    block = spec.get('block')

    if spec.get('grow') and block and hasattr(m, 'append_block_element'):
        bf = next((f for f in plugin.fields
                   if f['block_chain'] and f['block_chain'][-1].lower() == block.lower()), None)
        if not bf:
            return [{'effect': 'init defaults', 'ok': False, 'reason': f'block {block} not in plugin'}]
        boff, esize = bf['block_offsets'][-1], bf['block_sizes'][-1]
        if m.i32(src_base + boff) == 0:
            return [{'effect': 'init defaults', 'ok': False, 'reason': 'init source block empty'}]
        src_leaf = m.follow(src_base, [boff], [esize], 0)
        elem = bytes(m.data[src_leaf:src_leaf + esize])
        for tpath, base in m.find_tags(cls, path):
            if m.i32(base + boff) == 0:
                m.append_block_element(base, boff, esize, elem)
                out.append({'effect': 'init defaults', 'tag': f'{cls} {tpath}', 'ok': True,
                            'old': '(empty)', 'new': f'{block} seeded'})
        return out

    copy_fields = spec.get('copy', []) or []
    set_map = spec.get('set', {}) or {}
    only_zero = spec.get('only_if_zero')
    srcvals = {f: m.read_tag_field(src_base, f, plugin, block=block) for f in copy_fields}
    for tpath, base in m.find_tags(cls, path):
        if only_zero is not None:
            cur = m.read_tag_field(base, only_zero, plugin, block=block)
            if cur not in (0, 0.0, None):
                continue
        n = 0
        for f in copy_fields:
            if srcvals.get(f) is not None and m.write_tag_field(base, f, srcvals[f], plugin, block=block) is not None:
                n += 1
        for f, val in set_map.items():
            fld = plugin.find(f, block)
            v = fld['options'].get(str(val).strip().lower()) if (fld and fld.get('options') and isinstance(val, str)) else val
            if v is not None and m.write_tag_field(base, f, v, plugin, block=block) is not None:
                n += 1
        if n:
            out.append({'effect': 'init defaults', 'tag': f'{cls} {tpath}', 'ok': True,
                        'old': '(unset)', 'new': f'{n} default(s) set'})
    return out


# scnr Player Starting Profile weapon-slot byte layout per game. A weapon tagRef is
# ['weap' magic @0][ ... ][id]; H1 is 16 bytes (ident at +0xC), H2 is 8 bytes
# (datum at +0x4). Round fields (int16) follow the ref within the profile element.
_WEAP_MAGIC = 0x77656170
_STARTING_SLOTS = {
    'Halo 1': {'ref_size': 16, 'id_at': 0xC,
               'primary':   {'ref': 0x28, 'loaded': 0x38, 'total': 0x3A},
               'secondary': {'ref': 0x3C, 'loaded': 0x4C, 'total': 0x4E}},
    'Halo 2': {'ref_size': 8, 'id_at': 0x4,
               'primary':   {'ref': 0x28, 'loaded': 0x30, 'total': 0x32},
               'secondary': {'ref': 0x34, 'loaded': 0x3C, 'total': 0x3E}},
    # H3's profile element is 0x58 (MCC) but the weapon slots sit exactly where H1
    # puts them, with the same 16-byte tagRef. Verified against all 11 campaign maps.
    'Halo 3': {'ref_size': 16, 'id_at': 0xC,
               'primary':   {'ref': 0x28, 'loaded': 0x38, 'total': 0x3A},
               'secondary': {'ref': 0x3C, 'loaded': 0x4C, 'total': 0x4E}},
}

# H3 tag idents are (index + salt) << 16 | index. Sampling every tagRef in the
# starting-profile block of all 11 campaign maps gives salt 0xE176 for 159 of 160
# refs, so it's the formula — but the map is asked first (see _h3_ident_salt) and
# this is only the fallback, since one outlier shows the salt isn't truly fixed.
_H3_IDENT_SALT = 0xE176


def _h3_ident_salt(m, scnr_base, boff, esize, count):
    """Recover this map's tag-ident salt from the tagRefs already in its starting
    profiles, so we mint idents the way the map itself does. Falls back to the
    observed constant when a map has no usable reference to learn from."""
    seen = {}
    for i in range(count):
        poff = m.follow(scnr_base, [boff], [esize], i)
        if poff is None:
            continue
        for ro in (0x28, 0x3C):
            rid = struct.unpack_from('<I', m.data, poff + ro + 0xC)[0]
            if rid == 0xFFFFFFFF:
                continue
            idx = rid & 0xFFFF
            t = m.tag(idx)
            if t and t.get('class') == 'weap':
                d = ((rid >> 16) - idx) & 0xFFFF
                seen[d] = seen.get(d, 0) + 1
    return max(seen, key=seen.get) if seen else _H3_IDENT_SALT


def _h3_profile_role(index, name):
    """('chief'|'dervish'|None, is_respawn) for a Player Starting Profile.

    Names are only trustworthy on some maps: 020_base, 030_outskirts, 070_waste and
    120_halo leave the four player profiles named 'player starting profile_N' or
    blank. The index convention does hold everywhere -- 0/1 are chief initial/respawn
    and 2/3 dervish initial/respawn, confirmed by the covenant weapons 2/3 always
    carry. So trust an explicit chief/dervish name where there is one, and fall back
    to the index only for generic/unnamed profiles. Named NPC profiles (marine_*,
    barracks_*, arbiter_*, johnson_swap, elite_insertion, shotty_man...) match
    neither rule and are deliberately left alone."""
    n = (name or '').strip().lower()
    generic = (not n) or n.startswith('player starting profile')
    if 'dervish' in n:
        role = 'dervish'
    elif 'chief' in n:
        role = 'chief'
    elif generic and index in (0, 1):
        role = 'chief'
    elif generic and index in (2, 3):
        role = 'dervish'
    else:
        return None, False
    return role, ('respawn' in n) or (generic and index in (1, 3))


def _weap_ref_id(m, name, game=None, salt=None):
    """Full tag ident (H1/H3) / datum (H2) for a weap tag by name, or None if that
    tag isn't in this map — the safety net for a picked weapon the map lacks."""
    if game == 'Halo 3':                                    # H3: mint the ident
        for t in getattr(m, 'tags', []):
            if t.get('class') == 'weap' and t.get('name') == name:
                i = t['index']
                s = _H3_IDENT_SALT if salt is None else salt
                return (((i + s) & 0xFFFF) << 16) | (i & 0xFFFF)
        return None
    if isinstance(getattr(m, 'tags', None), dict):          # H1 HaloMap
        for i in range(m.tag_count):
            b = m.tag_array_off + i * 32
            if bytes(m.data[b:b + 4][::-1]).decode('latin1') != 'weap':
                continue
            try:
                if m._cstr((m.u32(b + 0x10) - m.magic) & 0xFFFFFFFF) == name:
                    return m.u32(b + 0xC)
            except Exception:
                pass
        return None
    for t in getattr(m, 'tags', []):                        # H2 Halo2Map
        if t.get('class') == 'weap' and t.get('name') == name:
            return t.get('datum')
    return None


def _weap_base(m, name):
    if isinstance(getattr(m, 'tags', None), dict):
        return m.tags.get(('weap', name))
    for t in getattr(m, 'tags', []):
        if t.get('class') == 'weap' and t.get('name') == name:
            return t.get('base')
    return None


def _scnr_base(m):
    if hasattr(m, 'scenario_tag'):                          # H2
        t = m.scenario_tag()
        return t['base'] if t else None
    tags = m.find_tags('scnr', 'levels' + chr(92) + '*')    # H1
    return tags[0][1] if tags else None


def _write_starting_weapon(m, poff, slot, refid, loaded, total, game):
    lay = _STARTING_SLOTS[game]
    s = lay[slot]
    ro = poff + s['ref']
    struct.pack_into('<I', m.data, ro, _WEAP_MAGIC)
    if lay['ref_size'] == 16:
        struct.pack_into('<II', m.data, ro + 4, 0, 0)       # clear the H1 name-ptr words
    struct.pack_into('<I', m.data, ro + lay['id_at'], refid & 0xFFFFFFFF)
    if loaded is not None:
        struct.pack_into('<h', m.data, poff + s['loaded'], max(-32768, min(32767, int(loaded))))
    if total is not None:
        struct.pack_into('<h', m.data, poff + s['total'], max(-32768, min(32767, int(total))))


def _null_starting_weapon(m, poff, slot, game):
    """Empty a profile's weapon slot: a null tagRef (class + id both -1) and 0 rounds.
    A null secondary is common in vanilla profiles; a null primary starts the player
    empty-handed."""
    lay = _STARTING_SLOTS[game]
    s = lay[slot]
    ro = poff + s['ref']
    struct.pack_into('<I', m.data, ro, 0xFFFFFFFF)
    if lay['ref_size'] == 16:
        struct.pack_into('<II', m.data, ro + 4, 0, 0)
    struct.pack_into('<I', m.data, ro + lay['id_at'], 0xFFFFFFFF)
    struct.pack_into('<h', m.data, poff + s['loaded'], 0)
    struct.pack_into('<h', m.data, poff + s['total'], 0)


def _profile_is_empty(m, poff, game):
    """True if this profile's Primary weapon slot is a null tagRef."""
    lay = _STARTING_SLOTS[game]
    ro = poff + lay['primary']['ref'] + lay['id_at']
    return struct.unpack_from('<I', m.data, ro)[0] == 0xFFFFFFFF


def _apply_starting_equipment(m, game, registry, starting):
    """Set the player Starting Profile weapons from the run's picks. `starting` =
    {'primary': weap-tag or None, 'secondary': weap-tag or None, 'profiles': [..]}.
    Rounds come from each weap tag's CURRENT Magazines values (so a Magazine effect
    already applied this run carries through; else vanilla). Missing weapons are
    skipped, not written (safety net)."""
    out = []
    scnr_plug = registry.get('scnr')
    weap_plug = registry.get('weap')
    scnr_base = _scnr_base(m)
    if scnr_plug is None or scnr_base is None:
        return [{'effect': 'starting weapons', 'ok': False,
                 'reason': 'scnr plugin/tag unavailable'}]
    bf = None
    for fn in ('Starting Health Damage', 'Starting Health Modifier'):
        bf = scnr_plug.find(fn, 'Player Starting Profile')
        if bf:
            break
    lay = _STARTING_SLOTS.get(game)
    if not bf or not lay:
        return [{'effect': 'starting weapons', 'ok': False,
                 'reason': 'Player Starting Profile layout unavailable'}]
    boff = bf['block_offsets'][-1]
    esize = bf['block_sizes'][-1]
    count = m.i32(scnr_base + boff)
    salt = _h3_ident_salt(m, scnr_base, boff, esize, count) if game == 'Halo 3' else None

    def _null_profiles(idxs, label):
        for i in idxs:
            poff = m.follow(scnr_base, [boff], [esize], i)
            if poff is None:
                continue
            for slot in ('primary', 'secondary'):
                _null_starting_weapon(m, poff, slot, game)
            out.append({'effect': 'starting weapons', 'field': label(i),
                        'ok': True, 'old': 'weapons', 'new': 'emptied (null)'})

    # A plan of (weapon slot, [profile indices], weap tag, report label). H3 with
    # 2-player coop is the only case where the two picks land on different profiles
    # rather than the two slots of the same one (#8).
    prim, sec = starting.get('primary'), starting.get('secondary')
    if game == 'Halo 3' and starting.get('h3_coop'):
        roles = {}
        for i in range(count):
            poff = m.follow(scnr_base, [boff], [esize], i)
            if poff is None:
                continue
            nm = bytes(m.data[poff:poff + 0x20]).split(b'\0')[0].decode('latin1', 'replace')
            roles[i] = _h3_profile_role(i, nm)
        # The coop options act on the respawn profiles here, not on a fixed index 1.
        null_respawn = bool(starting.get('null_respawn'))
        hold_respawn = bool(starting.get('skip_respawn')) or null_respawn
        if null_respawn:
            _null_profiles([i for i, (r, resp) in sorted(roles.items()) if r and resp],
                           lambda i: f'Profile {i} (respawn)')
        def _of(role):
            return [i for i, (r, resp) in sorted(roles.items())
                    if r == role and not (hold_respawn and resp)]
        # guard_empty: this path matches profiles by role rather than by an index the
        # user named, so it can sweep in scripted weaponless ones (chief_pre_training).
        plan = [('primary', _of('chief'), prim, 'Chief Weapon', True),
                ('primary', _of('dervish'), sec, 'Dervish Weapon', True)]
    else:
        # Pre-H3, and H3 with coop off: both picks go on the same profile(s), P1 as
        # Primary and P2 as Secondary. H3 uses profile 0 only — its other profiles
        # belong to the second character or to NPCs.
        default = [0] if game == 'Halo 3' else [0, 1]
        _null_profiles([p for p in (starting.get('null_profiles') or []) if 0 <= p < count],
                       lambda i: f'Profile {i}')
        profiles = [i for i in (starting.get('profiles') or default) if 0 <= i < count]
        if game == 'Halo 3':
            profiles = [i for i in profiles if i == 0]
        # No guard here: these profiles were named outright, and a map that starts
        # the player unarmed on purpose (Halo 1's a10) should still honour the picks.
        plan = [('primary', profiles, prim, 'Primary Weapon', False),
                ('secondary', profiles, sec, 'Secondary Weapon', False)]

    null_empty = bool(starting.get('null_empty_slots'))
    for slot, profiles, tag, label, guard_empty in plan:
        if not tag:
            # #5: nothing to put here (a grenade pick, or no second player). Empty the
            # slot so the setting visibly takes effect instead of leaving the map's
            # vanilla weapon in place. Profiles already empty are left alone.
            if null_empty:
                n = 0
                for i in profiles:
                    poff = m.follow(scnr_base, [boff], [esize], i)
                    if poff is None or (guard_empty and _profile_is_empty(m, poff, game)):
                        continue
                    _null_starting_weapon(m, poff, slot, game)
                    n += 1
                if n:
                    out.append({'effect': 'starting weapons', 'field': label, 'ok': True,
                                'old': 'map default', 'new': f'emptied on {n} profile(s)'})
            continue
        _, name = hm.split_tag(tag)
        short = name.rsplit(chr(92), 1)[-1]
        refid = _weap_ref_id(m, name, game, salt)
        if refid is None:      # SAFETY NET: weapon tag absent from this map
            out.append({'effect': 'starting weapons', 'field': label,
                        'ok': False, 'reason': f'weapon not in this map: {short}'})
            continue
        wb = _weap_base(m, name)
        loaded = total = None
        if wb is not None and weap_plug is not None:
            loaded = m.read_tag_field(wb, 'Rounds Loaded Maximum', weap_plug, block='Magazines', index=0)
            total = m.read_tag_field(wb, 'Rounds Total Maximum', weap_plug, block='Magazines', index=0)
        # Battery weapons (energy sword, plasma pistol) have no Magazines block, so
        # there are no counts to copy. Vanilla profiles store 0 for these, not the
        # -1 the plugin calls "weapon default" (-1 didn't actually read back as a
        # default in testing), so match vanilla rather than leaving the replaced
        # weapon's counts behind.
        loaded = 0 if loaded is None else loaded
        total = 0 if total is None else total
        n = 0
        for i in profiles:
            poff = m.follow(scnr_base, [boff], [esize], i)
            if poff is None:
                continue
            # A null Primary is deliberate: it's a scripted empty-handed state
            # (chief_pre_training, no_weapon_profile, injured_profile...). Arming
            # those breaks the scene, so leave any weaponless profile weaponless.
            if guard_empty and _profile_is_empty(m, poff, game):
                continue
            _write_starting_weapon(m, poff, slot, refid, loaded, total, game)
            n += 1
        out.append({'effect': 'starting weapons', 'field': label,
                    'ok': True, 'old': short,
                    'new': f'set on {n} profile(s) ({loaded}/{total} rounds)'})
    return out


# ---- Skulls -----------------------------------------------------------------
# "Betrayal": every human squad turns on the player. Campaign maps leave squad
# Team at Default and let the engine resolve allegiance from the character, so
# flipping sides means writing an explicit Team on the squads that are human.
#
# H1 keeps allegiance per ENCOUNTER (squads hang off the encounter); H2 and H3
# keep it per SQUAD, reaching the character through a palette -- directly in H2,
# via the Fire-Teams sub-block in H3.
# Which side the betrayed humans join, per game. Not Covenant: a third faction reads
# as its own event and keeps the Covenant fighting them too. H1's enum has no Heretic
# (slot 6 is Unused6), so Flood is the only real third option there. H3 does define
# Heretic even though the campaign has none, so its allegiances are untested —
# see the note in halo.json's Betrayal entry.
_BETRAYAL_TEAM = {'Halo 1': 4, 'Halo 2': 6, 'Halo 3': 6}   # Flood / Heretic / Heretic
_BETRAYAL = {
    'Halo 2': {'squads': (0x160, 0x74), 'team': 0x24, 'char_idx': 0x36,
               'palette': (0x178, 0x08), 'pal_id_at': 0x4, 'fireteams': None},
    'Halo 3': {'squads': (0x384, 0x40), 'team': 0x24, 'char_idx': 0x8,
               'palette': (0x3A8, 0x10), 'pal_id_at': 0xC, 'fireteams': (0x30, 0x60)},
}
# Characters whose squads count as "human" for Betrayal. Matched against the last
# path component of the character/actor tag name. Keep these specific: a loose word
# like "commander" also matches `elite commander energy sword`, which flipped a
# Covenant encounter on b30 until it was removed.
_HUMAN_WORDS = ('marine', 'crewman', 'captain', 'johnson', 'miranda', 'keyes',
                'sergeant', 'pilot', 'civilian', 'odst')


# Belt-and-braces: whatever _HUMAN_WORDS matches, a tag naming a Covenant/Flood/
# Sentinel species is never human. Checked against the WHOLE path, since the species
# usually shows up in a parent folder (`characters\elite\elite commander\...`).
_NONHUMAN_WORDS = ('elite', 'grunt', 'jackal', 'brute', 'hunter', 'flood', 'sentinel',
                   'drone', 'engineer', 'prophet', 'monitor', 'bugger', 'skirmisher')


# Humans that stay loyal: a squad containing one of these never flips, even though
# it classifies as human. Johnson is scripted in several missions and turning him
# hostile breaks those sequences.
_BETRAYAL_LOYAL = ('johnson', 'miranda')


def _is_loyal_tag(name):
    return bool(name) and any(w in name.lower() for w in _BETRAYAL_LOYAL)


def _is_human_tag(name):
    if not name:
        return False
    low = name.lower()
    if any(w in low for w in _NONHUMAN_WORDS):
        return False
    return any(w in low.rsplit(chr(92), 1)[-1] for w in _HUMAN_WORDS)


def _apply_betrayal(m, game, registry):
    """Flip every human squad/encounter onto a hostile third faction (see
    _BETRAYAL_TEAM): Flood in Halo 1, Heretic in Halo 2 and 3."""
    scnr_base = _scnr_base(m)
    if scnr_base is None:
        return [{'effect': 'Betrayal', 'ok': False, 'reason': 'scenario tag unavailable'}]

    team = _BETRAYAL_TEAM.get(game)
    if team is None:
        return [{'effect': 'Betrayal', 'ok': False, 'reason': f'not supported in {game}'}]
    team_name = {4: 'Flood', 6: 'Heretic'}.get(team, str(team))

    flipped, skipped = [], 0
    if game == 'Halo 1':
        # H1: allegiance is per encounter, and an encounter's squads name actors
        # from the Actor Palette. Proven in-game on a10.
        pal = m.follow_all(scnr_base, [0x420], [0x10], 'all')
        names = []
        for el in pal:
            ident = struct.unpack_from('<I', m.data, el + 0xC)[0]
            names.append(_tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None)
        for e in m.follow_all(scnr_base, [0x42C], [0xB0], 'all'):
            kinds = set()
            for sq in m.follow_all(e, [0x80], [0xE8], 'all'):
                ati = struct.unpack_from('<h', m.data, sq + 0x20)[0]
                if 0 <= ati < len(names) and names[ati]:
                    kinds.add(names[ati])
            if not kinds:
                continue
            if all(_is_human_tag(k) for k in kinds) and not any(_is_loyal_tag(k) for k in kinds):
                struct.pack_into('<h', m.data, e + 0x24, team)
                flipped.append(_cstr_at(m, e))
            else:
                skipped += 1
        label = 'encounters'
    else:
        lay = _BETRAYAL.get(game)
        if not lay:
            return [{'effect': 'Betrayal', 'ok': False, 'reason': f'not supported in {game}'}]
        poff, pel = lay['palette']
        names = []
        for el in m.follow_all(scnr_base, [poff], [pel], 'all'):
            ident = struct.unpack_from('<I', m.data, el + lay['pal_id_at'])[0]
            names.append(_tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None)
        soff, sel = lay['squads']
        for sq in m.follow_all(scnr_base, [soff], [sel], 'all'):
            idxs = []
            if lay['fireteams']:
                foff, fel = lay['fireteams']
                for ft in m.follow_all(sq, [foff], [fel], 'all'):
                    idxs.append(struct.unpack_from('<h', m.data, ft + lay['char_idx'])[0])
            else:
                idxs.append(struct.unpack_from('<h', m.data, sq + lay['char_idx'])[0])
            kinds = {names[i] for i in idxs if 0 <= i < len(names) and names[i]}
            if not kinds:
                continue
            if all(_is_human_tag(k) for k in kinds) and not any(_is_loyal_tag(k) for k in kinds):
                struct.pack_into('<h', m.data, sq + lay['team'], team)
                flipped.append(_cstr_at(m, sq))
            else:
                skipped += 1
        label = 'squads'
    return [{'effect': 'Betrayal', 'field': f'Squad Team ({label})', 'ok': True,
             'old': 'as the map defines', 'new': f'{len(flipped)} human {label} -> {team_name}',
             'detail': ', '.join(flipped[:12]) + ('…' if len(flipped) > 12 else '')}]


def _cstr_at(m, off, limit=0x20):
    return bytes(m.data[off:off + limit]).split(b'\0')[0].decode('latin1', 'replace')


# scnr weapon-placement + palette layout per game (Weapons list, Weapon Palette).
_MAP_WEAPONS = {
    'Halo 1': {'weapons': (0x270, 0x5C), 'palette': (0x27C, 0x30), 'pal_id_at': 0xC,
               'palette_index': 0x0, 'rounds_left': 0x48, 'rounds_loaded': 0x4A},
    'Halo 2': {'weapons': (0x90, 0x54), 'palette': (0x98, 0x28), 'pal_id_at': 0x4,
               'palette_index': 0x0, 'rounds_left': 0x4C, 'rounds_loaded': 0x4E},
}


def _tag_name_by_id(m, rid):
    row = rid & 0xFFFF
    if hasattr(m, 'tag'):                                   # H2
        t = m.tag(row)
        return t['name'] if t else None
    b = m.tag_array_off + row * 32                          # H1
    try:
        return m._cstr((m.u32(b + 0x10) - m.magic) & 0xFFFFFFFF)
    except Exception:
        return None


def _block_base(m, off):
    ptr = m.u32(off + 4)
    return m.p2o(ptr) if hasattr(m, 'p2o') else (ptr - m.magic) & 0xFFFFFFFF


def _spread_slots(N, counts):
    """Assign each (key, count) `count` placement slots EVENLY spread across [0, N)
    — evenly-spaced positions with collisions bumped to the nearest free slot, so a
    weapon's replacements are scattered through the level (not clustered up front),
    and different weapons interleave. Returns {slot_index: key}."""
    target = {}
    for key, c in counts:
        if c <= 0:
            continue
        for k in range(c):
            pos = min(int((k + 0.5) * N / c), N - 1)
            if pos not in target:
                target[pos] = key
                continue
            for d in range(1, N):
                if pos + d < N and (pos + d) not in target:
                    target[pos + d] = key
                    break
                if pos - d >= 0 and (pos - d) not in target:
                    target[pos - d] = key
                    break
            else:
                break
    return target


def _apply_weapon_swaps(m, game, registry, swaps):
    """Replace a fraction of the map's weapon placements with the players' picked
    weapons, scattered evenly. `swaps` = {weap-tag: rate 0..1}. Rounds are set to the
    weapon's VANILLA magazine values (this runs BEFORE the effect ops, so Magazine
    picks don't apply). Weapons absent from the map's Weapon Palette are skipped."""
    out = []
    lay = _MAP_WEAPONS.get(game)
    scnr_base = _scnr_base(m)
    if not lay or scnr_base is None:
        return [{'effect': 'map weapons', 'ok': False, 'reason': 'scnr/layout unavailable'}]
    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    N = m.i32(scnr_base + woff)
    if N <= 0:
        return [{'effect': 'map weapons', 'ok': False, 'reason': 'no weapon placements in map'}]
    wbase = _block_base(m, scnr_base + woff)
    pbase = _block_base(m, scnr_base + poff)
    pcount = m.i32(scnr_base + poff)
    pal = {i: _tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at'])) for i in range(pcount)}
    weap_plug = registry.get('weap')

    assign = []          # (palette_index, count, rounds_left, rounds_loaded, short)
    for tag, rate in swaps.items():
        if not rate or rate <= 0:
            continue
        _, name = hm.split_tag(tag)
        short = name.rsplit(chr(92), 1)[-1]
        pi = next((i for i, n in pal.items() if n == name), None)
        if pi is None:                          # SAFETY NET: not in the map's palette
            out.append({'effect': 'map weapons', 'field': short, 'ok': False,
                        'reason': 'weapon not in this map\'s palette'})
            continue
        c = int(round(rate * N))
        if c <= 0:
            out.append({'effect': 'map weapons', 'field': short, 'ok': True, 'skip': True,
                        'reason': f'rate too low for {N} placements (rounds to 0)'})
            continue
        rl = rd = -1
        wb = _weap_base(m, name)
        if wb is not None and weap_plug is not None:
            t = m.read_tag_field(wb, 'Rounds Total Maximum', weap_plug, block='Magazines', index=0)
            l = m.read_tag_field(wb, 'Rounds Loaded Maximum', weap_plug, block='Magazines', index=0)
            rl = int(t) if t is not None else -1
            rd = int(l) if l is not None else -1
        assign.append((pi, c, rl, rd, short))

    # never replace more than N placements (UI caps the slider sum, this is a guard)
    while sum(a[1] for a in assign) > N and assign:
        j = max(range(len(assign)), key=lambda k: assign[k][1])
        pi, c, rl, rd, s = assign[j]
        assign[j] = (pi, c - 1, rl, rd, s)

    slots = _spread_slots(N, [(a[0], a[1]) for a in assign])
    info = {a[0]: (a[2], a[3], a[4]) for a in assign}
    done = {}
    for slot, pi in slots.items():
        e = wbase + slot * wes
        struct.pack_into('<h', m.data, e + lay['palette_index'], pi)
        rl, rd, short = info[pi]
        if rl >= 0:
            struct.pack_into('<h', m.data, e + lay['rounds_left'], max(-32768, min(32767, rl)))
        if rd >= 0:
            struct.pack_into('<h', m.data, e + lay['rounds_loaded'], max(-32768, min(32767, rd)))
        done[short] = done.get(short, 0) + 1
    for short, n in done.items():
        out.append({'effect': 'map weapons', 'field': short, 'ok': True,
                    'old': f'{N} placements', 'new': f'{n} swapped in'})
    # a pick that survived rate-rounding but got trimmed to 0 by the N cap
    for _pi, _c, _rl, _rd, short in assign:
        if done.get(short, 0) == 0:
            out.append({'effect': 'map weapons', 'field': short, 'ok': True, 'skip': True,
                        'reason': f'trimmed to 0 (total capped at {N} placements)'})
    return out


# --- zoom-UI copy: give a scopeless weapon a working scope overlay -----------
# The scope lives in the weapon's HUD tag (H2 nhdt / H1 wphi), reached via the weap
# tag's HUD-interface tagRef. We copy the donor's scope sub-elements into the target
# HUD by growing the relevant block(s). Elements are copied verbatim, so embedded
# tagRefs (scope masks/bitmaps) keep their map-global datums and resolve to the
# donor's art in place.
#
# H1 needs BOTH parts of the scope: the full-screen mask is a "Screen Effect" block
# element (with Mask tagRefs), and the reticle is a "Zoom Overlay" Crosshair. A HUD
# is "scoped" iff it has a Screen Effect. H2's scope is a set of zoom-gated Bitmap
# Widgets (flat), gated on the [Yes]Unit "Zoomed" flag bits. Each source block gives
# a selector (which elements are the scope) and, if its elements carry a child
# reflexive (H1 Crosshair -> Crosshair Overlays), a (child_off, child_elem) to
# relocate into the target's own tag data so the copy owns it (see _selfcontain).
_ZOOM_UI = {
    'Halo 1': {'hud_ref': 0x480, 'id_at': 0xC,
               'scoped_block': 0xAC,       # Screen Effect present => already scoped
               'donor_pref': ('sniper rifle', 'pistol'),
               'blocks': [
                   {'off': 0xAC, 'elem': 0xB8, 'sel': ('all',), 'child': None},        # scope mask
                   {'off': 0x84, 'elem': 0x68, 'sel': ('eq', 0x0, 1),                   # zoom reticle
                    'child': (0x34, 0x6C)},                                            # Crosshair Overlays
               ]},
    'Halo 2': {'hud_ref': 0x2B0, 'id_at': 0x4,
               'scoped_block': None,       # detected via the zoom-gated widget selector
               'donor_pref': ('sniper_rifle', 'beam_rifle', 'battle_rifle'),
               'blocks': [
                   {'off': 0x8, 'elem': 0x64, 'sel': ('and', 0x8, 0b11 << 7), 'child': None},
               ]},
}


def _selfcontain(m, elem, child):
    """H1: relocate an element's child reflexive block into freshly appended tag
    data and repoint it there, so the copied element owns its child instead of
    pointing into the donor tag (which the H1 engine won't render across tags).
    `child` = (child_reflexive_offset, child_elem_size); None -> element unchanged."""
    if not child:
        return elem
    coff, cesz = child
    cnt = struct.unpack_from('<I', elem, coff)[0]
    ptr = struct.unpack_from('<I', elem, coff + 4)[0]
    if cnt <= 0:
        return elem
    src = (ptr - m.magic) & 0xFFFFFFFF
    new_off = m.append_raw(bytes(m.data[src:src + cnt * cesz]))
    b = bytearray(elem)
    struct.pack_into('<I', b, coff + 4, (new_off + m.magic) & 0xFFFFFFFF)
    return bytes(b)


def _hud_base(m, game, weap_base):
    """Follow a weap tag's HUD-interface tagRef to its HUD tag's base offset."""
    z = _ZOOM_UI[game]
    rid = m.u32(weap_base + z['hud_ref'] + z['id_at'])
    if rid in (0, 0xFFFFFFFF):
        return None
    row = rid & 0xFFFF
    if hasattr(m, 'tag'):                                   # H2: datum row -> tag
        t = m.tag(row)
        return t['base'] if t else None
    b = m.tag_array_off + row * 32                          # H1: tag-array meta_ptr
    off = (m.u32(b + 0x14) - m.magic) & 0xFFFFFFFF
    return off if 0 <= off < len(m.data) else None


def _block_elems(m, hud_base, bs):
    """Elements of one HUD source block matching its selector (list of raw bytes)."""
    cnt = m.i32(hud_base + bs['off'])
    if cnt <= 0:
        return []
    off = _block_base(m, hud_base + bs['off'])
    sel = bs['sel']
    out = []
    for i in range(cnt):
        e = off + i * bs['elem']
        if sel[0] == 'all':
            hit = True
        else:
            val = struct.unpack_from('<H', m.data, e + sel[1])[0]
            hit = (val == sel[2]) if sel[0] == 'eq' else bool(val & sel[2])
        if hit:
            out.append(bytes(m.data[e:e + bs['elem']]))
    return out


def _hud_is_scoped(m, game, hud_base):
    """True if this HUD already renders a scope (so we leave it alone)."""
    z = _ZOOM_UI[game]
    if z['scoped_block'] is not None:                      # H1: Screen Effect present
        return m.i32(hud_base + z['scoped_block']) > 0
    return bool(_block_elems(m, hud_base, z['blocks'][0]))  # H2: a zoom-gated widget


def _zoom_donor(m, game, exclude_hud, prefer=None):
    """The scoped donor weapon to copy from (its HUD base + short name), or
    (None, None). If `prefer` (a weap tag path) names a weapon that is present and
    scoped on this map, it wins; otherwise the best configured/auto donor is used."""
    z = _ZOOM_UI[game]
    if prefer:
        _, pname = hm.split_tag(prefer)
        wb = _weap_base(m, pname)
        if wb is not None:
            hud = _hud_base(m, game, wb)
            if hud is not None and hud != exclude_hud and _hud_is_scoped(m, game, hud):
                return hud, pname.rsplit(chr(92), 1)[-1]
    if isinstance(getattr(m, 'tags', None), dict):          # H1
        weaps = [(n, off) for (c, n), off in m.tags.items() if c == 'weap']
    else:                                                   # H2
        weaps = [(t['name'], t['base']) for t in m.tags
                 if t.get('class') == 'weap' and t.get('base')]
    cands = []
    for name, wb in weaps:
        hud = _hud_base(m, game, wb)
        if hud is None or hud == exclude_hud or not _hud_is_scoped(m, game, hud):
            continue
        cands.append((name, hud))
    if not cands:
        return None, None
    pref = z['donor_pref']
    cands.sort(key=lambda it: (pref.index(it[0].rsplit(chr(92), 1)[-1])
                               if it[0].rsplit(chr(92), 1)[-1] in pref else len(pref)))
    name, hud = cands[0]
    return hud, name.rsplit(chr(92), 1)[-1]


def _apply_zoom_ui(m, game, targets, prefer_donor=None):
    """Give each target weapon (weap tag paths) a scope if its HUD lacks one, by
    copying every scope source block from a donor weapon on the map. `prefer_donor`
    (a weap tag path) is used when present + scoped, else an auto donor. Idempotent:
    a HUD already scoped (vanilla, or shared with a weapon patched earlier this run)
    is left alone."""
    z = _ZOOM_UI.get(game)
    out = []
    if not z:
        return out
    grown = set()
    for tag in targets:
        _, name = hm.split_tag(tag)
        short = name.rsplit(chr(92), 1)[-1]
        wb = _weap_base(m, name)
        if wb is None:
            out.append({'effect': 'zoom UI', 'field': short, 'ok': False,
                        'reason': 'weapon not in this map'})
            continue
        hud = _hud_base(m, game, wb)
        if hud is None:
            out.append({'effect': 'zoom UI', 'field': short, 'ok': False,
                        'reason': 'weapon has no HUD interface'})
            continue
        if hud in grown or _hud_is_scoped(m, game, hud):
            out.append({'effect': 'zoom UI', 'field': short, 'ok': True, 'skip': True,
                        'old': short, 'new': 'already has a scope — unchanged'})
            continue
        donor_hud, donor = _zoom_donor(m, game, exclude_hud=hud, prefer=prefer_donor)
        if donor_hud is None:
            out.append({'effect': 'zoom UI', 'field': short, 'ok': False,
                        'reason': 'no scoped donor weapon in this map'})
            continue
        copied = 0
        for bs in z['blocks']:
            elems = _block_elems(m, donor_hud, bs)
            if not elems:
                continue
            if bs['child']:                # relocate each element's child sub-block
                elems = [_selfcontain(m, e, bs['child']) for e in elems]
            m.grow_block(hud, bs['off'], bs['elem'], elems)
            copied += len(elems)
        grown.add(hud)
        out.append({'effect': 'zoom UI', 'field': short, 'ok': True, 'old': short,
                    'new': f'scope copied from {donor} ({copied} element(s))'})
    return out


def apply_run(map_path, plan, registry, target_difficulty, backup=True, game=None,
              starting=None, weapon_swaps=None, zoom_ui=None, zoom_donor=None,
              from_baseline=True, remove_cutscenes=False, skulls=()):
    """Apply a plan to the map. Each plan item: {tag, name, ops:[{field, block,
    difficulty, op_str}]}. `starting` optionally sets the player Starting Profile
    weapons. Returns (results, backup_path). The map is only saved (and a one-time
    .bak made) if at least one write succeeds.

    Patching is idempotent: whenever a .bak (the pristine original) exists, the
    map is rebuilt FROM that baseline rather than compounded onto the live file.
    So re-patching never double-applies, and dropping an effect from the plan
    (e.g. a spent one-map Exhaust) cleanly removes it — the baseline restores the
    bytes and only the remaining effects are re-applied. Pass from_baseline=False
    to instead patch the live file in place (used by the debug single-field
    patch, which must not wipe the other already-applied effects)."""
    bak = Path(str(map_path) + '.bak')
    baseline = str(bak) if (from_baseline and backup and bak.exists()) else map_path
    m = open_map(baseline, game)
    results = []
    if weapon_swaps:
        # Scatter picked weapons through the map's placements. Runs BEFORE the ops so
        # each swapped weapon gets its VANILLA rounds (Magazine picks don't apply).
        results.extend(_apply_weapon_swaps(m, game, registry, weapon_swaps))
    for item in plan:
        cls, path = hm.split_tag(item['tag'])
        plugin = registry.get(cls)
        if item.get('init_defaults'):
            # Seed enemies that lack a field/block by default (e.g. Elite grenades)
            # BEFORE the normal ops, so those scale the freshly-set baseline.
            results.extend(_apply_init_defaults(m, item['init_defaults'], registry))
        for op in item.get('ops', []):
            base = {'effect': item['name'], 'tag': item['tag'], 'field': op['field']}
            if op.get('reload_anim'):
                # Halo 3 reload-speed: scale the first-person reload ANIMATION length
                # (these weapons carry no tag-side Reload Time). item['tag'] is the
                # jmad fp-graph pattern; the operator supplies the multiplier.
                parsed = hm.parse_operator(op.get('op_str'))
                if not parsed:
                    results.append({**base, 'ok': False, 'reason': 'blank/invalid operator'})
                    continue
                oper, val = parsed
                mult = hm.OP_FUNCS[oper](1.0, val)   # *0.5 or =0.5 -> 0.5
                import halo3_reload
                rep = halo3_reload.scale_reload(m, path, mult, game=game)
                r = {**base}
                if rep.get('ok'):
                    r.update(ok=True, skip=bool(rep.get('skip')),
                             old='reload anim', new=(rep.get('reason') if rep.get('skip')
                                  else f"x{mult:g} ({rep['animations']} anim, {rep['graphs']} graph)"))
                else:
                    r.update(ok=False, reason=rep.get('reason', 'reload scale failed'))
                results.append(r)
                continue
            if plugin is None:
                results.append({**base, 'ok': False, 'reason': f'no plugin for {cls}'})
                continue
            if op.get('derived'):
                # Auto-computed field: value = sum of the source fields' CURRENT
                # (post-edit) values, per tag. Ordered after the normal ops, so
                # edits to the sources are already in the in-memory image.
                results.extend(_apply_derived(m, cls, path, item['name'], op, plugin))
                continue
            if op.get('set') is not None:
                # Fixed set: force the field to a constant regardless of magnitude
                # (e.g. an enum enabler like Special-Fire Mode -> Overcharge). The
                # value may be an enum OPTION NAME, resolved via the plugin.
                field = apply_difficulty(op['field'], op, target_difficulty)
                fld = plugin.find(field, op.get('block'), op.get('nth', 0) or 0)
                sval = op['set']
                if isinstance(sval, str):
                    sval = (fld or {}).get('options', {}).get(sval.strip().lower())
                if sval is None:
                    results.append({**base, 'ok': False,
                                    'reason': f"unknown set value {op['set']!r}"})
                    continue
                for r in m.apply_field(cls, path, field, 'set', float(sval), plugin,
                                       block=op.get('block'), index=op.get('index', 0) or 0,
                                       nth=op.get('nth', 0) or 0):
                    r['effect'] = item['name']
                    results.append(r)
                continue
            parsed = hm.parse_operator(op.get('op_str'))
            if not parsed:
                results.append({**base, 'ok': False, 'reason': 'blank/invalid operator'})
                continue
            oper, val = parsed
            negate = bool(op.get('negate'))
            if negate:
                # H2 onward wants this value negative no matter what's typed (a
                # positive input here has been observed to do nothing useful, for
                # reasons that aren't clear from the tag data alone) -- force the
                # sign rather than just flipping it, so a negative input doesn't
                # silently flip back to positive.
                val = -abs(val)
            field = apply_difficulty(op['field'], op, target_difficulty)
            for r in m.apply_field(cls, path, field, oper, val, plugin,
                                   block=op.get('block'), index=op.get('index', 0) or 0,
                                   nth=op.get('nth', 0) or 0):
                r['effect'] = item['name']
                if negate:
                    r['negated'] = True
                results.append(r)

    if starting:
        # After the ops (so any Magazine effect is already in the weap tags),
        # set the player Starting Profile weapons + rounds from the run's picks.
        results.extend(_apply_starting_equipment(m, game, registry, starting))

    if zoom_ui:
        # Structural growth LAST: copy a donor scope overlay into each scopeless
        # target weapon's HUD tag. Done after every value op so the relocated HUD
        # block can't disturb them.
        results.extend(_apply_zoom_ui(m, game, zoom_ui, prefer_donor=zoom_donor))

    # Skulls are whole-map rules rather than tag edits, so they run last, after every
    # value op. Like the rest they start from the pristine baseline, so unpicking the
    # skull and re-patching restores the map.
    for skull in (skulls or ()):
        if str(skull).strip().lower() == 'betrayal':
            results.extend(_apply_betrayal(m, str(game).strip(), registry))

    if remove_cutscenes and str(game).strip() in THIRD_GEN_GAMES:
        # Halo 3 opt-in: neutralise the Cortana/Gravemind vision cutscenes on the map
        # (in-place HSC statement-skip). Runs from the pristine baseline like everything
        # else, so it's reversible by turning the option off and re-patching.
        import halo3_cutscene
        rep = halo3_cutscene.remove_cortana_flicker(m)
        r = {'tag': 'scnr', 'field': 'Cortana/Gravemind cutscenes',
             'effect': 'Remove Halo 3 cutscenes'}
        if rep.get('ok'):
            r.update(ok=True, skip=(rep['edits'] == 0),
                     old='present', new=f"removed ({rep['removed_exprs']} exprs)")
        elif rep.get('reason') == 'no cutscene recipe for this map':
            r.update(ok=True, skip=True, reason=rep['reason'])   # H3 map w/o cutscenes: N/A
        else:
            r.update(ok=False, reason=rep.get('reason', 'cutscene removal failed'))
        results.append(r)

    backup_path = None
    if any(r.get('ok') and not r.get('skip') for r in results):
        if backup:
            bp = Path(str(map_path) + '.bak')
            if not bp.exists():                     # keep the pristine original
                shutil.copy2(map_path, bp)
            backup_path = str(bp)
        m.save(map_path)
    return results, backup_path
