# halo_patch.py — glue between the roller's selected effects and halo_map.py.
# Collects the effects chosen during a run, resolves each to its Assembly plugin,
# and applies typed operators to the map with a per-insert success/failure report.
# No GUI dependency; safe to unit-test headless.

import base64
import hashlib
import json
import math
import os
import re
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


def collect_effects(rounds, mission_id=None, valid_bosses=None):
    """Unique patchable effects from a run's rounds, in first-seen order, each
    with a selection `count`, and a source `group`/`cat` (specific weapon,
    player-general, specific enemy, enemy-general, friend, boss, exhaust) for
    display. Exhausts are one-map negatives: an exhaust is only included when
    patching the mission it was rolled in (mission_id), so leaving that mission
    drops it automatically (paired with apply_run's idempotent re-patch).

    `valid_bosses` works the same way for bosses: pass the boss names the mission
    being patched can actually field, and effects for a boss that no longer turns up
    are left out instead of cluttering the list with edits that can't do anything.
    They come back on their own if a later mission fields that boss again. Omit it
    (None) to keep every boss — callers without the database in hand, such as the
    magnitude collector, shouldn't silently drop effects."""
    seen, order = {}, []

    def add(mod, group, cat):
        if not isinstance(mod, dict) or mod.get('_game_excluded'):
            return
        tag = mod.get('tag')
        if not tag:
            return
        # A tag may still be a per-GAME dict ({'Halo 1': ..., 'Halo 3': ...}) when the
        # caller hasn't resolved it for a specific game — the patcher resolves first,
        # but the save path collects straight off the raw run. A dict can't be a dict
        # key, so flatten it for identity only; the entry keeps the original value.
        key = (tag if isinstance(tag, str) else repr(sorted(tag.items())),
               mod.get('name'))
        if key not in seen:
            seen[key] = {'name': mod.get('name'), 'desc': mod.get('desc', ''),
                         'desc_overrides': mod.get('desc_overrides'),  # #7
                         'tag': tag, 'targets': list(mod.get('targets') or []),
                         'skull': mod.get('skull'),
                         'affected_by_skull': mod.get('affected_by_skull'),
                         'harder_when': mod.get('harder_when'),
                         'easier_when': mod.get('easier_when'),
                         'init_defaults': mod.get('init_defaults'),
                         '_missing_in_db': mod.get('_missing_in_db'),
                         # source identity, so the patcher can remove it from the run
                         'weapon': mod.get('weapon'), 'enemy': mod.get('enemy'),
                         'equipment': mod.get('equipment'),
                         'group': group, 'cat': cat, 'count': 0}
            order.append(key)
        seen[key]['count'] += 1

    for rd in rounds or []:
        for pk in ('player1', 'player2'):
            mod = (rd.get(pk) or {}).get('mod')
            if isinstance(mod, dict):
                src = mod.get('weapon') or mod.get('equipment')
                add(mod, src if src else 'Player (general)', 0 if src else 1)
        for k in ('enemy1', 'enemy2'):
            mod = rd.get(k)
            if isinstance(mod, dict):
                # An effect whose tag several enemies share edits all of them, so it
                # belongs under the general group even though it was drafted from one
                # enemy's card (flagged upstream, where the game is known).
                specific = mod.get('enemy') and not mod.get('_generic_target')
                add(mod, mod['enemy'] if specific else 'Enemy (general)',
                    2 if specific else 3)
        add(rd.get('wildcard'), 'Friend / Wildcard', 4)
        add(rd.get('wildcard2'), 'Friend / Wildcard', 4)   # player 2's wildcard slot
        for k in ('boss1', 'boss2'):
            b = rd.get(k)
            if isinstance(b, dict) and valid_bosses is not None:
                if b.get('boss') and b['boss'] not in valid_bosses:
                    continue        # that boss doesn't appear in this mission
            add(b, 'Boss', 5)
        for k in ('exhaust1', 'exhaust2'):
            ex = rd.get(k)
            if isinstance(ex, dict) and (mission_id is None
                                         or ex.get('_exhaust_mission') == mission_id):
                add(ex, 'Exhaust', 6)
    return [seen[k] for k in order]


# Bump when the MEANING of a written value changes, so codes from before and after
# don't compare equal and quietly suggest two players are in sync when they aren't.
SIGNATURE_VERSION = 1


def patch_signature(results, map_path=None, difficulty=None):
    """A short code identifying WHAT a patch wrote, for two players to compare.

    Built from the writes that actually landed — tag, field and the resulting value —
    not from the typed magnitudes, because the same magnitude on a different starting
    value produces different gameplay, and that is the disagreement worth catching.
    Sorted, so the order effects happen to be applied in can't change it, and rounded,
    so float noise can't either. The map and difficulty are folded in as well: the same
    edits on another level or difficulty are not the same patch.

    Codes are only comparable between the same tool version, since a change to how a
    value is computed SHOULD produce a different code — hence SIGNATURE_VERSION, bumped
    whenever the way values are computed changes."""
    lines = []
    for r in results or []:
        if not (r.get('ok') and not r.get('skip')):
            continue                       # skips/failures wrote nothing
        new = r.get('new')
        if isinstance(new, float):
            new = f"{new:.4f}"
        lines.append(f"{r.get('tag', '')}|{r.get('field', '')}|{new}")
    if not lines:
        return None
    head = f"{os.path.basename(str(map_path or ''))}|{difficulty or ''}|{SIGNATURE_VERSION}"
    blob = head + '\n' + '\n'.join(sorted(lines))
    digest = hashlib.sha256(blob.encode('utf-8')).digest()
    code = base64.b32encode(digest).decode('ascii').rstrip('=')[:8]
    return f"{code[:4]}-{code[4:8]}"


def _tag_variants(tag):
    """Every concrete tag string a mod's `tag` can stand for. A run holds effects
    UNRESOLVED, so the tag may still be a {game: tag} dict (see collect_effects)."""
    if isinstance(tag, str):
        return [tag]
    if isinstance(tag, dict):
        return [v for v in tag.values() if isinstance(v, str)]
    return []


def latest_round_keys(rounds, mission_id=None):
    """(tag, name) for every effect picked in the LAST round, so the patcher can
    highlight this round's picks — including ones drafted in an earlier round too,
    which carry no other visual cue and are otherwise hard to find in a long list.

    Built by running collect_effects over just that round, so it follows exactly the
    same slots (both players, enemies, wildcards, bosses, exhausts) automatically."""
    if not rounds:
        return set()
    keys = set()
    for e in collect_effects(rounds[-1:], mission_id):
        for tag in _tag_variants(e.get('tag')):
            keys.add((tag, e.get('name')))
    return keys


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


# "Eyepatch": zero every weapon's aim assist. Autoaim is the reticule's stickiness
# and Magnetism the pull that bends your aim onto a target; both exist in all three
# games (H3 additionally has the two Falloff Range fields). Deviation Angle is
# deliberately NOT included -- that's AI projectile scatter, not player aim assist.
_AIM_ASSIST_FIELDS = ('Autoaim Angle', 'Autoaim Range', 'Autoaim Falloff Range',
                      'Magnetism Angle', 'Magnetism Range', 'Magnetism Falloff Range')


def _apply_eyepatch(m, game, registry):
    """Zero the aim-assist fields on every weap tag in the map."""
    plugin = registry.get('weap')
    if plugin is None:
        return [{'effect': 'Eyepatch', 'ok': False, 'reason': 'no weap plugin'}]
    tags = m.find_tags('weap', '*')
    if not tags:
        return [{'effect': 'Eyepatch', 'ok': False, 'reason': 'no weapons in this map'}]
    zeroed, touched = 0, set()
    for field in _AIM_ASSIST_FIELDS:
        fld = plugin.find(field)
        if not fld or fld['block_chain']:        # not in this game's plugin
            continue
        fmt, _ = hm.TYPE_FMT[fld['type']]
        for name, base in tags:
            try:
                struct.pack_into(fmt, m.data, base + fld['offset'], 0)
            except Exception:
                continue
            zeroed += 1
            touched.add(name)
    if not zeroed:
        return [{'effect': 'Eyepatch', 'ok': False, 'reason': 'no aim-assist fields resolved'}]
    return [{'effect': 'Eyepatch', 'field': 'Aim assist (autoaim + magnetism)', 'ok': True,
             'old': 'as the map defines', 'tag': 'weap *',
             'new': f'zeroed on {len(touched)} weapon(s), {zeroed} field write(s)'}]


# Brute equipment loadout: char 'Equipment Definitions' (H3), elem 0x24 —
# Equipment tagRef @0x0 (ident at +0xC), Flags @0x10, Relative Drop Chance @0x14.
_EQUIP_DEFS = {'Halo 3': {'block': 0x1B0, 'elem': 0x24, 'id_at': 0xC, 'chance': 0x14}}
# Only Brutes carry equipment at all, so that's the whole search space.
_EQUIP_CARRIER_TAG = 'objects' + chr(92) + 'characters' + chr(92) + 'brute' + chr(92) + '*'


# scnr equipment placements + palette, per game (mirrors _MAP_WEAPONS). Equipment
# cards are Halo 3 only today, but the other two are laid out the same way.
_MAP_EQUIPMENT = {
    'Halo 1': {'items': (0x258, 0x28), 'palette': (0x264, 0x30), 'pal_id_at': 0xC,
               'palette_index': 0x0},
    'Halo 2': {'items': (0x80, 0x38), 'palette': (0x88, 0x28), 'pal_id_at': 0x4,
               'palette_index': 0x0},
    'Halo 3': {'items': (0xFC, 0x8C), 'palette': (0x108, 0x10), 'pal_id_at': 0xC,
               'palette_index': 0x0},
}


def map_equipment_placement_count(m, game):
    """How many equipment placements the level has — the denominator for an
    equipment replacement percentage."""
    lay = _MAP_EQUIPMENT.get(str(game).strip())
    scnr_base = _scnr_base(m)
    if not lay or scnr_base is None:
        return 0
    return max(0, m.i32(scnr_base + lay['items'][0]))


def _apply_equipment_swaps(m, game, swaps):
    """Replace a share of the level's EQUIPMENT placements, scattered evenly.
    `swaps` = {eqip-tag: rate 0..1}. Same idea as _apply_weapon_swaps, minus the
    ammo bookkeeping — equipment placements carry no rounds."""
    out = []
    lay = _MAP_EQUIPMENT.get(str(game).strip())
    scnr_base = _scnr_base(m)
    if not lay or scnr_base is None:
        return [{'effect': 'map equipment', 'ok': False, 'reason': 'scnr/layout unavailable'}]
    ioff, ies = lay['items']
    poff, pes = lay['palette']
    N = m.i32(scnr_base + ioff)
    if N <= 0:
        return [{'effect': 'map equipment', 'ok': False,
                 'reason': 'no equipment placements in this level'}]
    ibase = _block_base(m, scnr_base + ioff)
    pbase = _block_base(m, scnr_base + poff)
    pcount = m.i32(scnr_base + poff)
    pal = {i: _tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
           for i in range(pcount)}

    assign = []
    for tag, rate in (swaps or {}).items():
        if not rate or rate <= 0:
            continue
        _, name = hm.split_tag(tag)
        short = name.rsplit(chr(92), 1)[-1]
        pi = next((i for i, n in pal.items() if n == name), None)
        if pi is None:                       # SAFETY NET: not in this level's palette
            out.append({'effect': 'map equipment', 'field': short, 'ok': False,
                        'reason': "equipment not in this level's palette"})
            continue
        c = int(round(rate * N))
        if c <= 0:
            out.append({'effect': 'map equipment', 'field': short, 'ok': True,
                        'skip': True,
                        'reason': f'rate too low for {N} placements (rounds to 0)'})
            continue
        assign.append((pi, c, short))

    while sum(a[1] for a in assign) > N and assign:
        j = max(range(len(assign)), key=lambda k: assign[k][1])
        pi, c, s = assign[j]
        assign[j] = (pi, c - 1, s)

    # In Halo 3 a placement only renders where the swapped-in model streams, so confine
    # each piece to placements in a BSP where vanilla already puts it. H1/H2 have no
    # such per-zone streaming, so they spread across every slot as before.
    if str(game).strip() == 'Halo 3':
        slot_masks = [struct.unpack_from('<H', m.data, ibase + i * ies + _EQ_ATTACH)[0]
                      for i in range(N)]
        slots = _spread_slots_bsp(N, slot_masks,
                                  [(a[0], a[1], _h3_stream_mask(m, ioff, ies, a[0])) for a in assign])
    else:
        slots = _spread_slots(N, [(a[0], a[1]) for a in assign])
    names = {a[0]: a[2] for a in assign}
    done = {}
    for slot, pi in slots.items():
        struct.pack_into('<h', m.data, ibase + slot * ies + lay['palette_index'], pi)
        done[pi] = done.get(pi, 0) + 1
    for pi, n in done.items():
        out.append({'effect': 'map equipment', 'field': names[pi], 'ok': True,
                    'tag': 'scnr', 'old': f'{N} placements',
                    'new': f'{n} swapped in'})
    for pi, c, short in assign:                  # streaming left a piece nowhere to go
        if pi not in done:
            out.append({'effect': 'map equipment', 'field': short, 'ok': True, 'skip': True,
                        'reason': 'no free placement in a BSP where it streams'})
    return out


def equipment_drop_chances(m, game, eq_path):
    """[(brute short name, chance)] for one piece of equipment — the vanilla display
    for a drop-chance row, so the relative weights are visible before editing."""
    lay = _EQUIP_DEFS.get(str(game).strip())
    if not lay:
        return []
    out = []
    for name, base in m.find_tags('char', _EQUIP_CARRIER_TAG):
        for el in m.follow_all(base, [lay['block']], [lay['elem']], 'all'):
            rid = struct.unpack_from('<I', m.data, el + lay['id_at'])[0]
            if rid == 0xFFFFFFFF:
                continue
            nm = _tag_name_by_id(m, rid)
            if isinstance(nm, str) and nm == eq_path:
                out.append((name.rsplit(chr(92), 1)[-1],
                            round(struct.unpack_from('<f', m.data, el + lay['chance'])[0], 3)))
    return out


def _apply_equipment_drop(m, game, eq_path, oper, val):
    """Scale how often Brutes drop one piece of equipment.

    Relative Drop Chance is a WEIGHT within each character's own equipment list, not
    a probability — a Brute picks among its entries in proportion. So raising one
    entry shifts that Brute's odds toward it rather than guaranteeing a drop, and
    entries sitting at 0 stay at 0 under a multiply (they're deliberately disabled).
    """
    lay = _EQUIP_DEFS.get(str(game).strip())
    if not lay:
        return [{'effect': 'equipment drop', 'ok': False,
                 'reason': f'not supported in {game}'}]
    short = eq_path.rsplit(chr(92), 1)[-1]
    tags = m.find_tags('char', _EQUIP_CARRIER_TAG)
    if not tags:
        return [{'effect': 'equipment drop', 'field': short, 'ok': False,
                 'reason': 'no Brutes in this map'}]
    hits, changed = 0, 0
    for name, base in tags:
        for el in m.follow_all(base, [lay['block']], [lay['elem']], 'all'):
            rid = struct.unpack_from('<I', m.data, el + lay['id_at'])[0]
            if rid == 0xFFFFFFFF:
                continue
            nm = _tag_name_by_id(m, rid)
            if not isinstance(nm, str) or nm != eq_path:
                continue
            hits += 1
            old = struct.unpack_from('<f', m.data, el + lay['chance'])[0]
            new = max(0.0, hm.OP_FUNCS[oper](old, val))
            if abs(new - old) > 1e-9:
                struct.pack_into('<f', m.data, el + lay['chance'], new)
                changed += 1
    if not hits:
        return [{'effect': 'equipment drop', 'field': short, 'ok': False,
                 'reason': 'no Brute on this map carries it'}]
    return [{'effect': 'equipment drop', 'field': short, 'ok': True,
             'skip': changed == 0, 'tag': 'char brute*',
             'old': f'{hits} carrier entr{"y" if hits == 1 else "ies"}',
             'new': (f'{changed} changed' if changed
                     else 'all entries were 0 (equipment disabled on those Brutes)')}]


def _cstr_at(m, off, limit=0x20):
    return bytes(m.data[off:off + limit]).split(b'\0')[0].decode('latin1', 'replace')


# scnr weapon-placement + palette layout per game (Weapons list, Weapon Palette).
_MAP_WEAPONS = {
    'Halo 1': {'weapons': (0x270, 0x5C), 'palette': (0x27C, 0x30), 'pal_id_at': 0xC,
               'palette_index': 0x0, 'rounds_left': 0x48, 'rounds_loaded': 0x4A},
    'Halo 2': {'weapons': (0x90, 0x54), 'palette': (0x98, 0x28), 'pal_id_at': 0x4,
               'palette_index': 0x0, 'rounds_left': 0x4C, 'rounds_loaded': 0x4E},
    # Halo 3 was missing entirely, so map weapon swapping silently did nothing there
    # — the placement block just resolved to 0 entries. Palette elements are 16-byte
    # tagRefs (ident at +0xC) like the rest of H3.
    'Halo 3': {'weapons': (0x114, 0xA8), 'palette': (0x120, 0x10), 'pal_id_at': 0xC,
               'palette_index': 0x0, 'rounds_left': 0x6C, 'rounds_loaded': 0x6E},
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
    """File offset of a tagblock's element array. Each generation resolves its
    pointer differently: H1 subtracts the map magic, H2 exposes p2o(), and H3 stores
    realVA>>2 which data2off() unpacks."""
    ptr = m.u32(off + 4)
    if hasattr(m, 'data2off'):                       # Halo 3
        return m.data2off(ptr)
    if hasattr(m, 'p2o'):                            # Halo 2
        return m.p2o(ptr)
    return (ptr - m.magic) & 0xFFFFFFFF              # Halo 1


# --- Halo 3 starting equipment -------------------------------------------------
# H3 has no "Starting Equipment" profile field (Reach added one; in H3 that offset is
# the Editor Folder Index). What it can do is PLACE equipment, and an item sitting on
# a Player Starting Location is walked into the instant the level loads. Confirmed
# in-game on 020_base.
#
# A placement only appears if ALL of these hold:
#   Can Attach To BSP Flags @0x50 includes the BSP that loads there,
#   Placement Flags @0x4 has Not Automatically / Never Placed clear,
#   Editor Folder Index @0x42 is -1, or the scenario script's object_destroy_folder
#     calls delete it wherever it is,
#   Position @0x8 is exact — placed equipment never settles under gravity.
_H3_SPAWNS = (0x24C, 0x18)              # Player Starting Locations block
_H3_SPAWN_BSP, _H3_SPAWN_TYPE = 0x14, 0x16
_EQ_PALETTE, _EQ_NAME, _EQ_FLAGS, _EQ_POS = 0x0, 0x2, 0x4, 0x8
_EQ_NODES, _EQ_UID, _EQ_FOLDER, _EQ_ATTACH, _EQ_GAMEFLAGS = 0x24, 0x38, 0x42, 0x50, 0x5C
_PLACE_NOT_AUTO, _PLACE_NEVER = 1 << 0, 1 << 3


def h3_player_spawns(m):
    """The level's Player Starting Locations as [(position, bsp_index), ...].

    Deliberately index-based, NOT filtered by Campaign Player Type: every H3 map has
    exactly four, but seven maps label them {chief, dervish, 4, 4} while Tsavo
    Highway, Floodgate and Cortana label all four as type 0. Matching on type would
    silently place nothing for player 2 on those levels. Index 0 is the solo spawn."""
    scnr_base = _scnr_base(m)
    boff, esize = _H3_SPAWNS
    if scnr_base is None:
        return []
    base = _block_base(m, scnr_base + boff)
    if not base:
        return []
    out = []
    for i in range(max(0, m.i32(scnr_base + boff))):
        e = base + i * esize
        out.append((struct.unpack_from('<fff', m.data, e),
                    struct.unpack_from('<h', m.data, e + _H3_SPAWN_BSP)[0]))
    return out


def _h3_reserve(m, sizes):
    """Reserve one 16-byte-aligned region per entry in `sizes`, all inside a SINGLE
    partition zero-run, each mapping back to a tag pointer. Returns the list of file
    offsets, or None if no run fits them all.

    H3 stores tagblock pointers as realVA>>2 resolved through the partition table, so
    a block may only live where a partition maps it: appending at EOF is unusable, and
    the partition holding the scenario can't be extended because the tail tables sit
    immediately behind it. Relocating into an existing zero run is the way in. Every
    playable H3 map has 31-62 KB of such slack; only the intro and epilogue cinematics
    have none, and those carry no equipment at all. Placing several grown blocks in one
    run keeps them from clobbering each other."""
    total = 0
    for sz in sizes:
        total = ((total + 15) & ~15) + sz
    for la, psz, fb in m.partitions:
        if fb is None or not psz or fb + psz > len(m.data):
            continue
        for mo in re.finditer(rb'\x00{%d,}' % (total + 16), bytes(m.data[fb:fb + psz])):
            offs, cur, ok = [], fb + mo.start(), True
            for sz in sizes:
                cur = (cur + 15) & ~15
                if cur + sz > fb + mo.end() or m.off2data(cur) is None:
                    ok = False
                    break
                offs.append(cur)
                cur += sz
            if ok:
                return offs
    return None


def _h3_free_run(m, need):
    """Single-region convenience wrapper over _h3_reserve."""
    got = _h3_reserve(m, [need])
    return got[0] if got else None


def _h3_tag_datum(m, cls, path):
    """The tag datum (salt<<16)|row for a class+path present in the map, or None.

    A palette entry references a tag by this datum, so it's what we must write to add
    a piece the level doesn't currently stock — the tag itself is already loaded (the
    equipment models ship in the map), it just isn't in the scenario's palette."""
    io = m.index_header_off
    tbl = m.va2off(m.u64(io + 0x18))                    # tag table: 8 bytes/row
    want = str(path).replace('/', '\\').lower()
    for t in m.tags:
        if t.get('class') == cls and t.get('name') \
                and str(t['name']).replace('/', '\\').lower() == want:
            row = t['index']
            salt = struct.unpack_from('<H', m.data, tbl + row * 8 + 2)[0]
            return ((salt << 16) | (row & 0xFFFF)) & 0xFFFFFFFF
    return None


# Hand-picked drop points (world pos) for maps where the Player Starting Location is
# unusable — a cinematic/vehicle spot, or spawn-protected. Confirmed reachable in-game.
# Maps not listed drop on the player spawn. See the project memory on BSP/streaming.
_H3_LOADOUT_ANCHOR = {
    '020_base':    (-25.8, 44.4, -7.2),      # hallway by the armory racks
    '100_citadel': (-254.0, 215.2, -10.5),   # the on-foot start after the Pelican
    '120_halo':    (-269.6, -424.1, -10.0),  # just before the drop to the control centre
}

# (map -> equipment basenames) that do NOT stream at that map's start — their model
# resources are only loaded in a later zone, so a placement at the start renders
# nothing (baked in the PVS, unfixable). Such a piece is dropped instead on the nearest
# weapon in a BSP where it DOES stream. Confirmed in-game 2026-07-23.
_H3_NO_START_STREAM = {
    '040_voi':     frozenset({'gravlift_equipment'}),
    '070_waste':   frozenset({'autoturret_equipment'}),
    '100_citadel': frozenset({'autoturret_equipment'}),
}


def _h3_mask_at(m, pos):
    """Attach mask of the nearest vanilla weapon to `pos` — approximates which BSP is
    loaded there, so a placement dropped at pos attaches to the right BSP."""
    lay = _MAP_WEAPONS['Halo 3']
    wo, we = lay['weapons']
    scnr = _scnr_base(m)
    wN, wb = max(0, m.i32(scnr + wo)), _block_base(m, scnr + wo)
    best, bestd = 1, None
    for i in range(wN) if wb else []:
        e = wb + i * we
        att = struct.unpack_from('<H', m.data, e + _EQ_ATTACH)[0]
        if not att:
            continue
        wp = struct.unpack_from('<fff', m.data, e + _EQ_POS)
        dd = sum((a - b) ** 2 for a, b in zip(wp, pos))
        if bestd is None or dd < bestd:
            bestd, best = dd, att
    return best


def _h3_stream_mask(m, block_off, elem, pal_idx):
    """BSP mask where a palette entry is known to stream — the union of attach masks of
    every vanilla placement in the block at `block_off` (equipment or weapon) using it.
    A placement only renders where the model streams, i.e. where vanilla puts it."""
    scnr = _scnr_base(m)
    N, base = max(0, m.i32(scnr + block_off)), _block_base(m, scnr + block_off)
    mask = 0
    for i in range(N) if base else []:
        e = base + i * elem
        if struct.unpack_from('<h', m.data, e)[0] == pal_idx:   # palette index @0x0
            mask |= struct.unpack_from('<H', m.data, e + _EQ_ATTACH)[0]
    return mask


def _spread_slots_bsp(N, slot_masks, assign):
    """Like _spread_slots, but each key is confined to placements whose BSP mask
    (slot_masks[i]) overlaps the key's own stream mask, so a swapped-in piece only lands
    where its model streams. `assign` = [(key, count, stream_mask)]. Returns {slot: key}.
    A piece whose stream BSPs have too few free slots simply gets fewer than requested."""
    # Serve the most BSP-constrained pieces FIRST: one with few eligible slots must claim
    # them before a broad piece (which has alternatives) eats them, so each piece keeps
    # its fair share whenever the slots exist. Without this, a broad piece processed
    # first can starve a narrow one even when a fair split was possible.
    def eligible(smask):
        return N if not smask else sum(1 for mm in slot_masks if mm & smask)
    order = sorted(range(len(assign)), key=lambda j: eligible(assign[j][2]))

    taken = {}
    for j in order:
        key, c, smask = assign[j]
        if c <= 0:
            continue
        # smask == 0 means the piece has no vanilla placements to learn its streaming
        # from (e.g. an enemy-carried-only weapon) — don't restrict it, since it may
        # well stream via enemy loadouts we can't see. Otherwise confine to its BSPs.
        valid = [i for i in range(N)
                 if i not in taken and (not smask or (slot_masks[i] & smask))]
        if not valid:
            continue
        c = min(c, len(valid))
        for k in range(c):                       # evenly spaced, distinct for c<=len
            taken[valid[min(len(valid) - 1, int((k + 0.5) * len(valid) / c))]] = key
    return taken


def _h3_fallback_weapon(m, from_pos, equip_mask, used):
    """Nearest vanilla weapon placement (index not in `used`) whose attach mask overlaps
    equip_mask — i.e. a designer-placed floor spot in the first BSP zone where a piece
    that can't stream at the start DOES stream. Returns (index, pos, mask) or None."""
    lay = _MAP_WEAPONS['Halo 3']
    wo, we = lay['weapons']
    scnr = _scnr_base(m)
    wN, wb = max(0, m.i32(scnr + wo)), _block_base(m, scnr + wo)
    cands = []
    for i in range(wN) if wb else []:
        if i in used:
            continue
        e = wb + i * we
        att = struct.unpack_from('<H', m.data, e + _EQ_ATTACH)[0]
        if att & equip_mask:
            wp = struct.unpack_from('<fff', m.data, e + _EQ_POS)
            cands.append((sum((a - b) ** 2 for a, b in zip(wp, from_pos)), i, wp, att & equip_mask))
    if not cands:
        return None
    cands.sort(key=lambda c: c[0])
    _, i, wp, mask = cands[0]
    return i, wp, mask


def _apply_spawn_equipment(m, game, spec):
    """Grant Halo 3 starting equipment by APPENDING placements at the player start.

    `spec` = {'groups': [[eqip tag path, ...], ...]}. Group i is player i's items:
    group 0 -> player 1, group 1 -> player 2. With 2-player coop off the caller hands a
    single merged group. Each group drops at that player's start — the curated
    _H3_LOADOUT_ANCHOR where the spawn is unusable, else the Player Starting Location.

    A piece that does not stream at the start (_H3_NO_START_STREAM) can't render there,
    so it falls back to the nearest weapon in a BSP where it does stream; several such
    pieces spread across the nearest distinct weapons rather than stacking on one.

    Appending rather than reusing a vanilla placement is the point: relocating an
    existing one would delete that pickup from wherever the level put it."""
    out = []
    lay = _MAP_EQUIPMENT.get(str(game).strip())
    scnr_base = _scnr_base(m)
    groups = [[t for t in (g or []) if t] for g in (spec.get('groups') or [])]
    if str(game).strip() != 'Halo 3' or not lay or scnr_base is None or not any(groups):
        return out
    ioff, ies = lay['items']
    poff, pes = lay['palette']
    N = max(0, m.i32(scnr_base + ioff))
    base = _block_base(m, scnr_base + ioff)
    if not N or not base:
        return [{'effect': 'starting equipment', 'ok': False,
                 'reason': 'level has no equipment placements to extend'}]

    # A placement references the Equipment Palette by index. A piece the level never
    # uses isn't in the palette, but its tag IS loaded (the models ship in the map), so
    # we can append a palette entry pointing at it rather than giving up.
    pal = {}                        # tag path (lower) -> palette index
    pal_by_datum = {}               # tag datum -> palette index (name-independent)
    pc = max(0, m.i32(scnr_base + poff))
    pbase = _block_base(m, scnr_base + poff)
    for i in range(pc) if pbase else []:
        datum = m.u32(pbase + i * pes + lay['pal_id_at'])
        pal_by_datum.setdefault(datum, i)
        nm = _tag_name_by_id(m, datum)
        if isinstance(nm, str):
            pal[nm.replace('/', '\\').lower()] = i

    spawns = h3_player_spawns(m)
    if not spawns:
        return [{'effect': 'starting equipment', 'ok': False,
                 'reason': 'no player starting locations'}]

    map_id = str(getattr(m, 'internal_name', '') or '')
    anchor = _H3_LOADOUT_ANCHOR.get(map_id)
    skip = _H3_NO_START_STREAM.get(map_id, frozenset())
    anchor_mask = _h3_mask_at(m, anchor) if anchor else None

    def _resolve_pi(tag, key, label):
        """Palette index for a tag (appending an entry if needed), or (None, None) with
        a skip already emitted. Second value = whether a palette entry was appended."""
        pi = pal.get(key, new_pal_idx.get(key))
        if pi is not None:
            return pi, False
        datum = _h3_tag_datum(m, 'eqip', tag)
        if datum is None:
            out.append({'effect': 'starting equipment', 'field': label, 'ok': True,
                        'skip': True, 'reason': 'equipment not present in this level'})
            return None, None
        # duplicate guard: reuse an entry already present by datum (name-independent)
        if datum in pal_by_datum:
            new_pal_idx[key] = pal_by_datum[datum]
            return pal_by_datum[datum], False
        pi = pc + len(new_pal)
        new_pal.append(datum)
        new_pal_idx[key] = pi
        return pi, True

    plan = []                   # (pi, pos, mask, label, si, added, mode)
    new_pal = []                # datums to append to the palette, in assignment order
    new_pal_idx = {}            # path key -> the palette index it will get
    used_weapons = set()        # weapon placements already used as a fallback drop
    ring = {}                   # base-point key -> how many items dropped there so far
    for si, items in enumerate(groups):
        if not items:
            continue
        if not anchor and si >= len(spawns):
            # a non-error outcome (solo level, no player 2): report as a skip
            for tag in items:
                out.append({'effect': 'starting equipment',
                            'field': str(tag).rsplit('\\', 1)[-1], 'ok': True, 'skip': True,
                            'reason': f'no player starting location {si}'})
            continue
        base_pos = anchor if anchor else spawns[si][0]
        base_mask = anchor_mask if anchor else (1 << max(0, spawns[si][1]))
        bkey = 'anchor' if anchor else si
        for tag in items:
            key = str(tag).replace('/', '\\').lower()
            label = str(tag).rsplit('\\', 1)[-1]
            pi, added = _resolve_pi(tag, key, label)
            if pi is None:
                continue
            if label in skip:
                # can't stream at the start -> drop on the nearest weapon in a BSP where
                # it does; multiple such pieces spread over distinct weapons
                emask = _h3_stream_mask(m, ioff, ies, pi)
                fb = _h3_fallback_weapon(m, base_pos, emask, used_weapons) if emask else None
                if fb is None:
                    out.append({'effect': 'starting equipment', 'field': label, 'ok': True,
                                'skip': True, 'reason': "can't spawn at start, no fallback spot"})
                    continue
                used_weapons.add(fb[0])
                plan.append((pi, fb[1], fb[2], label, si, added, 'fallback'))
            else:
                # tight ring around the base point so multiple items don't interpenetrate
                kk = ring.get(bkey, 0)
                ring[bkey] = kk + 1
                ang = kk * 1.9
                p = (base_pos[0] + 0.8 * math.cos(ang), base_pos[1] + 0.8 * math.sin(ang), base_pos[2])
                plan.append((pi, p, base_mask, label, si, added, 'start'))
    if not plan:
        return out

    # A template placement that already spawns on its own, so new elements inherit
    # valid Type / Source / BSP Policy instead of guessed values.
    tmpl = next((i for i in range(N)
                 if not struct.unpack_from('<I', m.data, base + i * ies + _EQ_FLAGS)[0]
                 & (_PLACE_NOT_AUTO | _PLACE_NEVER)), None)
    if tmpl is None:
        return out + [{'effect': 'starting equipment', 'ok': False,
                       'reason': 'no auto-spawning placement to use as a template'}]

    # Reserve slack for both grown blocks in one run so neither clobbers the other.
    items_need = (N + len(plan)) * ies
    pal_need = (pc + len(new_pal)) * pes
    sizes = [items_need] + ([pal_need] if new_pal else [])
    got = _h3_reserve(m, sizes)
    if got is None:
        return out + [{'effect': 'starting equipment', 'ok': False,
                       'reason': f'no free run of {sum(sizes)} bytes to relocate blocks'}]
    dest = got[0]

    # --- grow the palette first (placements below reference its new indices) ---
    if new_pal:
        pdest = got[1]
        m.data[pdest:pdest + pc * pes] = m.data[pbase:pbase + pc * pes]
        pal_tmpl = m.data[pbase:pbase + pes]            # an eqip tagRef, for the group id
        for j, datum in enumerate(new_pal):
            pe_off = pdest + (pc + j) * pes
            m.data[pe_off:pe_off + pes] = pal_tmpl
            struct.pack_into('<I', m.data, pe_off + lay['pal_id_at'], datum)
        struct.pack_into('<i', m.data, scnr_base + poff, pc + len(new_pal))
        struct.pack_into('<I', m.data, scnr_base + poff + 4, m.off2data(pdest))

    # --- grow the placements ---
    m.data[dest:dest + N * ies] = m.data[base:base + N * ies]
    uids = [m.u32(base + i * ies + _EQ_UID) for i in range(N)]
    nxt = max(u & 0xFFFF for u in uids) + 1
    salt = uids[tmpl] >> 16

    for k, (pi, pos, mask, label, si, added, mode) in enumerate(plan):
        e = dest + (N + k) * ies
        m.data[e:e + ies] = m.data[base + tmpl * ies: base + (tmpl + 1) * ies]
        struct.pack_into('<h', m.data, e + _EQ_PALETTE, pi)
        struct.pack_into('<h', m.data, e + _EQ_NAME, -1)
        fl = struct.unpack_from('<I', m.data, e + _EQ_FLAGS)[0] & ~(_PLACE_NOT_AUTO | _PLACE_NEVER)
        struct.pack_into('<I', m.data, e + _EQ_FLAGS, fl)
        struct.pack_into('<fff', m.data, e + _EQ_POS, pos[0], pos[1], pos[2])
        struct.pack_into('<ii', m.data, e + _EQ_NODES, 0, 0)     # own no Node Orientations
        struct.pack_into('<I', m.data, e + _EQ_UID, ((salt << 16) | (nxt + k)) & 0xFFFFFFFF)
        struct.pack_into('<h', m.data, e + _EQ_FOLDER, -1)       # immune to object_destroy_folder
        struct.pack_into('<H', m.data, e + _EQ_ATTACH, mask)
        struct.pack_into('<H', m.data, e + _EQ_GAMEFLAGS, 0)     # campaign, not MP-only
        if mode == 'fallback':
            where = "at nearest weapon (can't stream at start)"
        elif anchor:
            where = 'at start anchor'
        else:
            where = f'on spawn {si}'
        out.append({'effect': 'starting equipment', 'field': label, 'ok': True,
                    'old': 'not present', 'new': where + (' (+palette)' if added else '')})

    # repoint the placements last, so the map stays consistent if anything above raised
    struct.pack_into('<i', m.data, scnr_base + ioff, N + len(plan))
    struct.pack_into('<I', m.data, scnr_base + ioff + 4, m.off2data(dest))
    return out


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


def map_weapon_placement_count(m, game):
    """How many weapon placements the level has — the denominator a Map Presence
    percentage applies to. 0 if the game has no known layout."""
    lay = _MAP_WEAPONS.get(str(game).strip())
    scnr_base = _scnr_base(m)
    if not lay or scnr_base is None:
        return 0
    return max(0, m.i32(scnr_base + lay['weapons'][0]))


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

    # NOTE: no BSP/streaming filter here (unlike _apply_equipment_swaps). Weapons are
    # carried by nearly every enemy and marine, so their models stream in essentially
    # every combat zone — i.e. everywhere weapon placements sit — and the streaming gate
    # never bites. Confining to placement BSPs would only under-place a common weapon
    # whose own placements happen to cluster in a few zones.
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


# --- Sprint (New Features / Experimental) ----------------------------------
# Tunes a map that was BUILT with the sprint mod (invisible weapon + the
# global_scripts sprint.hsc). All of it is field/byte edits, no rebuild:
#   speed%      matg Run/Sneak Forward, and every player-held weapon's Forward
#               Movement Penalty (the sprint weapon alone stays at 0, so holding
#               it = full speed). Normal movement is unchanged.
#   duration    sprint_ticks   short global   (seconds * 30)
#   cooldown    sprint_cooldown short global   (seconds * 30)
#   enabled     sprint_enabled  boolean global (the master gate)
# See halo1-sprint-from-scratch memory for the storage format.
_SPRINT_STOCK_RUN, _SPRINT_STOCK_SNEAK = 2.25, 0.9
_SPRINT_WEAP = 'weapons\\sprint\\sprint'
_SPRINT_AI_ONLY = ('weapons\\energy sword\\energy sword',
                   'weapons\\fuel rod gun\\hunter fuel rod')


def _sprint_player_held(name):
    """Weapons the player can carry on foot get the movement penalty. Vehicle
    guns and AI-only weapons must stay at 0 or they'd sprint permanently."""
    return not name.startswith('vehicles\\') and name not in _SPRINT_AI_ONLY


def set_global(m, name, value):
    """Patch a Halo 1 script-global's init value in a built map, by name, no
    rebuild. scnr Globals block (0x4A8, elem 0x5C): each global's Init Expression
    Index (@0x28) indexes the Script Syntax Data blob (dataref @0x474; 56-byte
    header, then 20-byte nodes). Value TYPE is int16 @node+0x04 (5=bool, 6=real,
    7=short, 8=long); the constant is at node+0x10 (bool=1 byte, short=int16,
    real=f32, long=i32). Returns (old, new) or None if the global is absent.

    Halo 2 keeps its globals somewhere else entirely, so those go through h2_tune."""
    if _is_h2_map(m):
        return _h2_global(m, name, value, write=True)
    scnr = next((k for k in m.tags if k[0] == 'scnr'), None)
    if scnr is None:
        return None
    meta = m.tags[scnr]
    syn = (m.u32(meta + 0x474 + 12) - m.magic) & 0xFFFFFFFF
    cnt = m.i32(meta + 0x4A8)
    ptr = (m.u32(meta + 0x4A8 + 4) - m.magic) & 0xFFFFFFFF
    for i in range(cnt):
        b = ptr + i * 0x5C
        if m._cstr(b) != name:
            continue
        node = m.u32(b + 0x28) & 0xFFFF
        nb = syn + 56 + node * 20
        vtype = struct.unpack_from('<h', m.data, nb + 0x04)[0]
        off = nb + 0x10
        if vtype == 5:                                   # boolean: 1 byte
            old = m.data[off]; m.data[off] = 1 if value else 0
            return old, m.data[off]
        if vtype == 6:                                   # real
            old = struct.unpack_from('<f', m.data, off)[0]
            struct.pack_into('<f', m.data, off, float(value)); return old, float(value)
        if vtype == 8:                                   # long
            old = struct.unpack_from('<i', m.data, off)[0]
            struct.pack_into('<i', m.data, off, int(value)); return old, int(value)
        old = struct.unpack_from('<h', m.data, off)[0]   # short (default)
        struct.pack_into('<h', m.data, off, int(value)); return old, int(value)
    return None


def read_global(m, name):
    """Read a script-global's init value by name. Same layout as set_global.
    Returns the value, or None if the global isn't in this map."""
    if _is_h2_map(m):
        return _h2_global(m, name)
    scnr = next((k for k in m.tags if k[0] == 'scnr'), None)
    if scnr is None:
        return None
    meta = m.tags[scnr]
    syn = (m.u32(meta + 0x474 + 12) - m.magic) & 0xFFFFFFFF
    cnt = m.i32(meta + 0x4A8)
    ptr = (m.u32(meta + 0x4A8 + 4) - m.magic) & 0xFFFFFFFF
    for i in range(cnt):
        b = ptr + i * 0x5C
        if m._cstr(b) != name:
            continue
        nb = syn + 56 + (m.u32(b + 0x28) & 0xFFFF) * 20
        vtype = struct.unpack_from('<h', m.data, nb + 0x04)[0]
        off = nb + 0x10
        if vtype == 5:
            return bool(m.data[off])
        if vtype == 6:
            return struct.unpack_from('<f', m.data, off)[0]
        if vtype == 8:
            return struct.unpack_from('<i', m.data, off)[0]
        return struct.unpack_from('<h', m.data, off)[0]
    return None


# Flashlight-key abilities, matching sprint.hsc's ability0/ability1 selector.
_ABILITY_IDS = {'none': 0, 'sprint': 1, 'overshield': 2, 'camo': 3, 'regeneration': 4}

# Camo's duration is not a script global: it's the Powerup Time on the camo equipment
# tag (stock 45s), mirrored into the script's camo window. Cooldown is separate and
# starts when that window ends, so a full cycle is duration + cooldown.
_CAMO_TAG = 'powerups\\active camouflage'
_CAMO_SECONDS = 5.0
_CAMO_COOLDOWN_TICKS = 900      # 30s

# --- per game ------------------------------------------------------------------
# The two games' ability scripts were written years apart and do NOT share names or
# shape. Halo 1 selects an ability PER PLAYER (ability0/ability1) and gives each its own
# cooldown; Halo 2 runs one ability for both players (ab_kind) behind a single
# ab_cooldown, and has no separate overshield duration. Only vit_max, medi_rate,
# medi_ticks, sprint_ticks, camo_ticks and the fx_* set are spelled the same.
_SPRINT_WEAP_BY_GAME = {
    'Halo 1': _SPRINT_WEAP,
    # H2 already shipped an invisible token -- the weapon melee-only characters carry.
    'Halo 2': 'objects\\weapons\\melee\\unarmed\\unarmed',
}
_CAMO_TAG_BY_GAME = {
    'Halo 1': _CAMO_TAG,
    'Halo 2': 'objects\\powerups\\active_camouflage\\active_camouflage',
}
# Halo 1 global name -> the Halo 2 script's name, or None where H2 has no counterpart
# and the write is simply dropped.
#
# Nearly identity now: the per-player rewrite (h2_genscript.py) put the H2 script on H1
# naming, so ability0/ability1, os_shield, os_ticks and the four separate cooldowns all
# exist under their H1 names. Only the two H1 bookkeeping globals have no H2 twin.
#
# Maps built BEFORE that rewrite still carry the old shared names (ab_kind, ab_shield,
# ab_cooldown). They are handled in _apply_sprint by falling back to ab_kind rather than
# by aliasing here, so a stale deployed map keeps working and just runs one ability for
# both players.
_GLOBAL_ALIASES_H2 = {
    'medi_heal': None,      # H2 heals purely from medi_rate
    'os_body': None,        # H1-only, and unused there too
}


def _is_h2_map(m):
    """Halo 2 maps get the second-gen parser, which is also how the script globals are
    laid out differently -- see _h2_global()."""
    return type(m).__name__ == 'Halo2Map'


def _h2_tune():
    """Imported lazily: h2_tune imports THIS module, so a top-level import would be
    circular."""
    import importlib
    import sys as _sys
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sprint_toolkit')
    if here not in _sys.path:
        _sys.path.insert(0, here)
    return importlib.import_module('h2_tune')


def _h2_global(m, name, value=None, write=False):
    """Read or write a Halo 2 script global, going through h2_tune so the second-gen
    layout lives in exactly one place (globals at scnr+0x1C0 elem 0x28, and the syntax
    node table at scnr+0x23C -- NOT the 0x1A8 the Assembly plugin lists)."""
    name = _GLOBAL_ALIASES_H2.get(name, name)
    if name is None:
        return None
    t = _h2_tune()
    if t.read_global(m, name) is None:
        return None
    if not write:
        return t.read_global(m, name)
    old = t.read_global(m, name)
    return old, t.write_global(m, name, value)

# The engine's absolute vitality scale, measured in-game: a full body/shield is 75
# units. object_set_shield's argument is in 1/75 units (so x3 overshield = 3/75), and
# regeneration's per-tick write-back must scale the [0,1] getters by exactly this.
_VIT_MAX = 75.0
_OS_SHIELD_BASE = 1.0 / _VIT_MAX

# ...but only in Halo 1. Measured the same way in Halo 2 (no health bar there, so the
# SHIELD is the instrument: x1/x2/x3 came out at 0.01425/0.0285/0.04275, i.e. 1/70) the
# scale is 70. Close enough to 75 to look plausible and wrong enough to drift, so
# nothing measured in one game may be assumed to carry to the other.
_VIT_MAX_BY_GAME = {'Halo 1': 75.0, 'Halo 2': 70.0}

# Regeneration plays a pulsing effect so the ability is legible -- essential in H2,
# which shows no health at all, and clearer than a creeping bar in H1. The effect ids
# are per game (different tag sets entirely) and were picked by testing every
# candidate in-game; see the tables in sprint.hsc / global_scripts.hsc. Only
# self-contained effects show on a player: impact/contact and weapon effects resolve
# against a surface or their own markers and silently draw nothing.
# 'kind'/'every' drive the regeneration pulse; 'ready' is the burst fired when a
# cooldown expires, which is a different shape of cue and wanted a different effect in
# both games. All four ids were chosen by walking candidate ladders in-game.
_FX_BY_GAME = {
    'Halo 1': {'kind': 5, 'every': 10,      # cyborg shield depletion
               'ready': 30, 'ready_n': 3, 'ready_gap': 5},    # jackal shield depletion
    'Halo 2': {'kind': 8, 'every': 45,      # regret teleport
               'ready': 2, 'ready_n': 3, 'ready_gap': 10},    # elite shield recharge
}


def _vit_max(game):
    return _VIT_MAX_BY_GAME.get(str(game).strip(), _VIT_MAX)


def _sprint_null_ref(m, base, roff):
    struct.pack_into('<I', m.data, base + roff + 0, 0xFFFFFFFF)
    struct.pack_into('<I', m.data, base + roff + 12, 0xFFFFFFFF)


def _apply_sprint(m, game, registry, cfg):
    """Tune the pre-built ability mod (flashlight-key abilities, one per player).

    cfg keys, all optional:
      player_abilities  {0: name, 1: name} where name is none/sprint/overshield/
                        regeneration. Falls back to enabled_players/enabled, which
                        mean sprint, so older callers keep working.
      sprint            speed_pct, duration_ticks, cooldown_ticks
      overshield        os_mult, os_duration_ticks, os_cooldown_ticks
      regeneration      medi_percent, medi_duration_ticks, medi_cooldown_ticks

    No-op with a reported skip if the map wasn't built with the toolkit."""
    ref = {'effect': 'Abilities', 'tag': 'matg globals\\globals', 'field': 'ability'}
    gname = str(game).strip()
    is_h2 = _is_h2_map(m)
    # Guard: the map must actually carry the mod. Checked BEFORE any write so a plain
    # map is never touched. Halo 1 is identified by its purpose-built sprint weapon;
    # Halo 2 reuses the stock `unarmed` token, which every map has, so the ability
    # SCRIPT is the tell there instead.
    if is_h2:
        # `ability0` is the current per-player script; `ab_kind` is the older shared one,
        # still accepted so a map deployed before the rewrite keeps working.
        if read_global(m, 'ability0') is None and read_global(m, 'ab_kind') is None:
            return [{**ref, 'ok': True, 'skip': True,
                     'reason': 'no ability script on this map (not built with the mod)'}]
    elif not m.find_tags('weap', _SPRINT_WEAP_BY_GAME.get(gname, _SPRINT_WEAP)):
        return [{**ref, 'ok': True, 'skip': True,
                 'reason': 'no sprint weapon on this map (not built with the mod)'}]
    # Per-player ability. `player_abilities` is authoritative; otherwise fall back to
    # the older enabled_players/enabled (a bool set meaning "sprint").
    pa = cfg.get('player_abilities')
    if pa is None:
        ep = cfg.get('enabled_players')
        if ep is None:
            ep = {0, 1} if cfg.get('enabled') else set()
        pa = {p: ('sprint' if p in set(ep) else 'none') for p in (0, 1)}
    pa = {int(p): (n or 'none') for p, n in pa.items()}
    active = {n for n in pa.values() if n != 'none'}

    # Deployed maps span several script generations, so check that this map's script
    # actually carries what each requested ability needs BEFORE writing anything --
    # enabling regeneration on a map built before vit_max existed would silently
    # ratchet health and shield to full.
    needs = {'regeneration': ('medi_rate', 'vit_max'), 'overshield': ('os_shield',),
             'camo': ('camo_ticks',)}
    camo_tag = _CAMO_TAG_BY_GAME.get(gname, _CAMO_TAG)
    if 'camo' in active and not m.find_tags('eqip', camo_tag):
        return [{**ref, 'ok': True, 'skip': True,
                 'reason': 'camo needs a map built with the camo pickup '
                           '(rebuild with the current toolkit)'}]
    for name in sorted(active):
        missing = [g for g in needs.get(name, ()) if read_global(m, g) is None]
        if missing:
            return [{**ref, 'ok': True, 'skip': True,
                     'reason': '%s needs a map built with the current toolkit '
                               '(missing %s)' % (name, ', '.join(missing))}]

    # Maps built with the multi-ability script carry ability0/ability1 -- BOTH games now.
    # A pre-rebuild map only knows sprint, gated by sprint_enabled0/1 (or one shared
    # sprint_enabled).
    #
    # Halo 2 used to run ONE ability for both players, because the script API has no
    # per-player input: H1 discriminates with unit_get_current_flashlight_state <unit>,
    # and H2 has no such verb -- every player_action_test_* takes no argument. That is
    # lifted by the `p2-vision-trigger` halo2.dll patch, which repoints the unused
    # unit_get_enterable_by_player at player 2's slot of the action bitfield (see
    # sprint_toolkit/h2_dll_patch.py). Maps rebuilt since then carry ability0/ability1
    # like H1; maps deployed before it still carry ab_kind and fall back below.
    chosen = None
    wrote = False
    for p in (0, 1):
        if set_global(m, 'ability%d' % p,
                      _ABILITY_IDS.get(pa.get(p, 'none'), 0)) is not None:
            wrote = True
    if not wrote and is_h2 and read_global(m, 'ab_kind') is not None:
        # Legacy shared-ability map: player 1's pick wins, and player 2's is reported as
        # ignored rather than silently dropped.
        chosen = pa.get(0, 'none')
        if chosen == 'none':
            chosen = pa.get(1, 'none')
        set_global(m, 'ab_kind', _ABILITY_IDS.get(chosen, 0))
        wrote = True
    if not wrote:
        s0 = 1 if pa.get(0) == 'sprint' else 0
        s1 = 1 if pa.get(1) == 'sprint' else 0
        r0 = set_global(m, 'sprint_enabled0', s0)
        r1 = set_global(m, 'sprint_enabled1', s1)
        if r0 is None and r1 is None:
            if set_global(m, 'sprint_enabled', 1 if (s0 or s1) else 0) is None:
                return [{**ref, 'ok': True, 'skip': True,
                         'reason': 'ability script globals missing '
                                   '(map not built with the mod)'}]
        if active - {'sprint'}:
            return [{**ref, 'ok': True, 'skip': True,
                     'reason': 'map predates the powerup abilities -- rebuild it to use '
                               '%s' % ', '.join(sorted(active - {'sprint'}))}]

    # --- tuning, written whenever supplied so a card can tune a shared value --------
    # Regeneration heals a fixed amount PER TICK; the division is done here because
    # dividing by a short global inside HaloScript misbehaved.
    if cfg.get('medi_duration_ticks') is not None:
        set_global(m, 'medi_ticks', max(1, int(cfg['medi_duration_ticks'])))
    if cfg.get('medi_cooldown_ticks') is not None:
        set_global(m, 'medi_cooldown', max(0, int(cfg['medi_cooldown_ticks'])))
    if cfg.get('medi_percent') is not None:
        heal = float(cfg['medi_percent']) / 100.0 * _vit_max(game)
        ticks = cfg.get('medi_duration_ticks') or read_global(m, 'medi_ticks') or 150
        set_global(m, 'medi_heal', heal)
        set_global(m, 'medi_rate', heal / float(max(1, int(ticks))))
    # The write-back scale has to match the unit's true max or regeneration ratchets.
    set_global(m, 'vit_max', _vit_max(game))

    # Regeneration pulse. Rate is user-facing (per game); the effect id falls back to
    # the tested default. Written only when the globals exist, so maps built before the
    # pulse was added still patch cleanly.
    fx = _FX_BY_GAME.get(str(game).strip(), _FX_BY_GAME['Halo 1'])
    if read_global(m, 'fx_every') is not None:
        per_game = cfg.get('regen_fx_every_by_game') or {}
        every = per_game.get(str(game).strip()) or cfg.get('regen_fx_every') or fx['every']
        set_global(m, 'fx_every', max(1, int(every)))
        set_global(m, 'fx_kind', int(cfg.get('regen_fx_kind') or fx['kind']))
        # The ready cue is pointless when the ability returns before it finishes, so
        # suppress it rather than firing into the middle of the effect.
        dur = int(cfg.get('medi_duration_ticks') or read_global(m, 'medi_ticks') or 150)
        cool = int(cfg.get('medi_cooldown_ticks') or read_global(m, 'medi_cooldown') or 0)
        if read_global(m, 'fx_ready') is not None:
            set_global(m, 'fx_ready', fx['ready'] if cool > dur else 0)
            set_global(m, 'fx_ready_n', fx['ready_n'])
            set_global(m, 'fx_ready_gap', fx['ready_gap'])

    # Camo: the real duration is the equipment tag's Powerup Time, mirrored into the
    # script window. Only written when camo is actually in play -- the tag is shared
    # with any stock camo pickups in the level, so an unused ability must not touch it.
    # Gated on camo actually being in play, never on the cfg merely carrying a value:
    # callers pass their defaults every time, and Powerup Time is a VANILLA tag shared
    # with any stock camo pickups in the level.
    if 'camo' in active:
        secs = float(cfg.get('camo_seconds') or _CAMO_SECONDS)
        eq = registry.get('eqip')
        if eq is not None and m.find_tags('eqip', camo_tag):
            m.apply_field('eqip', camo_tag, 'Powerup Time', 'set', secs, eq)
        set_global(m, 'camo_ticks', max(1, int(cfg.get('camo_duration_ticks')
                                               or round(secs * 30))))
        set_global(m, 'camo_cooldown',
                   max(0, int(cfg.get('camo_cooldown_ticks', _CAMO_COOLDOWN_TICKS))))

    if cfg.get('os_mult') is not None:
        set_global(m, 'os_shield', float(cfg['os_mult']) * _OS_SHIELD_BASE)
    if cfg.get('os_duration_ticks') is not None:
        set_global(m, 'os_ticks', max(1, int(cfg['os_duration_ticks'])))
    if cfg.get('os_cooldown_ticks') is not None:
        set_global(m, 'os_cooldown', max(0, int(cfg['os_cooldown_ticks'])))

    set_global(m, 'sprint_ticks', int(cfg.get('duration_ticks', 90)))
    set_global(m, 'sprint_cooldown', int(cfg.get('cooldown_ticks', 60)))

    # A LEGACY H2 map has a single ab_cooldown rather than one per ability, and every
    # *_cooldown above aliases onto it -- so whichever was written last would win by
    # accident. Write the ACTIVE ability's cooldown here, after them all, so it wins on
    # purpose. Rebuilt maps carry the four separate cooldowns and skip this.
    if chosen and chosen != 'none':
        cool = {'sprint': cfg.get('cooldown_ticks', 60),
                'overshield': cfg.get('os_cooldown_ticks'),
                'regeneration': cfg.get('medi_cooldown_ticks'),
                'camo': cfg.get('camo_cooldown_ticks', _CAMO_COOLDOWN_TICKS)}.get(chosen)
        if cool is not None:
            set_global(m, 'ab_cooldown', max(0, int(cool)))

    results = []
    if not active:
        # Nothing enabled: close the gates and leave the map at its vanilla baseline
        # speed (apply_run patches from the .bak baseline, so no speed edits = vanilla).
        results.append({**ref, 'ok': True, 'old': 'ability', 'new': 'off'})
    elif chosen:
        # LEGACY H2 map, built before the per-player rewrite: one selector for both
        # players, so report what actually happens rather than echoing a per-player
        # choice this map cannot honour.
        results.append({**ref, 'effect': chosen.capitalize(), 'ok': True,
                        'old': 'ability', 'new': '%s on both players' % chosen})
        other = [pa.get(p, 'none') for p in (0, 1) if pa.get(p, 'none') not in ('none', chosen)]
        if other:
            results.append({**ref, 'ok': True, 'skip': True,
                            'reason': 'this Halo 2 map predates per-player abilities, so '
                                      'one runs for both players -- %s was not applied '
                                      '(rebuild it to use both)'
                                      % ', '.join(sorted(set(other)))})
    else:
        for p in (0, 1):
            if pa.get(p, 'none') == 'none':
                continue
            results.append({**ref, 'effect': pa[p].capitalize(),
                            'ok': True, 'old': 'ability',
                            'new': '%s on P%d' % (pa[p], p + 1)})
    # The sprint SPEED mechanic is sprint-only: raising global run speed and penalising
    # every real weapon back down. Powerups must leave the baseline alone, so if nobody
    # has sprint we simply don't write it.
    if 'sprint' not in active:
        for cr in cfg.get('card_reports') or []:
            results.append({'ok': True, 'tag': cr.get('tag') or ref['tag'],
                            'effect': cr.get('effect', 'Ability'), 'field': cr.get('field', ''),
                            'old': cr.get('old'), 'new': cr.get('new')})
        return results

    mg, wp = registry.get('matg'), registry.get('weap')
    if mg is None or wp is None:
        return [{**ref, 'ok': False, 'reason': 'matg/weap plugin missing'}]

    mult = max(1.0, cfg.get('speed_pct', 150) / 100.0)
    penalty = 1.0 - (1.0 / mult) if mult > 1.0 else 0.0
    # Global run/sneak speed = sprint speed; a held real weapon penalises back to normal.
    mg_ref = ('matg', 'globals\\globals')
    m.apply_field(*mg_ref, 'Run Forward', 'set', _SPRINT_STOCK_RUN * mult, mg,
                  block='Player Information')
    m.apply_field(*mg_ref, 'Sneak Forward', 'set', _SPRINT_STOCK_SNEAK * mult, mg,
                  block='Player Information')
    for name, _ in m.read_all('weap', '*', 'Forward Movement Penalty', wp):
        if not _sprint_player_held(name):
            continue
        val = 0.0 if name == _SPRINT_WEAP else penalty
        m.apply_field('weap', name, 'Forward Movement Penalty', 'set', val, wp)
    # Sprint weapon: no fast strafing, and empty first person (null the flag FP refs).
    if m.find_tags('weap', _SPRINT_WEAP):
        m.apply_field('weap', _SPRINT_WEAP, 'Sideways Movement Penalty', 'set', 0.5, wp)
        wbase = m.find_tags('weap', _SPRINT_WEAP)[0][1]
        _sprint_null_ref(m, wbase, 0x45C)    # First Person Model
        _sprint_null_ref(m, wbase, 0x46C)    # First Person Animations
    sp = {p for p, n in pa.items() if n == 'sprint'}
    who = 'P1+P2' if sp == {0, 1} else ('P1' if sp == {0} else ('P2' if sp == {1} else '-'))
    state = 'on %s %d%%, %.1fs / %.1fs cd' % (
        who, cfg.get('speed_pct', 150), cfg.get('duration_ticks', 90) / 30.0,
        cfg.get('cooldown_ticks', 60) / 30.0)
    results = [r for r in results if r.get('effect') != 'Sprint']
    results.append({**ref, 'effect': 'Sprint', 'ok': True, 'old': 'sprint', 'new': state})
    # Each drafted tuning card (Speed/Duration/Cooldown) reports its own before→new
    # step, so it reads like a normal field edit in the summary instead of a skip.
    for cr in cfg.get('card_reports') or []:
        results.append({'ok': True, 'tag': cr.get('tag') or ref['tag'],
                        'effect': cr.get('effect', 'Sprint'), 'field': cr.get('field', ''),
                        'old': cr.get('old'), 'new': cr.get('new')})
    return results


def apply_run(map_path, plan, registry, target_difficulty, backup=True, game=None,
              starting=None, weapon_swaps=None, zoom_ui=None, zoom_donor=None,
              from_baseline=True, remove_cutscenes=False, skulls=(),
              equipment_swaps=None, spawn_equipment=None, sprint=None):
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
    if equipment_swaps:
        # Same placement-scatter idea, on the equipment block.
        results.extend(_apply_equipment_swaps(m, str(game).strip(), equipment_swaps))
    # Skulls are whole-map rules, applied BEFORE the per-field ops. Order matters for
    # any skull that zeroes a field a normal effect also touches (Eyepatch vs an
    # aim-assist buff): running the skull first leaves the effect something to act on,
    # whereas running it last would flatten the effect's result to the skull's value.
    for skull in (skulls or ()):
        s = str(skull).strip().lower()
        if s == 'betrayal':
            results.extend(_apply_betrayal(m, str(game).strip(), registry))
        elif s == 'eyepatch':
            results.extend(_apply_eyepatch(m, str(game).strip(), registry))
    for item in plan:
        if item.get('missing_in_db'):
            # The effect was removed or renamed out of halo.json since this run was
            # drafted, so all we hold is the frozen snapshot taken when it was picked.
            # Its tag/fields may no longer mean what they did — patching from stale
            # data is worse than not patching, so report it as skipped and move on.
            results.append({'effect': item['name'], 'tag': item['tag'], 'field': '',
                            'ok': True, 'skip': True,
                            'reason': 'no longer in halo.json — skipped '
                                      '(remove it from the run, or re-add the effect)'})
            continue
        cls, path = hm.split_tag(item['tag'])
        plugin = registry.get(cls)
        if item.get('init_defaults'):
            # Seed enemies that lack a field/block by default (e.g. Elite grenades)
            # BEFORE the normal ops, so those scale the freshly-set baseline.
            results.extend(_apply_init_defaults(m, item['init_defaults'], registry))
        for op in item.get('ops', []):
            base = {'effect': item['name'], 'tag': item['tag'], 'field': op['field']}
            if op.get('equip_drop'):
                # Brute equipment loadout: the element to edit is picked by which
                # equipment its tagRef points at, which no index/block target can
                # express — hence a dedicated op rather than a plugin field write.
                parsed = hm.parse_operator(op.get('op_str'))
                if not parsed:
                    results.append({**base, 'ok': False, 'reason': 'blank/invalid operator'})
                    continue
                oper, val = parsed
                for r in _apply_equipment_drop(m, str(game).strip(), op['equip_drop'], oper, val):
                    r['effect'] = item['name']
                    results.append(r)
                continue
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
            # `negate`/`offset` describe how this game STORES the setting relative to
            # what the magnitude means: meaning = scale * stored + offset. H1 keeps a
            # modifier that is 1 when normal and rises; H2 keeps a damage that is 0
            # when normal and falls, i.e. meaning = -stored + 1. Expressing it as a
            # mapping (rather than flipping the typed number, which only ever worked
            # for + and -) is what makes '*' and '=' agree across the two games: on
            # the base-0 field, '*2' used to multiply 0 and change nothing.
            negate = bool(op.get('negate'))
            scale = -1.0 if negate else 1.0
            offset = float(op.get('offset') or 0.0)
            field = apply_difficulty(op['field'], op, target_difficulty)
            for r in m.apply_field(cls, path, field, oper, val, plugin,
                                   block=op.get('block'), index=op.get('index', 0) or 0,
                                   nth=op.get('nth', 0) or 0,
                                   scale=scale, offset=offset):
                r['effect'] = item['name']
                if negate or offset:
                    r['negated'] = True     # summary marks the remapped write
                results.append(r)

    if starting:
        # After the ops (so any Magazine effect is already in the weap tags),
        # set the player Starting Profile weapons + rounds from the run's picks.
        results.extend(_apply_starting_equipment(m, game, registry, starting))

    if spawn_equipment:
        # Halo 3 starting equipment. Structural (it grows the Equipment block by
        # relocating it), so it runs after every value op — but before the zoom UI,
        # which relocates HUD blocks and would otherwise compete for the same slack.
        results.extend(_apply_spawn_equipment(m, game, spawn_equipment))

    if zoom_ui:
        # Structural growth LAST: copy a donor scope overlay into each scopeless
        # target weapon's HUD tag. Done after every value op so the relocated HUD
        # block can't disturb them.
        results.extend(_apply_zoom_ui(m, game, zoom_ui, prefer_donor=zoom_donor))

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

    if sprint:
        # Sprint tuning (speed + duration/cooldown/enable). Whole-map, value-only,
        # so order among the structural passes doesn't matter — do it last.
        results.extend(_apply_sprint(m, game, registry, sprint))

    backup_path = None
    if any(r.get('ok') and not r.get('skip') for r in results):
        if backup:
            bp = Path(str(map_path) + '.bak')
            if not bp.exists():                     # keep the pristine original
                shutil.copy2(map_path, bp)
            backup_path = str(bp)
        m.save(map_path)
    return results, backup_path
